<script>
  import { invalidateAll } from "$app/navigation";
  import ProjectsTable from "$lib/ProjectsTable.svelte";
  import { currentContext } from "$lib/stores";
  let { data } = $props();
  const ConfigKey = $derived(currentContext);

  let selectedTab = $state("configured_projects");

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
  <title>dry_agent - Available Projects</title>
</svelte:head>

{#key ConfigKey}
  {#if $currentContext != "default" && $currentContext != null}
    {#if data.configExists}
      <div class="is-flex">
        <h1 class="title m-4 is-flex-grow-1">Projects</h1>
        <div class="tabs is-toggle m-4">
          <ul>
            <li class:is-active={selectedTab === "configured_projects"}>
              <a
                href="#"
                onclick={(e) => {
                  e.preventDefault();
                  selectTab("configured_projects");
                }}
              >
                <span class="is-small">
                  <i class="fas fa-image" aria-hidden="true"></i>
                </span>
                <span>Configured Projects</span>
              </a>
            </li>
            <li class:is-active={selectedTab === "available_projects"}>
              <a
                href="#"
                onclick={(e) => {
                  e.preventDefault();
                  selectTab("available_projects");
                }}
              >
                <span class="is-small">
                  <i class="fas fa-music" aria-hidden="true"></i>
                </span>
                <span>Available Projects</span>
              </a>
            </li>
          </ul>
        </div>
      </div>
      {#if selectedTab === "configured_projects"}
        <ProjectsTable context={$currentContext} show_all={false} />
      {:else if selectedTab === "available_projects"}
        <ProjectsTable context={$currentContext} show_all={true} />
      {/if}
    {:else}
      <h1 class="title m-4">Root Config Not Found</h1>
      <div class="m-4">
        <p>
          It looks like there is no configuration file for this Docker context.
        </p>
        <br />
        <a href="/config" class="button is-link">Setup the Root Config</a>
      </div>
    {/if}
  {:else}
    <h1 class="title">No Context</h1>
    <a href="/docker" class="button is-link">
      Create and/or set a default Docker context
    </a>
  {/if}
{/key}
