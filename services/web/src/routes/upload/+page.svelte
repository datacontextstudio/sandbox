<script lang="ts">
	import { untrack } from 'svelte';
	import type { PageData } from './$types';
	import { ingestFile, getJob } from '$lib/api.js';

	let { data }: { data: PageData } = $props();

	interface FileUpload {
		id: string;
		name: string;
		status: 'uploading' | 'polling' | 'completed' | 'failed';
		job_id: string | null;
		chunks_indexed: number | null;
		error: string | null;
	}

	let collections = $state<string[]>(untrack(() => data.collections.slice()));
	let selectedCollection = $state<string>(untrack(() => data.collections[0] ?? '__new__'));
	let newCollectionName = $state('');
	let uploads = $state<FileUpload[]>([]);
	let isDragging = $state(false);

	let effectiveCollection = $derived(
		selectedCollection === '__new__' ? newCollectionName.trim() : selectedCollection
	);

	let canUpload = $derived(effectiveCollection.length > 0);

	function handleFiles(fileList: FileList | null | undefined) {
		if (!fileList || !canUpload) return;
		for (const file of fileList) {
			uploadFile(file);
		}
	}

	async function uploadFile(file: File) {
		const id = crypto.randomUUID();
		const entry: FileUpload = {
			id,
			name: file.name,
			status: 'uploading',
			job_id: null,
			chunks_indexed: null,
			error: null
		};
		uploads = [...uploads, entry];

		try {
			const resp = await ingestFile(file, effectiveCollection);
			uploads = uploads.map((u) =>
				u.id === id ? { ...u, status: 'polling', job_id: resp.job_id } : u
			);
			pollJob(id, resp.job_id);

			if (!collections.includes(effectiveCollection)) {
				collections = [...collections, effectiveCollection];
			}
		} catch (e) {
			uploads = uploads.map((u) =>
				u.id === id ? { ...u, status: 'failed', error: String(e) } : u
			);
		}
	}

	function pollJob(entryId: string, jobId: string) {
		const interval = setInterval(async () => {
			try {
				const job = await getJob(jobId);
				if (job.status === 'completed') {
					clearInterval(interval);
					uploads = uploads.map((u) =>
						u.id === entryId
							? { ...u, status: 'completed', chunks_indexed: Number(job.fields.chunks_indexed ?? 0) }
							: u
					);
				} else if (job.status === 'failed') {
					clearInterval(interval);
					uploads = uploads.map((u) =>
						u.id === entryId
							? { ...u, status: 'failed', error: job.fields.error ?? 'Processing failed' }
							: u
					);
				}
			} catch {
				// transient error, keep polling
			}
		}, 2000);
	}
</script>

<div class="space-y-6">
	<div>
		<h1 class="text-2xl font-bold text-gray-900">Upload Documents</h1>
		<p class="mt-1 text-sm text-gray-500">Add files to a collection for indexing and search.</p>
	</div>

	<!-- Collection selector -->
	<div class="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
		<h2 class="text-sm font-semibold text-gray-700 uppercase tracking-wide">Collection</h2>

		<div class="flex flex-col sm:flex-row gap-3">
			<select
				bind:value={selectedCollection}
				class="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
			>
				<option value="__new__">+ Create new collection…</option>
				{#each collections as name}
					<option value={name}>{name}</option>
				{/each}
			</select>

			{#if selectedCollection === '__new__'}
				<input
					type="text"
					bind:value={newCollectionName}
					placeholder="Collection name"
					class="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
				/>
			{/if}
		</div>

		{#if !canUpload}
			<p class="text-xs text-amber-600">Enter a collection name to enable uploads.</p>
		{/if}
	</div>

	<!-- Drop zone -->
	<label
		class="block rounded-xl border-2 border-dashed p-12 text-center transition-colors"
		class:border-blue-400={isDragging}
		class:bg-blue-50={isDragging}
		class:border-gray-300={!isDragging}
		class:opacity-50={!canUpload}
		class:cursor-pointer={canUpload}
		class:cursor-not-allowed={!canUpload}
		ondragover={(e) => {
			e.preventDefault();
			if (canUpload) isDragging = true;
		}}
		ondragleave={() => {
			isDragging = false;
		}}
		ondrop={(e) => {
			e.preventDefault();
			isDragging = false;
			if (canUpload) handleFiles(e.dataTransfer?.files);
		}}
	>
		<svg
			class="mx-auto h-10 w-10 text-gray-400 mb-3"
			fill="none"
			viewBox="0 0 24 24"
			stroke="currentColor"
		>
			<path
				stroke-linecap="round"
				stroke-linejoin="round"
				stroke-width="1.5"
				d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"
			/>
		</svg>
		<p class="text-sm font-medium text-gray-700">
			Drop files here or <span class="text-blue-600 underline">browse</span>
		</p>
		<p class="mt-1 text-xs text-gray-400">PDF, DOCX, PPTX, TXT and more</p>
		<input
			type="file"
			multiple
			accept=".pdf,.docx,.pptx,.txt,.md,.csv"
			disabled={!canUpload}
			class="hidden"
			onchange={(e) => handleFiles(e.currentTarget.files)}
		/>
	</label>

	<!-- Upload queue -->
	{#if uploads.length > 0}
		<div class="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">
			{#each uploads as upload (upload.id)}
				<div class="flex items-center gap-4 px-5 py-3">
					<div class="flex-1 min-w-0">
						<p class="text-sm font-medium text-gray-800 truncate">{upload.name}</p>
						{#if upload.status === 'completed'}
							<p class="text-xs text-green-600 mt-0.5">{upload.chunks_indexed} chunks indexed</p>
						{:else if upload.status === 'failed'}
							<p class="text-xs text-red-500 mt-0.5">{upload.error}</p>
						{/if}
					</div>

					<div class="flex-shrink-0">
						{#if upload.status === 'uploading'}
							<span
								class="inline-flex items-center gap-1.5 rounded-full bg-blue-100 px-2.5 py-1 text-xs font-medium text-blue-700"
							>
								<span
									class="h-3 w-3 animate-spin rounded-full border-2 border-blue-300 border-t-blue-600"
								></span>
								Uploading
							</span>
						{:else if upload.status === 'polling'}
							<span
								class="inline-flex items-center gap-1.5 rounded-full bg-indigo-100 px-2.5 py-1 text-xs font-medium text-indigo-700"
							>
								<span
									class="h-3 w-3 animate-spin rounded-full border-2 border-indigo-300 border-t-indigo-600"
								></span>
								Processing
							</span>
						{:else if upload.status === 'completed'}
							<span
								class="inline-flex items-center rounded-full bg-green-100 px-2.5 py-1 text-xs font-medium text-green-700"
							>
								Done
							</span>
						{:else}
							<span
								class="inline-flex items-center rounded-full bg-red-100 px-2.5 py-1 text-xs font-medium text-red-700"
							>
								Failed
							</span>
						{/if}
					</div>
				</div>
			{/each}
		</div>
	{/if}
</div>
