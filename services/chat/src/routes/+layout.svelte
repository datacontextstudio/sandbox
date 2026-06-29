<script lang="ts">
	import '../app.css';

	let { children } = $props();
</script>

<svelte:head>
	<title>DataContext Chat</title>
</svelte:head>

{@render children()}
