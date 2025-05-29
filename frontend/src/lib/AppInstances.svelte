<script>
  import { currentContext } from "$lib/stores";
  import ModalTerminal from "./ModalTerminal.svelte";

  let { app } = $props();
  const ContextKey = $derived(currentContext);
  const appTitle = $derived(app.replace(/\b\w/g, (c) => c.toUpperCase()));
  let dataLoadedForContext = null;

  let instances = $state([]);
  let rootEnv = $state(null);
  let envDist = $state(null);
  let projectServices = $state([]);
  let loading = $state(true);
  let error = $state(null);
  let validationErrors = $state({});

  let expandedInstance = $state(null); // currently expanded instance
  let expandedConfig = $state(null); // config data for the expanded instance
  let originalFormData = $state({}); // original to track dirty data
  let formData = $state({}); // editable form values
  let saving = $state(false);
  let saveError = $state(null);
  let saveSuccess = $state(null);
  let showTerminal = $state(false);
  let terminalShowServiceSelector = $state(false);
  let terminalCommand = $state("");
  let terminalRestartable = $state(false);
  let terminalReloadOnClose = $state(false);
  let fetchedServiceStatus = $state(false);
  let terminalSelectedService = $state("all");

  const cidrRegex =
    /^(?:(?:25[0-5]|2[0-4]\d|1\d{2}|[1-9]?\d)\.){3}(?:25[0-5]|2[0-4]\d|1\d{2}|[1-9]?\d)\/(?:[0-9]|[1-2][0-9]|3[0-2])$/;
  const domainRegex = /^(?!-)(?:[a-zA-Z0-9-]{1,63}(?<!-)\.)+[a-zA-Z]{2,}$/;

  let terminalControls;
  function onTerminalFormChange() {
    terminalControls.setTitle(terminalCommand);
    terminalControls.setCommand(terminalCommand);
  }

  function onTerminalServiceChange(event) {
    terminalSelectedService = event.target.value;

    // Remove any existing `service=...` argument from the command
    let baseCommand = terminalCommand.replace(/\bservice=\S+/g, "").trim();

    // Add the new service arg if it's not "all"
    if (terminalSelectedService !== "all") {
      baseCommand += ` service=${terminalSelectedService}`;
    }

    terminalControls?.setCommand(baseCommand);
    terminalControls?.setTitle(baseCommand);
  }

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
        `/api/projects/env-dist/?app=${encodeURIComponent(app)}`,
      );
      if (!envDistRes.ok) {
        throw new Error(`Failed to fetch env_dist: ${envDistRes.status}`);
      }
      envDist = await envDistRes.json();

      const projectServicesRes = await fetch(
        `/api/projects/services/?app=${encodeURIComponent(app)}`,
      );
      if (!projectServicesRes.ok) {
        throw new Error(
          `Failed to fetch app services: ${projectServicesRes.status}`,
        );
      }
      projectServices = (await projectServicesRes.json()).services;

      console.log("projectServices", $state.snapshot(projectServices));
      const rootEnvRes = await fetch(`/api/d.rymcg.tech/config`);
      if (!rootEnvRes.ok) {
        throw new Error(`Failed to fetch root env: ${rootEnvRes.status}`);
      }
      rootEnv = await rootEnvRes.json();
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

  function openTerminal(
    command,
    restartable,
    reloadOnClose,
    showServiceSelector,
  ) {
    terminalCommand = command;
    terminalRestartable = restartable;
    terminalReloadOnClose = reloadOnClose;
    terminalShowServiceSelector = showServiceSelector;
    showTerminal = true;
  }

  function validate(key, value) {
    if (value.startsWith(" ") || value.endsWith(" ")) {
      const isValid = false;
      validationErrors = {
        ...validationErrors,
        [key]: isValid ? null : "Must not start or end with whitespace",
      };
      return isValid;
    } else if (key === `${envDist.meta.PREFIX}_IP_SOURCERANGE`) {
      const isValid = cidrRegex.test(value);
      validationErrors = {
        ...validationErrors,
        [key]: isValid ? null : "Must be a valid CIDR (e.g. 192.168.1.0/24)",
      };
      return isValid;
    } else if (key === `${envDist.meta.PREFIX}_TRAEFIK_HOST`) {
      const isValid = domainRegex.test(value);
      validationErrors = {
        ...validationErrors,
        [key]: isValid ? null : "Must be a valid domain (e.g. foo.example.com)",
      };
      return isValid;
    } else if (
      key.endsWith("_UID") ||
      key.endsWith("_GID") ||
      key.endsWith("_PORT")
    ) {
      const n = Number(value);
      const isValid = Number.isInteger(n) && n >= 0 && n <= 65535;
      validationErrors = {
        ...validationErrors,
        [key]: isValid ? null : "Must be an integer between 0 and 65535",
      };
      return isValid;
    }
    return true;
  }

  function handleBlur(key, value, instance) {
    const originalValue = originalFormData[key];
    if (value === originalValue) return;
    if (!validate(key, value)) return;
    autoSave(instance);
  }

  $effect(() => {
    if ($currentContext == null) return;
    if (dataLoadedForContext !== $currentContext) {
      console.log("loading data for context:", $currentContext);
      dataLoadedForContext = $currentContext;
      loadData();
    }
  });
