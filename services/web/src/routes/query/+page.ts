export const ssr = false;

import type { PageLoad } from './$types';
import type { McpServer } from '$lib/api.js';
import { getCollections, getMcpServers } from '$lib/api.js';

export const load: PageLoad = async () => {
	const [collectionsResult, serversResult] = await Promise.all([
		getCollections().catch(() => ({ collections: [] as string[] })),
		getMcpServers().catch(() => [] as McpServer[])
	]);
	return { collections: collectionsResult.collections, servers: serversResult };
};
