"""UI onboarding for a device-agnostic PowerLink Home Assistant hub."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlsplit

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, OptionsFlow
from homeassistant.helpers import selector

from .const import CONF_DEVICES, CONF_PLEX_SERVERS, DOMAIN

_DEVICE_ID = re.compile(r"^[a-z][a-z0-9_]{1,39}$")
_MAX_DEVICES = 32


class PowerLinkConfigFlow(ConfigFlow, domain=DOMAIN):
    """One hub per Home Assistant, any number of configured endpoints."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        if user_input is not None:
            await self.async_set_unique_id("powerlink_hub")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title="PowerLink", data={})
        return self.async_show_form(step_id="user", data_schema=vol.Schema({}))

    @staticmethod
    def async_get_options_flow(config_entry):
        return PowerLinkOptionsFlow()


class PowerLinkOptionsFlow(OptionsFlow):
    """Configure any mix of local, routed and scripted device endpoints."""

    async def async_step_init(self, user_input=None):
        devices = self.config_entry.options.get(CONF_DEVICES, [])
        servers = self.config_entry.options.get(CONF_PLEX_SERVERS, [])
        options = ["add_device", "add_plex_server"]
        if devices:
            options.extend(["edit_device", "remove_device"])
        if servers:
            options.append("remove_plex_server")
        return self.async_show_menu(step_id="init", menu_options=options)

    def _devices(self) -> list[dict[str, Any]]:
        return list(self.config_entry.options.get(CONF_DEVICES, []))

    def _servers(self) -> list[dict[str, Any]]:
        return list(self.config_entry.options.get(CONF_PLEX_SERVERS, []))

    def _save(self, *, devices=None, servers=None):
        return self.async_create_entry(
            title="",
            data={
                **self.config_entry.options,
                CONF_DEVICES: self._devices() if devices is None else devices,
                CONF_PLEX_SERVERS: self._servers() if servers is None else servers,
            },
        )

    def _device_schema(self, previous: dict[str, Any] | None = None) -> vol.Schema:
        data = previous or {}
        return vol.Schema({
            vol.Required("device_id", default=data.get("device_id", "")): str,
            vol.Required("name", default=data.get("name", "")): str,
            vol.Optional("media_player", default=data.get("media_player", "")): str,
            vol.Optional("wake_script", default=data.get("wake_script", "")): str,
            vol.Optional("launch_script", default=data.get("launch_script", "")): str,
            vol.Required("wake_mode", default=data.get("wake_mode", "when_off")):
                vol.In(["always", "when_off", "never"]),
            vol.Required("warmup_seconds", default=data.get("warmup_seconds", 3)):
                vol.All(vol.Coerce(int), vol.Range(min=0, max=90)),
            vol.Required("max_height", default=data.get("max_height", 1080)):
                vol.In([480, 720, 1080, 2160, 4320]),
            vol.Required("launch_method", default=data.get("launch_method", "adb")):
                vol.In(["adb", "script", "select_source"]),
        })

    @staticmethod
    def _validate_device(data: dict[str, Any], existing: list[dict[str, Any]], previous_id: str | None) -> str | None:
        device_id = data["device_id"]
        if not _DEVICE_ID.fullmatch(device_id):
            return "bad_device_id"
        if not data["name"].strip() or len(data["name"]) > 80:
            return "bad_device_name"
        if any(v["device_id"] == device_id and v["device_id"] != previous_id for v in existing):
            return "duplicate_device_id"
        if data["media_player"] and not data["media_player"].startswith("media_player."):
            return "bad_media_player"
        if data["wake_script"] and not data["wake_script"].startswith("script."):
            return "bad_wake_script"
        if data["launch_script"] and not data["launch_script"].startswith("script."):
            return "bad_launch_script"
        if data["launch_method"] == "script" and not data["launch_script"]:
            return "launch_script_required"
        if data["launch_method"] in ("adb", "select_source") and not data["media_player"]:
            return "media_player_required"
        return None

    async def async_step_add_device(self, user_input=None):
        devices = self._devices()
        if len(devices) >= _MAX_DEVICES:
            return self.async_abort(reason="device_limit")
        errors = {}
        if user_input is not None:
            reason = self._validate_device(user_input, devices, None)
            if reason:
                errors["base"] = reason
            else:
                return self._save(devices=[*devices, user_input])
        return self.async_show_form(
            step_id="add_device",
            data_schema=self._device_schema(user_input),
            errors=errors,
        )

    async def async_step_edit_device(self, user_input=None):
        if user_input:
            self._editing = user_input["device_id"]
            return await self.async_step_edit_device_details()
        return self.async_show_form(
            step_id="edit_device",
            data_schema=vol.Schema({
                vol.Required("device_id"): vol.In({
                    d["device_id"]: d["name"] for d in self._devices()
                }),
            }),
        )

    async def async_step_edit_device_details(self, user_input=None):
        current = next((d for d in self._devices() if d["device_id"] == self._editing), None)
        if current is None:
            return self.async_abort(reason="device_not_found")
        errors = {}
        if user_input is not None:
            if user_input["device_id"] != self._editing:
                errors["base"] = "device_id_immutable"
            else:
                reason = self._validate_device(user_input, self._devices(), self._editing)
                if reason:
                    errors["base"] = reason
                else:
                    devices = [user_input if d["device_id"] == self._editing else d for d in self._devices()]
                    return self._save(devices=devices)
        return self.async_show_form(
            step_id="edit_device_details",
            data_schema=self._device_schema(user_input or current),
            errors=errors,
        )

    async def async_step_remove_device(self, user_input=None):
        devices = self._devices()
        if user_input:
            return self._save(devices=[
                d for d in devices if d["device_id"] != user_input["device_id"]
            ])
        return self.async_show_form(
            step_id="remove_device",
            data_schema=vol.Schema({
                vol.Required("device_id"): vol.In({
                    d["device_id"]: d["name"] for d in devices
                }),
            }),
        )

    async def async_step_add_plex_server(self, user_input=None):
        errors = {}
        if user_input:
            server_id = user_input["id"]
            parsed = urlsplit(user_input["url"])
            if not _DEVICE_ID.fullmatch(server_id):
                errors["base"] = "bad_device_id"
            elif any(v["id"] == server_id for v in self._servers()):
                errors["base"] = "duplicate_server_id"
            elif parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password:
                errors["base"] = "invalid_plex_url"
            elif len(self._servers()) >= 8:
                return self.async_abort(reason="server_limit")
            elif not user_input["token"]:
                errors["base"] = "missing_plex_token"
            else:
                return self._save(servers=[*self._servers(), {
                    "id": server_id, "url": user_input["url"].rstrip("/"),
                    "token": user_input["token"],
                }])
        return self.async_show_form(
            step_id="add_plex_server",
            data_schema=vol.Schema({
                vol.Required("id"): str,
                vol.Required("url"): str,
                vol.Required("token"): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
                ),
            }),
            errors=errors,
        )

    async def async_step_remove_plex_server(self, user_input=None):
        servers = self._servers()
        if user_input:
            return self._save(servers=[s for s in servers if s["id"] != user_input["id"]])
        return self.async_show_form(
            step_id="remove_plex_server",
            data_schema=vol.Schema({
                vol.Required("id"): vol.In({s["id"]: s["url"] for s in servers}),
            }),
        )