</script>

{#key ContextKey}
  {#if $currentContext != "default" && $currentContext != null}
    <div class="is-flex is-align-items-center is-flex-wrap-wrap m-4">
      <h1 class="title m-0">
        <span class="is-no-text-wrap">
          <a href="/projects">projects</a> / {appTitle}
        </span>
        <span class="subtitle is-6 ml-4 is-no-text-wrap"
          ><a
            href="https://github.com/EnigmaCurry/d.rymcg.tech/blob/master/{app}/README.md"
            target="_blank"
          >
            README</a
          ></span
        >
      </h1>
      <div class="is-flex-grow-1"></div>
      <div class="field has-addons">
        <p class="control">
          <button
            class="button is-link"
            on:click={() =>
              openTerminal(`d.rymcg.tech make ${app} cd`, false, true, false)}
          >
            Workstation
          </button>
        </p>
        <p class="control">
          <button
            class="button is-primary"
            on:click={() =>
              openTerminal(
                `d.rymcg.tech make ${app} instance-new`,
                false,
                true,
                false,
              )}
          >
            New Instance
          </button>
        </p>
      </div>
    </div>

    {#if loading}
      <div class="notification is-dark is-info has-text-centered">
        <span class="loader"></span>
        <p class="animated-dots">
          Loading<span>.</span><span>.</span><span>.</span>
        </p>
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
              class="instance_row"
              class:is-primary={expandedInstance === instance.instance}
              class:has-background-grey-darker={instance.status == null}
              class:is-dark={instance.status === "running"}
              on:click={() => toggleExpand(instance)}
              style="cursor: pointer;"
            >
              <td>
                <button class="button is-fullwidth is-info is-dark">
                  {instance.instance}
                </button>
              </td>
              <td class="status_icon" style="vertical-align: middle;">
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
                          disabled={saving}
                          on:click={() =>
                            openTerminal(
                              `d.rymcg.tech make ${app} config instance=${instance.instance}`,
                              false,
                              true,
                              false,
                            )}
                        >
                          Config
                        </button>

                        <button
                          class="button is-link"
                          title="(Re)start service"
                          disabled={saving}
                          on:click={() =>
                            openTerminal(
                              `d.rymcg.tech make ${app} install instance=${instance.instance}`,
                              false,
                              true,
                              false,
                            )}
                        >
                          Install
                        </button>

                        {#if statusMap[instance.instance] === "running"}
                          <button
                            class="button is-warning"
                            title="Stop service"
                            disabled={saving}
                            on:click={() =>
                              openTerminal(
                                `d.rymcg.tech make ${app} stop instance=${instance.instance}`,
                                false,
                                true,
                                false,
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
                        <!--         false, -->
                        <!--       )} -->
                        <!--   > -->
                        <!--     Start -->
                        <!--   </button> -->
                        <!-- {/if} -->

                        <button
                          class="button is-danger"
                          title="Remove container AND data volume(s)"
                          disabled={saving}
                          on:click={() =>
                            openTerminal(
                              `d.rymcg.tech make ${app} destroy instance=${instance.instance}`,
                              false,
                              true,
                              false,
                            )}
                        >
                          Destroy
                        </button>
                        {#if statusMap[instance.instance] != "uninstalled"}
                          <button
                            class="button has-background-dark"
                            title="View service logs"
                            disabled={saving}
                            on:click={() =>
                              openTerminal(
                                `d.rymcg.tech make ${app} logs instance=${instance.instance}`,
                                false,
                                false,
                                true,
                              )}
                          >
                            Logs
                          </button>
                          <button
                            class="button is-link"
                            on:click={() =>
                              openTerminal(
                                `d.rymcg.tech make ${app} switch instance=${instance.instance}`,
                                false,
                                true,
                                false,
                              )}
                          >
                            Workstation
                          </button>
                        {/if}
                        {#if statusMap[instance.instance] === "uninstalled"}
                          <button
                            class="button has-background-danger-light has-text-danger-dark"
                            title="Delete configuration (but keep data volume(s))"
                            disabled={saving}
                            on:click={() =>
                              openTerminal(
                                `d.rymcg.tech make ${app} clean instance=${instance.instance}`,
                                false,
                                true,
                                false,
                              )}
                          >
                            Clean
                          </button>
                        {/if}
                      </div>
                    </div>
                    {#if expandedConfig?.env && envDist?.env}
                      <div class="mb-4">
                        <h2 class="subtitle">
                          To reconfigure this instance, click Config, or edit
                          the variables below.
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
                          <div
                            class="field"
                            style={key === `${envDist.meta.PREFIX}_INSTANCE`
                              ? "display: none;"
                              : ""}
                          >
                            <label class="label">
                              {key}
                              <span class="help">{meta.comments}</span>
                            </label>

                            <div class="control">
                              {#if meta.default_value === "true" || meta.default_value === "false"}
                                <label class="radio">
                                  <input
                                    type="radio"
                                    name={key}
                                    value="true"
                                    bind:group={formData[key]}
                                    on:blur={() =>
                                      handleBlur(key, formData[key], instance)}
                                  />
                                  True
                                </label>
                                <label class="radio">
                                  <input
                                    type="radio"
                                    name={key}
                                    value="false"
                                    bind:group={formData[key]}
                                    on:blur={() =>
                                      handleBlur(key, formData[key], instance)}
                                  />
                                  False
                                </label>
                              {:else}
                                <input
                                  class="input"
                                  type="text"
                                  bind:value={formData[key]}
                                  placeholder={meta.default_value}
                                  disabled={key ===
                                    `${envDist.meta.PREFIX}_INSTANCE`}
                                  on:blur={() =>
                                    handleBlur(key, formData[key], instance)}
                                />
                              {/if}
                              {#if validationErrors[key]}
                                <p class="help is-danger">
                                  {validationErrors[key]}
                                </p>
                              {/if}
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
  bind:visible={showTerminal}
  bind:title={terminalCommand}
  bind:command={terminalCommand}
  bind:update={terminalControls}
  bind:restartable={terminalRestartable}
  on:close={async () => {
    showTerminal = false;
    if (terminalReloadOnClose) {
      fetchedServiceStatus = false;
      await loadData();
    }
  }}
>
  <div slot="form" class="field ml-4 mr-4">
    {#if terminalShowServiceSelector}
      <label class="label">Service</label>
      <div class="control">
        <div class="select is-fullwidth">
          <select
            on:change={onTerminalServiceChange}
            bind:value={terminalSelectedService}
          >
            <option value="all">all</option>
            {#each $state.snapshot(projectServices) as service}
              <option value={service}>{service}</option>
            {/each}
          </select>
        </div>
      </div>
    {/if}
  </div>
</ModalTerminal>

<style>
  .instance_row.is-primary .status_icon span {
    background-color: #440707;
    padding: 0.5em;
    opacity: 0.5;
  }
</style>
