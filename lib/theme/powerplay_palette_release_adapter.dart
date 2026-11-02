import 'mono_theme.dart';
import 'powerplay_palette.dart';

export 'powerplay_palette.dart';

/// Use the existing published MonoPalette theme builder and its cache.
extension PowerPlayPaletteReleaseAdapter on PowerPlayPalette {
  MonoPalette toMonoPalette({required bool dark, bool oled = false}) {
    final c = colors(dark: dark, oled: oled);
    return MonoPalette(
      bg: c.background,
      surface: c.surface,
      outline: c.outline,
      text: c.text,
      textMuted: c.textMuted,
      accent: c.accent,
    );
  }
}
