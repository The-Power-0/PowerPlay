import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:plezy/theme/mono_theme.dart';
import 'package:plezy/theme/powerplay_palette_release_adapter.dart';

void main() {
  test('ten curated palettes each support light, dark and OLED', () {
    expect(PowerPlayPalette.values.length, 10);
    final colors = <Color>{};
    for (final palette in PowerPlayPalette.values) {
      final light = palette.toMonoPalette(dark: false);
      final dark = palette.toMonoPalette(dark: true);
      final oled = palette.toMonoPalette(dark: true, oled: true);
      expect(light.brightness, Brightness.light);
      expect(dark.brightness, Brightness.dark);
      expect(oled.bg, const Color(0xFF000000));
      expect(monoTheme(oled).scaffoldBackgroundColor, const Color(0xFF000000));
      expect(colors.add(dark.accent), isTrue);
    }
  });

  test('dual-tone palettes render secondary hue while OLED stays true black', () {
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

  test('legacy monochrome remains identical to current built-ins', () {
    expect(PowerPlayPalette.monochrome.toMonoPalette(dark: false), MonoPalette.light);
    expect(PowerPlayPalette.monochrome.toMonoPalette(dark: true), MonoPalette.dark);
    expect(PowerPlayPalette.monochrome.toMonoPalette(dark: true, oled: true), MonoPalette.oled);
  });

  test('cached themes share identity for the same resolved palette', () {
    final one = PowerPlayPalette.signaturePurple.toMonoPalette(dark: true, oled: true);
    final two = PowerPlayPalette.signaturePurple.toMonoPalette(dark: true, oled: true);
    expect(identical(monoTheme(one), monoTheme(two)), isTrue);
  });
}
