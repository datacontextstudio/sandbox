const INTERNAL_BASE = '/internal-api';
const API_BASE = '/api';

export interface Session {
	id: string;
	collections: string[];
	created_at: string;
}

export interface Message {
	id: string;
	session_id: string;
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

export async function getMessages(sessionId: string): Promise<Message[]> {
	const res = await fetch(`${INTERNAL_BASE}/sessions/${sessionId}/messages`);
	return handleResponse<Message[]>(res);
}

export async function saveMessage(sessionId: string, role: string, content: string): Promise<Message> {
	const res = await fetch(`${INTERNAL_BASE}/sessions/${sessionId}/messages`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ role, content })
	});
	return handleResponse<Message>(res);
}

export async function queryCollections(
	query: string,
	collections: string[],
	llmModel: string = 'llama3'
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
