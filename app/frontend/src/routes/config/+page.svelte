<script>
  import { onMount } from "svelte";
  import Terminal from "$lib/Terminal.svelte";

  let instanceId = 0;
</script>

<svelte:head>
  <title>dry_agent - Config</title>
</svelte:head>

<Terminal
  restartable="true"
  fullscreen=true
  fontSize=20
  command="/bin/bash -c 'while :; do d.rymcg.tech config; done'"
  />
