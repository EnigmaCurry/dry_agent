<script>
  import { onMount } from "svelte";
  import InlineTerminal from "$lib/InlineTerminal.svelte";

  let instanceId = 0;
</script>

<svelte:head>
  <title>dry_agent - Config</title>
</svelte:head>

<InlineTerminal
  restartable="true"
  fullscreen=true
  fontSize=20
  command="/bin/bash -c 'while :; do d.rymcg.tech config; done'"
  />
