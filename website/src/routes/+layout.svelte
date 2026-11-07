<script lang="ts">
	import './layout.css';
	import favicon from '$lib/assets/favicon.svg';

	let { children } = $props();

	const siteSchema = {
		"@context": "https://schema.org",
		"@type": "WebSite",
		"name": "PowerPlay",
		"url": "https://github.com/The-Power-0/PowerPlay"
	};

	const orgSchema = {
		"@context": "https://schema.org",
		"@type": "Organization",
		"name": "PowerPlay",
		"url": "https://github.com/The-Power-0/PowerPlay",
		"logo": "https://raw.githubusercontent.com/The-Power-0/PowerPlay/main/website/static/og/powerplay-social.png",
		"sameAs": ["https://github.com/The-Power-0/PowerPlay"]
	};
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	{@html `<script type="application/ld+json">${JSON.stringify(siteSchema)}</script>`}
	{@html `<script type="application/ld+json">${JSON.stringify(orgSchema)}</script>`}
</svelte:head>
{@render children()}
