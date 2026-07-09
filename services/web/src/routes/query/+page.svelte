<script lang="ts">
	import type { PageData } from './$types';
	import type { QueryResult } from '$lib/api.js';
	import { queryCollections, createChatSession, findChatSession } from '$lib/api.js';

	let { data }: { data: PageData } = $props();

	let selectedCollections = $state(new Set<string>());
	let selectedTools = $state(new Set<string>());
	let queryText = $state('');
	let topK = $state(5);
	let generate = $state(true);
	let llmModel = $state('llama3.1');
	let includeResults = $state(false);

	let isLoading = $state(false);
	let queryError = $state<string | null>(null);
	let answer = $state<string | null>(null);
	let results = $state<QueryResult[] | null>(null);
	let hasSearched = $state(false);

	let lastQueryCurl = $state<string | null>(null);
	let activeTab = $state<'query' | 'api'>('query');
	let copied = $state(false);

	let isStartingChat = $state(false);
	let chatError = $state<string | null>(null);

	async function startChat() {
		if (selectedCollections.size === 0 || isStartingChat) return;
		isStartingChat = true;
		chatError = null;
		try {
			const cols = [...selectedCollections].sort();
			const tools = [...selectedTools].sort();
			const existing = await findChatSession(cols, tools);
			const sessionId = existing ? existing.id : (await createChatSession(cols, tools)).id;
			window.open(`http://localhost:3001/${sessionId}`, '_blank');
		} catch (e) {
			chatError = String(e);
		} finally {
			isStartingChat = false;
		}
	}

	async function copyToClipboard() {
		if (!lastQueryCurl) return;
		await navigator.clipboard.writeText(lastQueryCurl);
		copied = true;
		setTimeout(() => (copied = false), 2000);
	}

	function buildCurl(req: {
		query: string;
		collections: string[];
		tools: string[];
		top_k: number;
		generate: boolean;
		llm_model: string;
		include_results: boolean;
	}): string {
		const body = JSON.stringify(req, null, 2);
		return `curl -X POST http://localhost:8000/query \\\n  -H "Content-Type: application/json" \\\n  -d '${body}'`;
	}

	let canSubmit = $derived(
		queryText.trim().length > 0 && selectedCollections.size > 0 && !isLoading
	);

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

	function toggleTool(id: string) {
		const next = new Set(selectedTools);
		if (next.has(id)) {
			next.delete(id);
		} else {
			next.add(id);
		}
		selectedTools = next;
	}

	async function runQuery() {
		if (!canSubmit) return;
		isLoading = true;
		queryError = null;
		answer = null;
		results = null;
		lastQueryCurl = null;
		hasSearched = true;
		activeTab = 'query';

		const req = {
			query: queryText,
			collections: [...selectedCollections],
			tools: [...selectedTools],
			top_k: topK,
			generate,
			llm_model: llmModel,
			include_results: includeResults
		};
		lastQueryCurl = buildCurl(req);

		try {
			const resp = await queryCollections(req);
			answer = resp.answer;
			results = resp.results ?? null;
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
		<p class="mt-1 text-sm text-gray-500">Select one or more collections and ask a question.</p>
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

	<!-- Tools grid -->
	<div class="bg-white rounded-xl border border-gray-200 p-6 space-y-3">
		<div class="flex items-center justify-between">
			<h2 class="text-sm font-semibold text-gray-700 uppercase tracking-wide">Tools</h2>
			{#if selectedTools.size > 0}
				<span class="text-xs text-gray-400">{selectedTools.size} selected</span>
			{/if}
		</div>

		{#if data.servers.length === 0}
			<p class="text-sm text-gray-400 py-4 text-center">
				No tool servers configured yet. Add one from the <a
					href="/tools"
					class="text-blue-600 hover:underline">Tools</a
				> tab.
			</p>
		{:else}
			<div class="space-y-4">
				{#each data.servers as server (server.id)}
					<div>
						<p class="mb-2 text-xs font-medium text-gray-500">{server.name}</p>
						{#if server.tools.length === 0}
							<p class="text-xs text-gray-400">No tools available on this server.</p>
						{:else}
							<div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2">
								{#each server.tools as tool (tool.name)}
									{@const toolId = `${server.name}.${tool.name}`}
									{@const selected = selectedTools.has(toolId)}
									<button
										onclick={() => toggleTool(toolId)}
										class="rounded-lg border px-3 py-2.5 text-left text-sm font-medium transition-colors"
										class:border-blue-500={selected}
										class:bg-blue-50={selected}
										class:text-blue-800={selected}
										class:border-gray-200={!selected}
										class:text-gray-700={!selected}
									>
										<span class="block truncate">{tool.name}</span>
										{#if selected}
											<span class="text-xs text-blue-500">✓ selected</span>
										{/if}
									</button>
								{/each}
							</div>
						{/if}
					</div>
				{/each}
			</div>
		{/if}
	</div>

	<!-- Start chat -->
	{#if selectedCollections.size > 0}
		<div class="flex items-center gap-3">
			<button
				onclick={startChat}
				disabled={isStartingChat}
				class="rounded-lg bg-blue-600 px-5 py-2 text-sm font-semibold text-white transition-opacity disabled:opacity-40 hover:bg-blue-700"
			>
				{#if isStartingChat}
					<span class="flex items-center gap-2">
						<span
							class="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/30 border-t-white"
						></span>
						Starting…
					</span>
				{:else}
					Start chat
				{/if}
			</button>
			{#if chatError}
				<p class="text-sm text-red-600">{chatError}</p>
			{/if}
		</div>
	{/if}

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
			}}></textarea>

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

			<label class="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
				<input type="checkbox" bind:checked={includeResults} class="rounded text-blue-600" />
				<span>Return Results</span>
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

	<!-- Results tabs -->
	{#if hasSearched}
		<div>
			<!-- Tab bar -->
			<div class="flex border-b border-gray-200">
				<button
					onclick={() => (activeTab = 'query')}
					class="px-4 py-2 text-sm font-medium transition-colors -mb-px border-b-2"
					class:border-gray-900={activeTab === 'query'}
					class:text-gray-900={activeTab === 'query'}
					class:border-transparent={activeTab !== 'query'}
					class:text-gray-500={activeTab !== 'query'}
					class:hover:text-gray-700={activeTab !== 'query'}
				>
					Query
				</button>
				<button
					onclick={() => (activeTab = 'api')}
					class="px-4 py-2 text-sm font-medium transition-colors -mb-px border-b-2"
					class:border-gray-900={activeTab === 'api'}
					class:text-gray-900={activeTab === 'api'}
					class:border-transparent={activeTab !== 'api'}
					class:text-gray-500={activeTab !== 'api'}
					class:hover:text-gray-700={activeTab !== 'api'}
				>
					API Call
				</button>
			</div>

			<!-- Query tab panel -->
			{#if activeTab === 'query'}
				<div class="space-y-4 pt-4">
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

					{#if results && results.length > 0}
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
					{:else if results !== null && !isLoading && !queryError}
						<div class="rounded-xl border border-gray-200 bg-white px-5 py-8 text-center">
							<p class="text-sm text-gray-400">No results found for this query.</p>
						</div>
					{/if}
				</div>
			{/if}

			<!-- API Call tab panel -->
			{#if activeTab === 'api'}
				<div class="pt-4">
					<div class="rounded-xl border border-gray-700 bg-gray-900 p-5">
						<div class="flex items-center justify-between mb-3">
							<h3 class="text-xs font-semibold text-gray-400 uppercase tracking-wide">API Call</h3>
							<button
								onclick={copyToClipboard}
								class="flex items-center gap-1.5 text-xs text-gray-400 hover:text-gray-200 transition-colors"
								title="Copy to clipboard"
							>
								{#if copied}
									<svg
										xmlns="http://www.w3.org/2000/svg"
										class="h-4 w-4 text-green-400"
										viewBox="0 0 20 20"
										fill="currentColor"
									>
										<path
											fill-rule="evenodd"
											d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
											clip-rule="evenodd"
										/>
									</svg>
									<span class="text-green-400">Copied!</span>
								{:else}
									<svg
										xmlns="http://www.w3.org/2000/svg"
										class="h-4 w-4"
										viewBox="0 0 20 20"
										fill="currentColor"
									>
										<path d="M8 3a1 1 0 011-1h2a1 1 0 110 2H9a1 1 0 01-1-1z" />
										<path
											d="M6 3a2 2 0 00-2 2v11a2 2 0 002 2h8a2 2 0 002-2V5a2 2 0 00-2-2 3 3 0 01-3 3H9a3 3 0 01-3-3z"
										/>
									</svg>
									<span>Copy</span>
								{/if}
							</button>
						</div>
						<pre
							class="text-xs text-green-400 font-mono whitespace-pre-wrap break-all leading-relaxed">{lastQueryCurl}</pre>
					</div>
				</div>
			{/if}
		</div>
	{/if}
</div>
