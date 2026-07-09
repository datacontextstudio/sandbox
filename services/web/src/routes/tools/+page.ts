export const ssr = false;

import type { PageLoad } from './$types';
import type { McpServer } from '$lib/api.js';
import { getMcpServers } from '$lib/api.js';

export const load: PageLoad = async () => {
	try {
		const servers = await getMcpServers();
		return { servers, error: null as string | null };
	} catch (e) {
		return { servers: [] as McpServer[], error: String(e) };
	}
};
