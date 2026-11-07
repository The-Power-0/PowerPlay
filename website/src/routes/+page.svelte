<script lang="ts">
  import PageMetadata from '$lib/components/PageMetadata.svelte';

  const title = 'PowerPlay — Plex on Fire TV';
  const description =
    'PowerPlay is an independently maintained Plex-focused Fire TV player with PowerShuffle, Home Assistant control, and PowerLink room-to-room queue transfers.';
  const url = 'https://github.com/The-Power-0/PowerPlay';
</script>

<PageMetadata {title} {description} {url} />

<main class="site-shell">
  <div class="hero">
    <img class="hero-art" src="/og/plezy-social.png" alt="PowerPlay blue-purple logo and play glyph" />
    <p class="eyebrow">POWERPLAY 2.0 · VISUAL REBRAND CANDIDATE</p>
    <h1>Your Plex library, powered for Fire TV.</h1>
    <p class="intro">Designed for responsive playback, simple D-pad navigation, intelligent PowerShuffle rotations, and seamless transfers between paired rooms.</p>
    <div class="actions">
      <a class="primary" href="https://github.com/The-Power-0/PowerPlay/releases/latest" target="_blank" rel="noopener noreferrer">Get the latest stable APK</a>
      <a class="secondary" href="https://github.com/The-Power-0/PowerLink" target="_blank" rel="noopener noreferrer">Explore PowerLink</a>
    </div>
    <p class="availability">Official downloads are provided through GitHub Releases. The visual 2.0.0 release is under review and is not published yet. We do not claim ownership of upstream mobile or desktop store listings.</p>
  </div>
  <section class="details" aria-label="PowerPlay features">
    <article><h2>PowerShuffle</h2><p>Smarter, separately tracked Plex episode rotation with Home Assistant managing the logical queue.</p></article>
    <article><h2>PowerLink</h2><p>Transfer a playing queue and position to a paired Fire Stick, including supported 1080p and 4K copies.</p></article>
    <article><h2>Fire TV performance</h2><p>Focused player startup, device handling, D-pad navigation, and native ExoPlayer playback.</p></article>
  </section>
  <footer>PowerPlay is an independent GPL-3.0-licensed derivative of <a href="https://github.com/edde746/plezy">Plezy</a>. Unaffiliated with Plex, Plezy or Amazon. Original notices and attributions are retained.</footer>
</main>

<style>
  :global(body) { background: #030718; color: #f8fbff; }
  .site-shell { max-width: 1160px; margin: 0 auto; padding: clamp(1rem, 3vw, 3rem); font-family: system-ui, sans-serif; }
  .hero { padding: 2rem 0 4rem; }
  .hero-art { display: block; width: 100%; max-width: 1060px; height: auto; border-radius: 20px; }
  .eyebrow { font-size: .75rem; font-weight: 800; letter-spacing: .2em; color: #00e3f7; margin: 1.8rem 0 .8rem; }
  h1 { font-size: clamp(2.2rem, 5.4vw, 4.7rem); line-height: 1.06; font-weight: 850; letter-spacing: -.05em; margin: 0 0 1rem; }
  .intro { color: #bbd0ed; max-width: 700px; font-size: clamp(1rem,1.8vw,1.25rem); line-height: 1.65; }
  .actions { display: flex; flex-wrap: wrap; gap: .8rem; margin: 2rem 0 1.5rem; }
  .actions a { border-radius: 999px; padding: .85rem 1.3rem; text-decoration: none; font-weight: 750; }
  .primary { background: linear-gradient(110deg,#04daf2,#2379ff,#a137ff); color: #02061a; }
  .secondary { color: #f8fbff; border: 1px solid #38608d; }
  .availability { color: #9aafd1; max-width: 780px; font-size: .85rem; line-height: 1.65; }
  .details { display: grid; grid-template-columns: repeat(3,minmax(0,1fr)); gap: 1rem; margin-bottom: 4rem; }
  .details article { padding: 1.25rem; border: 1px solid #263f70; border-radius: 18px; background: #0a1335; }
  .details h2 { font-size: 1.13rem; margin: 0 0 .5rem; }
  .details p { color: #bfd0ea; line-height: 1.55; }
  footer { color: #849abe; font-size: .85rem; padding: 2rem 0; border-top: 1px solid #263f70; }
  footer a { color: #41c8fe; }
  @media (max-width: 740px) { .details { grid-template-columns: 1fr; } }
</style>
