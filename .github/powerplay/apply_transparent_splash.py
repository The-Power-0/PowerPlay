#!/usr/bin/env python3
"""PowerPlay 1.2.4: losslessly preserve logo art while removing splash-only dark matte.

Uses Python's PNG/deflate standard library (no network/pip). Launcher PNG is
left unchanged; separate RGBA assets are used only by Flutter and Android splashes.
"""
import argparse
import binascii
import struct
import zlib
from pathlib import Path

SIGNATURE = b"\x89PNG\r\n\x1a\n"


def chunk(kind, payload):
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(
        ">I", binascii.crc32(kind + payload) & 0xffffffff
    )


def rgb_png(path):
    data = path.read_bytes()
    if not data.startswith(SIGNATURE):
        raise ValueError(f"not PNG: {path}")
    position = len(SIGNATURE)
    payloads = []
    width = height = None
    while position + 12 <= len(data):
        length = struct.unpack_from(">I", data, position)[0]
        kind = data[position + 4:position + 8]
        payload = data[position + 8:position + 8 + length]
        crc = struct.unpack_from(">I", data, position + 8 + length)[0]
        if binascii.crc32(kind + payload) & 0xffffffff != crc:
            raise ValueError(f"PNG CRC error: {kind!r}")
        position += length + 12
        if kind == b"IHDR":
            width, height, depth, color, comp, filt, interlace = struct.unpack(">IIBBBBB", payload)
            if (depth, color, comp, filt, interlace) != (8, 2, 0, 0, 0):
                raise ValueError("Source must be 8-bit, noninterlaced RGB PNG")
        elif kind == b"IDAT":
            payloads.append(payload)
        elif kind == b"IEND":
            break
    if not width or not height:
        raise ValueError("PNG has no dimensions")
    raw = zlib.decompress(b"".join(payloads))
    stride = width * 3
    offset = 0
    rows = []
    prev = bytearray(stride)
    for _ in range(height):
        f = raw[offset]
        offset += 1
        row = bytearray(raw[offset:offset + stride])
        offset += stride
        if len(row) != stride:
            raise ValueError("Truncated PNG")
        for i in range(stride):
            a = row[i - 3] if i >= 3 else 0
            b = prev[i]
            c = prev[i - 3] if i >= 3 else 0
            if f == 1:
                row[i] = (row[i] + a) & 255
            elif f == 2:
                row[i] = (row[i] + b) & 255
            elif f == 3:
                row[i] = (row[i] + ((a + b) // 2)) & 255
            elif f == 4:
                predict = a + b - c
                distances = (abs(predict - a), abs(predict - b), abs(predict - c))
                predictor = (a, b, c)[distances.index(min(distances))]
                row[i] = (row[i] + predictor) & 255
            elif f != 0:
                raise ValueError(f"Unknown PNG filter {f}")
        rows.append(row)
        prev = row
    if offset != len(raw):
        raise ValueError("Unexpected PNG data tail")
    return width, height, rows


def make_transparent(source, dest):
    width, height, rows = rgb_png(source)
    raw = bytearray()
    transparent = opaque = 0
    for row in rows:
        out = bytearray()
        for p in range(0, len(row), 3):
            r, g, b = row[p:p + 3]
            # Original icon was rendered onto the approx (4, 7, 15) matte.
            # A modest noise floor avoids a faint background rectangle while
            # partial alpha softens the outline's antialiased edge.
            strength = max(r - 4, g - 7, b - 15)
            alpha = max(0, min(255, round((strength - 15) * 255 / 65)))
            if alpha == 0:
                out.extend((0, 0, 0, 0))
                transparent += 1
            else:
                if alpha == 255:
                    opaque += 1
                # Unblend the original matte for correct rendering on light,
                # OLED and multicolor backgrounds. Keep original RGB if opaque.
                inv = 255 - alpha
                rgb = [
                    max(0, min(255, round((channel * 255 - matte * inv) / alpha)))
                    for channel, matte in ((r, 4), (g, 7), (b, 15))
                ]
                out.extend((*rgb, alpha))
        raw.extend(b"\0")
        raw.extend(out)
    if transparent < width * height // 3 or opaque < width * height // 10:
        raise ValueError("Suspicious transparency mask; original logo may have changed")
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    result = SIGNATURE + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b"")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(result)
    print(f"Transparent splash: {source.name} -> {dest.name} ({width}x{height}, {transparent} transparent pixels)")


def change_once(path, before, after):
    contents = path.read_text()
    if contents.count(before) != 1:
        raise ValueError(f"{path}: expected one matching anchor, found {contents.count(before)}")
    path.write_text(contents.replace(before, after, 1))


def main(root):
    make_transparent(root / "assets/powerplay.png", root / "assets/powerplay_splash.png")
    native = root / "android/app/src/main/res"
    make_transparent(
        native / "drawable-nodpi/powerplay_foreground.png",
        native / "drawable-nodpi/powerplay_splash_foreground.png",
    )
    main_dart = root / "lib/main.dart"
    original = main_dart.read_text()
    old = "Image.asset('assets/powerplay.png'"
    if original.count(old) != 2:
        raise ValueError("Expected two Flutter splash logo references")
    main_dart.write_text(original.replace(old, "Image.asset('assets/powerplay_splash.png'"))
    change_once(root / "pubspec.yaml", "    - assets/powerplay.png\n",
                "    - assets/powerplay.png\n    - assets/powerplay_splash.png\n")
    change_once(native / "drawable/splash_icon.xml",
                'android:drawable="@drawable/powerplay_foreground"',
                'android:drawable="@drawable/powerplay_splash_foreground"')
    change_once(native / "drawable/powerplay_launch_background.xml",
                'android:src="@drawable/powerplay_foreground"',
                'android:src="@drawable/powerplay_splash_foreground"')
    # Adaptive launcher remains the original opaque icon and is never altered.
    assert '@drawable/powerplay_foreground' in (
        native / "mipmap-anydpi-v26/ic_launcher.xml").read_text()
    print("PASS: Flutter/Android startup logos transparent; launcher unchanged")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    main(parser.parse_args().source.resolve())
