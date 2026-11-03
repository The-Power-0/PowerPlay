"""PowerLink HA coordinator: device registry and short-lived windowed handoffs."""
from __future__ import annotations

import asyncio
import secrets
import time
from dataclasses import dataclass
from typing import Any, Mapping
from urllib.parse import urlencode

from homeassistant.helpers.storage import Store

from .const import DOMAIN, STORAGE_VERSION, STORAGE_KEY, SESSION_TTL_SECONDS
from .device import DeviceSettings
from .handoff import HandoffError, QueueSnapshot, WindowPlanner
from .launcher import execute_wake, launch_powerplay
from .plex_catalog import PlexCopyCatalog


@dataclass
class ActiveTransfer:
    snapshot: QueueSnapshot
    destination: DeviceSettings
    planner: WindowPlanner
    created_at: float
    acknowledged: bool = False


class PowerLinkController:
    def __init__(self, hass, data: Mapping[str, Any]) -> None:
        self.hass = hass
        self.options = dict(data)
        self.devices: dict[str, DeviceSettings] = {}
        self._store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._transfers: dict[str, ActiveTransfer] = {}
        self._lock = asyncio.Lock()
        plex_url, plex_token = data.get("plex_base_url"), data.get("plex_token")
        self.plex = PlexCopyCatalog(
            hass, plex_url, plex_token, server_id=data.get("plex_server_id", "")
        ) if plex_url and plex_token else None

    async def async_load(self) -> None:
        saved = await self._store.async_load() or {}
        for raw in saved.get("devices", []):
            try:
                settings = DeviceSettings.parse(raw)
                self.devices[settings.entity_id] = settings
            except HandoffError:
                continue

    async def register_device(self, config: Mapping[str, Any]) -> DeviceSettings:
        settings = DeviceSettings.parse(config)
        if self.hass.states.get(settings.entity_id) is None:
            raise HandoffError(f"No Home Assistant entity: {settings.entity_id}")
        async with self._lock:
            self.devices[settings.entity_id] = settings
            await self._store.async_save({
                "devices": [dev.as_dict() for dev in self.devices.values()],
            })
        return settings

    def device(self, entity_id: str) -> DeviceSettings:
        device = self.devices.get(entity_id)
        if device is None:
            raise HandoffError(f"Unregistered destination: {entity_id}")
        return device

    def _purge_expired(self) -> None:
        now = time.monotonic()
        for key, item in list(self._transfers.items()):
            if now - item.created_at >= SESSION_TTL_SECONDS:
                del self._transfers[key]

    async def prepare(self, raw: Mapping[str, Any], target: str) -> dict[str, Any]:
        device = self.device(target)
        snapshot = QueueSnapshot.parse(raw)
        planner = WindowPlanner(
            snapshot, device.policy,
            self.plex.find_copies if self.plex is not None else None,
        )
        current = await planner.ensure_current_playable()
        base = device.endpoint_base_url or self.options.get("base_url")
        if not base:
            raise HandoffError("Configure a Home Assistant URL reachable from this destination")
        token = secrets.token_urlsafe(32)
        session = ActiveTransfer(snapshot, device, planner, time.monotonic())
        self._purge_expired()
        self._transfers[token] = session
        # Deep-link carries only the token and API base, never a Plex token,
        # queue manifest or Home Assistant long-lived API bearer.
        uri = "powerplay://powerlink?" + urlencode({
            "v": "1", "base": base, "token": token,
        })
        return {
            "destination": target,
            "deep_link": uri,
            "queue_length": len(snapshot.items),
            "current_index": snapshot.current_index,
            "position_ms": snapshot.position_ms,
            "shuffled": snapshot.shuffled,
            "initial_media": current["media"],
            "expires_in": SESSION_TTL_SECONDS,
        }

    def _session(self, token: str) -> ActiveTransfer:
        self._purge_expired()
        if not isinstance(token, str) or len(token) > 128 or token not in self._transfers:
            raise HandoffError("Unknown or expired transfer")
        return self._transfers[token]

    async def window(self, token: str, start: int, count: int) -> dict[str, Any]:
        session = self._session(token)
        result = await session.planner.window(start, count)
        result["destination"] = session.destination.entity_id
        return result

    async def acknowledge(self, token: str, status: str) -> None:
        session = self._session(token)
        if status not in ("started", "failed"):
            raise HandoffError("Invalid acknowledgment status")
        if session.acknowledged:
            return
        session.acknowledged = True
        # Intentionally do not stop the source device automatically. An actual
        # playback-start acknowledgment is the only safe point for automations
        # to request it; a successful adb "am start" is not enough.
        self.hass.bus.async_fire("powerlink_handoff_acknowledged", {
            "source_device": session.snapshot.source_device,
            "destination_device": session.destination.entity_id,
            "status": status,
            "queue_length": len(session.snapshot.items),
            "shuffled": session.snapshot.shuffled,
        })
        if status == "failed":
            self._transfers.pop(token, None)

    async def open_device(self, entity_id: str, context) -> None:
        device = self.device(entity_id)
        await execute_wake(self.hass, device, context)
        await launch_powerplay(self.hass, device, context)

    async def handoff(self, raw: Mapping[str, Any], target: str, context) -> dict[str, Any]:
        device = self.device(target)
        if not device.supports_protocol_v1:
            raise HandoffError(
                "Destination has not been confirmed to support PowerLink v1 "
                "(requires PowerPlay 1.3.0+ client-side receiver)"
            )
        # Plan and verify the actual current item BEFORE waking/moving focus.
        prepared = await self.prepare(raw, target)
        await execute_wake(self.hass, device, context)
        await launch_powerplay(self.hass, device, context, uri=prepared["deep_link"])
        # The receiver must explicitly acknowledge playback via the relay
        # before any source-stopping action may be taken by HA automations.
        return prepared
