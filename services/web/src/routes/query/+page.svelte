<script lang="ts">
	import type { PageData } from './$types';
	import type { QueryResult } from '$lib/api.js';
	import { queryCollections } from '$lib/api.js';

	let { data }: { data: PageData } = $props();

	let selectedCollections = $state(new Set<string>());
	let queryText = $state('');
	let topK = $state(5);
	let generate = $state(false);
	let llmModel = $state('llama3');

	let isLoading = $state(false);
	let queryError = $state<string | null>(null);
	let answer = $state<string | null>(null);
	let results = $state<QueryResult[]>([]);
	let hasSearched = $state(false);

	let canSubmit = $derived(queryText.trim().length > 0 && selectedCollections.size > 0 && !isLoading);

	function toggleCollection(name: string) {
		const next = new Set(selectedCollections);
		if (next.has(name)) {
			next.delete(name);
		} else {
			next.add(name);
		}
		selectedCollections = next;
	}

	function selectAll() {
		selectedCollections = new Set(data.collections);
	}

	function clearAll() {
		selectedCollections = new Set();
	}

	async function runQuery() {
		if (!canSubmit) return;
		isLoading = true;
		queryError = null;
		answer = null;
		results = [];
		hasSearched = true;

		try {
			const resp = await queryCollections({
				query: queryText,
				collections: [...selectedCollections],
				top_k: topK,
				generate,
				llm_model: llmModel
			});
			answer = resp.answer;
			results = resp.results;
		} catch (e) {
			queryError = String(e);
		} finally {
			isLoading = false;
		}
	}
</script>

<div class="space-y-6">
	<div>
		<h1 class="text-2xl font-bold text-gray-900">Query Collections</h1>
		<p class="mt-1 text-sm text-gray-500">
			Select one or more collections and ask a question.
		</p>
	</div>

	<!-- Collections grid -->
	<div class="bg-white rounded-xl border border-gray-200 p-6 space-y-3">
		<div class="flex items-center justify-between">
			<h2 class="text-sm font-semibold text-gray-700 uppercase tracking-wide">Collections</h2>
			<div class="flex gap-3 text-xs">
				{#if data.collections.length > 0}
					<button onclick={selectAll} class="text-blue-600 hover:underline">Select all</button>
					<button onclick={clearAll} class="text-gray-500 hover:underline">Clear</button>
				{/if}
				{#if selectedCollections.size > 0}
					<span class="text-gray-400">{selectedCollections.size} selected</span>
				{/if}
			</div>
		</div>

		{#if data.collections.length === 0}
			<p class="text-sm text-gray-400 py-4 text-center">
				No collections yet. Upload some documents first.
			</p>
		{:else}
			<div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2">
				{#each data.collections as name}
					{@const selected = selectedCollections.has(name)}
					<button
						onclick={() => toggleCollection(name)}
						class="rounded-lg border px-3 py-2.5 text-left text-sm font-medium transition-colors"
						class:border-blue-500={selected}
						class:bg-blue-50={selected}
						class:text-blue-800={selected}
						class:border-gray-200={!selected}
						class:text-gray-700={!selected}
					>
						<span class="block truncate">{name}</span>
						{#if selected}
							<span class="text-xs text-blue-500">✓ selected</span>
						{/if}
					</button>
				{/each}
			</div>
		{/if}
	</div>

	<!-- Query form -->
	<div class="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
		<h2 class="text-sm font-semibold text-gray-700 uppercase tracking-wide">Query</h2>

		<textarea
			bind:value={queryText}
			placeholder="Ask a question about your documents…"
			rows={3}
			class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 resize-y focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
			onkeydown={(e) => {
				if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) runQuery();
			}}
		></textarea>

		<div class="flex flex-wrap items-center gap-4">
			<label class="flex items-center gap-2 text-sm text-gray-700">
				<span>Top results</span>
				<input
					type="number"
					bind:value={topK}
					min={1}
					max={20}
					class="w-16 rounded-md border border-gray-300 px-2 py-1 text-sm text-center focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
				/>
			</label>

			<label class="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
				<input type="checkbox" bind:checked={generate} class="rounded text-blue-600" />
				<span>Generate AI answer</span>
			</label>

			{#if generate}
				<label class="flex items-center gap-2 text-sm text-gray-700">
					<span>Model</span>
					<input
						type="text"
						bind:value={llmModel}
						class="rounded-md border border-gray-300 px-2 py-1 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
					/>
				</label>
			{/if}
		</div>

		<div class="flex items-center gap-3">
			<button
				onclick={runQuery}
				disabled={!canSubmit}
				class="rounded-lg bg-gray-900 px-5 py-2 text-sm font-semibold text-white transition-opacity disabled:opacity-40"
			>
				{#if isLoading}
					<span class="flex items-center gap-2">
						<span
							class="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/30 border-t-white"
						></span>
						Searching…
					</span>
				{:else}
					Search
				{/if}
			</button>
			<p class="text-xs text-gray-400">⌘ Enter to submit</p>
		</div>
	</div>

	<!-- Results -->
	{#if queryError}
		<div class="rounded-xl border border-red-200 bg-red-50 px-5 py-4">
			<p class="text-sm font-medium text-red-700">Error</p>
			<p class="text-sm text-red-600 mt-1">{queryError}</p>
		</div>
	{/if}

	{#if answer}
		<div class="rounded-xl border border-amber-200 bg-amber-50 p-5">
			<h3 class="text-sm font-semibold text-amber-900 mb-2">AI Answer</h3>
			<p class="text-sm text-amber-800 whitespace-pre-wrap leading-relaxed">{answer}</p>
		</div>
	{/if}

	{#if results.length > 0}
		<div class="space-y-3">
			<h2 class="text-sm font-semibold text-gray-700 uppercase tracking-wide">
				{results.length} result{results.length !== 1 ? 's' : ''}
			</h2>
			{#each results as result, i}
				<div class="bg-white rounded-xl border border-gray-200 p-5">
					<div class="flex items-center gap-2 mb-3">
						<span class="text-xs font-medium text-gray-400">#{i + 1}</span>
						<span
							class="rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-800"
						>
							{result.collection_name}
						</span>
						<span class="ml-auto text-sm font-semibold text-green-700">
							{(result.score * 100).toFixed(1)}%
						</span>
					</div>
					<p class="text-sm text-gray-800 leading-relaxed line-clamp-4">{result.text}</p>
					{#if result.file_path}
						<p class="mt-2 text-xs font-mono text-gray-400 truncate">{result.file_path}</p>
					{/if}
				</div>
			{/each}
		</div>
	{:else if hasSearched && !isLoading && !queryError}
		<div class="rounded-xl border border-gray-200 bg-white px-5 py-8 text-center">
			<p class="text-sm text-gray-400">No results found for this query.</p>
		</div>
	{/if}
</div>
