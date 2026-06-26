export const ssr = false;

import type { PageLoad } from './$types';
import { getCollections } from '$lib/api.js';

export const load: PageLoad = async () => {
	try {
		const data = await getCollections();
		return { collections: data.collections };
	} catch {
		return { collections: [] as string[] };
	}
};
