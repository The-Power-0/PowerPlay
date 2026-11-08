#!/usr/bin/env python3
"""Rebuild default PowerPlay branding from its editable Wave + Circuit SVG masters.
Requires: cairosvg and Pillow. Does not touch playback, app IDs, or signing.
Run from root: python scripts/branding/render_production_assets.py
Then run refresh_alternate_icons.py and scripts/codegen/generate_app_icons.py.
"""
from pathlib import Path
from io import BytesIO
from PIL import Image
import cairosvg

ROOT=Path(__file__).resolve().parents[2]
DIR=ROOT/"assets/brand"
MARK=(DIR/"powerplay-mark.svg").read_text(encoding="utf-8")
# The exact approved SVG is the only glyph source. The launcher adds a backdrop
# and safe-area placement, never redraws or simplifies any design detail.
def launcher_svg() -> str:
    inner=MARK[MARK.index("<defs>"):MARK.rfind("</svg>")]
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024" '
            f'viewBox="0 0 1024 1024"><rect width="1024" height="1024" '
            f'rx="168" fill="#05091F"/>'
            f'<g transform="translate(512 512) scale(.76) translate(-627 -627)">'
            f'{inner}</g></svg>')
ICON=launcher_svg()
MONO=MARK
FLAT=MARK
NAVY="#05091F"

def raster(svg,size):
    return Image.open(BytesIO(cairosvg.svg2png(bytestring=svg.encode(),
                  output_width=size[0],output_height=size[1]))).convert("RGBA")

