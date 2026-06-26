const BASE = '/api';

export interface CollectionsResponse {
	collections: string[];
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

export interface QueryResponse {
	query: string;
	results: QueryResult[];
	answer: string | null;
}

export interface QueryRequest {
	query: string;
	collections: string[];
	top_k: number;
	generate: boolean;
	llm_model: string;
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
