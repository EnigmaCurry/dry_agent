<script>
  import { onMount } from "svelte";
  import ModalTerminal from "./ModalTerminal.svelte";
  import {
    currentContext,
    dockerContexts,
    refreshDockerContexts,
  } from "$lib/stores";

  /**
   * @typedef {Object} SSHConfig
   * @property {string[]} Host
   * @property {string} HostName
   * @property {string} User
   * @property {number} Port
   */

  /** @type {SSHConfig[]|null} */
  let sshConfigs = null;
  /** @type {string|null} */
  let error = null;

  /**
   * SSH connection statuses.
   * @type {{ [key: string]: "pending" | "success" | "error" }}
   */
  let statuses = {};

  /**
   * Docker context statuses.
   * @type {{ [key: string]: "pending" | "success" | "error" }}
   */
  let dockerStatuses = {};

  /**
   * If a Docker test fails, store its error detail.
   * @type {{ [key: string]: string }}
   */
  let dockerDetails = {};

  // Variables for the "Add SSH Connection" modal and form.
  let showForm = false;
  /** @type {string|null} */
  let formError = null;
  let newSSHConfig = {
    Host: "",
    Hostname: "",
    User: "root",
    Port: 22,
  };

  // Variable to hold the client key.
  let clientKey = "";
  // Variable for the copy button icon.
  let copyIcon = "📋";

  // New state variables for the terminal overlay.
  let showTerminal = false;
  /** @type {string|null} */
  let activeTerminalHost = null;

  let showInfoModal = false;
  /** @type {string|null} */
  let infoHost = null;
  /** @type {string|null} */
  let hostFingerprint = null;
  let infoError = null;

  /** @type {string|null} */
  let terminalCommand = null;
  let terminalRestartable = "false";

  /** @type {string|null} */
  let defaultContext = null;

  /**
   * Fetches the client key from /api/ssh_config/key.
   */
  async function loadClientKey() {
    try {
      const response = await fetch("/api/ssh_config/key");
      if (response.ok) {
        const data = await response.json();
        clientKey = data.key;
      } else {
        clientKey = "Error: Unable to load client key.";
      }
    } catch (err) {
      clientKey = err instanceof Error ? err.message : String(err);
    }
  }

  /**
   * Opens the add form and loads the client key.
   */
  async function openAddForm() {
    showForm = true;
    await loadClientKey();
  }

  /**
   * Opens the terminal overlay for the given host and command.
   * @param {string} host
   * @param {string} command
   */
  function openTerminal(host, command, restartable) {
    activeTerminalHost = host;
    terminalCommand = command;
    terminalRestartable = restartable;
    showTerminal = true;
  }

  /**
   * Copies the client key to the clipboard.
   * Changes the copy button icon briefly to a checkmark.
   */
  async function copyClientKey() {
    try {
      await navigator.clipboard.writeText(clientKey);
      copyIcon = "✅";
      setTimeout(() => {
        copyIcon = "📋";
      }, 2000);
    } catch (err) {
      console.error("Failed to copy client key", err);
    }
  }

  /**
   * Selects all text in the clicked pre element.
   * @param {MouseEvent} event
   */
  function selectPre(event) {
    const range = document.createRange();
    range.selectNodeContents(event.currentTarget);
    const selection = window.getSelection();
    selection.removeAllRanges();
    selection.addRange(range);
  }

  /**
   * Fetches the list of SSH configurations and initializes their statuses.
   */
  async function loadConfigs() {
    try {
      const response = await fetch("/api/ssh_config/");
      if (!response.ok) {
        throw new Error("Failed to fetch SSH configuration");
      }
      const data = await response.json();
      sshConfigs = Array.isArray(data) ? data : [];

      // Reset statuses
      statuses = {};
      dockerStatuses = {};
      dockerDetails = {};
      await loadDockerContexts();
      await loadDefaultContext();

      for (const config of sshConfigs) {
        const hostAlias = config.Host[0];
        statuses[hostAlias] = "pending";
        dockerStatuses[hostAlias] = "pending";
        testConnection(hostAlias);
        testDockerContext(hostAlias);
      }
    } catch (err) {
      sshConfigs = []; // Prevents UI from getting stuck
      error = err instanceof Error ? err.message : String(err);
      console.error("Error fetching SSH configurations:", err);
    }
  }

  /**
   * Tests an SSH connection given a host alias.
   * @param {string} host The host alias to test.
   */
  async function testConnection(host) {
    try {
      const response = await fetch(`/api/ssh_config/test/${host}`);
      statuses[host] = response.ok ? "success" : "error";
    } catch (err) {
      statuses[host] = "error";
    }
    // Trigger reactivity.
    statuses = { ...statuses };
  }

  /**
   * Loads the list of Docker contexts.
   */
  async function loadDockerContexts() {
    try {
      const response = await fetch("/api/docker_context/");
      if (response.ok) {
        const data = await response.json();
        dockerContexts.set(data);
      } else {
        dockerContexts.set([]);
      }
    } catch (err) {
      dockerContexts.set([]);
    }
  }

  /**
   * Tests (or creates then tests) a Docker context for the given host alias.
   * @param {string} host The host alias to test.
   */
  async function testDockerContext(host) {
    // If the docker context doesn't exist, create it.
    if (!$dockerContexts.includes(host)) {
      try {
        // Send the context_name as a query parameter.
        const response = await fetch(
          `/api/docker_context/?context_name=${encodeURIComponent(host)}`,
          { method: "POST" },
        );
        if (response.ok) {
          await refreshDockerContexts();
        } else {
          dockerStatuses[host] = "error";
          dockerDetails[host] = "Failed to create Docker context";
          dockerStatuses = { ...dockerStatuses };
          dockerDetails = { ...dockerDetails };
          return;
        }
      } catch (err) {
        dockerStatuses[host] = "error";
        dockerDetails[host] = err instanceof Error ? err.message : String(err);
        dockerStatuses = { ...dockerStatuses };
        dockerDetails = { ...dockerDetails };
        return;
      }
    }
    // Now test the docker context.
    try {
      const response = await fetch(`/api/docker_context/test/${host}`);
      if (response.ok) {
        dockerStatuses[host] = "success";
        dockerDetails[host] = "";
      } else {
        let errorData = await response.json();
        let detail = errorData.detail || "Docker test failed";
        dockerStatuses[host] = "error";
        dockerDetails[host] = detail;
      }
    } catch (err) {
      dockerStatuses[host] = "error";
      dockerDetails[host] = err instanceof Error ? err.message : String(err);
    }
    dockerStatuses = { ...dockerStatuses };
    dockerDetails = { ...dockerDetails };
  }

  /**
   * Deletes an SSH connection given a host alias.
   * Also deletes the corresponding Docker context.
   * @param {string} host The host alias to delete.
   */
  async function deleteSSHConfig(host) {
    try {
      let dockerDeleteFailed = false;

      // Try to delete the Docker context
      const dockerResponse = await fetch(`/api/docker_context/${host}`, {
        method: "DELETE",
      });
      if (!dockerResponse.ok) {
        dockerDeleteFailed = true;
        console.error(`Failed to delete Docker context for ${host}`);
      }

      // Always attempt to delete the SSH config, even if docker delete failed
      const sshResponse = await fetch(`/api/ssh_config/${host}`, {
        method: "DELETE",
      });
      if (!sshResponse.ok) {
        throw new Error("Failed to delete SSH configuration");
      }

      // Local cleanups
      if (sshConfigs) {
        sshConfigs = sshConfigs.filter((config) => config.Host[0] !== host);
      }
      delete statuses[host];
      delete dockerStatuses[host];
      delete dockerDetails[host];

      await refreshDockerContexts();

      // 🔥 If the deleted host was the currentContext, set a new default
      if (host === $currentContext) {
        if ($dockerContexts.length > 0) {
          const newDefault = $dockerContexts[0];
          await setDefaultContext(newDefault);
          currentContext.set(newDefault);
        } else {
          currentContext.set(null);
        }
      }

      // 🔔 After all, if docker delete failed, warn user
      if (dockerDeleteFailed) {
        alert(
          `Warning: SSH config was deleted, but failed to delete Docker context for ${host}.`,
        );
      }
    } catch (err) {
      alert(err instanceof Error ? err.message : String(err));
      console.error("Error deleting configuration:", err);
    }
  }

  /**
   * Adds a new SSH connection using the form data.
   * @param {Event} event The form submission event.
   */
  async function addSSHConfig(event) {
    event.preventDefault();
    formError = null;
    try {
      const response = await fetch("/api/ssh_config/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(newSSHConfig),
      });
      const data = await response.json();
      if (!response.ok) {
        formError =
          data.detail || "An error occurred while adding the SSH connection.";
        return;
      }

      newSSHConfig = { Host: "", Hostname: "", User: "root", Port: 22 };
      showForm = false;

      await loadConfigs();
      await refreshDockerContexts();

      // 🔽 Set as default if this is the only SSH context
      if (sshConfigs.length === 1) {
        const firstHost = sshConfigs[0].Host[0];
        await testDockerContext(firstHost);
        await setDefaultContext(firstHost);
      }
    } catch (err) {
      formError = err instanceof Error ? err.message : String(err);
      console.error("Error adding SSH configuration:", err);
    }
  }

  async function openInfoModal(host) {
    infoHost = host;
    showInfoModal = true;
    hostFingerprint = null;
    infoError = null;

    try {
      const response = await fetch(`/api/ssh_config/fingerprint/${host}`);
      if (response.ok) {
        const data = await response.json();
        hostFingerprint = data.fingerprint;
      } else {
        const data = await response.json();
        infoError = data.detail || "Failed to fetch fingerprint.";
      }
    } catch (err) {
      infoError = err instanceof Error ? err.message : String(err);
    }
  }

  async function loadDefaultContext() {
    try {
      const response = await fetch("/api/docker_context/default");
      if (response.ok) {
        const data = await response.json();
        defaultContext = data.default_context;
      } else {
        defaultContext = null;
      }
    } catch (err) {
      defaultContext = null;
    }
  }

  async function setDefaultContext(host) {
    try {
      const response = await fetch(`/api/docker_context/${host}/default`, {
        method: "PUT",
      });
      if (response.ok) {
        defaultContext = host;
        currentContext.set(host);
      } else {
        alert("Failed to set default Docker context.");
      }
    } catch (err) {
      alert(
        "Error setting default context: " +
          (err instanceof Error ? err.message : String(err)),
      );
    }
  }

  onMount(() => {
    loadConfigs();
    loadDefaultContext();
    refreshDockerContexts();
  });
