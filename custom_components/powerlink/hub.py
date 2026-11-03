"""Home Assistant-owned PowerLink orchestration; Fire TV has no polling tasks."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import secrets
import shlex
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import aiohttp_client, entity_registry
from homeassistant.helpers.storage import Store

from .const import (
    APP_PACKAGE, CONF_DEVICES, CONF_PLEX_SERVERS, MAX_TRANSFER_WINDOW,
    SESSION_MAX_AGE_SECONDS, TRANSFER_TTL_SECONDS,
)
from .models import DevicePolicy, QueueSnapshot, map_window, select_media_copy
from .plex import PlexCatalog


@dataclass(slots=True)
class PreparedTransfer:
    """One immutable queue, with lazy destination copy resolution."""

    token: str
    source: str
    destination: str
    snapshot: QueueSnapshot
    created: float
    current_copy: dict[str, Any]


class PowerLinkHub:
    """A single HA controller with any number of Fire TV endpoint profiles."""

    def __init__(self, hass: HomeAssistant, entry) -> None:
        self.hass = hass
        self.entry = entry
        self._store = Store(hass, 1, "powerlink_pairings")
        self._pairings: dict[str, str] = {}
        self._snapshots: dict[str, tuple[float, QueueSnapshot]] = {}
        self._transfers: dict[str, PreparedTransfer] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self.catalog = PlexCatalog(
            aiohttp_client.async_get_clientsession(hass),
            list(entry.options.get(CONF_PLEX_SERVERS, [])),
        )

    async def async_setup(self) -> None:
        data = await self._store.async_load() or {}
        # Only token hashes persist; plaintext tokens are shown once to admins.
        self._pairings = {
            k: v for k, v in data.items()
            if isinstance(k, str) and isinstance(v, str) and len(v) == 64
        }

    @property
    def devices(self) -> dict[str, dict[str, Any]]:
        return {
            d["device_id"]: d for d in self.entry.options.get(CONF_DEVICES, [])
        }

    def device(self, device_id: str) -> dict[str, Any]:
        device = self.devices.get(device_id)
        if device is None:
            raise ServiceValidationError(f"Unknown PowerLink device: {device_id}")
        return device

    async def async_pair_device(self, device_id: str) -> dict[str, str]:
        self.device(device_id)
        token = secrets.token_urlsafe(32)
        self._pairings[device_id] = hashlib.sha256(token.encode("utf-8")).hexdigest()
        await self._store.async_save(dict(self._pairings))
        # Never log token or put it in a URL.
        return {
            "device_id": device_id,
            "pairing_token": token,
            "session_endpoint": "/api/powerlink/v1/sessions",
            "transfer_endpoint": "/api/powerlink/v1/transfers/{id}",
        }

    def authenticated(self, device_id: str | None, token: str | None) -> bool:
        if not device_id or not token or len(token) > 256:
            return False
        if device_id not in self.devices:
            return False
        expected = self._pairings.get(device_id)
        if expected is None:
            return False
        actual = hashlib.sha256(token.encode("utf-8")).hexdigest()
        return hmac.compare_digest(expected, actual)

    def publish_snapshot(self, device_id: str, payload: dict[str, Any]) -> QueueSnapshot:
        self.device(device_id)
        snapshot = QueueSnapshot.from_dict(payload)
        if snapshot.source_device != device_id:
            raise ServiceValidationError("Snapshot source must match the authenticated device")
        self._snapshots[device_id] = (time.monotonic(), snapshot)
        return snapshot

    def _clean_expired(self) -> None:
        now = time.monotonic()
        self._transfers = {
            key: value for key, value in self._transfers.items()
            if now - value.created <= TRANSFER_TTL_SECONDS
        }
        self._snapshots = {
            key: value for key, value in self._snapshots.items()
            if now - value[0] <= SESSION_MAX_AGE_SECONDS
        }

    def snapshot_for(self, source: str) -> QueueSnapshot:
        self._clean_expired()
        match = self._snapshots.get(source)
        if match is None:
            raise ServiceValidationError(
                "Source has no fresh full queue snapshot; ask PowerPlay to send its current position and queue"
            )
        return match[1]

    def _lock_for(self, device_id: str) -> asyncio.Lock:
        return self._locks.setdefault(device_id, asyncio.Lock())

    @staticmethod
    def _validated_link(uri: str) -> str:
        if len(uri) > 2048 or any(ord(c) < 32 for c in uri):
            raise ServiceValidationError("Unsafe PowerPlay launch link")
        parsed = urlsplit(uri)
        if parsed.scheme != "powerplay" or parsed.hostname not in ("open", "play", "powerlink", "shuffle"):
            raise ServiceValidationError("Only PowerPlay deep links may be launched")
        if parsed.username or parsed.password or parsed.port:
            raise ServiceValidationError("A PowerPlay link may not include network credentials")
        return uri

    async def _script(self, script_entity: str, *, uri: str, device_id: str) -> None:
        name = script_entity.split(".", 1)[-1]
        if not self.hass.services.has_service("script", name):
            raise HomeAssistantError(f"PowerLink script is unavailable: {script_entity}")
        # Calling the named script service blocks until the full script finishes.
        await self.hass.services.async_call(
            "script", name,
            {"powerlink_uri": uri, "powerlink_device": device_id},
            blocking=True,
        )

    async def async_launch(self, device_id: str, uri: str = "powerplay://open") -> dict[str, Any]:
        device = self.device(device_id)
        link = self._validated_link(uri)
        async with self._lock_for(device_id):
            media_player = device.get("media_player") or ""
            wake_script = device.get("wake_script") or ""
            state = self.hass.states.get(media_player) if media_player else None
            wake_mode = device.get("wake_mode", "when_off")
            should_wake = wake_mode == "always" or (
                wake_mode == "when_off" and (state is None or state.state in ("off", "standby", "unknown", "unavailable"))
            )
            if should_wake:
                if wake_script:
                    await self._script(wake_script, uri=link, device_id=device_id)
                elif media_player:
                    await self.hass.services.async_call(
                        "media_player", "turn_on", {"entity_id": media_player}, blocking=True
                    )
                else:
                    raise ServiceValidationError(
                        "Device requires a wake script when it has no Home Assistant media_player"
                    )
                delay = int(device.get("warmup_seconds", 3))
                if delay:
                    await asyncio.sleep(min(delay, 90))
            method = device.get("launch_method", "adb")
            if method == "script":
                launch_script = device.get("launch_script") or ""
                if not launch_script:
                    raise ServiceValidationError("Configure a launch script for this endpoint")
                await self._script(launch_script, uri=link, device_id=device_id)
            elif method == "adb":
                if not media_player:
                    raise ServiceValidationError("ADB launch requires a media_player entity")
                if not self.hass.services.has_service("androidtv", "adb_command"):
                    raise HomeAssistantError("Configure the Android Debug Bridge integration first")
                # shlex quoting avoids shell injection from a validated URL.
                command = (
                    "am start -a android.intent.action.VIEW"
                    f" -d {shlex.quote(link)} {APP_PACKAGE}"
                )
                await self.hass.services.async_call(
                    "androidtv", "adb_command",
                    {"entity_id": media_player, "command": command}, blocking=True,
                )
            elif method == "select_source":
                if link != "powerplay://open":
                    raise ServiceValidationError(
                        "select_source cannot deliver a transfer; use ADB or a launch script"
                    )
                await self.hass.services.async_call(
                    "media_player", "select_source",
                    {"entity_id": media_player, "source": APP_PACKAGE}, blocking=True,
                )
            else:
                raise ServiceValidationError(f"Unsupported launch method: {method}")
            return {"device_id": device_id, "result": "launch_requested", "method": method}

    async def async_handoff(self, source: str, destination: str) -> dict[str, Any]:
        """Fail closed until current item is playable on the destination.

        The original source is never stopped in this operation. Only a future
        destination 'playing' acknowledgement may be used for source teardown.
        """
        if source == destination:
            raise ServiceValidationError("Source and destination must differ")
        self.device(source)
        device = self.device(destination)
        if not self.catalog.configured:
            raise ServiceValidationError("Configure one or more Plex servers in PowerLink")
        snapshot = self.snapshot_for(source)
        policy = DevicePolicy(max_height=int(device.get("max_height", 1080)))
        current = snapshot.items[snapshot.index]
        copies = await self.catalog.lookup(current.guid)
        selected = select_media_copy(current, copies, policy)
        if selected is None:
            raise ServiceValidationError(
                f"No compatible Plex copy for the current item on {destination}; source remains playing"
            )
        self._clean_expired()
        transfer_id = secrets.token_urlsafe(24)
        while transfer_id in self._transfers:
            transfer_id = secrets.token_urlsafe(24)
        transfer = PreparedTransfer(
            token=transfer_id, source=source, destination=destination,
            snapshot=snapshot, created=time.monotonic(),
            current_copy=selected.to_dict(),
        )
        self._transfers[transfer_id] = transfer
        try:
            await self.async_launch(
                destination, f"powerplay://powerlink/resume?id={transfer_id}"
            )
        except Exception:
            self._transfers.pop(transfer_id, None)
            raise
        return {
            "transfer_id": transfer_id,
            "source_device": source,
            "destination_device": destination,
            "queue_length": len(snapshot.items),
            "index": snapshot.index,
            "position_ms": snapshot.position_ms,
            "shuffled": snapshot.shuffled,
            "status": "launch_requested",
            "source_stopped": False,
        }

    def transfer_for(self, transfer_id: str, destination: str) -> PreparedTransfer:
        self._clean_expired()
        result = self._transfers.get(transfer_id)
        if result is None or result.destination != destination:
            raise ServiceValidationError("Transfer not found, expired, or belongs to another device")
        return result

    async def async_transfer_window(
        self, transfer_id: str, destination: str, start: int, limit: int
    ) -> dict[str, Any]:
        """Resolve only the requested page; never reorder or drop queue slots."""
        transfer = self.transfer_for(transfer_id, destination)
        snapshot = transfer.snapshot
        if not (0 <= start < len(snapshot.items)) or not 1 <= limit <= MAX_TRANSFER_WINDOW:
            raise ServiceValidationError("Queue window out of range")
        end = min(start + limit, len(snapshot.items))
        policy = DevicePolicy(max_height=int(self.device(destination).get("max_height", 1080)))
        entries = snapshot.items[start:end]
        async def one(item):
            matches = await self.catalog.lookup(item.guid)
            return select_media_copy(item, matches, policy)
        copies = await asyncio.gather(*(one(item) for item in entries))
        return {
            "protocol": 1,
            "transfer_id": transfer_id,
            "source_device": transfer.source,
            "destination_device": destination,
            "total": len(snapshot.items),
            "index": snapshot.index,
            "position_ms": snapshot.position_ms,
            "shuffled": snapshot.shuffled,
            "profile_id": snapshot.profile_id,
            "start": start,
            "entries": map_window(snapshot, start, copies),
            "next_start": end if end < len(snapshot.items) else None,
        }

    def discover(self) -> list[dict[str, Any]]:
        """Use HA's known entities; no broadcast discovery or background scan."""
        assigned = {
            d.get("media_player"): d["device_id"]
            for d in self.devices.values() if d.get("media_player")
        }
        registry = entity_registry.async_get(self.hass)
        return [
            {
                "entity_id": entity.entity_id,
                "name": self.hass.states.get(entity.entity_id).name
                if self.hass.states.get(entity.entity_id) is not None else entity.entity_id,
                "platform": entity.platform,
                "state": self.hass.states.get(entity.entity_id).state
                if self.hass.states.get(entity.entity_id) is not None else "unknown",
                "assigned_device": assigned.get(entity.entity_id),
                "fire_tv_candidate": entity.platform in ("androidtv", "firetv"),
            }
            for entity in registry.entities.values()
            if entity.entity_id.startswith("media_player.")
        ]
