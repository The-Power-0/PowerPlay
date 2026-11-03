"""Plex API variant matching with no network access in unit tests."""

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
    if name not in sys.modules:
        module = types.ModuleType(name)
        module.__path__ = [str(path)]
        sys.modules[name] = module

from custom_components.powerlink.plex import parse_copies, parse_height  # noqa: E402


class PlexCatalogTests(unittest.TestCase):
    def test_actual_media_height_overrides_misleading_resolution(self):
        self.assertEqual(parse_height({"height": 1080, "videoResolution": "4k"}), 1080)
        self.assertEqual(parse_height({"videoResolution": "4k"}), 2160)
        self.assertEqual(parse_height({"videoResolution": "1080"}), 1080)
        self.assertEqual(parse_height({"videoResolution": "mystery"}), 0)

    def test_exact_guid_and_duplicate_library_copies(self):
        response = {
            "MediaContainer": {"Metadata": [
                {"type": "episode", "guid": "plex://episode/g1", "ratingKey": "81",
                 "librarySectionTitle": "TV Shows", "parentIndex": 2, "index": 5,
                 "Media": [{"height": 1080}]},
                {"type": "episode", "guid": "plex://episode/g1", "ratingKey": "82",
                 "librarySectionTitle": "TV Shows [4K]", "parentIndex": 2, "index": 5,
                 "Media": [{"height": 2160}]},
                {"type": "episode", "guid": "plex://episode/g2", "ratingKey": "83",
                 "librarySectionTitle": "TV Shows", "Media": [{"height": 1080}]},
                {"type": "episode", "guid": "plex://episode/g1", "ratingKey": "84",
                 "librarySectionTitle": "TV Shows", "Media": [{}]},
            ]}}
        copies = parse_copies(response, "plex_a", "plex://episode/g1")
        self.assertEqual([v.rating_key for v in copies], ["81", "82"])
        self.assertEqual([v.max_height for v in copies], [1080, 2160])
        self.assertEqual([(v.season, v.episode) for v in copies], [(2, 5), (2, 5)])

    def test_nonmatching_plex_guid_fails_closed(self):
        self.assertEqual(parse_copies(
            {"MediaContainer": {"Metadata": [{"guid": "plex://movie/g2",
                "type": "movie", "ratingKey": "22", "Media": [{"height": 2160}]}]}},
            "plex_a", "plex://movie/g1"), [])


if __name__ == "__main__":
    unittest.main()
