<script>
  import { currentContext } from "$lib/stores";
  import ModalTerminal from "./ModalTerminal.svelte";

  let { app } = $props();
  const ContextKey = $derived(currentContext);
  const appTitle = $derived(app.replace(/\b\w/g, (c) => c.toUpperCase()));

  let instances = $state([]);
  let rootEnv = $state(null);
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
  let showTerminal = $state(false);
  let terminalCommand = $state("");
  let terminalRestartable = $state(false);
  let terminalReloadOnClose = $state(false);
  let fetchedServiceStatus = $state(false);

  /** @type {Record<string, string|null>} */
  let statusMap = $state({});

  async function loadData() {
    loading = true;
    error = null;
    instances = [];
    rootEnv = null;
    envDist = null;
    expandedInstance = null;
    expandedConfig = null;
    formData = {};
    try {
      const instancesRes = await fetch(
        `/api/instances/?app=${encodeURIComponent(app)}&include_status=${!fetchedServiceStatus}`,
      );
      if (!instancesRes.ok) {
        throw new Error(`Failed to fetch instances: ${instancesRes.status}`);
      }
      const instancesData = await instancesRes.json();
      const contextData = instancesData[$currentContext];
      if (contextData && contextData[app]) {
        instances = sortInstances(contextData[app] || []);

        for (const instance of instances) {
          if (instance.status != null) {
            statusMap[instance.instance] = instance.status;
          } else if (statusMap[instance.instance]) {
            instance.status = statusMap[instance.instance];
          }
        }
      }

      const envDistRes = await fetch(
        `/api/apps/env-dist/?app=${encodeURIComponent(app)}`,
      );
      if (!envDistRes.ok) {
        throw new Error(`Failed to fetch env_dist: ${envDistRes.status}`);
      }
      envDist = await envDistRes.json();

      const rootEnvRes = await fetch(`/api/d.rymcg.tech/config`);
      if (!rootEnvRes.ok) {
        throw new Error(`Failed to fetch root env: ${rootEnvRes.status}`);
      }
      rootEnv = (await rootEnvRes.json()).env;
    } catch (err) {
      console.error(err);
      error = err.message;
    } finally {
      loading = false;
      fetchedServiceStatus = true;
    }
  }

  function sortInstances(list) {
    const statusOrder = { running: 0, exited: 1 };

    return list.slice().sort((a, b) => {
      const aStatusRaw = a.status ?? statusMap[a.instance];
      const bStatusRaw = b.status ?? statusMap[b.instance];

      const aStatus = statusOrder[aStatusRaw] ?? 2;
      const bStatus = statusOrder[bStatusRaw] ?? 2;

      if (aStatus !== bStatus) return aStatus - bStatus;

      if (a.instance === "default") return -1;
      if (b.instance === "default") return 1;

      return a.instance.localeCompare(b.instance);
    });
  }

  async function toggleExpand(instance) {
    if (expandedInstance !== null && expandedInstance !== instance.instance) {
      await autoSave({ instance: expandedInstance });
    }

    if (expandedInstance === instance.instance) {
      expandedInstance = null;
      expandedConfig = null;
      formData = {};
      await loadData();
    } else {
      await loadData();
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
      originalFormData = structuredClone($state.snapshot(formData));
    } catch (err) {
      saveError = err.message;
      console.error("Auto-save failed:", err);
    } finally {
      saving = false;
    }
  }

  function makeUrl(host) {
    const port = rootEnv.PUBLIC_HTTPS_PORT || "443";
    const path = (envDist?.http_path || "/").replace(/^\/?/, "/");
    return `https://${host}${port !== "443" ? `:${port}` : ""}${path}`;
  }

  function openTerminal(command, restartable, reloadOnClose) {
    terminalCommand = command;
    terminalRestartable = restartable;
    terminalReloadOnClose = reloadOnClose;
    showTerminal = true;
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
    {:else if saveError}
      <div class="notification is-danger">
        <p><strong>Error saving config</strong>: {saveError}</p>
      </div>
    {:else if instances.length > 0 && rootEnv}
      <table class="table is-striped is-fullwidth">
        <thead>
          <tr>
            <th>Instance</th>
            <th>Status</th>
            <th>URL</th>
          </tr>
        </thead>
        <tbody>
          {#each instances as instance (instance.instance)}
            <tr
              class:is-primary={expandedInstance === instance.instance}
              class:has-background-grey-darker={instance.status == null}
              class:is-dark={instance.status === "running"}
              on:click={() => toggleExpand(instance)}
              style="cursor: pointer;"
            >
              <td>
                <button
                  class="button is-fullwidth"
                  class:is-dark={expandedInstance !== instance.instance}
                  class:is-info={expandedInstance !== instance.instance}
                  class:is-danger={expandedInstance === instance.instance}
                >
                  {instance.instance}
                </button>
              </td>
              <td style="vertical-align: middle;">
                {#if instance.status === "running"}
                  <span class="title" title="Instance is running">🏃</span>
                {:else if instance.status === "exited"}
                  <span class="title" title="Instance is stopped">💤</span>
                {:else}
                  <span class="subtitle" title="Instance is not installed">
                    🌱
                  </span>
                {/if}
              </td>
              <td style="vertical-align: middle;">
                <a
                  href={makeUrl(instance.traefik_host)}
                  target="_blank"
                  class:has-text-light={expandedInstance !== instance.instance}
                  class:has-text-dark={expandedInstance === instance.instance}
                  on:click|stopPropagation
                >
                  {makeUrl(instance.traefik_host)}
                </a>
              </td>
            </tr>

            {#if expandedInstance === instance.instance}
              <tr>
                <td colspan="100%">
                  <div class="box">
                    <div
                      class="is-flex is-justify-content-space-between"
                      style="width: 100%;"
                    >
                      <div></div>
                      <!-- Empty left side -->
                      <div class="buttons has-addons">
                        <button
                          class="button is-info"
                          title="Reconfigure .env file"
                          on:click={() =>
                            openTerminal(
                              `d.rymcg.tech make ${app} config instance=${instance.instance}`,
                              false,
                              true,
                            )}
                        >
                          Reconfigure
                        </button>

                        <button
                          class="button is-link"
                          title="Start service"
                          on:click={() =>
                            openTerminal(
                              `d.rymcg.tech make ${app} install instance=${instance.instance}`,
                              false,
                              true,
                            )}
                        >
                          Install
                        </button>

                        {#if statusMap[instance.instance] === "running"}
                          <button
                            class="button is-warning"
                            title="Stop service"
                            on:click={() =>
                              openTerminal(
                                `d.rymcg.tech make ${app} stop instance=${instance.instance}`,
                                false,
                                true,
                              )}
                          >
                            Stop
                          </button>
                        {/if}

                        <!-- {#if statusMap[instance.instance] === "exited"} -->
                        <!--   <button -->
                        <!--     class="button has-background-info-dark" -->
                        <!--     on:click={() => -->
                        <!--       openTerminal( -->
                        <!--         `d.rymcg.tech make ${app} start instance=${instance.instance}`, -->
                        <!--         false, -->
                        <!--         true, -->
                        <!--       )} -->
                        <!--   > -->
                        <!--     Start -->
                        <!--   </button> -->
                        <!-- {/if} -->

                        <button
                          class="button is-danger"
                          title="Remove container AND data volume(s)"
                          on:click={() =>
                            openTerminal(
                              `d.rymcg.tech make ${app} destroy instance=${instance.instance}`,
                              false,
                              true,
                            )}
                        >
                          Destroy
                        </button>
                        {#if statusMap[instance.instance] != "uninstalled"}
                          <button
                            class="button has-background-dark"
                            title="View service logs"
                            on:click={() =>
                              openTerminal(
                                `d.rymcg.tech make ${app} logs instance=${instance.instance}`,
                                false,
                                false,
                              )}
                          >
                            Logs
                          </button>
                        {/if}
                      </div>
                    </div>
                    {#if expandedConfig?.env && envDist?.env}
                      <div class="mb-4">
                        <h2 class="subtitle">
                          Edit the environment variables below.
                        </h2>
                        <em
                          >All changes are saved automatically. Reinstall to
                          apply.</em
                        >
                      </div>
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

<ModalTerminal
  command={terminalCommand}
  title={terminalCommand}
  visible={showTerminal}
  restartable={terminalRestartable}
  on:close={async () => {
    showTerminal = false;
    if (terminalReloadOnClose) window.location.reload();
  }}
/>
