import type { PageLoad } from './$types';
import { getChat, getChatMessages } from '$lib/api.js';

export const load: PageLoad = async ({ params }) => {
	const { session_id, chat_id } = params;
	const [chat, messages] = await Promise.all([
		getChat(session_id, chat_id),
		getChatMessages(session_id, chat_id)
	]);
	return { chat, messages };
};
