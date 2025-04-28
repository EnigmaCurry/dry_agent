<script>
  import { currentContext } from "$lib/stores";

  let { app } = $props();
  const ContextKey = $derived(currentContext);
  const appTitle = $derived(app.replace(/\b\w/g, (c) => c.toUpperCase()));

  let instances = $state([]);
  let envDist = $state(null); // new
  let loading = $state(true);
  let error = $state(null);

  async function loadData() {
    loading = true;
    error = null;
    instances = [];
    envDist = null;

    try {
      // Fetch instances
      const instancesRes = await fetch(
        `/api/instances/?app=${encodeURIComponent(app)}`,
      );
      if (!instancesRes.ok) {
        throw new Error(`Failed to fetch instances: ${instancesRes.status}`);
      }
      const instancesData = await instancesRes.json();
      const contextData = instancesData[$currentContext];
      if (contextData && contextData[app]) {
        instances = contextData[app]; // Array of objects
      }

      // Fetch env_dist
      const envDistRes = await fetch(
        `/api/apps/env-dist/?app=${encodeURIComponent(app)}`,
      );
      if (!envDistRes.ok) {
        throw new Error(`Failed to fetch env_dist: ${envDistRes.status}`);
      }
      envDist = await envDistRes.json();
    } catch (err) {
      error = err.message;
    } finally {
      loading = false;
    }
  }

  $effect(() => {
    if ($currentContext != null) {
      loadData();
    }
  });
</script>

{#key ContextKey}
  {#if $currentContext != "default" && $currentContext != null}
    <h1 class="title">{appTitle}</h1>

    {#if loading}
      <div class="notification">
        <p>Loading data...</p>
      </div>
    {:else if error}
      <p class="has-text-danger">Error: {error}</p>
    {:else}
      {#if instances.length > 0}
        <table class="table is-striped is-fullwidth">
          <thead>
            <tr>
              <th>Instance Name</th>
              <th>Env File Path</th>
            </tr>
          </thead>
          <tbody>
            {#each instances as instance}
              <tr>
                <td>{instance.instance}</td>
                <td>{instance.env_path}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      {:else}
        <div class="notification is-primary">
          <p>
            No instances of this app are configured for the current context.
          </p>
        </div>
      {/if}

      {#if envDist}
        <h2 class="subtitle mt-5">Environment Variables</h2>
        <table class="table is-narrow is-fullwidth">
          <thead>
            <tr>
              <th>Key</th>
              <th>Default Value</th>
            </tr>
          </thead>
          <tbody>
            {#each Object.entries(envDist.env || {}) as [key, value]}
              <tr>
                <td><code>{key}</code></td>
                <td>{value}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      {/if}
    {/if}
  {/if}
{/key}
