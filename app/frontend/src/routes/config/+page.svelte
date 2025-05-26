<script>
  import { onMount } from "svelte";
  import Terminal from "$lib/Terminal.svelte";
  import { currentContext } from "$lib/stores";

  const terminalInstanceKey = $derived($currentContext);
</script>

<svelte:head>
  <title>dry_agent - Config</title>
</svelte:head>

{#if $currentContext != "default" && $currentContext != null}
  {#key terminalInstanceKey}
    <Terminal
      restartable={true}
      fullscreen={true}
      fontSize="20"
      showWindowList={false}
      command="/bin/bash -c 'while :; do d.rymcg.tech config; done'"
    />
  {/key}
{:else}
  <h1 class="title is-no-text-wrap">No Context</h1>
  <a href="/docker" class="button is-link"
    >Create and/or set a default Docker context</a
  >
{/if}
