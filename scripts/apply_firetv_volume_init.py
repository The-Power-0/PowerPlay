#!/usr/bin/env python3
"""Retain ExoPlayer volume requested before the native core is initialized."""
from pathlib import Path

path = Path("lib/mpv/player/platform/player_android.dart")
source = path.read_text(encoding="utf-8")


def replace_one(before: str, after: str) -> None:
    global source
    count = source.count(before)
    if count != 1:
        raise SystemExit(f"{path}: expected one anchor, found {count}: {before[:100]!r}")
    source = source.replace(before, after)


replace_one(
    "  bool _downmixNormalize = true;\n",
    "  bool _downmixNormalize = true;\n"
    "  double? _requestedVolume;\n",
)
replace_one(
    "      await invoke('setAudioDownmix', {\n"
    "        'enabled': _downmixEnabled,\n"
    "        'centerBoostDb': _downmixCenterBoostDb,\n"
    "        'normalize': _downmixNormalize,\n"
    "      });\n"
    "      if (disposed) throw StateError('Player was disposed during initialization');\n",
    "      await invoke('setAudioDownmix', {\n"
    "        'enabled': _downmixEnabled,\n"
    "        'centerBoostDb': _downmixCenterBoostDb,\n"
    "        'normalize': _downmixNormalize,\n"
    "      });\n"
    "      final pendingVolume = _requestedVolume;\n"
    "      if (pendingVolume != null) {\n"
    "        await invoke('setVolume', {'volume': pendingVolume});\n"
    "      }\n"
    "      if (disposed) throw StateError('Player was disposed during initialization');\n",
)
replace_one(
    "  Future<void> setVolume(double volume) async {\n"
    "    await invoke('setVolume', {'volume': volume});\n"
    "    if (!disposed) setVolumeState(volume);\n"
    "  }\n",
    "  Future<void> setVolume(double volume) async {\n"
    "    if (disposed) return;\n"
    "    _requestedVolume = volume;\n"
    "    await _applyWhenInitialized(\n"
    "      () => invoke('setVolume', {'volume': volume}),\n"
    "      () => _requestedVolume == volume,\n"
    "    );\n"
    "    if (!disposed && _requestedVolume == volume) setVolumeState(volume);\n"
    "  }\n",
)
path.write_text(source, encoding="utf-8")
print("ExoPlayer volume is retained until native initialization.")
