<script lang="ts">
  import { onMount } from "svelte";
  import Terminal from "./Terminal.svelte";

  interface AppInfo {
    name: string;
    description: string;
  }

  let apps: AppInfo[] = [];
  let loading = true;
  let error: string | null = null;
  let showTerminal = false;
  let terminalCommand = null;
  let configApp = null;
  
  /**
   * Opens the terminal overlay for the given host and command.
   * @param {string} host
   * @param {string} command
   */
  function openTerminal(app, command) {
    console.log(command);
    configApp = app;
    terminalCommand = command;;
    showTerminal = true;
  }

  onMount(async () => {
    try {
      const res = await fetch("/api/apps/available");
      if (!res.ok) throw new Error(`Error fetching apps: ${res.statusText}`);
      const data = await res.json();
      apps = data.apps;
    } catch (err) {
      error = err.message;
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
              class="button is-info is-small"
              onclick={() =>
              openTerminal(
              app.name,
              `d.rymcg.tech make ${app.name} config`
              )}
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

<!-- Overlay modal for InlineTerminal -->
{#if showTerminal}
  <div class="modal is-active">
    <div
      class="modal-background"
      onclick={() => {
        showTerminal = false;
      }}
    ></div>
    <div class="modal-card" style="width: 80%; max-width: 80%;">
      <header class="modal-card-head">
        <p class="modal-card-title">d make {configApp} config</p>
        <button
          class="delete"
          aria-label="close"
          onclick={() => {
            showTerminal = false;
          }}
        ></button>
      </header>
      <section class="modal-card-body">
        <Terminal
          restartable={false}
          command={terminalCommand}
          on:close={() => {
            showTerminal = false;
          }}
        />
      </section>
    </div>
  </div>
{/if}
