<script>
  import { onMount } from "svelte";
  import InlineTerminal from "$lib/InlineTerminal.svelte";

  /** @type {import('./$types').PageProps} */
  let { data } = $props();

  /** @type {string|null} */
  let terminalCommand = $state("");
  let terminalRestartable = $state("false");

  let instanceId = 0;
  let showTerminal = $state(false);

  /**
   * Opens the terminal overlay for the given host and command.
   * @param {string} command
   * @param {string} restartable
   */
  function openTerminal(command, restartable) {
    terminalCommand = command;
    terminalRestartable = restartable;
    showTerminal = true;
  }

  onMount(() => {
    if (data.status == 404) {
      openTerminal("d.rymcg.tech config", "true");
    }
  });

</script>

<svelte:head>
  <title>dry_agent - Config</title>
</svelte:head>

<h1 class="title">Context Config</h1>

{#if data.status === 404}
  <p>
    Config file not found for context: <code>{data.context}</code>.
  </p>
{:else}
  <p>Config file found at: <code>{data.config_path}</code></p>
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
        <p class="modal-card-title">{terminalCommand}</p>
        <button
          class="delete"
          aria-label="close"
          onclick={() => {
            showTerminal = false;
          }}
        ></button>
      </header>
      <section class="modal-card-body">
        <InlineTerminal
          restartable={terminalRestartable}
          command={terminalCommand}
          on:close={() => {
            showTerminal = false;
          }}
        />
      </section>
    </div>
  </div>
{/if}
