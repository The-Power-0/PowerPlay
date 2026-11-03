"""Short-lived PowerLink transfer endpoint.

Possession of the 256-bit random token authorizes only one queue manifest,
not Home Assistant itself. Deploy HTTPS for cross-network clients. Never
expose an HA API key or Plex access token through this endpoint.
"""
from __future__ import annotations

from aiohttp import web
from homeassistant.components.http import HomeAssistantView

from .const import DOMAIN
from .handoff import HandoffError, MAX_WINDOW_ITEMS


class PowerLinkSessionView(HomeAssistantView):
    url = "/api/powerlink/v1/session/{token}"
    name = "api:powerlink:session"
    requires_auth = False

    async def get(self, request: web.Request, token: str) -> web.Response:
        controller = request.app["hass"].data.get(DOMAIN)
        if controller is None:
            raise web.HTTPNotFound()
        try:
            start = int(request.query.get("start", 0))
            count = int(request.query.get("count", 16))
            if count < 1 or count > MAX_WINDOW_ITEMS:
                raise ValueError("Window too large")
            result = await controller.window(token, start, count)
        except (HandoffError, ValueError):
            raise web.HTTPNotFound() from None
        return web.json_response(result, headers={"Cache-Control": "no-store", "Pragma": "no-cache"})


class PowerLinkAcknowledgmentView(HomeAssistantView):
    url = "/api/powerlink/v1/session/{token}/ack"
    name = "api:powerlink:ack"
    requires_auth = False

    async def post(self, request: web.Request, token: str) -> web.Response:
        controller = request.app["hass"].data.get(DOMAIN)
        if controller is None:
            raise web.HTTPNotFound()
        try:
            data = await request.json()
            if not isinstance(data, dict):
                raise ValueError("Expected object")
            await controller.acknowledge(token, data.get("status"))
        except (HandoffError, ValueError):
            raise web.HTTPNotFound() from None
        return web.json_response({"acknowledged": True},
                                 headers={"Cache-Control": "no-store"})
