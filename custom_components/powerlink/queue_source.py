"""Reassemble the exact Plex queue on HA using immutable playQueueItemID order.

Plex returns a window of queue entries. Anchored windows can be smaller
than requested, so walk each edge with overlap checks. No Plex ownership
transfer or queue mutation is performed. A truncated or changing queue
fails rather than skipping episodes or silently reshuffling.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from .models import InvalidSnapshot, QueueItem

QueuePage = Callable[[int, int], Awaitable[dict[str, Any]]]


@dataclass(frozen=True, slots=True)
class PlexQueueRead:
    items: tuple[QueueItem, ...]
    selected_index: int
    shuffled: bool
    version: int


def _number(value: Any, label: str) -> int:
    try:
        result = int(value)
    except (ValueError, TypeError) as exc:
        raise InvalidSnapshot(f"Invalid Plex {label}") from exc
    if result < 0:
        raise InvalidSnapshot(f"Invalid Plex {label}")
    return result


def _container(response: dict[str, Any]) -> dict[str, Any]:
    value = response.get("MediaContainer")
    if not isinstance(value, dict):
        raise InvalidSnapshot("Plex queue returned no MediaContainer")
    return value


def _rows(container: dict[str, Any]) -> list[dict[str, Any]]:
    rows = container.get("Metadata")
    if not isinstance(rows, list):
        raise InvalidSnapshot("Plex queue returned no metadata list")
    for row in rows:
        if not isinstance(row, dict) or row.get("playQueueItemID") is None:
            raise InvalidSnapshot("Plex queue item missing a distinct playQueueItemID")
    ids = [_number(row["playQueueItemID"], "queue item ID") for row in rows]
    if len(ids) != len(set(ids)):
        raise InvalidSnapshot("Plex queue window contains repeated queue-item IDs")
    return rows


def _ids(rows: list[dict[str, Any]]) -> list[int]:
    return [_number(row["playQueueItemID"], "queue item ID") for row in rows]


def _queue_item(row: dict[str, Any], server_id: str) -> QueueItem:
    def optional_int(name: str) -> int | None:
        value = row.get(name)
        return _number(value, name) if value is not None else None

    return QueueItem.from_dict({
        "guid": row.get("guid"),
        "kind": row.get("type"),
        "rating_key": str(row.get("ratingKey") or ""),
        "server_id": server_id,
        "title": str(row.get("title") or ""),
        "season": optional_int("parentIndex"),
        "episode": optional_int("index"),
    })


async def read_complete_plex_queue(
    fetch_page: QueuePage,
    *,
    server_id: str,
    selected_item_id: int,
    max_items: int = 5000,
    max_requests: int = 110,
) -> PlexQueueRead:
    """Fetch contiguous windows and verify ordering, count and queue version."""
    if selected_item_id <= 0:
        raise InvalidSnapshot("Selected Plex queue-item ID required")
    initial = _container(await fetch_page(selected_item_id, min(max_items, 250)))
    total = _number(initial.get("playQueueTotalCount"), "queue total count")
    version = _number(initial.get("playQueueVersion"), "queue version")
    if not 1 <= total <= max_items:
        raise InvalidSnapshot("Plex queue is empty or exceeds PowerLink limits")
    initial_items = _rows(initial)
    current_ids = _ids(initial_items)
    if selected_item_id not in current_ids:
        raise InvalidSnapshot("Plex queue response does not contain the selected item")
    if len(current_ids) > total:
        raise InvalidSnapshot("Plex queue response exceeds the declared total")
    items = list(initial_items)
    seen = set(current_ids)
    requests = 1

    async def checked(center_id: int) -> list[dict[str, Any]]:
        nonlocal requests
        if requests >= max_requests:
            raise InvalidSnapshot("Plex queue requires more window requests than permitted")
        requests += 1
        response = _container(await fetch_page(center_id, 50))
        if _number(response.get("playQueueTotalCount"), "total count") != total:
            raise InvalidSnapshot("Plex queue length changed during capture")
        if _number(response.get("playQueueVersion"), "version") != version:
            raise InvalidSnapshot("Plex queue was reordered during capture")
        rows = _rows(response)
        if center_id not in _ids(rows):
            raise InvalidSnapshot("Plex queue window does not include its requested center")
        return rows

    # Both edges only expand outward. For each anchored page check that its
    # known overlap is the same contiguous sequence, never sort by ratingKey
    # (a queue can intentionally contain the same episode several times).
    while len(items) < total:
        changed = False
        for direction in ("before", "after"):
            if len(items) >= total:
                break
            anchor = _ids(items)[0 if direction == "before" else -1]
            page = await checked(anchor)
            ids = _ids(page)
            index = ids.index(anchor)
            segment = page[:index] if direction == "before" else page[index + 1:]
            if direction == "before":
                # The immediately preceding rows must precede the old head;
                # when the entire page lies in seen, this is a real boundary.
                extra = [row for row in segment if _number(row["playQueueItemID"], "queue item ID") not in seen]
                if extra:
                    if len(extra) != len(segment):
                        raise InvalidSnapshot("Noncontiguous overlapping Plex queue window")
                    items = [*extra, *items]
            else:
                extra = [row for row in segment if _number(row["playQueueItemID"], "queue item ID") not in seen]
                if extra:
                    if len(extra) != len(segment):
                        raise InvalidSnapshot("Noncontiguous overlapping Plex queue window")
                    items.extend(extra)
            if extra:
                seen.update(_ids(extra))
                changed = True
            if len(items) > total:
                raise InvalidSnapshot("Plex queue page traversal exceeded its total count")
        if not changed:
            raise InvalidSnapshot("Plex returned an incomplete, unexpandable queue window")

    ordered_ids = _ids(items)
    if len(set(ordered_ids)) != total or selected_item_id not in ordered_ids:
        raise InvalidSnapshot("Plex queue lost entries or selected-item identity")

    raw_shuffled = initial.get("playQueueShuffled", False)
    if raw_shuffled not in (True, False, 0, 1):
        raise InvalidSnapshot("Invalid Plex shuffled flag")

    return PlexQueueRead(
        items=tuple(_queue_item(row, server_id) for row in items),
        selected_index=ordered_ids.index(selected_item_id),
        shuffled=bool(raw_shuffled),
        version=version,
    )
