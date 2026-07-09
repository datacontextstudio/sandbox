<script lang="ts">
	import type { PageData } from './$types';
	import type { Message } from '$lib/api.js';
	import { saveChatMessage, queryCollections, generateTitle, updateChatTitle } from '$lib/api.js';
	import { page } from '$app/state';
	import { invalidateAll, replaceState } from '$app/navigation';

	let { data }: { data: PageData } = $props();

	let messages = $state<Message[]>(data.messages ?? []);
	let inputText = $state('');
	let isLoading = $state(false);
	let sendError = $state<string | null>(null);
	let messagesEndEl = $state<HTMLDivElement | null>(null);
	let needsTitle = $state(data.chat.title === null);
	let handledFirstMessage = false;
	let openToolResponseMsg = $state<Message | null>(null);

	// Re-sync local state when navigating between chats (component is reused, not remounted)
	$effect(() => {
		messages = data.messages ?? [];
		needsTitle = data.chat.title === null;
		handledFirstMessage = false;
		sendError = null;
	});

	function scrollToBottom() {
		setTimeout(() => messagesEndEl?.scrollIntoView({ behavior: 'smooth' }), 50);
	}

	$effect(() => {
		const state = page.state as Record<string, unknown>;
		const firstMessage = state?.firstMessage as string | undefined;
		if (firstMessage && !handledFirstMessage) {
			handledFirstMessage = true;
			replaceState('', {});
			isLoading = true;
			respondToMessage(firstMessage);
		}
	});

	async function respondToMessage(userQuery: string) {
		sendError = null;
		try {
			const { answer, tool_responses } = await queryCollections(userQuery, data.session.collections);
			const assistantContent = answer ?? 'No answer was generated.';
			const assistantMsg = await saveChatMessage(
				data.session.id,
				data.chat.id,
				'assistant',
				assistantContent,
				tool_responses
			);
			messages = [...messages, assistantMsg];
			scrollToBottom();

			if (needsTitle) {
				needsTitle = false;
				try {
					const title = await generateTitle(userQuery);
					await updateChatTitle(data.session.id, data.chat.id, title);
					await invalidateAll();
				} catch {
					// title generation is non-critical; chat still works
				}
			}
		} catch (e) {
			sendError = String(e);
		} finally {
			isLoading = false;
		}
	}

	async function sendMessage() {
		const text = inputText.trim();
		if (!text || isLoading) return;

		inputText = '';
		sendError = null;
		isLoading = true;

		try {
			const userMsg = await saveChatMessage(data.session.id, data.chat.id, 'user', text);
			messages = [...messages, userMsg];
			scrollToBottom();
			await respondToMessage(text);
		} catch (e) {
			sendError = String(e);
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

<div class="flex-1 flex flex-col h-full min-h-0">
	<!-- Message thread -->
	<div class="flex-1 overflow-y-auto px-4 py-6 min-h-0">
		<div class="max-w-3xl mx-auto space-y-4">
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
						class:shadow-sm={message.role === 'assistant'}
						class:rounded-bl-sm={message.role === 'assistant'}
					>
						<p class="whitespace-pre-wrap">{message.content}</p>

						{#if message.role === 'assistant' && message.tool_responses?.length}
							<button
								onclick={() => (openToolResponseMsg = message)}
								class="mt-2 inline-flex cursor-pointer items-center gap-1.5 rounded-full border border-gray-200 px-2.5 py-1 text-xs font-medium text-gray-500 hover:text-gray-700"
							>
								<svg
									xmlns="http://www.w3.org/2000/svg"
									class="h-3.5 w-3.5"
									fill="none"
									viewBox="0 0 24 24"
									stroke="currentColor"
									stroke-width="2"
								>
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										d="M11.42 15.17L17.25 21A2.652 2.652 0 0021 17.25l-5.877-5.877M11.42 15.17l2.496-3.03c.317-.384.74-.626 1.208-.766M11.42 15.17l-4.655 5.653a2.548 2.548 0 11-3.586-3.586l6.837-5.63m5.108-.233c.55-.164 1.163-.188 1.743-.14a4.5 4.5 0 004.486-6.336l-3.276 3.277a3.004 3.004 0 01-2.25-2.25l3.276-3.276a4.5 4.5 0 00-6.336 4.486c.091 1.076-.071 2.264-.904 2.95l-.102.085m-1.745 1.437L5.909 7.5H4.5L2.25 3.75l1.5-1.5L7.5 4.5v1.409l4.26 4.26m-1.745 1.437l1.745-1.437m6.615 8.206L15.75 15.75M4.867 19.125h.008v.008h-.008v-.008z"
									/>
								</svg>
								Tool Response
							</button>
						{/if}
					</div>
				</div>
			{/each}

			{#if isLoading}
				<div class="flex justify-start">
					<div class="bg-white border border-gray-200 shadow-sm rounded-2xl rounded-bl-sm px-4 py-3">
						<span class="flex items-center gap-2 text-sm text-gray-400">
							<span class="h-3.5 w-3.5 animate-spin rounded-full border-2 border-gray-200 border-t-gray-500"></span>
							Thinking…
						</span>
					</div>
				</div>
			{/if}

			<div bind:this={messagesEndEl}></div>
		</div>
	</div>

	<!-- Error -->
	{#if sendError}
		<div class="mx-4 mb-2 rounded-lg border border-red-200 bg-red-50 px-4 py-2.5 text-sm text-red-700">
			{sendError}
		</div>
	{/if}

	<!-- Input -->
	<div class="border-t border-gray-200 bg-white p-4 shrink-0">
		<div class="max-w-3xl mx-auto flex gap-3 items-end">
			<textarea
				bind:value={inputText}
				onkeydown={handleKeydown}
				placeholder="Ask a follow-up question… (Enter to send, Shift+Enter for new line)"
				rows={2}
				disabled={isLoading}
				class="flex-1 resize-none rounded-xl border border-gray-200 px-4 py-3 text-sm text-gray-900 focus:border-gray-400 focus:ring-0 focus:outline-none disabled:opacity-50 bg-gray-50"
			></textarea>
			<button
				onclick={sendMessage}
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

{#if openToolResponseMsg}
	<div class="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
		<div class="mx-4 w-full max-w-lg rounded-xl bg-white p-6 shadow-lg">
			<h2 class="text-base font-semibold text-gray-900">Tool Response</h2>

			<div class="mt-4 max-h-96 space-y-4 overflow-y-auto">
				{#each openToolResponseMsg.tool_responses ?? [] as toolResponse}
					<div>
						<p class="text-xs font-semibold uppercase tracking-wide text-gray-500">
							{toolResponse.tool}
						</p>
						<pre class="mt-1 whitespace-pre-wrap rounded-lg bg-gray-50 p-3 text-sm text-gray-800">{toolResponse.response}</pre>
					</div>
				{/each}
			</div>

			<div class="mt-6 flex justify-end">
				<button
					onclick={() => (openToolResponseMsg = null)}
					class="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 transition-opacity hover:bg-gray-50"
				>
					Close
				</button>
			</div>
		</div>
	</div>
{/if}
