"""PowerLink Home Assistant integration for PowerPlay Fire TV clients."""

from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.service import async_register_admin_service

from .const import DOMAIN
from .http import PowerLinkSessionView, PowerLinkTransferAckView, PowerLinkTransferView
from .hub import PowerLinkHub

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Prepare the hub registry without starting background polling."""
    hass.data.setdefault(DOMAIN, {})
    return True


def _hub_for(hass: HomeAssistant) -> PowerLinkHub:
    hubs = hass.data.get(DOMAIN, {})
    for value in hubs.values():
        if isinstance(value, PowerLinkHub):
            return value
    raise ServiceValidationError("PowerLink is not configured")


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Start one multi-endpoint controller from its UI configuration."""
    await async_setup(hass, {})
    hub = PowerLinkHub(hass, entry)
    await hub.async_setup()
    hass.data[DOMAIN][entry.entry_id] = hub

    async def _reload(hass: HomeAssistant, changed: ConfigEntry) -> None:
        await hass.config_entries.async_reload(changed.entry_id)

    entry.async_on_unload(entry.add_update_listener(_reload))

    if not hass.data[DOMAIN].get("_registered"):
        # The app POSTs only when a handoff is requested; no websocket/scan
        # loop runs while viewing content.
        hass.http.register_view(PowerLinkSessionView())
        hass.http.register_view(PowerLinkTransferView())
        hass.http.register_view(PowerLinkTransferAckView())

        async def discover(call: ServiceCall):
            response = {"devices": _hub_for(hass).discover()}
            return response if call.return_response else None

        async def pair(call: ServiceCall):
            return await _hub_for(hass).async_pair_device(call.data["device_id"])

        async def launch(call: ServiceCall):
            result = await _hub_for(hass).async_launch(
                call.data["device_id"], call.data.get("uri") or "powerplay://open"
            )
            return result if call.return_response else None

        async def handoff(call: ServiceCall):
            result = await _hub_for(hass).async_handoff(
                call.data["source_device"], call.data["destination_device"]
            )
            return result if call.return_response else None

        hass.services.async_register(
            DOMAIN, "discover_devices", discover,
            schema=vol.Schema({}), supports_response=SupportsResponse.ONLY,
        )
        async_register_admin_service(
            hass, DOMAIN, "pair_device", pair,
            schema=vol.Schema({vol.Required("device_id"): str}),
            supports_response=SupportsResponse.ONLY,
        )
        hass.services.async_register(
            DOMAIN, "launch", launch,
            schema=vol.Schema({
                vol.Required("device_id"): str,
                vol.Optional("uri"): str,
            }), supports_response=SupportsResponse.OPTIONAL,
        )
        hass.services.async_register(
            DOMAIN, "handoff", handoff,
            schema=vol.Schema({
                vol.Required("source_device"): str,
                vol.Required("destination_device"): str,
            }), supports_response=SupportsResponse.OPTIONAL,
        )
        hass.data[DOMAIN]["_registered"] = True
    _LOGGER.info("PowerLink loaded with %s configured endpoints", len(hub.devices))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Remove app controller without disturbing configured Android TV entities."""
    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    entry.async_unload()
    if not any(isinstance(v, PowerLinkHub) for v in hass.data.get(DOMAIN, {}).values()):
        for service in ("discover_devices", "pair_device", "launch", "handoff"):
            hass.services.async_remove(DOMAIN, service)
        hass.data[DOMAIN]["_registered"] = False
        # HTTP views are registered by Home Assistant for process lifetime;
        # requests correctly return 503 while no hub is configured.
    return True
