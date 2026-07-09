const BASE = '/api';
const INTERNAL_BASE = '/internal-api';

export interface ChatSession {
	id: string;
	collections: string[];
	created_at: string;
}

export interface CollectionsResponse {
	collections: string[];
}

export interface DocumentInfo {
	job_id: string;
	file_path: string;
	chunk_count: number;
}

export interface DocumentsResponse {
	collection_name: string;
	documents: DocumentInfo[];
}

export interface DeleteResponse {
	deleted: boolean;
	detail: string;
}

export interface IngestResponse {
	job_id: string;
	status: 'pending' | 'processing' | 'completed' | 'failed';
	file_path: string;
	collection_name: string;
}

export interface JobStatusResponse {
	job_id: string;
	status: string;
	fields: Record<string, string>;
}

export interface QueryResult {
	text: string;
	score: number;
	collection_name: string;
	file_path: string | null;
	chunk_index: number | null;
	metadata: Record<string, unknown>;
}

export interface ToolResponse {
	tool: string;
	response: string;
}

export interface QueryResponse {
	query: string;
	results: QueryResult[] | null;
	answer: string | null;
	tool_responses: ToolResponse[] | null;
}

export interface QueryRequest {
	query: string;
	collections: string[];
	top_k: number;
	generate: boolean;
	llm_model: string;
	include_results: boolean;
}

async function handleResponse<T>(res: Response): Promise<T> {
	if (!res.ok) {
		const text = await res.text().catch(() => res.statusText);
		throw new Error(`${res.status}: ${text}`);
	}
	return res.json() as Promise<T>;
}

export async function getCollections(): Promise<CollectionsResponse> {
	const res = await fetch(`${BASE}/collections`);
	return handleResponse<CollectionsResponse>(res);
}

export async function ingestFile(
	file: File,
	collectionName: string,
	metadata?: Record<string, unknown>
): Promise<IngestResponse> {
	const form = new FormData();
	form.append('file', file);
	form.append('collection_name', collectionName);
	if (metadata) {
		form.append('metadata', JSON.stringify(metadata));
	}
	const res = await fetch(`${BASE}/ingest`, { method: 'POST', body: form });
	return handleResponse<IngestResponse>(res);
}

export async function getJob(jobId: string): Promise<JobStatusResponse> {
	const res = await fetch(`${BASE}/jobs/${jobId}`);
	return handleResponse<JobStatusResponse>(res);
}

export async function queryCollections(req: QueryRequest): Promise<QueryResponse> {
	const res = await fetch(`${BASE}/query`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(req)
	});
	return handleResponse<QueryResponse>(res);
}

export async function getCollectionDocuments(name: string): Promise<DocumentsResponse> {
	const res = await fetch(`${BASE}/collections/${encodeURIComponent(name)}/documents`);
	return handleResponse<DocumentsResponse>(res);
}

export async function deleteDocument(collectionName: string, jobId: string): Promise<DeleteResponse> {
	const res = await fetch(
		`${BASE}/collections/${encodeURIComponent(collectionName)}/documents/${encodeURIComponent(jobId)}`,
		{ method: 'DELETE' }
	);
	return handleResponse<DeleteResponse>(res);
}

export async function deleteCollection(name: string): Promise<DeleteResponse> {
	const res = await fetch(`${BASE}/collections/${encodeURIComponent(name)}`, { method: 'DELETE' });
	return handleResponse<DeleteResponse>(res);
}

export async function findChatSession(collections: string[]): Promise<ChatSession | null> {
	const params = new URLSearchParams();
	collections.forEach((c) => params.append('collections', c));
	const res = await fetch(`${INTERNAL_BASE}/sessions?${params}`);
	if (!res.ok) return null;
	return res.json() as Promise<ChatSession | null>;
}

export async function createChatSession(collections: string[]): Promise<ChatSession> {
	const res = await fetch(`${INTERNAL_BASE}/sessions`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ collections })
	});
	return handleResponse<ChatSession>(res);
}
