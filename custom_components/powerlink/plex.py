"""Bounded Plex GUID-to-library-copy lookup on Home Assistant, never Fire TV."""

from __future__ import annotations

import asyncio
import time
from collections import OrderedDict
from typing import Any
from urllib.parse import urlsplit

from aiohttp import ClientError, ClientSession, ClientTimeout

from .models import MediaCopy


def parse_height(media: dict[str, Any]) -> int:
    """Prefer actual media height; '4k' labels are not sufficient evidence."""
    try:
        height = int(media.get("height") or 0)
    except (TypeError, ValueError):
        height = 0
    if height > 0:
        return height
    label = str(media.get("videoResolution") or "").lower()
    return {"4k": 2160, "2160": 2160, "1080": 1080, "720": 720,
            "576": 576, "480": 480, "sd": 480}.get(label, 0)


def parse_copies(data: dict[str, Any], server_id: str, guid: str) -> list[MediaCopy]:
    """Parse Plex /library/all?guid=<guid> without trusting a fuzzy search hit."""
    container = data.get("MediaContainer", {})
    entries = container.get("Metadata", []) if isinstance(container, dict) else []
    if not isinstance(entries, list):
        return []
    result: list[MediaCopy] = []
    for entry in entries:
        if not isinstance(entry, dict) or entry.get("guid") != guid:
            continue
        kind = entry.get("type")
        if kind not in ("movie", "episode") or not entry.get("ratingKey"):
            continue
        versions = entry.get("Media", [])
        if not isinstance(versions, list):
            continue
        def number(key: str) -> int | None:
            try:
                return int(entry[key]) if entry.get(key) is not None else None
            except (ValueError, TypeError):
                return None
        # Different Plex Media versions can coexist under ONE ratingKey.
        # Evaluate each separately: a 4K+1080 entry must still work on
        # an HD-only Fire Stick without server transcoding or fuzzy remaps.
        for media_index, version in enumerate(versions):
            if not isinstance(version, dict):
                continue
            height = parse_height(version)
            if height <= 0:
                continue  # Unknown resolution: fail closed, not auto-select 4K.
            media_id = version.get("id")
            result.append(MediaCopy(
                guid=guid, kind=kind, rating_key=str(entry["ratingKey"]),
                server_id=server_id,
                library_title=str(entry.get("librarySectionTitle") or ""),
                max_height=height,
                season=number("parentIndex"),
                episode=number("index"),
                media_id=str(media_id) if media_id is not None else None,
                media_index=media_index,
            ))
    return result


class PlexCatalog:
    """Small TTL/LRU, four concurrent requests; never polls or scans libraries."""

    def __init__(self, session: ClientSession, servers: list[dict[str, str]]) -> None:
        self._http = session
        self._servers = list(servers)
        self._cache: OrderedDict[str, tuple[float, list[MediaCopy]]] = OrderedDict()
        self._semaphore = asyncio.Semaphore(4)
        for server in self._servers:
            parts = urlsplit(server["url"])
            if parts.scheme not in ("http", "https") or not parts.hostname or not server.get("token"):
                raise ValueError("Plex server URL and token must be explicitly configured")

    @property
    def configured(self) -> bool:
        return bool(self._servers)

    async def lookup(self, guid: str) -> list[MediaCopy]:
        now = time.monotonic()
        cached = self._cache.get(guid)
        if cached is not None and now - cached[0] < 300:
            self._cache.move_to_end(guid)
            return cached[1]
        async with self._semaphore:
            cached = self._cache.get(guid)
            if cached is not None and time.monotonic() - cached[0] < 300:
                return cached[1]
            if not self._servers:
                raise ValueError("No Plex servers configured in PowerLink options")
            # Allow several Plex servers while keeping fan-out on HA, not on the TV.
            pages = await asyncio.gather(
                *(self._get(server, guid) for server in self._servers[:8]),
                return_exceptions=True,
            )
            combined: list[MediaCopy] = []
            succeeded = False
            for page in pages:
                if isinstance(page, BaseException):
                    continue
                succeeded = True
                combined.extend(page)
            if not succeeded:
                raise ConnectionError("Plex GUID lookup failed on all configured servers")
            self._cache[guid] = (time.monotonic(), combined)
            self._cache.move_to_end(guid)
            while len(self._cache) > 2048:
                self._cache.popitem(last=False)
            return combined

    async def _get(self, server: dict[str, str], guid: str) -> list[MediaCopy]:
        base = server["url"].rstrip("/")
        url = base + "/library/all"
        try:
            async with self._http.get(
                url,
                params={"guid": guid},
                headers={"X-Plex-Token": server["token"], "Accept": "application/json"},
                timeout=ClientTimeout(total=12),
                allow_redirects=False,
            ) as response:
                response.raise_for_status()
                payload = await response.json()
        except (ClientError, TimeoutError, ValueError) as exc:
            raise ConnectionError("Plex lookup unavailable") from exc
        return parse_copies(payload, server["id"], guid)
