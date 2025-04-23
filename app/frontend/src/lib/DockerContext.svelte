<script>
  import { onMount } from "svelte";
  import InlineTerminal from "./InlineTerminal.svelte"; // Adjust path as needed

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

  /**
   * List of Docker context names.
   * @type {string[]}
   */
  let dockerContexts = [];

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
        dockerContexts = await response.json();
      } else {
        dockerContexts = [];
      }
    } catch (err) {
      dockerContexts = [];
    }
  }

  /**
   * Tests (or creates then tests) a Docker context for the given host alias.
   * @param {string} host The host alias to test.
   */
  async function testDockerContext(host) {
    // If the docker context doesn't exist, create it.
    if (!dockerContexts.includes(host)) {
      try {
        // Send the context_name as a query parameter.
        const response = await fetch(
          `/api/docker_context/?context_name=${encodeURIComponent(host)}`,
          { method: "POST" },
        );
        if (response.ok) {
          dockerContexts.push(host);
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
      // First, delete the Docker context.
      const dockerResponse = await fetch(`/api/docker_context/${host}`, {
        method: "DELETE",
      });
      if (!dockerResponse.ok) {
        throw new Error("Failed to delete Docker context");
      }
      // Then, delete the SSH configuration.
      const sshResponse = await fetch(`/api/ssh_config/${host}`, {
        method: "DELETE",
      });
      if (!sshResponse.ok) {
        throw new Error("Failed to delete SSH configuration");
      }
      if (sshConfigs) {
        sshConfigs = sshConfigs.filter((config) => config.Host[0] !== host);
      }
      delete statuses[host];
      delete dockerStatuses[host];
      delete dockerDetails[host];
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
        // Show error detail from response, or a default error message.
        formError =
          data.detail || "An error occurred while adding the SSH connection.";
        return;
      }
      // Clear the form and close the dialog.
      newSSHConfig = { Host: "", Hostname: "", User: "", Port: 22 };
      showForm = false;
      // Refresh the table.
      loadConfigs();
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
      } else {
        alert("Failed to set default Docker context.");
      }
    } catch (err) {
      alert("Error setting default context: " + (err instanceof Error ? err.message : String(err)));
    }
  }

  onMount(() => {
    loadConfigs();
    loadDefaultContext();
  });
</script>

<div class="container">
  {#if error}
    <div class="notification is-danger">{error}</div>
  {:else if sshConfigs === null}
    <div class="notification is-info">Loading SSH connections...</div>
  {:else if sshConfigs.length === 0}
    <div class="notification is-warning">No SSH connections defined.</div>
  {:else}
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
            <td>{config.Host[0]}</td>
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
                  class="button is-link is-small"
                  onclick={() =>
                    openTerminal(
                      config.Host[0],
                      `DOCKER_CONTEXT=${config.Host[0]} d.rymcg.tech config`,
                      "false",
                    )}
                >
                  Reconfigure
                </button>
                <button
                  class="button is-light is-small"
                  onclick={() => openInfoModal(config.Host[0])}
                >
                  Info
                </button>
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
                {#if dockerStatuses[config.Host[0]] === "success"}
                  {#if defaultContext === config.Host[0]}
                    <span class="tag is-success is-light">🏁 Default</span>
                  {:else}
                    <button
                      class="button is-primary is-small"
                      onclick={() => setDefaultContext(config.Host[0])}
                      >
                      Set Default
                    </button>
                  {/if}
                {/if}
              {/if}
            </td>
          </tr>
        {/each}
      </tbody>
    </table>
  {/if}
  <div class="has-text-centered" style="margin-top: 1rem;">
    <button class="button is-link" onclick={openAddForm}>
      Add new context
    </button>
  </div>
</div>

<!-- Modal for adding a new SSH connection -->
<div class="modal {showForm ? 'is-active' : ''}">
  <div class="modal-background" onclick={() => (showForm = false)}></div>
  <div class="modal-card">
    <header class="modal-card-head">
      <p class="modal-card-title">Add SSH Docker Context</p>
      <button
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
        style="display: flex; align-items: flex-start; gap: 0.5rem; margin: 1em 0 1em 0;"
      >
        <pre
          onclick={selectPre}
          style="background: #371d1d; padding: 1em; border-radius: 4px; flex-grow: 1; font-weight: bold;">{clientKey}</pre>
        <button class="button is-small" onclick={copyClientKey}>
          {copyIcon}
        </button>
      </div>
      <!-- Group fields into two rows using Bulma columns -->
      <div class="columns">
        <div class="column">
          <div class="field">
            <label for="host" class="label">Host Alias</label>
            <div class="control">
              <input
                name="host"
                class="input"
                type="text"
                bind:value={newSSHConfig.Host}
                placeholder="Enter host alias"
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
                name="hostname"
                class="input"
                type="text"
                bind:value={newSSHConfig.Hostname}
                placeholder="Enter hostname or IP address"
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
                name="username"
                class="input"
                type="text"
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
                name="port"
                class="input"
                type="number"
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
          <button
            type="submit"
            class="button is-primary"
            onclick={addSSHConfig}
          >
            Add
          </button>
        </p>
      </div>
    </section>
  </div>
</div>

<!-- Overlay modal for InlineTerminal -->
{#if showTerminal}
  <div class="modal is-active">
    <div
      class="modal-background"
      onclick={() => {
        showTerminal = false;
        loadConfigs();
      }}
    ></div>
    <div class="modal-card" style="width: 80%; max-width: 80%;">
      <header class="modal-card-head">
        <p class="modal-card-title">Terminal for {activeTerminalHost}</p>
        <button
          class="delete"
          aria-label="close"
          onclick={() => {
            showTerminal = false;
            loadConfigs();
          }}
        ></button>
      </header>
      <section class="modal-card-body">
        <InlineTerminal
          restartable={terminalRestartable}
          command={terminalCommand}
          on:close={() => {
            showTerminal = false;
            loadConfigs();
          }}
        />
      </section>
    </div>
  </div>
{/if}

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
