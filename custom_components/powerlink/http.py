"""Authenticated PowerLink application-to-Home-Assistant session exchange.

Fire TV only sends a full snapshot when a transfer is requested. The hub
resolves Plex variants lazily per window, keeping extra device CPU near zero.
"""

from __future__ import annotations

import json
import logging

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.exceptions import ServiceValidationError

from .const import DOMAIN, MAX_SNAPSHOT_BYTES
from .hub import PowerLinkHub
from .models import InvalidSnapshot

_LOGGER = logging.getLogger(__name__)


def _get_hub(request: web.Request) -> PowerLinkHub:
    hass = request.app["hass"]
    data = hass.data.get(DOMAIN, {})
    for value in data.values():
        if isinstance(value, PowerLinkHub):
            return value
    raise web.HTTPServiceUnavailable(text="PowerLink is not configured")


def _authenticate(request: web.Request) -> tuple[PowerLinkHub, str]:
    hub = _get_hub(request)
    device = request.headers.get("X-PowerLink-Device")
    header = request.headers.get("Authorization", "")
    token = header[7:] if header.startswith("Bearer ") else None
    if not hub.authenticated(device, token):
        raise web.HTTPUnauthorized(text="PowerLink device not paired")
    assert device is not None
    return hub, device


class PowerLinkSessionView(HomeAssistantView):
    """Receive a bounded complete queue snapshot from the source app."""

    url = "/api/powerlink/v1/sessions"
    name = "api:powerlink:sessions"
    requires_auth = False  # Explicit per-device bearer auth instead of HA account credentials.

    async def post(self, request: web.Request) -> web.Response:
        hub, device_id = _authenticate(request)
        if request.content_length and request.content_length > MAX_SNAPSHOT_BYTES:
            raise web.HTTPRequestEntityTooLarge(
                max_size=MAX_SNAPSHOT_BYTES, actual_size=request.content_length
            )
        body = await request.content.read(MAX_SNAPSHOT_BYTES + 1)
        if len(body) > MAX_SNAPSHOT_BYTES:
            raise web.HTTPRequestEntityTooLarge(
                max_size=MAX_SNAPSHOT_BYTES, actual_size=len(body)
            )
        try:
            data = json.loads(body)
            snapshot = hub.publish_snapshot(device_id, data)
        except (ValueError, TypeError, InvalidSnapshot, ServiceValidationError) as exc:
            raise web.HTTPBadRequest(text=str(exc)) from exc
        request.app["hass"].bus.async_fire(
            "powerlink_snapshot_received", {
                "device_id": device_id,
                "queue_length": len(snapshot.items),
                "shuffled": snapshot.shuffled,
            },
        )
        return self.json({
            "accepted": True, "protocol": 1,
            "queue_length": len(snapshot.items),
            "selected_index": snapshot.index,
        })


class PowerLinkTransferView(HomeAssistantView):
    """Serve destination-resolved immutable queue windows, 50 entries at most."""

    url = r"/api/powerlink/v1/transfers/{transfer_id}"
    name = "api:powerlink:transfer"
    requires_auth = False

    async def get(self, request: web.Request, transfer_id: str) -> web.Response:
        hub, device_id = _authenticate(request)
        try:
            start = int(request.query.get("start", "0"))
            limit = int(request.query.get("limit", "50"))
        except ValueError as exc:
            raise web.HTTPBadRequest(text="Invalid queue window range") from exc
        try:
            result = await hub.async_transfer_window(transfer_id, device_id, start, limit)
        except ServiceValidationError as exc:
            raise web.HTTPBadRequest(text=str(exc)) from exc
        except ConnectionError as exc:
            _LOGGER.warning("PowerLink Plex lookup failed for transfer %s", transfer_id)
            raise web.HTTPServiceUnavailable(text="Plex unavailable for queue resolution") from exc
        return self.json(result)


class PowerLinkTransferAckView(HomeAssistantView):
    """Destination confirms playback; never automatically tears down source."""

    url = r"/api/powerlink/v1/transfers/{transfer_id}/ready"
    name = "api:powerlink:transfer_ready"
    requires_auth = False

    async def post(self, request: web.Request, transfer_id: str) -> web.Response:
        hub, device_id = _authenticate(request)
        try:
            transfer = hub.transfer_for(transfer_id, device_id)
        except ServiceValidationError as exc:
            raise web.HTTPBadRequest(text=str(exc)) from exc
        # Source should only be stopped by a future explicitly configured
        # policy after receipt of an authenticated 'playing' acknowledgement.
        request.app["hass"].bus.async_fire(
            "powerlink_transfer_ready", {
                "source_device": transfer.source,
                "destination_device": transfer.destination,
                "transfer_id": transfer_id,
            },
        )
        return self.json({"accepted": True, "source_stopped": False})
