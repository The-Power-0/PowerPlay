#!/usr/bin/env python3
"""Rebrand every selectable icon without renaming persistent icon IDs.
The approved PowerPlay SVG master remains the single source of truth.
After running, regenerate binaries with scripts/codegen/generate_app_icons.py.
"""
from __future__ import annotations
import xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/"assets/app_icons/source"
GLYPH=(ROOT/"assets/brand/powerplay-mark.svg").read_text(encoding="utf-8")
MONO=(ROOT/"assets/brand/powerplay-mark-monochrome.svg").read_text(encoding="utf-8")
LEGACY="M335.65,192.66"
def inner(svg:str)->str:
    return svg[svg.index("</defs>")+7:svg.rfind("</svg>")]
def defs(svg:str)->str:
    return svg[svg.index("<defs>"):svg.index("</defs>")+7]
def strip_plezy_background(svg:str)->str:
    """Remove any foreground Plezy silhouette that was baked into a theme backdrop."""
    root=ET.fromstring(svg)
    def recurse(parent):
        for child in list(parent):
            if child.tag.endswith("path") and LEGACY in child.attrib.get("d",""):
                parent.remove(child)
            else:recurse(child)
    recurse(root)
    ET.register_namespace("", "http://www.w3.org/2000/svg")
    return ET.tostring(root,encoding="unicode")
HEADER='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" width="1024" height="1024">'
def mark(art:str,scale:float)->str:
    return '<g transform="translate(512 512) scale('+str(scale)+') translate(-512 -512)">'+inner(art)+'</g>'
def run():
    count=0
    for folder in sorted(SOURCE.iterdir()):
        if not folder.is_dir() or not (folder/"background.svg").exists():continue
        background=strip_plezy_background((folder/"background.svg").read_text(encoding="utf-8"))
        (folder/"background.svg").write_text(background,encoding="utf-8")
        tv=folder/"tv_background.svg"
        if tv.exists():tv.write_text(strip_plezy_background(tv.read_text(encoding="utf-8")),encoding="utf-8")
        color=GLYPH
        if folder.name in {"paper","matcha","gold"}:
            color=GLYPH.replace('fill="url(#whiteSteel)"','fill="#132243"')
        (folder/"foreground.svg").write_text(HEADER+defs(color)+mark(color,.69)+"</svg>\n",encoding="utf-8")
        (folder/"monochrome.svg").write_text(HEADER+mark(MONO,.69)+"</svg>\n",encoding="utf-8")
        # Keep theme background and palette; only change the symbol in front.
        root=background.rsplit("</svg>",1)[0]
        (folder/"icon.svg").write_text(root+defs(color)+mark(color,.87)+"</svg>\n",encoding="utf-8")
        for filename in ("icon.svg","foreground.svg","monochrome.svg","background.svg"):
            assert LEGACY not in (folder/filename).read_text(encoding="utf-8"),(folder.name,filename)
        count+=1
    assert count==23, f"Expected 23 stable icon IDs, found {count}"
    print(f"Updated {count} alternate icon design sources")
if __name__=="__main__":run()
