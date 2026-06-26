<script lang="ts">
	import './layout.css';
	import favicon from '$lib/assets/favicon.svg';
	import { page } from '$app/state';

	let { children } = $props();
</script>

<svelte:head><link rel="icon" href={favicon} /></svelte:head>

<div class="min-h-screen bg-gray-50">
	<nav class="bg-gray-900 text-white px-6 py-3 flex items-center gap-8">
		<span class="font-semibold text-base tracking-tight select-none">DataContext Studio</span>
		<a
			href="/upload"
			class="text-sm font-medium transition-colors"
			class:text-white={page.url.pathname === '/upload'}
			class:text-gray-400={page.url.pathname !== '/upload'}
		>
			Upload
		</a>
		<a
			href="/query"
			class="text-sm font-medium transition-colors"
			class:text-white={page.url.pathname === '/query'}
			class:text-gray-400={page.url.pathname !== '/query'}
		>
			Query
		</a>
	</nav>
	<main class="max-w-5xl mx-auto px-6 py-8">
		{@render children()}
	</main>
</div>
