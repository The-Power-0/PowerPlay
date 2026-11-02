#!/usr/bin/env python3
"""Stage 12: avoid redundant Media3 native volume setter writes.

Do not coalesce seek, playback speed, play/pause, media generation or track
events: they carry ordering and recovery semantics even at equal values.
"""
from pathlib import Path
p=Path("android/app/src/main/kotlin/com/edde746/plezy/exoplayer/ExoPlayerCore.kt")
s=p.read_text(encoding="utf-8")
a=("  fun setVolume(volume: Float) {\n"
   "    exoPlayer?.volume = volume.coerceIn(0f, 1f)\n"
   "    delegate?.onPropertyChange(\"volume\", (volume * 100).toDouble())\n"
   "  }")
b=("  fun setVolume(volume: Float) {\n"
   "    val normalized = volume.coerceIn(0f, 1f)\n"
   "    // Skip redundant native player setter churn from rapid UI rerenders.\n"
   "    // Keep the property notification for Dart's observed state contract.\n"
   "    val player = exoPlayer\n"
   "    if (player != null && player.volume != normalized) player.volume = normalized\n"
   "    delegate?.onPropertyChange(\"volume\", (volume * 100).toDouble())\n"
   "  }")
if s.count(a)!=1: raise SystemExit("Media3 volume setter changed upstream")
p.write_text(s.replace(a,b), encoding="utf-8")
print("Media3 volume setter skips redundant writes and retains Dart notification.")