def save(path,im):
    p=ROOT/path
    p.parent.mkdir(parents=True,exist_ok=True)
    if p.suffix==".webp": im.save(p,"WEBP",lossless=True,method=6,exact=True)
    elif p.suffix==".ico":
        im.save(p,"ICO",sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
    else: im.save(p,"PNG",optimize=True)

def mark_framed(size,scale):
    w,h=size
    output=Image.new("RGBA",size)
    n=round(min(w,h)*scale)
    icon=raster(MARK,(n,n))
    output.alpha_composite(icon,((w-n)//2,(h-n)//2))
    return output

def wide(size):
    w,h=size
    output=Image.new("RGBA",size,NAVY)
    n=round(h*1.08)
    icon=raster(MARK,(n,n))
    output.alpha_composite(icon,((w-n)//2,(h-n)//2))
    return output

def banner():
    d=MARK[MARK.index("<defs>"):MARK.index("</defs>")+7]
    b=MARK[MARK.index("</defs>")+7:MARK.rfind("</svg>")]
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="560" viewBox="0 0 1920 560">{d}
<defs><linearGradient id="word" x1="1200" y1="120" x2="1830" y2="450" gradientUnits="userSpaceOnUse"><stop stop-color="#00DDF9"/><stop offset=".5" stop-color="#1871FF"/><stop offset="1" stop-color="#E22AF6"/></linearGradient></defs>
<rect width="1920" height="560" rx="28" fill="#05091F"/>
<g transform="translate(30 27) scale(.40)">{b}</g>
<path d="M565 115 V442" stroke="#177BFB" stroke-width="3" opacity=".7"/>
<text x="611" y="302" font-family="DejaVu Sans,Arial,sans-serif" font-size="157" font-weight="900" font-style="italic" letter-spacing="-6" fill="white">POWER</text>
<text x="1220" y="302" font-family="DejaVu Sans,Arial,sans-serif" font-size="157" font-weight="900" font-style="italic" letter-spacing="-6" fill="url(#word)">PLAY</text>
<text x="659" y="391" font-family="DejaVu Sans,Arial,sans-serif" font-size="36" letter-spacing="6" fill="#C4D5F4">MEDIA  •  LIBRARIES  •  SHUFFLE  •  POWERLINK</text></svg>'''

def render():
    # Preserve the approved v10 SVG byte-for-byte as assets/brand/powerplay-mark.svg.
    lockup=banner()
    (DIR/"powerplay-app-icon.svg").write_text(ICON,encoding="utf-8")
    (DIR/"powerplay-mark-monochrome.svg").write_text(MARK,encoding="utf-8")
    (DIR/"powerplay-mark-flat.svg").write_text(MARK,encoding="utf-8")
    (DIR/"powerplay-banner.svg").write_text(lockup,encoding="utf-8")
    (ROOT/"docs/artwork").mkdir(parents=True,exist_ok=True)
    (ROOT/"docs/artwork/powerplay-banner.svg").write_text(lockup,encoding="utf-8")
    (ROOT/"docs/artwork/powerplay-icon.svg").write_text(MARK,encoding="utf-8")
    for n in (64,128,256,512,1024,2048):
        save(f"assets/brand/renders/powerplay-mark-{n}.png",raster(MARK,(n,n)))
    for n in (128,512,1024):
        save(f"assets/brand/renders/powerplay-icon-{n}.png",raster(ICON,(n,n)))
    save("assets/brand/renders/powerplay-monochrome-512.png",raster(MONO,(512,512)))
    save("assets/brand/renders/powerplay-mark-flat-512.png",raster(FLAT,(512,512)))
    for n in (1920,3840):
        save(f"assets/brand/renders/powerplay-banner-{n}.png",raster(lockup,(n,int(n*560/1920))))
    save("docs/artwork/powerplay-banner.webp",raster(lockup,(1920,560)))
    save("docs/artwork/powerplay-icon.webp",raster(ICON,(512,512)))
    for name in ("powerplay.png","plezy.png","powerplay_splash.png"):
        save("assets/"+name,raster(MARK,(1024,1024)))
    (ROOT/"assets/plezy.svg").write_text(MARK,encoding="utf-8")
    (ROOT/"assets/plezy_adaptive_foreground.svg").write_text(FLAT,encoding="utf-8")
    save("android/app/src/main/res/drawable-nodpi/powerplay_foreground.png",mark_framed((1024,1024),.72))
    save("android/app/src/main/res/drawable-nodpi/powerplay_splash_foreground.png",mark_framed((1024,1024),.75))
    for d,n in (("mdpi",48),("hdpi",72),("xhdpi",96),("xxhdpi",144),("xxxhdpi",192)):
        save(f"android/app/src/main/res/mipmap-{d}/ic_launcher.png",raster(ICON,(n,n)))
    for d,size in (("xhdpi",(640,360)),("xxhdpi",(960,540)),("xxxhdpi",(1280,720))):
        save(f"android/app/src/main/res/drawable-{d}/tv_banner.png",wide(size))
    for d,n in (("mdpi",24),("hdpi",36),("xhdpi",48)):
        save(f"android/app/src/main/res/drawable-{d}/ic_stat_notification.png",raster(MONO,(n,n)))
    for tag,size in (("",(400,240)),("@2x",(800,480))):
        root="tvos/Runner/Assets.xcassets/AppIcon.brandassets/App Icon.imagestack/"
        save(root+"Back.imagestacklayer/Content.imageset/Back"+tag+".png",Image.new("RGBA",size,NAVY))
        save(root+"Front.imagestacklayer/Content.imageset/Front"+tag+".png",mark_framed(size,.65))
        save(root+"Middle.imagestacklayer/Content.imageset/Middle"+tag+".png",Image.new("RGBA",size))
    root="tvos/Runner/Assets.xcassets/AppIcon.brandassets/App Icon - App Store.imagestack/"
    sz=(1280,768)
    save(root+"Back.imagestacklayer/Content.imageset/Back.png",Image.new("RGBA",sz,NAVY))
    save(root+"Front.imagestacklayer/Content.imageset/Front.png",mark_framed(sz,.65))
    save(root+"Middle.imagestacklayer/Content.imageset/Middle.png",Image.new("RGBA",sz))
    for fn,size in (("top-shelf.png",(1920,720)),("top-shelf-wide.png",(2320,720)),("top-shelf-wide@2x.png",(4640,1440))):
        folder="Top Shelf Image Wide.imageset/" if "wide" in fn else "Top Shelf Image.imageset/"
        save("tvos/Runner/Assets.xcassets/AppIcon.brandassets/"+folder+fn,wide(size))
    save("windows/runner/resources/app_icon.ico",raster(ICON,(256,256)))
    social=Image.new("RGBA",(1200,630),NAVY)
    social.alpha_composite(raster(lockup,(1200,350)),(0,140))
    save("website/static/og/powerplay-social.png",social)
    catalog=ROOT/"ios/Runner/Assets.xcassets/AppIcon.appiconset"
    if catalog.exists():
        for f in catalog.glob("*.png"):
            with Image.open(f) as im: sz=im.size
            save(f.relative_to(ROOT),raster(ICON,sz))
    print("Rendered PowerPlay vector-derived production branding.")

if __name__=="__main__":
    render()
