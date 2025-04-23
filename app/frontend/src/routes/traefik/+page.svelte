<script>
  import InlineTerminal from "$lib/InlineTerminal.svelte";

  let instanceId = 0;

  function handleExit() {
    instanceId += 1;
  }
</script>

<svelte:head>
  <title>dry_agent - Traefik</title>
</svelte:head>

<p>Configure Traefik</p>

{#key instanceId}
  <InlineTerminal
    command="d.rymcg.tech make traefik config"
    fontSize="12"
    height="300px"
    on:exit={handleExit}
  />
{/key}
