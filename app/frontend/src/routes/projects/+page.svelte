<script>
  import { invalidateAll } from "$app/navigation";
  import { page } from "$app/stores";
  import ProjectsTable from "$lib/ProjectsTable.svelte";
  import { currentContext } from "$lib/stores";
  let { data } = $props();
  const ConfigKey = $derived(currentContext);

  // Default fallback
  let selectedTab = $state("configured_projects");

  // Check for selected_tab query param
  $effect(() => {
    const tab = $page.url.searchParams.get("t");
    if (tab === "configured_projects" || tab === "available_projects") {
      selectedTab = tab;
    }
  });

  $effect(() => {
    const url = new URL(window.location);
    if (url.searchParams.get("t") !== selectedTab) {
      url.searchParams.set("t", selectedTab);
      history.replaceState(null, "", url);
    }
  });

  function selectTab(tab) {
    selectedTab = tab;
  }

  $effect(() => {
    if ($currentContext != null) {
      //console.log("invalidate page");
      invalidateAll();
    }
  });
</script>

<svelte:head>
  <title>dry_agent - Available Projects</title>
</svelte:head>

{#key ConfigKey}
  {#if $currentContext != "default" && $currentContext != null}
    {#if data.configExists}
      <div class="is-flex is-flex-wrap-wrap">
        <h1 class="title m-4 is-flex-grow-1 is-no-text-wrap">Projects</h1>
        <div class="is-flex-grow-1"></div>
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
      <h1 class="title m-4 is-no-text-wrap">Root Config Not Found</h1>
      <div class="m-4">
        <p>
          It looks like there is no configuration file for this Docker context.
        </p>
        <br />
        <a href="/config" class="button is-link">Setup the Root Config</a>
      </div>
    {/if}
  {:else}
    <h1 class="title is-no-text-wrap">No Context</h1>
    <a href="/docker" class="button is-link">
      Create and/or set a default Docker context
    </a>
  {/if}
{/key}
