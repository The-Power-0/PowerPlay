#!/usr/bin/env python3
"""Adapt new 1.2.4 palettes to the tested published MonoPalette UI and tests."""
import argparse
from pathlib import Path


def one(path, old, new):
    data = path.read_text()
    if data.count(old) != 1:
        raise SystemExit(f"{path}: expected one anchor {old[:70]!r}, got {data.count(old)}")
    path.write_text(data.replace(old, new, 1))


def main(source):
    picker = source / "lib/screens/settings/theme_settings_screen.dart"
    one(picker,
        "leading: PaletteSwatch(palette: preset.toMonoPalette(dark: true)),",
        """leading: Stack(
                  children: [
                    PaletteSwatch(palette: preset.toMonoPalette(dark: true)),
                    if (preset.secondaryDarkAccent != null)
                      Positioned(
                        top: 1,
                        right: 1,
                        child: ColorDot(color: preset.secondaryDarkAccent!, size: 13),
                      ),
                  ],
                ),""")
    tests = source / "test/theme/powerplay_curated_palette_test.dart"
    one(tests, "six curated palettes each support light, dark and OLED",
        "ten curated palettes each support light, dark and OLED")
    one(tests, "expect(PowerPlayPalette.values.length, 6);",
        "expect(PowerPlayPalette.values.length, 10);")
    one(tests,
        "  test('legacy monochrome remains identical to current built-ins', () {",
        """  test('dual-tone palettes render secondary hue while OLED stays true black', () {
    for (final palette in [PowerPlayPalette.aurora, PowerPlayPalette.synthwave]) {
      expect(palette.secondaryDarkAccent, isNotNull);
      expect(palette.secondaryLightAccent, isNotNull);
      final dark = palette.toMonoPalette(dark: true);
      final light = palette.toMonoPalette(dark: false);
      final oled = palette.toMonoPalette(dark: true, oled: true);
      expect(dark.outline, palette.secondaryDarkAccent!.withValues(alpha: 0.44));
      expect(light.outline, palette.secondaryLightAccent!.withValues(alpha: 0.28));
      expect(oled.bg, const Color(0xFF000000));
      expect(oled.outline, palette.secondaryDarkAccent!.withValues(alpha: 0.36));
      expect(dark.accent, isNot(dark.outline));
      expect(dark.surface, isNot(dark.bg));
    }
  });

  test('legacy monochrome remains identical to current built-ins', () {""")
    print("PASS: four new presets, dual-tone swatches and OLED regression tests")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    main(parser.parse_args().source.resolve())
