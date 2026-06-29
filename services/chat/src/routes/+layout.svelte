<script lang="ts">
	import '../app.css';

	let { children } = $props();
</script>

<svelte:head>
	<title>DataContext Chat</title>
</svelte:head>

<div class="min-h-screen bg-gray-50 flex flex-col">
	<nav class="bg-gray-900 text-white px-6 py-3 flex items-center gap-3 shrink-0">
		<span class="font-semibold text-base tracking-tight select-none">DataContext Chat</span>
	</nav>
	<div class="flex-1 flex flex-col">
		{@render children()}
	</div>
</div>
