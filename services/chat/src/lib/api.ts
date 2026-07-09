const INTERNAL_BASE = '/internal-api';
const API_BASE = '/api';

export interface Session {
	id: string;
	collections: string[];
	tools: string[];
	created_at: string;
}

export interface Chat {
	id: string;
	session_id: string;
	title: string | null;
	created_at: string;
}

export interface ToolResponse {
	tool: string;
	response: string;
}

export interface Message {
	id: string;
	chat_id: string;
	role: 'user' | 'assistant';
	content: string;
	tool_responses: ToolResponse[] | null;
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

export async function deleteChat(sessionId: string, chatId: string): Promise<void> {
	const res = await fetch(`${INTERNAL_BASE}/sessions/${sessionId}/chats/${chatId}`, {
		method: 'DELETE'
	});
	if (!res.ok) {
		const text = await res.text().catch(() => res.statusText);
		throw new Error(`${res.status}: ${text}`);
	}
}

export async function getChatMessages(sessionId: string, chatId: string): Promise<Message[]> {
	const res = await fetch(`${INTERNAL_BASE}/sessions/${sessionId}/chats/${chatId}/messages`);
	return handleResponse<Message[]>(res);
}

export async function saveChatMessage(
	sessionId: string,
	chatId: string,
	role: string,
	content: string,
	toolResponses?: ToolResponse[] | null
): Promise<Message> {
	const res = await fetch(`${INTERNAL_BASE}/sessions/${sessionId}/chats/${chatId}/messages`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ role, content, tool_responses: toolResponses ?? null })
	});
	return handleResponse<Message>(res);
}

export async function queryCollections(
	query: string,
	collections: string[],
	tools: string[] = [],
	llmModel: string = 'llama3.1'
): Promise<{ answer: string | null; tool_responses: ToolResponse[] | null }> {
	const res = await fetch(`${API_BASE}/query`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({
			query,
			collections,
			tools,
			top_k: 5,
			generate: true,
			llm_model: llmModel,
			include_results: false
		})
	});
	const data = await handleResponse<{ answer: string | null; tool_responses: ToolResponse[] | null }>(
		res
	);
	return { answer: data.answer, tool_responses: data.tool_responses };
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
