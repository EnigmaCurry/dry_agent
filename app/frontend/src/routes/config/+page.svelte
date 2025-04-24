<script>
  import { onMount } from "svelte";
  import Terminal from "$lib/Terminal.svelte";
  import { currentContext } from "$lib/stores";

  const terminalInstanceKey = $derived($currentContext);
</script>

<svelte:head>
  <title>dry_agent - Config</title>
</svelte:head>

{#key terminalInstanceKey}
<Terminal
  restartable="true"
  fullscreen=true
  fontSize=20
  command="/bin/bash -c 'while :; do d.rymcg.tech config; done'"
  />
{/key}
