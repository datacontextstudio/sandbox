import type { LayoutLoad } from './$types';
import { getSession, listChats } from '$lib/api.js';

export const ssr = false;

export const load: LayoutLoad = async ({ params }) => {
	const { session_id } = params;
	const [session, chats] = await Promise.all([
		getSession(session_id),
		listChats(session_id)
	]);
	return { session, chats };
};
