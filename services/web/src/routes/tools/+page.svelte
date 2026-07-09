<script lang="ts">
	import { untrack } from 'svelte';
	import type { PageData } from './$types';
	import type { McpServer } from '$lib/api.js';
	import { createMcpServer, deleteMcpServer, refreshMcpServer } from '$lib/api.js';

	let { data }: { data: PageData } = $props();

	let servers = $state<McpServer[]>(untrack(() => data.servers.slice()));
	let loadError = $state<string | null>(untrack(() => data.error));

	let expandedMap = $state<Record<string, boolean>>({});

	let newName = $state('');
	let newUrl = $state('');
	let isAdding = $state(false);
	let addError = $state<string | null>(null);
	let addWarning = $state<string | null>(null);

	let refreshingId = $state<string | null>(null);

	function toggleExpand(id: string) {
		expandedMap[id] = !expandedMap[id];
	}

	async function handleAddServer() {
		if (!newName.trim() || !newUrl.trim() || isAdding) return;
		isAdding = true;
		addError = null;
		addWarning = null;
		try {
			const server = await createMcpServer(newName.trim(), newUrl.trim());
			servers = [server, ...servers];
			if (server.status !== 'ok') {
				addWarning = server.detail ?? 'Server added, but could not connect.';
			}
			newName = '';
			newUrl = '';
		} catch (e) {
			addError = String(e);
		} finally {
			isAdding = false;
		}
	}

	async function handleRefresh(id: string) {
		refreshingId = id;
		try {
			const updated = await refreshMcpServer(id);
			servers = servers.map((s) => (s.id === id ? updated : s));
		} catch (e) {
			alert(`Failed to refresh tool server: ${e}`);
		} finally {
			refreshingId = null;
		}
	}

	async function handleDelete(id: string, name: string) {
		if (!confirm(`Delete tool server "${name}"? This cannot be undone.`)) return;
		try {
			await deleteMcpServer(id);
			servers = servers.filter((s) => s.id !== id);
		} catch (e) {
			alert(`Failed to delete tool server: ${e}`);
		}
	}
</script>

<div class="space-y-6">
	<div>
		<h1 class="text-2xl font-semibold text-gray-900">Tools</h1>
		<p class="mt-1 text-sm text-gray-500">
			Connect MCP tool servers and select which tools are available in a chat.
		</p>
	</div>

	<div class="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
		<h2 class="text-sm font-semibold text-gray-700 uppercase tracking-wide">Add tool server</h2>
		<div class="flex flex-wrap items-end gap-3">
			<label class="flex flex-col gap-1 text-sm text-gray-700">
				<span>Name</span>
				<input
					type="text"
					bind:value={newName}
					placeholder="fake-refund"
					class="rounded-md border border-gray-300 px-2 py-1.5 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
				/>
			</label>
			<label class="flex flex-1 min-w-[16rem] flex-col gap-1 text-sm text-gray-700">
				<span>SSE URL</span>
				<input
					type="text"
					bind:value={newUrl}
					placeholder="http://fake-refund:8010/sse"
					class="w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
				/>
			</label>
			<button
				onclick={handleAddServer}
				disabled={isAdding || !newName.trim() || !newUrl.trim()}
				class="rounded-lg bg-gray-900 px-5 py-2 text-sm font-semibold text-white transition-opacity disabled:opacity-40"
			>
				{isAdding ? 'Adding…' : 'Add'}
			</button>
		</div>
		{#if addError}
			<p class="text-sm text-red-600">{addError}</p>
		{/if}
		{#if addWarning}
			<div class="rounded-xl border border-amber-200 bg-amber-50 p-4">
				<p class="text-sm text-amber-900">{addWarning}</p>
			</div>
		{/if}
	</div>

	{#if loadError}
		<div class="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
			Failed to load tool servers: {loadError}
		</div>
	{:else if servers.length === 0}
		<div class="rounded-lg border border-dashed border-gray-300 py-12 text-center text-sm text-gray-400">
			No tool servers yet. Add one above to get started.
		</div>
	{:else}
		<div class="divide-y divide-gray-200 rounded-lg border border-gray-200 bg-white">
			{#each servers as server (server.id)}
				{@const expanded = expandedMap[server.id] ?? false}
				<div>
					<div class="flex items-center gap-3 px-4 py-3">
						<button
							onclick={() => toggleExpand(server.id)}
							class="flex min-w-0 flex-1 items-center gap-2 text-left"
							aria-expanded={expanded}
						>
							<svg
								class="h-4 w-4 shrink-0 text-gray-400 transition-transform"
								class:rotate-90={expanded}
								fill="none"
								viewBox="0 0 24 24"
								stroke="currentColor"
								stroke-width="2"
							>
								<path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
							</svg>
							<span class="truncate font-medium text-gray-800">{server.name}</span>
							<span class="shrink-0 rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-500">
								{server.tools.length} tool{server.tools.length === 1 ? '' : 's'}
							</span>
							{#if server.status !== 'ok'}
								<span class="shrink-0 rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">
									unreachable
								</span>
							{/if}
							<span class="truncate font-mono text-xs text-gray-400">{server.url}</span>
						</button>
						<button
							onclick={() => handleRefresh(server.id)}
							disabled={refreshingId === server.id}
							class="shrink-0 rounded px-3 py-1.5 text-xs font-medium text-gray-500 hover:bg-gray-100 hover:text-gray-700 disabled:opacity-40"
						>
							{refreshingId === server.id ? 'Refreshing…' : 'Refresh'}
						</button>
						<button
							onclick={() => handleDelete(server.id, server.name)}
							class="shrink-0 rounded px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50 hover:text-red-700"
						>
							Delete
						</button>
					</div>

					{#if expanded}
						<div class="border-t border-gray-100 bg-gray-50 px-4 py-3">
							{#if server.tools.length === 0}
								<p class="text-sm text-gray-400">No tools discovered on this server.</p>
							{:else}
								<ul class="space-y-3">
									{#each server.tools as tool (tool.name)}
										<li class="rounded bg-white px-3 py-3 shadow-sm ring-1 ring-gray-200">
											<p class="font-medium text-gray-800">{tool.name}</p>
											{#if tool.description}
												<p class="mt-1 text-sm text-gray-500">{tool.description}</p>
											{/if}
											{#if tool.input_schema}
												<pre
													class="mt-2 overflow-x-auto rounded bg-gray-900 px-3 py-2 text-xs text-green-400 whitespace-pre-wrap">{JSON.stringify(
														tool.input_schema,
														null,
														2
													)}</pre>
											{/if}
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
