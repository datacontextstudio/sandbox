const INTERNAL_BASE = '/internal-api';
const API_BASE = '/api';

export interface Session {
	id: string;
	collections: string[];
	created_at: string;
}

export interface Chat {
	id: string;
	session_id: string;
	title: string | null;
	created_at: string;
}

export interface Message {
	id: string;
	chat_id: string;
	role: 'user' | 'assistant';
	content: string;
	created_at: string;
}

async function handleResponse<T>(res: Response): Promise<T> {
	if (!res.ok) {
		const text = await res.text().catch(() => res.statusText);
		throw new Error(`${res.status}: ${text}`);
	}
	return res.json() as Promise<T>;
}

export async function getSession(sessionId: string): Promise<Session> {
	const res = await fetch(`${INTERNAL_BASE}/sessions/${sessionId}`);
	return handleResponse<Session>(res);
}

export async function listChats(sessionId: string): Promise<Chat[]> {
	const res = await fetch(`${INTERNAL_BASE}/sessions/${sessionId}/chats`);
	return handleResponse<Chat[]>(res);
}

export async function createChat(sessionId: string): Promise<Chat> {
	const res = await fetch(`${INTERNAL_BASE}/sessions/${sessionId}/chats`, {
		method: 'POST'
	});
	return handleResponse<Chat>(res);
}

export async function getChat(sessionId: string, chatId: string): Promise<Chat> {
	const res = await fetch(`${INTERNAL_BASE}/sessions/${sessionId}/chats/${chatId}`);
	return handleResponse<Chat>(res);
}

export async function updateChatTitle(sessionId: string, chatId: string, title: string): Promise<Chat> {
	const res = await fetch(`${INTERNAL_BASE}/sessions/${sessionId}/chats/${chatId}`, {
		method: 'PATCH',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ title })
	});
	return handleResponse<Chat>(res);
}

export async function getChatMessages(sessionId: string, chatId: string): Promise<Message[]> {
	const res = await fetch(`${INTERNAL_BASE}/sessions/${sessionId}/chats/${chatId}/messages`);
	return handleResponse<Message[]>(res);
}

export async function saveChatMessage(
	sessionId: string,
	chatId: string,
	role: string,
	content: string
): Promise<Message> {
	const res = await fetch(`${INTERNAL_BASE}/sessions/${sessionId}/chats/${chatId}/messages`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ role, content })
	});
	return handleResponse<Message>(res);
}

export async function queryCollections(
	query: string,
	collections: string[],
	llmModel: string = 'llama3.1'
): Promise<string | null> {
	const res = await fetch(`${API_BASE}/query`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({
			query,
			collections,
			top_k: 5,
			generate: true,
			llm_model: llmModel,
			include_results: false
		})
	});
	const data = await handleResponse<{ answer: string | null }>(res);
	return data.answer;
}

export async function generateTitle(
	query: string,
	llmModel: string = 'llama3.1'
): Promise<string> {
	const res = await fetch(`${API_BASE}/generate-title`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ query, llm_model: llmModel })
	});
	const data = await handleResponse<{ title: string }>(res);
	return data.title;
}
