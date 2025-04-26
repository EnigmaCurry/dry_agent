<script>
  import { invalidateAll } from '$app/navigation';
  import AppsTable from "$lib/AppsTable.svelte";
  import { currentContext } from "$lib/stores";
  let { data } = $props();
  const ConfigKey = $derived(currentContext);

  $effect(() => {
    if ($currentContext != null) {
      console.log("invalidate page");
      invalidateAll(); // 🔥 re-run load(), refresh props!
    }
  })

</script>

<svelte:head>
  <title>dry_agent - Available Apps</title>
</svelte:head>

{#key ConfigKey}
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
{/key}
