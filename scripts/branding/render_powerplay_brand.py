#!/usr/bin/env python3
"""Regenerate PowerPlay's platform artwork and alternate icons from approved SVG masters.
Requires cairosvg and Pillow. Run before scripts/codegen/generate_app_icons.py.
No package IDs, icon IDs, app data or playback code are modified.
"""
from __future__ import annotations
from copy import deepcopy
from io import BytesIO
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import cairosvg
from PIL import Image, ImageOps
ROOT=Path(__file__).resolve().parents[2]
BRAND=ROOT/"branding"
GLYPH=(BRAND/"powerplay-glyph.svg").read_text()
APP=(BRAND/"powerplay-app-icon.svg").read_text()
MONO=(BRAND/"powerplay-monochrome.svg").read_text()
BANNER=(BRAND/"powerplay-banner.svg").read_text()
OUT=ROOT
NS="{http://www.w3.org/2000/svg}"
def raster(svg:str,size:tuple[int,int])->Image.Image:
    return Image.open(BytesIO(cairosvg.svg2png(bytestring=svg.encode(),output_width=size[0],output_height=size[1]))).convert("RGBA")
def save_png(path:Path,im:Image.Image):
    path.parent.mkdir(parents=True,exist_ok=True)
    im.convert("RGBA").save(path,format="PNG",optimize=True)
def render_file(path:str,source:str,size:tuple[int,int]|None=None):
    f=OUT/path
    if size is None:
        if f.exists():
            with Image.open(f) as img: size=img.size
        else: size=(512,512)
    save_png(f,raster(source,size))
def svg_inner(source:str)->str:
    return source[source.find("</defs>")+7:source.rfind("</svg>")]
def replace_legacy_path(source:str)->str:
    # Old upstream Plezy triangle path is occasionally embedded in alt-icon backdrops as a glow.
    root=ET.fromstring(source)
    def clean(parent):
        for child in list(parent):
            if child.tag.endswith("path") and "M335.65,192.66" in child.attrib.get("d",""):
                parent.remove(child)
            else:clean(child)
    clean(root)
    return ET.tostring(root,encoding="unicode").replace("ns0:","").replace("xmlns:ns0=","xmlns=")
def change_alternates():
    root=OUT/"assets/app_icons/source"
    for folder in sorted(root.iterdir()):
        if not folder.is_dir() or not (folder/"background.svg").exists():continue
        bg=replace_legacy_path((folder/"background.svg").read_text())
        if bg!=(folder/"background.svg").read_text(): (folder/"background.svg").write_text(bg)
        tv=folder/"tv_background.svg"
        if tv.exists():
            v=replace_legacy_path(tv.read_text())
            if v!=tv.read_text(): tv.write_text(v)
        # Keep each named theme and its backdrop, replacing the legacy foreground on every platform.
        simple=folder.name in {"paper","matcha","gold"}
        mark=GLYPH if not simple else GLYPH.replace('fill="url(#steel)"','fill="#132243"')
        transformed='<g transform="translate(512 512) scale(.69) translate(-512 -512)">'+svg_inner(mark)+'</g>'
        header='<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024" viewBox="0 0 1024 1024">'
        (folder/"foreground.svg").write_text(header+mark[mark.index("<defs>"):mark.index("</defs>")+7]+transformed+"</svg>\n")
        alt=bg.replace("</svg>","")+mark[mark.index("<defs>"):mark.index("</defs>")+7]+'<g transform="translate(512 512) scale(.87) translate(-512 -512)">'+svg_inner(mark)+'</g></svg>\n'
        (folder/"icon.svg").write_text(alt)
        (folder/"monochrome.svg").write_text(header+'<g transform="translate(512 512) scale(.69) translate(-512 -512)">'+svg_inner(MONO)+'</g></svg>\n')
    print("Replaced all legacy alternate-icon foregrounds without renaming icon IDs")
def generated():
    render_file("assets/powerplay.png",GLYPH)
    render_file("assets/powerplay_splash.png",GLYPH)
    # Compatibility alias paths still referenced by upstream Flutter imports; their pixels are PowerPlay.
    render_file("assets/plezy.png",GLYPH)
    (OUT/"assets/plezy.svg").write_text(GLYPH)
    (OUT/"assets/plezy_adaptive_foreground.svg").write_text(GLYPH)
    for fn in ("powerplay_foreground.png","powerplay_splash_foreground.png"):
        render_file("android/app/src/main/res/drawable-nodpi/"+fn,GLYPH)
    for suffix,s in {"mdpi":48,"hdpi":72,"xhdpi":96,"xxhdpi":144,"xxxhdpi":192}.items():
        render_file("android/app/src/main/res/mipmap-"+suffix+"/ic_launcher.png",APP,(s,s))
    for suffix,size in {"xhdpi":(640,360),"xxhdpi":(960,540),"xxxhdpi":(1280,720)}.items():
        render_file("android/app/src/main/res/drawable-"+suffix+"/tv_banner.png",BANNER,size)
    (OUT/"docs/artwork").mkdir(parents=True,exist_ok=True)
    raster(APP,(512,512)).save(OUT/"docs/artwork/powerplay-icon.webp","WEBP",quality=95)
    raster(BANNER,(1280,373)).convert("RGB").save(OUT/"docs/artwork/powerplay-banner.webp","WEBP",quality=95)
    for root in (OUT/"ios/Runner/Assets.xcassets/AppIcon.appiconset",OUT/"macos/Runner/Assets.xcassets/AppIcon.appiconset"):
        if root.exists():
            for f in root.glob("*.png"):
                with Image.open(f) as img: size=img.size
                save_png(f,raster(APP,size))
    tv=OUT/"tvos/Runner/Assets.xcassets/AppIcon.brandassets"
    if tv.exists():
        for f in tv.rglob("*.png"):
            with Image.open(f) as img: size=img.size
            n=f.name.lower()
            if "back" in n:
                art='<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024" viewBox="0 0 1024 1024"><rect width="1024" height="1024" fill="#080C27"/></svg>'
            elif "middle" in n:
                art='<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024" viewBox="0 0 1024 1024"></svg>'
            elif "top-shelf" in n or "topshelf" in n:art=BANNER
            else:art=GLYPH
            save_png(f,raster(art,size))
    f=OUT/"windows/runner/resources/app_icon.ico"
    if f.exists():
        f.parent.mkdir(parents=True,exist_ok=True)
        raster(APP,(256,256)).save(f,format="ICO",sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
    # Default Android launcher vector is an older Plezy mark; update it in place.
    av=OUT/"android/app/src/main/res/drawable/ic_launcher_foreground.xml"
    av.write_text('''<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="108dp" android:height="108dp"
    android:viewportWidth="1024" android:viewportHeight="1024">
    <path android:fillColor="#07C9F5" android:strokeColor="#07C9F5"
       android:strokeWidth="25" android:strokeLineJoin="round"
       android:pathData="M242,172 L827,510 L242,848 Z"/>
    <path android:fillColor="#07112D"
       android:pathData="M267,226 L782,510 L267,794 Z"/>
    <path android:fillColor="#FFFFFF"
       android:pathData="M337,353 H575 C668,353 707,400 701,471 C695,546 649,580 558,580 H479 L518,518 H565 C613,518 632,493 630,466 C628,435 607,420 565,420 H337 Z"/>
    <path android:fillColor="#00E7F3"
       android:pathData="M451,422 L348,565 H424 L342,762 L576,492 H492 L536,422 Z"/>
</vector>
''')
if __name__=="__main__":
    change_alternates()
    generated()
    print("Rendered PowerPlay images, default platform icons, and alternate source designs")