</script>

<div class="is-flex is-flex-direction-column is-justify-content-space-between">
  {#if error}
    <div class="notification is-danger">{error}</div>
  {:else if sshConfigs === null}
    <div class="notification is-info">Loading SSH connections...</div>
  {:else if sshConfigs.length === 0}
    <div
      class="is-flex is-align-items-center is-justify-content-space-between m-4"
    >
      <h1 class="title m-0 is-no-text-wrap">SSH Config and Docker Contexts</h1>
      <div class="field has-addons">
        <p class="control">
          <button class="button is-link" onclick={openAddForm}>
            Add new context
          </button>
        </p>
      </div>
    </div>
    <div class="notification is-warning">No SSH connections defined.</div>
  {:else}
    <div
      class="is-flex is-align-items-center is-justify-content-space-between m-4"
    >
      <h1 class="title m-0 is-no-text-wrap">SSH Config and Docker Contexts</h1>
      <div class="field has-addons">
        <p class="control">
          <button class="button is-link" onclick={openAddForm}>
            Add new context
          </button>
        </p>
      </div>
    </div>
    <div class="is-scrollable-y">
      <table class="table is-striped is-hoverable">
        <thead>
          <tr>
            <th>Host</th>
            <th>HostName</th>
            <th>User</th>
            <th>Port</th>
            <th class="has-text-centered">Status</th>
            <th>Manage</th>
          </tr>
        </thead>
        <tbody>
          {#each sshConfigs as config}
            <tr>
              <td
                >{config.Host[0]}
                {#if dockerStatuses[config.Host[0]] === "success"}
                  {#if defaultContext === config.Host[0]}
                    <span class="tag ml-2 is-dark no-pointer">🏁 Default</span>
                  {/if}
                {/if}
              </td>
              <td>{config.HostName}</td>
              <td>{config.User}</td>
              <td>{config.Port}</td>
              <td class="has-text-centered">
                {#if statuses[config.Host[0]] === "pending"}
                  <span
                    role="img"
                    aria-label="Pending check"
                    title="Pending check">🕑</span
                  >
                {:else if statuses[config.Host[0]] === "success"}
                  {#if dockerStatuses[config.Host[0]] === "error"}
                    <!-- If the Docker test fails, replace the checkmark with a quarter moon,
                       using the error detail in the aria-label and title -->
                    <span
                      role="img"
                      aria-label={dockerDetails[config.Host[0]] ||
                        "Docker context failed"}
                      title={dockerDetails[config.Host[0]] ||
                        "Docker context failed"}>🌓</span
                    >
                  {:else}
                    <span
                      role="img"
                      aria-label="Connection successful"
                      title="Connection successful">✅</span
                    >
                    {#if dockerStatuses[config.Host[0]] === "success"}
                      <span
                        role="img"
                        aria-label="Docker context successful"
                        title="Docker context successful">🐋</span
                      >
                    {/if}
                  {/if}
                {:else if statuses[config.Host[0]] === "error"}
                  <span
                    role="img"
                    aria-label="Connection failed"
                    title="Connection failed">❌</span
                  >
                {/if}
              </td>
              <td>
                <button
                  class="button is-danger is-small"
                  onclick={() => deleteSSHConfig(config.Host[0])}
                >
                  Delete
                </button>
                {#if statuses[config.Host[0]] === "success"}
                  <button
                    class="button is-info is-small"
                    onclick={() =>
                      openTerminal(
                        config.Host[0],
                        `ssh -t ${config.Host[0]}`,
                        "true",
                      )}
                  >
                    Connect
                  </button>
                  <button
                    class="button is-light is-small"
                    onclick={() => openInfoModal(config.Host[0])}
                  >
                    Info
                  </button>
                  {#if dockerStatuses[config.Host[0]] === "success"}
                    {#if defaultContext != config.Host[0]}
                      <button
                        class="button is-primary is-small"
                        onclick={() => setDefaultContext(config.Host[0])}
                      >
                        Set Default
                      </button>
                    {/if}
                  {/if}
                  {#if dockerStatuses[config.Host[0]] === "error"}
                    <button
                      class="button is-warning is-small"
                      onclick={() =>
                        openTerminal(
                          config.Host[0],
                          `ssh -t ${config.Host[0]} "curl -sSL https://get.docker.com | sh"`,
                          "false",
                        )}
                    >
                      Install Docker
                    </button>
                  {/if}
                {/if}
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
</div>

<!-- Modal for adding a new SSH connection -->
<div class="modal {showForm ? 'is-active' : ''}">
  <div class="modal-background" onclick={() => (showForm = false)}></div>
  <div class="modal-card">
    <header class="modal-card-head">
      <p class="modal-card-title">Add SSH Docker Context</p>
      <button
        type="button"
        class="delete"
        aria-label="close"
        onclick={() => (showForm = false)}
      ></button>
    </header>
    <section class="modal-card-body">
      <!-- Display the client key with line wrapping, click-to-select and a copy button -->
      <p>
        Before adding a new context, copy this SSH key into your Docker server's
        authorized_keys file (e.g. <code>/root/.ssh/authorized_keys</code>):
      </p>
      <div
        style="display: flex; align-items: flex-start; gap: 0.5rem; margin: 1em 0;"
      >
        <pre
          onclick={selectPre}
          style="background: #371d1d; padding: 1em; border-radius: 4px; flex-grow: 1; font-weight: bold;">{clientKey}</pre>
        <button type="button" class="button is-small" onclick={copyClientKey}>
          {copyIcon}
        </button>
      </div>

      <!-- 🛠 Wrap the fields inside a real <form> -->
      <form onsubmit={addSSHConfig}>
        <div class="columns">
          <div class="column">
            <div class="field">
              <label for="host" class="label">Context</label>
              <div class="control">
                <input
                  id="host"
                  name="host"
                  class="input"
                  type="text"
                  minlength="2"
                  bind:value={newSSHConfig.Host}
                  placeholder="Enter short host alias (context)"
                  required
                />
              </div>
            </div>
          </div>
          <div class="column">
            <div class="field">
              <label for="hostname" class="label">Hostname or IP address</label>
              <div class="control">
                <input
                  id="hostname"
                  name="hostname"
                  class="input"
                  type="text"
                  minlength="1"
                  bind:value={newSSHConfig.Hostname}
                  placeholder="Enter fully qualified hostname or IP address"
                  required
                />
              </div>
            </div>
          </div>
        </div>

        <div class="columns">
          <div class="column">
            <div class="field">
              <label for="username" class="label">Username</label>
              <div class="control">
                <input
                  id="username"
                  name="username"
                  class="input"
                  type="text"
                  minlength="1"
                  bind:value={newSSHConfig.User}
                  placeholder="Enter username"
                  required
                />
              </div>
            </div>
          </div>
          <div class="column">
            <div class="field">
              <label for="port" class="label">Port</label>
              <div class="control">
                <input
                  id="port"
                  name="port"
                  class="input"
                  type="number"
                  min="1"
                  bind:value={newSSHConfig.Port}
                  required
                />
              </div>
            </div>
          </div>
        </div>

        {#if formError}
          <p class="help is-danger">{formError}</p>
        {/if}

        <div class="field is-grouped is-grouped-right">
          <p class="control">
            <button
              type="button"
              class="button"
              onclick={() => (showForm = false)}
            >
              Cancel
            </button>
          </p>
          <p class="control">
            <button type="submit" class="button is-primary"> Add </button>
          </p>
        </div>
      </form>
    </section>
  </div>
</div>

<ModalTerminal
  command={terminalCommand}
  title={activeTerminalHost}
  restartable={terminalRestartable}
  visible={showTerminal}
  on:close={() => (showTerminal = false)}
/>

{#if showInfoModal}
  <div class="modal is-active">
    <div class="modal-background" onclick={() => (showInfoModal = false)}></div>
    <div class="modal-card">
      <header class="modal-card-head">
        <p class="modal-card-title">Info for {infoHost}</p>
        <button
          class="delete"
          aria-label="close"
          onclick={() => (showInfoModal = false)}
        ></button>
      </header>
      <section class="modal-card-body">
        {#if infoError}
          <div class="notification is-danger">{infoError}</div>
        {:else if hostFingerprint === null}
          <div class="notification is-info">Fetching fingerprint...</div>
        {:else}
          <div class="content">
            <p><strong>SSH Fingerprint:</strong></p>
            <pre>{hostFingerprint}</pre>
          </div>
        {/if}
      </section>
      <footer class="modal-card-foot">
        <button class="button" onclick={() => (showInfoModal = false)}
          >Close</button
        >
      </footer>
    </div>
  </div>
{/if}
