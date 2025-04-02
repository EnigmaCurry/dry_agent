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

  /**
   * Tests an SSH connection given a host alias.
   * @param {string} host The host alias to test.
   */
  async function testConnection(host) {
    try {
      const response = await fetch(`/api/ssh_config/test/${host}`);
      if (response.ok) {
        statuses[host] = "success";
      } else {
        statuses[host] = "error";
      }
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
      // Remove the configuration from sshConfigs after deletion
      sshConfigs = sshConfigs.filter((config) => config.Host[0] !== host);
      // Optionally remove the status
      delete statuses[host];
    } catch (err) {
      alert(err instanceof Error ? err.message : String(err));
      console.error("Error deleting SSH configuration:", err);
    }
  }

  onMount(async () => {
    try {
      const response = await fetch("/api/ssh_config/");
      if (!response.ok) {
        throw new Error("Failed to fetch SSH configuration");
      }
      sshConfigs = await response.json();

      // Initialize each connection status to pending and then test it.
      sshConfigs.forEach((config) => {
        const hostAlias = config.Host[0];
        statuses[hostAlias] = "pending";
        testConnection(hostAlias);
      });
    } catch (err) {
      if (err instanceof Error) {
        error = err.message;
      } else {
        error = String(err);
      }
      console.error("Error fetching SSH configurations:", err);
    }
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
</div>
