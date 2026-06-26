<script lang="ts">
	import { untrack } from 'svelte';
	import type { PageData } from './$types';
	import type { DocumentInfo } from '$lib/api.js';
	import { getCollectionDocuments, deleteDocument, deleteCollection } from '$lib/api.js';

	let { data }: { data: PageData } = $props();

	let collections = $state<string[]>(untrack(() => data.collections.slice()));
	let loadError = $state<string | null>(untrack(() => data.error));

	interface CollectionState {
		expanded: boolean;
		loading: boolean;
		error: string | null;
		documents: DocumentInfo[];
	}

	let collectionStateMap = $state<Record<string, CollectionState>>({});

	$effect(() => {
		for (const name of collections) {
			if (!collectionStateMap[name]) {
				collectionStateMap[name] = { expanded: false, loading: false, error: null, documents: [] };
			}
		}
	});

	function stateFor(name: string): CollectionState {
		return collectionStateMap[name] ?? { expanded: false, loading: false, error: null, documents: [] };
	}

	async function toggleExpand(name: string) {
		const s = stateFor(name);
		if (s.expanded) {
			collectionStateMap[name] = { ...s, expanded: false };
			return;
		}
		collectionStateMap[name] = { ...s, expanded: true, loading: true, error: null };
		try {
			const resp = await getCollectionDocuments(name);
			collectionStateMap[name] = { ...collectionStateMap[name], loading: false, documents: resp.documents };
		} catch (e) {
			collectionStateMap[name] = { ...collectionStateMap[name], loading: false, error: String(e) };
		}
	}

	async function handleDeleteDocument(collectionName: string, jobId: string) {
		if (!confirm(`Delete this document from "${collectionName}"? This cannot be undone.`)) return;
		try {
			await deleteDocument(collectionName, jobId);
			const s = stateFor(collectionName);
			collectionStateMap[collectionName] = {
				...s,
				documents: s.documents.filter((d) => d.job_id !== jobId)
			};
		} catch (e) {
			alert(`Failed to delete document: ${e}`);
		}
	}

	async function handleDeleteCollection(name: string) {
		if (!confirm(`Delete collection "${name}" and all its documents? This cannot be undone.`)) return;
		try {
			await deleteCollection(name);
			collections = collections.filter((c) => c !== name);
			const next = { ...collectionStateMap };
			delete next[name];
			collectionStateMap = next;
		} catch (e) {
			alert(`Failed to delete collection: ${e}`);
		}
	}

	function filename(filePath: string): string {
		return filePath.split('/').at(-1) ?? filePath;
	}

	function shortJobId(jobId: string): string {
		return jobId.slice(0, 8) + '…';
	}
</script>

<div class="space-y-6">
	<div>
		<h1 class="text-2xl font-semibold text-gray-900">Collections</h1>
		<p class="mt-1 text-sm text-gray-500">
			{collections.length === 0
				? 'No collections yet.'
				: `${collections.length} collection${collections.length === 1 ? '' : 's'}`}
		</p>
	</div>

	{#if loadError}
		<div class="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
			Failed to load collections: {loadError}
		</div>
	{:else if collections.length === 0}
		<div class="rounded-lg border border-dashed border-gray-300 py-12 text-center text-sm text-gray-400">
			Upload documents to create your first collection.
		</div>
	{:else}
		<div class="divide-y divide-gray-200 rounded-lg border border-gray-200 bg-white">
			{#each collections as name (name)}
				{@const s = stateFor(name)}
				<div>
					<div class="flex items-center gap-3 px-4 py-3">
						<button
							onclick={() => toggleExpand(name)}
							class="flex min-w-0 flex-1 items-center gap-2 text-left"
							aria-expanded={s.expanded}
						>
							<svg
								class="h-4 w-4 shrink-0 text-gray-400 transition-transform"
								class:rotate-90={s.expanded}
								fill="none"
								viewBox="0 0 24 24"
								stroke="currentColor"
								stroke-width="2"
							>
								<path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
							</svg>
							<span class="truncate font-medium text-gray-800">{name}</span>
							{#if s.documents.length > 0}
								<span class="shrink-0 rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-500">
									{s.documents.length}
								</span>
							{/if}
						</button>
						<button
							onclick={() => handleDeleteCollection(name)}
							class="shrink-0 rounded px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50 hover:text-red-700"
						>
							Delete collection
						</button>
					</div>

					{#if s.expanded}
						<div class="border-t border-gray-100 bg-gray-50 px-4 py-3">
							{#if s.loading}
								<p class="text-sm text-gray-400">Loading documents…</p>
							{:else if s.error}
								<p class="text-sm text-red-500">{s.error}</p>
							{:else if s.documents.length === 0}
								<p class="text-sm text-gray-400">No documents found in this collection.</p>
							{:else}
								<ul class="space-y-2">
									{#each s.documents as doc (doc.job_id)}
										<li class="flex items-center gap-3 rounded bg-white px-3 py-2 shadow-sm ring-1 ring-gray-200">
											<div class="min-w-0 flex-1">
												<p class="truncate text-sm font-medium text-gray-800">{filename(doc.file_path)}</p>
												<p class="mt-0.5 font-mono text-xs text-gray-400">
													{shortJobId(doc.job_id)} &middot; {doc.chunk_count} chunk{doc.chunk_count === 1 ? '' : 's'}
												</p>
											</div>
											<button
												onclick={() => handleDeleteDocument(name, doc.job_id)}
												class="shrink-0 rounded px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50 hover:text-red-700"
											>
												Delete
											</button>
										</li>
									{/each}
								</ul>
							{/if}
						</div>
					{/if}
				</div>
			{/each}
		</div>
	{/if}
</div>
