<script lang="ts">
	import type { LayoutData } from './$types';
	import type { Chat } from '$lib/api.js';
	import { deleteChat } from '$lib/api.js';
	import { page } from '$app/state';
	import { goto, invalidateAll } from '$app/navigation';

	let { data, children }: { data: LayoutData; children: import('svelte').Snippet } = $props();

	const activeChatId = $derived(page.params.chat_id);

	let chatToDelete = $state<Chat | null>(null);
	let isDeleting = $state(false);
	let deleteError = $state<string | null>(null);

	function requestDelete(chat: Chat) {
		chatToDelete = chat;
		deleteError = null;
	}

	function cancelDelete() {
		chatToDelete = null;
		deleteError = null;
	}

	async function confirmDelete() {
		if (!chatToDelete) return;
		isDeleting = true;
		deleteError = null;
		try {
			await deleteChat(data.session.id, chatToDelete.id);
			const wasActive = activeChatId === chatToDelete.id;
			chatToDelete = null;
			if (wasActive) {
				await goto(`/${data.session.id}`);
			}
			await invalidateAll();
		} catch (e) {
			deleteError = String(e);
		} finally {
			isDeleting = false;
		}
	}
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
				<div class="group relative">
					<a
						href="/{data.session.id}/{chat.id}"
						class="flex items-center gap-2 w-full rounded-lg pl-3 pr-8 py-2 text-sm transition-colors truncate
							{activeChatId === chat.id
								? 'bg-gray-700 text-white'
								: 'text-gray-400 hover:bg-gray-800 hover:text-gray-200'}"
					>
						<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5 shrink-0 opacity-60" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
							<path stroke-linecap="round" stroke-linejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
						</svg>
						<span class="truncate">{chat.title ?? 'New chat'}</span>
					</a>
					<button
						onclick={(e) => {
							e.preventDefault();
							e.stopPropagation();
							requestDelete(chat);
						}}
						aria-label="Delete chat"
						class="absolute right-1.5 top-1/2 -translate-y-1/2 rounded-md p-1.5 text-gray-500 opacity-0 transition-opacity hover:bg-gray-700 hover:text-red-400 group-hover:opacity-100"
					>
						<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
							<path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
						</svg>
					</button>
				</div>
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

{#if chatToDelete}
	<div class="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
		<div class="mx-4 w-full max-w-sm rounded-xl bg-white p-6 shadow-lg">
			<h2 class="text-base font-semibold text-gray-900">Delete chat?</h2>
			<p class="mt-2 text-sm text-gray-600">
				"{chatToDelete.title ?? 'New chat'}" and its messages will be permanently deleted. This
				cannot be undone.
			</p>

			{#if deleteError}
				<div class="mt-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
					{deleteError}
				</div>
			{/if}

			<div class="mt-6 flex gap-3">
				<button
					onclick={cancelDelete}
					disabled={isDeleting}
					class="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 transition-opacity hover:bg-gray-50 disabled:opacity-40"
				>
					Cancel
				</button>
				<button
					onclick={confirmDelete}
					disabled={isDeleting}
					class="flex-1 rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white transition-opacity hover:bg-red-700 disabled:opacity-40 flex items-center justify-center gap-2"
				>
					{#if isDeleting}
						<span class="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/30 border-t-white"></span>
					{/if}
					Delete
				</button>
			</div>
		</div>
	</div>
{/if}
