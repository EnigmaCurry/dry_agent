<script>
  import { onMount } from "svelte";
  import Terminal from "./Terminal.svelte";
  import { debounce } from '$lib/utils';
  
  /**
   * @typedef {Object} AppInfo
   * @property {string} name
   * @property {string} description
   */

  /** @type {AppInfo[]} */
  let apps = [];

  /** @type {boolean} */
  let loading = true;

  /** @type {string|null} */
  let error = null;

  /** @type {boolean} */
  let showTerminal = false;

  /** @type {string|null} */
  let terminalCommand = null;

  /** @type {string|null} */
  let configApp = null;

  let terminalHeight = 300;

  const debouncedSetTerminalHeight = debounce(() => {
	terminalHeight = Math.min(window.innerHeight * 0.75, 700);
  }, 300);
  onMount(() => {
	window.addEventListener('resize', debouncedSetTerminalHeight);
	return () => {
	  window.removeEventListener('resize', debouncedSetTerminalHeight);
	}
  });

  /**
   * Opens the terminal overlay for the given app and command.
   * @param {string} app
   * @param {string} command
   */
  function openTerminal(app, command) {
    console.log(command);
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
      <section class="modal-card-body is-clipped">
        <Terminal
          restartable={false}
          height={`${terminalHeight}px`}
          command={terminalCommand}
          on:close={() => {
            showTerminal = false;
          }}
        />
      </section>
    </div>
  </div>
{/if}
