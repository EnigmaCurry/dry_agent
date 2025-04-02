<script>
  import { onMount } from "svelte";

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
   * @type {{ [key: string]: "pending" | "success" | "error" }}
   */
  let statuses = {};

  // Variables for the "Add SSH Connection" modal and form.
  let showForm = false;
  /** @type {string|null} */
  let formError = null;
  let newSSHConfig = {
    Host: "",
    Hostname: "",
    User: "",
    Port: 22,
  };

  /**
   * Fetches the list of SSH configurations and initializes their statuses.
   */
  async function loadConfigs() {
    try {
      const response = await fetch("/api/ssh_config/");
      if (!response.ok) {
        throw new Error("Failed to fetch SSH configuration");
      }
      sshConfigs = await response.json();
      // Reset statuses
      statuses = {};
      if (sshConfigs) {
        sshConfigs.forEach((config) => {
          const hostAlias = config.Host[0];
          statuses[hostAlias] = "pending";
          testConnection(hostAlias);
        });
      }
    } catch (err) {
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
    // Reassign to trigger reactivity.
    statuses = { ...statuses };
  }

  /**
   * Deletes an SSH connection given a host alias.
   * @param {string} host The host alias to delete.
   */
  async function deleteSSHConfig(host) {
    try {
      const response = await fetch(`/api/ssh_config/${host}`, {
        method: "DELETE",
      });
      if (!response.ok) {
        throw new Error("Failed to delete SSH configuration");
      }
      if (sshConfigs) {
        sshConfigs = sshConfigs.filter((config) => config.Host[0] !== host);
      }
      delete statuses[host];
    } catch (err) {
      alert(err instanceof Error ? err.message : String(err));
      console.error("Error deleting SSH configuration:", err);
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
        // Show error detail from response, or default error message.
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

  onMount(() => {
    loadConfigs();
  });
</script>

<div class="container">
  {#if error}
    <div class="notification is-danger">
      {error}
    </div>
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
                <span
                  role="img"
                  aria-label="Connection successful"
                  title="Connection successful">✅</span
                >
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
                on:click={() => deleteSSHConfig(config.Host[0])}
              >
                Delete
              </button>
            </td>
          </tr>
        {/each}
      </tbody>
    </table>
  {/if}
  <div class="has-text-centered" style="margin-top: 1rem;">
    <button class="button is-link" on:click={() => (showForm = true)}>
      Add new context
    </button>
  </div>
</div>

<!-- Modal for adding a new SSH connection -->
<div class="modal {showForm ? 'is-active' : ''}">
  <div class="modal-background" on:click={() => (showForm = false)}></div>
  <div class="modal-card">
    <header class="modal-card-head">
      <p class="modal-card-title">Add SSH Connection</p>
      <button
        class="delete"
        aria-label="close"
        on:click={() => (showForm = false)}
      ></button>
    </header>
    <section class="modal-card-body">
      <form on:submit|preventDefault={addSSHConfig}>
        <div class="field">
          <label for="host" class="label">Host</label>
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
        {#if formError}
          <p class="help is-danger">{formError}</p>
        {/if}
        <div class="field is-grouped is-grouped-right">
          <p class="control">
            <button
              type="button"
              class="button"
              on:click={() => (showForm = false)}
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
