<script>
  import InlineTerminal from "$lib/InlineTerminal.svelte";
</script>

<svelte:head>
  <title>dry_agent - Traefik</title>
</svelte:head>

<p>Configure Traefik</p>

<InlineTerminal command="d.rymcg.tech make traefik config" fontSize="12" height="300px" />
