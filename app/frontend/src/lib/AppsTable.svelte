<script>
  import { onMount } from "svelte";
  import ModalTerminal from "./ModalTerminal.svelte";

  /**
   * @typedef {Object} AppInfo
   * @property {string} name
   * @property {string} description
   */

  /** @type {AppInfo[]} */
  let apps = $state([]);

  let loading = $state(true);
  let error = $state(null);

  let showTerminal = $state(false);
  let terminalCommand = $state(null);
  let configApp = $state(null);

  /**
   * Opens the terminal overlay for the given app and command.
   * @param {string} app
   * @param {string} command
   */
  function openTerminal(app, command) {
    configApp = app;
    terminalCommand = command;
    showTerminal = true;
  }

  onMount(async () => {
    try {
      const res = await fetch("/api/apps/available");
      if (!res.ok) throw new Error(`Error fetching apps: ${res.statusText}`);
      const data = await res.json();
      apps = data.apps;
    } catch (err) {
      error = /** @type {Error} */(err).message;
    } finally {
      loading = false;
    }
  });
</script>

{#if loading}
  <div class="notification is-info">Loading apps…</div>
{:else if error}
  <div class="notification is-danger">❌ {error}</div>
{:else}
  <table class="table is-striped is-hoverable is-fullwidth">
    <thead>
      <tr>
        <th>Configure</th>
        <th>README</th>
      </tr>
    </thead>
    <tbody>
      {#each apps as app}
        <tr>
          <td>
            <button
              class="button is-white is-small"
              on:click={() => openTerminal(app.name, `d.rymcg.tech make ${app.name} config`)}
            >
              {app.name}
            </button>
          </td>
          <td>
            <a
              href={`https://github.com/EnigmaCurry/d.rymcg.tech/blob/master/${app.name}/README.md`}
              target="_blank"
              rel="noopener noreferrer"
              class="is-link"
            >
              {app.description}
            </a>
          </td>
        </tr>
      {/each}
    </tbody>
  </table>
{/if}

<ModalTerminal
  command="bash -c 'seq 1000 && whoami'"
  appName={configApp}
  visible={showTerminal}
  on:close={() => showTerminal = false}
/>
