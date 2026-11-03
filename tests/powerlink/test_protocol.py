"""Deterministic queue, copy policy and metadata tests, no HA runtime needed."""

from __future__ import annotations

import importlib
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for name, path in (
    ("custom_components", ROOT / "custom_components"),
    ("custom_components.powerlink", ROOT / "custom_components/powerlink"),
):
    module = types.ModuleType(name)
    module.__path__ = [str(path)]
    sys.modules[name] = module

from custom_components.powerlink.models import (  # noqa: E402
    DevicePolicy, InvalidSnapshot, MediaCopy, QueueItem, QueueSnapshot,
    map_window, select_media_copy,
)


def item(guid="plex://episode/ep1", kind="episode", rating_key="11"):
    return {
        "guid": guid, "kind": kind, "rating_key": rating_key,
        "server_id": "plex_a", "title": "Episode One",
        "season": 2 if kind == "episode" else None,
        "episode": 5 if kind == "episode" else None,
    }


def copy(guid="plex://episode/ep1", height=1080, rating_key="80", library="TV Shows"):
    return MediaCopy(guid=guid, kind="episode", rating_key=rating_key,
                     server_id="plex_a", library_title=library,
                     max_height=height, season=2, episode=5)


def snapshot(items=None, **kwargs):
    data = {
        "protocol": 1, "source_device": "living_room",
        "items": items or [item(), item(rating_key="11"), item("plex://episode/ep2", rating_key="12")],
        "index": 1, "position_ms": 1_237_912,
        "queue_id": "plex_queue_1234", "shuffled": True,
    }
    data.update(kwargs)
    return QueueSnapshot.from_dict(data)


class QueueContractTests(unittest.TestCase):
    def test_duplicates_shuffle_and_position_survive(self):
        source = snapshot()
        self.assertEqual(source.index, 1)
        self.assertTrue(source.shuffled)
        self.assertEqual(source.position_ms, 1_237_912)
        self.assertEqual([v.guid for v in source.items],
                         ["plex://episode/ep1", "plex://episode/ep1", "plex://episode/ep2"])
        self.assertEqual(QueueSnapshot.from_dict(source.to_dict()), source)

    def test_bad_queue_index_fails_closed(self):
        with self.assertRaises(InvalidSnapshot):
            snapshot(index=99)

    def test_truncated_or_ambiguous_queue_rejected(self):
        with self.assertRaises(InvalidSnapshot):
            snapshot(items=[{"title": "Episode One", "rating_key": "11"}])
        with self.assertRaises(InvalidSnapshot):
            snapshot(items=[item()], shuffled="true")
        with self.assertRaises(InvalidSnapshot):
            snapshot(items=[item()], index=-1)
        with self.assertRaises(InvalidSnapshot):
            snapshot(items=[item()] * 5001)

    def test_movie_and_episode_guids_do_not_interchange(self):
        with self.assertRaises(InvalidSnapshot):
            QueueItem.from_dict(item("plex://movie/abc", kind="episode"))

    def test_mapped_queue_never_skips_unavailable_entries(self):
        source = snapshot()
        rows = map_window(source, 0, [copy(), None, copy(guid="plex://episode/ep2")])
        self.assertEqual([r["index"] for r in rows], [0, 1, 2])
        self.assertEqual([r["status"] for r in rows], ["ok", "unavailable", "ok"])
        self.assertEqual(rows[0]["source"], rows[1]["source"])
        with self.assertRaises(IndexError):
            map_window(source, 2, [copy(), copy()])


class QualityPolicyTests(unittest.TestCase):
    def setUp(self):
        self.copies = [
            copy(height=2160, rating_key="4k", library="TV Shows [4K]"),
            copy(height=1080, rating_key="hd", library="TV Shows"),
            copy(height=720, rating_key="sd", library="TV Shows"),
        ]

    def test_living_room_to_bedroom_selects_1080_copy(self):
        selected = select_media_copy(QueueItem.from_dict(item()), self.copies, DevicePolicy(1080))
        self.assertEqual(selected.rating_key, "hd")

    def test_bedroom_to_living_room_selects_4k_even_with_hdmi_ui_1080(self):
        selected = select_media_copy(QueueItem.from_dict(item()), self.copies, DevicePolicy(2160))
        self.assertEqual(selected.rating_key, "4k")

    def test_4k_only_content_is_not_silently_sent_to_1080_endpoint(self):
        selected = select_media_copy(QueueItem.from_dict(item()), [self.copies[0]], DevicePolicy(1080))
        self.assertIsNone(selected)

    def test_missing_equivalent_fails_closed(self):
        other = copy(guid="plex://episode/different", height=1080)
        self.assertIsNone(select_media_copy(QueueItem.from_dict(item()), [other], DevicePolicy(1080)))

    def test_different_episode_in_same_show_must_not_match(self):
        candidate = MediaCopy(guid="plex://episode/ep1", kind="episode", rating_key="other",
                              server_id="plex_a", library_title="TV Shows",
                              max_height=1080, season=2, episode=6)
        self.assertIsNone(select_media_copy(QueueItem.from_dict(item()), [candidate], DevicePolicy(1080)))

    def test_1080_target_accepts_lower_quality_if_1080_missing(self):
        chosen = select_media_copy(QueueItem.from_dict(item()), [self.copies[2]], DevicePolicy(1080))
        self.assertEqual(chosen.rating_key, "sd")

    def test_library_name_cannot_masquerade_as_actual_resolution(self):
        source = copy(height=1080, rating_key="fake", library="TV Shows [4K]")
        real = copy(height=2160, rating_key="real", library="TV Shows")
        selected = select_media_copy(QueueItem.from_dict(item()), [source, real], DevicePolicy(2160))
        self.assertEqual(selected.rating_key, "real")


if __name__ == "__main__":
    unittest.main()
