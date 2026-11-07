#!/usr/bin/env python3
"""Pre-release audit of customer-facing PowerPlay branding. Do not erase upstream attribution."""
from __future__ import annotations
from pathlib import Path
import json,re
ROOT=Path(__file__).resolve().parents[2]
LOCALE=ROOT/"lib/i18n"
locales=sorted(LOCALE.glob("*.i18n.json"))
assert len(locales)>=20,f"Missing translations: {len(locales)}"
def values(j):
    if isinstance(j,str):yield j
    elif isinstance(j,list):
        for v in j:yield from values(v)
    elif isinstance(j,dict):
        for v in j.values():yield from values(v)
for file in locales:
    for s in values(json.loads(file.read_text(encoding="utf-8"))):
        assert not re.search(r'plezy',s,re.I),(file,s)
for file in [ROOT/"ios/Runner/Info.plist",ROOT/"tvos/Runner/Info.plist"]:
    content=file.read_text(encoding="utf-8")
    assert "<string>PowerPlay</string>" in content,file
    assert "<string>Plezy</string>" not in content,file
for p in [ROOT/"website/src/routes/+page.svelte",ROOT/"website/src/routes/+layout.svelte",ROOT/"website/src/lib/components/PageMetadata.svelte"]:
    assert "/og/plezy-social.png" not in p.read_text(encoding="utf-8"),p
assert (ROOT/"website/static/og/powerplay-social.png").is_file()
icons=sorted((ROOT/"assets/app_icons/source").glob("*/foreground.svg"))
assert len(icons)==23,len(icons)
for file in (ROOT/"assets/app_icons/source").rglob("*.svg"):
    assert "M335.65,192.66" not in file.read_text(encoding="utf-8"),file
assert (ROOT/"assets/brand/powerplay-mark.svg").exists()
assert (ROOT/"assets/brand/powerplay-app-icon.svg").exists()
assert "applicationId = \"com.power.powerplay\"" in (ROOT/"android/app/build.gradle.kts").read_text(encoding="utf-8")
assert "Plezy" in (ROOT/"UPSTREAM-README.md").read_text(encoding="utf-8"),"Retain upstream attribution"
print(f"Brand audit passed: {len(locales)} locales, 23 alternate icons, website and native labels")
