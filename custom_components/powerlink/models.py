"""Transport-neutral PowerLink queue contract; no Home Assistant imports."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import re

MAX_ITEMS = 5000
_ID = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


class InvalidSnapshot(ValueError):
    """A snapshot cannot be replayed without losing its original meaning."""


def _text(value: Any, label: str, max_length: int = 256) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > max_length:
        raise InvalidSnapshot(f"{label} must be a nonempty string of at most {max_length} characters")
    return value.strip()


def _int(value: Any, label: str, maximum: int = 86_400_000) -> int:
    if type(value) is not int or not 0 <= value <= maximum:
        raise InvalidSnapshot(f"{label} is out of range")
    return value


@dataclass(frozen=True, slots=True)
class QueueItem:
    """One position, including duplicates, in a real Plex play queue."""

    guid: str
    kind: str
    rating_key: str
    server_id: str
    title: str
    season: int | None = None
    episode: int | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> QueueItem:
        if not isinstance(data, dict):
            raise InvalidSnapshot("queue item must be an object")
        guid = _text(data.get("guid"), "guid", 200)
        if not (guid.startswith("plex://movie/") or guid.startswith("plex://episode/")):
            raise InvalidSnapshot("item needs a stable Plex movie/episode GUID")
        kind = _text(data.get("kind"), "kind", 12)
        if kind not in ("movie", "episode"):
            raise InvalidSnapshot("queue can only contain playable movies and episodes")
        if (kind == "movie") != guid.startswith("plex://movie/"):
            raise InvalidSnapshot("Plex GUID type does not match media kind")
        rating_key = _text(data.get("rating_key"), "rating_key", 64)
        server_id = _text(data.get("server_id"), "server_id", 128)
        season = data.get("season")
        episode = data.get("episode")
        if season is not None:
            season = _int(season, "season", 10000)
        if episode is not None:
            episode = _int(episode, "episode", 10000)
        return cls(guid, kind, rating_key, server_id, _text(data.get("title"), "title"), season, episode)

    def to_dict(self) -> dict[str, Any]:
        return {
            "guid": self.guid, "kind": self.kind, "rating_key": self.rating_key,
            "server_id": self.server_id, "title": self.title,
            "season": self.season, "episode": self.episode,
        }


@dataclass(frozen=True, slots=True)
class QueueSnapshot:
    """Immutable complete ordered queue and exact selection at handoff time."""

    source_device: str
    items: tuple[QueueItem, ...]
    index: int
    position_ms: int
    shuffled: bool
    queue_id: str
    profile_id: str | None = None

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> QueueSnapshot:
        if not isinstance(value, dict) or value.get("protocol") != 1:
            raise InvalidSnapshot("unsupported PowerLink snapshot protocol")
        raw_items = value.get("items")
        if not isinstance(raw_items, list) or not 1 <= len(raw_items) <= MAX_ITEMS:
            raise InvalidSnapshot("complete ordered queue must contain 1–5000 entries")
        items = tuple(QueueItem.from_dict(item) for item in raw_items)
        index = _int(value.get("index"), "index", len(items) - 1)
        position_ms = _int(value.get("position_ms"), "position_ms")
        if type(value.get("shuffled")) is not bool:
            raise InvalidSnapshot("shuffled must be boolean")
        source = _text(value.get("source_device"), "source_device", 64)
        queue_id = _text(value.get("queue_id"), "queue_id", 128)
        profile_id = value.get("profile_id")
        if profile_id is not None:
            profile_id = _text(profile_id, "profile_id", 128)
        return cls(source, items, index, position_ms, value["shuffled"], queue_id, profile_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "protocol": 1, "source_device": self.source_device,
            "queue_id": self.queue_id, "index": self.index,
            "position_ms": self.position_ms, "shuffled": self.shuffled,
            "profile_id": self.profile_id,
            "items": [item.to_dict() for item in self.items],
        }


@dataclass(frozen=True, slots=True)
class MediaCopy:
    """A matching Plex library entry, not necessarily the same rating key."""

    guid: str
    kind: str
    rating_key: str
    server_id: str
    library_title: str
    max_height: int
    season: int | None = None
    episode: int | None = None
    media_id: str | None = None
    media_index: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "guid": self.guid, "kind": self.kind, "rating_key": self.rating_key,
            "server_id": self.server_id, "library_title": self.library_title,
            "max_height": self.max_height,
            "media_id": self.media_id, "media_index": self.media_index,
        }


@dataclass(frozen=True, slots=True)
class DevicePolicy:
    """Destination capability is configured per device, never by room name."""

    max_height: int
    prefer_highest: bool = True

    def __post_init__(self) -> None:
        if self.max_height not in (480, 720, 1080, 2160, 4320):
            raise ValueError("unsupported device resolution cap")


def select_media_copy(item: QueueItem, copies: list[MediaCopy], policy: DevicePolicy) -> MediaCopy | None:
    """Pick an exact GUID/episode match without changing the queue or order.

    A 1080p device never selects a 2160p-only source. A 4K-capable destination
    picks the best available compatible source even if its HDMI UI is 1080p.
    No fuzzy title matching, and no silent fallback to the wrong episode.
    """
    compatible = [
        copy for copy in copies
        if copy.guid == item.guid and copy.kind == item.kind
        and (item.season is None or copy.season is None or copy.season == item.season)
        and (item.episode is None or copy.episode is None or copy.episode == item.episode)
        and 0 < copy.max_height <= policy.max_height
    ]
    if not compatible:
        return None
    def rank(copy: MediaCopy) -> tuple[int, int, str, str]:
        label_4k = "[4k]" in copy.library_title.lower()
        # High quality is the normal rule; folder names only break ties.
        height = copy.max_height if policy.prefer_highest else -copy.max_height
        return (-height, -(1 if label_4k and policy.max_height >= 2160 else 0), copy.server_id, copy.rating_key)
    return min(compatible, key=rank)


def map_window(
    snapshot: QueueSnapshot, start: int, results: list[MediaCopy | None]
) -> list[dict[str, Any]]:
    """Map an ordered page without deleting holes or duplicates."""
    if start < 0 or start + len(results) > len(snapshot.items):
        raise IndexError("window lies outside original queue")
    return [
        {"index": start + i, "source": snapshot.items[start + i].to_dict(),
         "copy": copy.to_dict() if copy else None,
         "status": "ok" if copy else "unavailable"}
        for i, copy in enumerate(results)
    ]
