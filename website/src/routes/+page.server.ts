import type { PageServerLoad } from './$types';

// PowerPlay does not sell through the upstream Plezy app-store listings.
// Do not fetch, cache, or display the upstream product's store prices/ratings.
export const load: PageServerLoad = async () => ({});
