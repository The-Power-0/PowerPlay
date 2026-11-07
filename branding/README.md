# PowerPlay 2.0.0 branding (release candidate)

- **Glyph:** `powerplay-glyph.svg` is a true right-facing equilateral play triangle with a white P and cyan lightning bolt.
- **App icon:** `powerplay-app-icon.svg` uses a deep navy plate and a blue-to-purple accent border.
- **Banner:** `powerplay-banner.svg` is the long-form PowerPlay lockup.
- **Monochrome:** `powerplay-monochrome.svg` for small controls and accessibility.
- **Rendering:** `python scripts/branding/render_powerplay_brand.py` regenerates default Android, iOS, tvOS, macOS, Windows and Flutter assets and replaces original Plezy glyphs in all 23 existing alternate-icon styles. Follow with `python scripts/codegen/generate_app_icons.py` to build all 23 icon variants and picker previews. Existing icon IDs and settings remain unchanged.

Palette: navy #080C27, cyan #00F3F6, blue #117AF9, purple #7460FF, magenta #E322F6. Use high-contrast flat glyphs in controls and keep strong glow primarily in promotional art.

**Compatibility policy:** Retain `com.power.powerplay`, existing PowerLink APIs, user data, signing identity and all application/deep-link IDs used by running clients. Legacy internal `plezy` filenames, Dart package/import names, native package paths, plugin channels, and legally required upstream attribution may remain where changing them would break software. Their visible images and display strings must instead use PowerPlay.
