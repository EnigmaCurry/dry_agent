<script>
  import { invalidateAll } from "$app/navigation";
  import AppsTable from "$lib/AppsTable.svelte";
  import { currentContext } from "$lib/stores";
  let { data } = $props();
  const ConfigKey = $derived(currentContext);

  let selectedTab = $state("configured_apps");

  function selectTab(tab) {
    selectedTab = tab;
  }

  $effect(() => {
    if ($currentContext != null) {
      console.log("invalidate page");
      invalidateAll(); // 🔥 re-run load(), refresh props!
    }
  });
</script>

<svelte:head>
  <title>dry_agent - Available Apps</title>
</svelte:head>

{#key ConfigKey}
  {#if $currentContext != "default" && $currentContext != null}
    {#if data.configExists}
      <div class="tabs is-toggle">
        <ul>
          <li class:is-active={selectedTab === "configured_apps"}>
            <a
              href="#"
              on:click|preventDefault={() => selectTab("configured_apps")}
            >
              <span class="is-small">
                <i class="fas fa-image" aria-hidden="true"></i>
              </span>
              <span>Configured Apps</span>
            </a>
          </li>
          <li class:is-active={selectedTab === "available_apps"}>
            <a
              href="#"
              on:click|preventDefault={() => selectTab("available_apps")}
            >
              <span class="is-small">
                <i class="fas fa-music" aria-hidden="true"></i>
              </span>
              <span>Available Apps</span>
            </a>
          </li>
        </ul>
      </div>

      {#if selectedTab === "configured_apps"}
        <AppsTable context={$currentContext} show_all={false} />
      {:else if selectedTab === "available_apps"}
        <AppsTable context={$currentContext} show_all={true} />
      {/if}
    {:else}
      <h1 class="title">Root Config Not Found</h1>
      <p>
        It looks like there is no configuration file for this Docker context.
      </p>
      <br />
      <a href="/config" class="button is-link">Setup the Root Config</a>
    {/if}
  {:else}
    <h1 class="title">No Context</h1>
    <a href="/docker" class="button is-link">
      Create and/or set a default Docker context
    </a>
  {/if}
{/key}
