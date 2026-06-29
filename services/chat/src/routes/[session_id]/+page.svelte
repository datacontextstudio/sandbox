<script lang="ts">
	import type { PageData } from './$types';
	import type { Message } from '$lib/api.js';
	import { saveMessage, queryCollections } from '$lib/api.js';

	let { data }: { data: PageData } = $props();

	let messages = $state<Message[]>(data.messages ?? []);
	let inputText = $state('');
	let isLoading = $state(false);
	let sendError = $state<string | null>(null);
	let messagesEndEl = $state<HTMLDivElement | null>(null);

	function scrollToBottom() {
		setTimeout(() => messagesEndEl?.scrollIntoView({ behavior: 'smooth' }), 50);
	}

	async function sendMessage() {
		const text = inputText.trim();
		if (!text || isLoading || !data.session) return;

		inputText = '';
		sendError = null;
		isLoading = true;

		const sessionId = data.session.id;
		const collections = data.session.collections;

		try {
			const userMsg = await saveMessage(sessionId, 'user', text);
			messages = [...messages, userMsg];
			scrollToBottom();

			const answer = await queryCollections(text, collections);
			const assistantContent = answer ?? 'No answer was generated.';

			const assistantMsg = await saveMessage(sessionId, 'assistant', assistantContent);
			messages = [...messages, assistantMsg];
			scrollToBottom();
		} catch (e) {
			sendError = String(e);
		} finally {
			isLoading = false;
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			sendMessage();
		}
	}
</script>

{#if data.error || !data.session}
	<div class="flex-1 flex items-center justify-center p-8">
		<div class="rounded-xl border border-red-200 bg-red-50 px-6 py-5 max-w-md text-center">
			<p class="text-sm font-medium text-red-700">Failed to load chat session</p>
			<p class="text-sm text-red-600 mt-1">{data.error ?? 'Session not found'}</p>
		</div>
	</div>
{:else}
	<div class="flex-1 flex flex-col max-w-3xl w-full mx-auto px-4 py-4 gap-4 min-h-0">

		<!-- Context badges -->
		<div class="bg-white rounded-xl border border-gray-200 px-4 py-3 flex flex-wrap items-center gap-2">
			<span class="text-xs font-semibold text-gray-500 uppercase tracking-wide shrink-0">Context:</span>
			{#each data.session.collections as collection}
				<span class="rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-800">
					{collection}
				</span>
			{/each}
		</div>

		<!-- Message thread -->
		<div class="flex-1 overflow-y-auto space-y-4 min-h-0">
			{#if messages.length === 0}
				<div class="flex items-center justify-center h-full">
					<p class="text-sm text-gray-400">Ask a question about your documents to get started.</p>
				</div>
			{/if}

			{#each messages as message (message.id)}
				<div class="flex {message.role === 'user' ? 'justify-end' : 'justify-start'}">
					<div
						class="max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed"
						class:bg-gray-900={message.role === 'user'}
						class:text-white={message.role === 'user'}
						class:rounded-br-sm={message.role === 'user'}
						class:bg-white={message.role === 'assistant'}
						class:border={message.role === 'assistant'}
						class:border-gray-200={message.role === 'assistant'}
						class:text-gray-800={message.role === 'assistant'}
						class:rounded-bl-sm={message.role === 'assistant'}
					>
						<p class="whitespace-pre-wrap">{message.content}</p>
					</div>
				</div>
			{/each}

			{#if isLoading}
				<div class="flex justify-start">
					<div class="bg-white border border-gray-200 rounded-2xl rounded-bl-sm px-4 py-3">
						<span class="flex items-center gap-2 text-sm text-gray-400">
							<span class="h-3.5 w-3.5 animate-spin rounded-full border-2 border-gray-200 border-t-gray-500"></span>
							Thinking…
						</span>
					</div>
				</div>
			{/if}

			<div bind:this={messagesEndEl}></div>
		</div>

		<!-- Error -->
		{#if sendError}
			<div class="rounded-lg border border-red-200 bg-red-50 px-4 py-2.5 text-sm text-red-700">
				{sendError}
			</div>
		{/if}

		<!-- Input -->
		<div class="bg-white rounded-xl border border-gray-200 p-3 flex gap-3 items-end shrink-0">
			<textarea
				bind:value={inputText}
				onkeydown={handleKeydown}
				placeholder="Ask a question… (Enter to send, Shift+Enter for new line)"
				rows={2}
				disabled={isLoading}
				class="flex-1 resize-none rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-900 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none disabled:opacity-50"
			></textarea>
			<button
				onclick={sendMessage}
				disabled={!inputText.trim() || isLoading}
				class="rounded-lg bg-gray-900 px-4 py-2 text-sm font-semibold text-white transition-opacity disabled:opacity-40 shrink-0"
			>
				Send
			</button>
		</div>
	</div>
{/if}
