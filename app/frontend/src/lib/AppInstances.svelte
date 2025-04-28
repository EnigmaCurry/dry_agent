<script>
  import { currentContext } from "$lib/stores";

  let { app } = $props();
  const ContextKey = $derived(currentContext);
  const appTitle = $derived(app.replace(/\b\w/g, (c) => c.toUpperCase()));

  let instances = $state([]);
  let envDist = $state(null);
  let loading = $state(true);
  let error = $state(null);

  let expandedInstance = $state(null); // currently expanded instance
  let expandedConfig = $state(null); // config data for the expanded instance
  let originalFormData = $state({}); // original to track dirty data
  let formData = $state({}); // editable form values
  let saving = $state(false);
  let saveError = $state(null);
  let saveSuccess = $state(null);

  async function loadData() {
    loading = true;
    error = null;
    instances = [];
    envDist = null;
    expandedInstance = null;
    expandedConfig = null;
    formData = {};
    try {
      const instancesRes = await fetch(
        `/api/instances/?app=${encodeURIComponent(app)}`,
      );
      if (!instancesRes.ok) {
        throw new Error(`Failed to fetch instances: ${instancesRes.status}`);
      }
      const instancesData = await instancesRes.json();
      const contextData = instancesData[$currentContext];
      if (contextData && contextData[app]) {
        instances = contextData[app];
      }

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

  async function toggleExpand(instance) {
    if (expandedInstance !== null && expandedInstance !== instance.instance) {
      await autoSave({ instance: expandedInstance });
    }

    if (expandedInstance === instance.instance) {
      expandedInstance = null;
      expandedConfig = null;
      formData = {};
    } else {
      expandedInstance = instance.instance;
      try {
        const res = await fetch(
          `/api/instances/config?env_path=${encodeURIComponent(instance.env_path)}`,
        );
        if (!res.ok) {
          throw new Error(`Failed to load instance config`);
        }
        expandedConfig = await res.json();

        formData = {};
        for (const [key, val] of Object.entries(expandedConfig.env || {})) {
          formData[key] = val ?? "";
        }
        originalFormData = structuredClone($state.snapshot(formData));
      } catch (err) {
        console.error(err);
        expandedConfig = null;
        formData = {};
      }
      console.log("Expanded config loaded:", expandedConfig);
    }
    saveError = null;
    saveSuccess = null;
  }

  async function saveConfig(instance) {
    saving = true;
    saveError = null;
    saveSuccess = null;
    try {
      const form = new FormData();
      form.append("app", app);
      form.append("context", $currentContext);

      for (const [key, value] of Object.entries(formData)) {
        form.append(key, value ?? "");
      }

      const res = await fetch("/api/instances/config", {
        method: "POST",
        body: form,
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Failed to save config");
      }

      saveSuccess = "Configuration saved successfully!";
    } catch (err) {
      saveError = err.message;
    } finally {
      saving = false;
    }
  }

  async function autoSave(instanceObj) {
    if (saving) return;
    if (!instanceObj) return;

    // Check if formData has actually changed compared to originalFormData
    const dirty = Object.keys(formData).some(
      (key) => formData[key] !== originalFormData[key],
    );

    if (!dirty) {
      console.log("No changes detected; skipping auto-save.");
      return; // Don't save if no actual changes
    }

    saving = true;
    saveError = null;
    try {
      const form = new FormData();
      form.append("app", app);
      form.append("context", $currentContext);

      for (const [key, value] of Object.entries(formData)) {
        form.append(key, value ?? "");
      }

      const res = await fetch("/api/instances/config", {
        method: "POST",
        body: form,
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Failed to save config");
      }

      saveSuccess = "Configuration saved successfully!";
      console.log("Auto-saved successfully.");
      // Update the originalFormData snapshot after saving
      originalFormData = structuredClone(formData);
    } catch (err) {
      saveError = err.message;
      console.error("Auto-save failed:", err);
    } finally {
      saving = false;
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
    {:else if instances.length > 0}
      <table class="table is-striped is-fullwidth">
        <thead>
          <tr>
            <th>Instance Name</th>
            <th>Env File Path</th>
          </tr>
        </thead>
        <tbody>
          {#each instances as instance (instance.instance)}
            <tr
              on:click={() => toggleExpand(instance)}
              class:is-dark={true}
              class:is-primary={expandedInstance === instance.instance}
              style="cursor: pointer;"
            >
              <td>{instance.instance}</td>
              <td>{instance.env_path}</td>
            </tr>

            {#if expandedInstance === instance.instance}
              <tr>
                <td colspan="2">
                  <div class="box">
                    {#if expandedConfig?.env && envDist?.env}
                      <form
                        on:submit|preventDefault={() => saveConfig(instance)}
                      >
                        {#each Object.entries(envDist.env || {}) as [key, meta]}
                          <div class="field">
                            <label class="label">
                              {key}
                              <span class="help">{meta.comments}</span>
                            </label>
                            <div class="control">
                              <input
                                class="input"
                                type="text"
                                bind:value={formData[key]}
                                placeholder={meta.default_value}
                                on:blur={() => autoSave(instance)}
                              />
                            </div>
                          </div>
                        {/each}
                      </form>
                    {:else}
                      <p>Loading instance config...</p>
                    {/if}
                  </div>
                </td>
              </tr>
            {/if}
          {/each}
        </tbody>
      </table>
    {:else}
      <div class="notification is-primary">
        <p>No instances of this app are configured for the current context.</p>
      </div>
    {/if}
  {/if}
{/key}
