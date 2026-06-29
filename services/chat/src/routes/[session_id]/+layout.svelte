<script lang="ts">
	import type { LayoutData } from './$types';
	import { page } from '$app/state';

	let { data, children }: { data: LayoutData; children: import('svelte').Snippet } = $props();

	const activeChatId = $derived(page.params.chat_id);
</script>

<div class="flex h-screen overflow-hidden bg-white">
	<!-- Sidebar -->
	<aside class="w-64 bg-gray-900 flex flex-col shrink-0">
		<!-- Brand -->
		<div class="px-4 py-4 border-b border-gray-700">
			<span class="text-white font-semibold text-sm tracking-tight select-none">DataContext Chat</span>
		</div>

		<!-- New chat button -->
		<div class="p-3">
			<a
				href="/{data.session.id}"
				class="flex items-center gap-2 w-full rounded-lg px-3 py-2 text-sm text-gray-300 hover:bg-gray-700 hover:text-white transition-colors"
			>
				<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
					<path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
				</svg>
				New chat
			</a>
		</div>

		<!-- Chat list -->
		<nav class="flex-1 overflow-y-auto px-2 pb-2 space-y-0.5">
			{#each data.chats as chat (chat.id)}
				<a
					href="/{data.session.id}/{chat.id}"
					class="flex items-center gap-2 w-full rounded-lg px-3 py-2 text-sm transition-colors truncate
						{activeChatId === chat.id
							? 'bg-gray-700 text-white'
							: 'text-gray-400 hover:bg-gray-800 hover:text-gray-200'}"
				>
					<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5 shrink-0 opacity-60" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
						<path stroke-linecap="round" stroke-linejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
					</svg>
					<span class="truncate">{chat.title ?? 'New chat'}</span>
				</a>
			{/each}
		</nav>

		<!-- Collections -->
		<div class="p-3 border-t border-gray-700">
			<p class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Context</p>
			<div class="flex flex-wrap gap-1.5">
				{#each data.session.collections as collection}
					<span class="rounded-full bg-gray-700 px-2 py-0.5 text-xs text-gray-300">
						{collection}
					</span>
				{/each}
			</div>
		</div>
	</aside>

	<!-- Main content -->
	<main class="flex-1 flex flex-col min-h-0 bg-gray-50">
		{@render children()}
	</main>
</div>
