<script lang="ts">
	import type { PageData } from './$types';
	import { createChat, saveChatMessage } from '$lib/api.js';
	import { goto } from '$app/navigation';

	let { data }: { data: PageData } = $props();

	let inputText = $state('');
	let isLoading = $state(false);
	let sendError = $state<string | null>(null);

	async function sendFirstMessage() {
		const text = inputText.trim();
		if (!text || isLoading || !data.session) return;

		inputText = '';
		sendError = null;
		isLoading = true;

		try {
			const chat = await createChat(data.session.id);
			await saveChatMessage(data.session.id, chat.id, 'user', text);
			await goto(`/${data.session.id}/${chat.id}`, {
				replaceState: true,
				state: { firstMessage: text }
			});
		} catch (e) {
			sendError = String(e);
			isLoading = false;
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			sendFirstMessage();
		}
	}
</script>

<div class="flex-1 flex flex-col h-full">
	<!-- Empty state -->
	<div class="flex-1 flex items-center justify-center p-8">
		<div class="text-center max-w-sm">
			<div class="mx-auto mb-4 h-12 w-12 rounded-full bg-gray-100 flex items-center justify-center">
				<svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
					<path stroke-linecap="round" stroke-linejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
				</svg>
			</div>
			<h2 class="text-base font-semibold text-gray-700 mb-1">Start a new chat</h2>
			<p class="text-sm text-gray-400">Ask a question about your documents to get started.</p>
		</div>
	</div>

	<!-- Error -->
	{#if sendError}
		<div class="mx-4 mb-2 rounded-lg border border-red-200 bg-red-50 px-4 py-2.5 text-sm text-red-700">
			{sendError}
		</div>
	{/if}

	<!-- Input -->
	<div class="border-t border-gray-200 bg-white p-4">
		<div class="max-w-3xl mx-auto flex gap-3 items-end">
			<textarea
				bind:value={inputText}
				onkeydown={handleKeydown}
				placeholder="Ask a question… (Enter to send, Shift+Enter for new line)"
				rows={2}
				disabled={isLoading}
				class="flex-1 resize-none rounded-xl border border-gray-200 px-4 py-3 text-sm text-gray-900 focus:border-gray-400 focus:ring-0 focus:outline-none disabled:opacity-50 bg-gray-50"
			></textarea>
			<button
				onclick={sendFirstMessage}
				disabled={!inputText.trim() || isLoading}
				class="rounded-xl bg-gray-900 px-5 py-3 text-sm font-semibold text-white transition-opacity disabled:opacity-40 shrink-0 flex items-center gap-2"
			>
				{#if isLoading}
					<span class="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/30 border-t-white"></span>
				{/if}
				Send
			</button>
		</div>
	</div>
</div>
