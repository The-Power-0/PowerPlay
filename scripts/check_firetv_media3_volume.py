#!/usr/bin/env python3
from pathlib import Path
s=Path("android/app/src/main/kotlin/com/edde746/plezy/exoplayer/ExoPlayerCore.kt").read_text(encoding="utf-8")
for marker in ('if (player != null && player.volume != normalized) player.volume = normalized','delegate?.onPropertyChange("volume", (volume * 100).toDouble())','fun seekTo(positionMs: Long)','fun setPlaybackSpeed(speed: Float)'):
    if marker not in s: raise SystemExit("Media3 guard changed: "+marker)
print("Media3 idempotent-volume source check passed.")
