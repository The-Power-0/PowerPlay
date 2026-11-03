"""Simulated Plex queue windows proving exact order and duplicate semantics."""

from __future__ import annotations

import asyncio
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for name, path in (
    ("custom_components", ROOT / "custom_components"),
    ("custom_components.powerlink", ROOT / "custom_components/powerlink"),
):
    if name not in sys.modules:
        module = types.ModuleType(name)
        module.__path__ = [str(path)]
        sys.modules[name] = module

from custom_components.powerlink.models import InvalidSnapshot  # noqa: E402
from custom_components.powerlink.queue_source import read_complete_plex_queue  # noqa: E402


def row(queue_id, rating_key, guid):
    return {
        "playQueueItemID": queue_id, "ratingKey": rating_key,
        "guid": guid, "type": "episode", "title": f"Episode {rating_key}",
        "parentIndex": 1, "index": 1,
    }


def response(items, *, selected=103, total=5, version=7, shuffled=True):
    return {
        "MediaContainer": {
            "playQueueTotalCount": total, "playQueueVersion": version,
            "playQueueShuffled": shuffled,
            "playQueueSelectedItemID": selected,
            "Metadata": list(items),
        }
    }


class PlexQueueReconstructionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # 101 and 103 intentionally point at the same ratingKey/GUID:
        # ordinary shuffle/playlist queues may repeat a particular episode.
        self.rows = [
            row(101, "10", "plex://episode/e10"),
            row(102, "20", "plex://episode/e20"),
            row(103, "10", "plex://episode/e10"),
            row(104, "30", "plex://episode/e30"),
            row(105, "40", "plex://episode/e40"),
        ]

    async def test_complete_queue_in_one_window(self):
        calls = []
        async def fetch(center, window):
            calls.append((center, window))
            return response(self.rows)
        result = await read_complete_plex_queue(fetch, server_id="plex_a", selected_item_id=103)
        self.assertEqual(len(calls), 1)
        self.assertEqual(result.selected_index, 2)
        self.assertTrue(result.shuffled)
        self.assertEqual(result.version, 7)
        self.assertEqual([i.rating_key for i in result.items], ["10", "20", "10", "30", "40"])

    async def test_partial_windows_restore_both_edges(self):
        calls = []
        async def fetch(center, window):
            calls.append(center)
            if center == 103:
                return response(self.rows[1:4])
            if center == 102:
                return response(self.rows[:3])
            if center == 104:
                return response(self.rows[2:])
            self.fail(f"unexpected Plex center: {center}")
        result = await read_complete_plex_queue(fetch, server_id="plex_a", selected_item_id=103)
        self.assertEqual(calls, [103, 102, 104])
        self.assertEqual([i.guid for i in result.items],
                         ["plex://episode/e10", "plex://episode/e20",
                          "plex://episode/e10", "plex://episode/e30",
                          "plex://episode/e40"])
        self.assertEqual(result.selected_index, 2)

    async def test_changing_queue_version_is_rejected(self):
        async def fetch(center, window):
            return response(self.rows[1:4] if center == 103 else self.rows[:3],
                            version=7 if center == 103 else 8)
        with self.assertRaises(InvalidSnapshot):
            await read_complete_plex_queue(fetch, server_id="plex_a", selected_item_id=103)

    async def test_unexpandable_queue_is_rejected(self):
        async def fetch(center, window):
            return response(self.rows[1:4])
        with self.assertRaises(InvalidSnapshot):
            await read_complete_plex_queue(fetch, server_id="plex_a", selected_item_id=103)

    async def test_missing_selected_item_is_rejected(self):
        async def fetch(center, window):
            return response(self.rows[:2])
        with self.assertRaises(InvalidSnapshot):
            await read_complete_plex_queue(fetch, server_id="plex_a", selected_item_id=103)

    async def test_reordered_or_duplicate_window_ids_are_rejected(self):
        async def fetch(center, window):
            return response([self.rows[0], self.rows[0]], total=2)
        with self.assertRaises(InvalidSnapshot):
            await read_complete_plex_queue(fetch, server_id="plex_a", selected_item_id=101)


if __name__ == "__main__":
    unittest.main()
