import type { PageLoad } from './$types';
import { getSession, getMessages } from '$lib/api.js';

export const ssr = false;

export const load: PageLoad = async ({ params }) => {
	const { session_id } = params;
	try {
		const [session, messages] = await Promise.all([
			getSession(session_id),
			getMessages(session_id)
		]);
		return { session, messages };
	} catch (e) {
		return { session: null, messages: [], error: String(e) };
	}
};
