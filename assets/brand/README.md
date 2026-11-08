# PowerPlay Wave + Circuit brand (review master)

## Approved concept
The user-approved raster remains the visual reference. These editable SVG masters recreate its rounded right-facing play triangle, optically left-shifted white P, flowing background bands, and circuit-only lightning bolt without a heartbeat/pulse motif. The color direction is diagonally cyan (upper left) through blue and violet to magenta (lower right).

The SVG masters are vector recreations, not pixel-identical automatic traces of the raster reference. Review SVG and generated PNGs side by side before release.

- `powerplay-mark.svg`: transparent master for glyphs and splash.
- `powerplay-mark-flat.svg`: simplified high-legibility icon.
- `powerplay-mark-monochrome.svg`: true one-color silhouette.
- `powerplay-app-icon.svg`: Fire TV/Android launcher tile.
- `powerplay-banner.svg`: generated README banner.
- `renders/`: generated PNG exports.

Run `python scripts/branding/render_production_assets.py`, `python scripts/branding/refresh_alternate_icons.py`, then `python scripts/codegen/generate_app_icons.py`. Stable IDs, signing identity, package name, playback logic and PowerLink protocol are not changed. Do not publish before review.
