# PowerPlay brand assets — 2.0.0 candidate

The primary mark is a **right-facing equilateral play triangle** surrounding a white P and a cyan lightning strike. It is intentionally related to, but visually distinct from, PowerLink's paired-link mark.

* `powerplay-mark.svg`: luminous transparent primary glyph.
* `powerplay-mark-monochrome.svg`: single-color fallback for toolbar and accessibility use.
* `powerplay-app-icon.svg`: dark navy rounded-square app icon.
* `powerplay-banner.svg`: official GitHub masthead.
* The Android launcher, splash, Fire TV banners, platform icon layers, Flutter assets, and documentation imagery are generated from these approved masters.

Color roles: PowerPlay uses white, cyan, electric blue and **purple**; PowerLink uses white, cyan and **blue** with restrained shared accents. Use flat assets at small UI sizes, rather than blurred glow.

**Compatibility:** keep `com.power.powerplay`, `powerplay://`, existing queue state keys and all PowerLink/PowerShuffle protocols unchanged. Internal `plezy` identifiers inherited from the upstream fork are not public branding and must only be renamed with comprehensive import/native tests. Preserve GPL attribution, original copyright notices and upstream-source provenance.
