<script>
  import InlineTerminal from "$lib/InlineTerminal.svelte";
</script>

<svelte:head>
  <title>dry_agent - Terminal</title>
</svelte:head>

<p>Hello!</p>

<InlineTerminal command="/bin/bash" fontSize="12" height="300px" />

<p>L8R</p>
