<script>
  import AppsTable from "$lib/AppsTable.svelte";
  import { currentContext } from "$lib/stores";
  export let data;
</script>

<svelte:head>
  <title>dry_agent - Available Apps</title>
</svelte:head>

{#if $currentContext != "default" && $currentContext != null}
  {#if data.configExists}
    <h1 class="title">Available Apps</h1>
    <AppsTable />
  {:else}
    <h1 class="title">Root Config Not Found</h1>
    <p>It looks like there is no configuration file for this Docker context.</p>
    <br/>
    <a href="/config" class="button is-link">Setup the Root Config</a>
  {/if}
{:else}
  <h1 class="title">No Context</h1>
  <a href="/docker" class="button is-link">Create and/or set a default Docker context</a>
{/if}

