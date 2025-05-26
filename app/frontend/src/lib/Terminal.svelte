<script>
  import { onMount, onDestroy, createEventDispatcher } from "svelte";
  import {
    terminalFontSize,
    terminalSessionState,
    eventSourceConnected,
  } from "$lib/stores";
  import TerminalView from "./TerminalView.svelte";

  const dispatch = createEventDispatcher();

  let {
    command = "/bin/bash",
    restartable = false,
    height = "300px",
    fontFamily = "monospace",
    lineHeight = 1.0,
    fullscreen = false,
  } = $props();

  /**
   * @type {any}
   */
  let fontSize = $state($terminalFontSize);

  let isRestartable = restartable === true;
  let terminalKey = $state(Date.now());
  let showRestart = $state(false);
  let hasExited = $state(false);
  let sessionName = $state("work");

  function handleKeydown(e) {
    if (e.key === "Escape" && hasExited) {
      dispatch("close");
    }
    if (e.key === "Enter" && hasExited && isRestartable) {
      restartTerminal();
    }
  }

  function restartTerminal() {
    terminalKey = Date.now();
    showRestart = false;
    hasExited = false;
  }

  async function fetchTmuxSessionState() {
    try {
      const res = await fetch(`/api/terminal/${sessionName}/window`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      terminalSessionState.set(data);
    } catch (err) {
      console.error("Failed to fetch terminal session state:", err);
    }
  }

  async function setActiveWindow(session, index) {
    try {
      const res = await fetch(
        `/api/terminal/${session}/window/active?index=${index}`,
        {
          method: "PUT",
        },
      );
      if (!res.ok) {
        console.error("Failed to set active window");
      }
    } catch (err) {
      console.error("Network error while setting active window:", err);
    }
  }

  async function createNewWindow(session) {
    const url = new URL(
      `/api/terminal/${session}/window`,
      window.location.origin,
    );
    url.searchParams.set("command", "bash");
    url.searchParams.set("active", "true");

    try {
      const res = await fetch(url.toString(), {
        method: "POST",
      });

      if (!res.ok) {
        console.error("Failed to create new window:", await res.text());
      }
    } catch (err) {
      console.error("Network error while creating new window:", err);
    }
  }

  async function deleteWindow(session, index) {
    const url = new URL(
      `/api/terminal/${session}/window/`,
      window.location.origin,
    );
    url.searchParams.set("window_index", index);

    try {
      const res = await fetch(url.toString(), {
        method: "DELETE",
      });

      if (!res.ok) {
        console.error("Failed to delete window:", await res.text());
      }
    } catch (err) {
      console.error("Network error while deleting window:", err);
    }
  }

  $effect(() => {
    const unsubscribe = terminalFontSize.subscribe((val) => {
      fontSize = val;
    });
    return unsubscribe;
  });

  onMount(async () => {
    window.addEventListener("keydown", handleKeydown);
    await fetchTmuxSessionState();
    setTimeout(async () => {
      await fetchTmuxSessionState();
    }, 2000);
  });

  onDestroy(() => {
    window.removeEventListener("keydown", handleKeydown);
  });
</script>

{#key terminalKey}
  <div
    class="is-flex is-flex-grow-1 is-flex-direction-column"
    class:inline-terminal-fullscreen={fullscreen === true}
    class:inline-terminal-wrapper={fullscreen != true}
  >
    {#if showRestart}
      <div id="inline-restart-overlay">
        <button
          type="button"
          class="button is-primary"
          onclick={restartTerminal}
        >
          Restart Terminal?
        </button>
        {#if !fullscreen}
          <p>Press ESC to close.</p>
        {/if}
      </div>
    {:else}
      <div
        id="window-list"
        class="mb-2"
        style="display: flex; flex-wrap: wrap; gap: 0.25rem;"
      >
        <button
          type="button"
          class="button is-small"
          onclick={(e) => {
            e.preventDefault();
            createNewWindow($terminalSessionState?.session);
          }}
          disabled={!$eventSourceConnected}
        >
          +
        </button>

        {#each $terminalSessionState?.windows ?? [] as window}
          <div class="field has-addons" style="align-items: stretch;">
            <p class="control">
              <button
                type="button"
                class="button is-small"
                class:is-info={window.index === $terminalSessionState?.active}
                onclick={() =>
                  setActiveWindow($terminalSessionState?.session, window.index)}
                disabled={!$eventSourceConnected}
              >
                {window.name}
              </button>
            </p>
            <p class="control">
              <button
                type="button"
                class="button is-small is-danger"
                title="Close window"
                onclick={() =>
                  deleteWindow($terminalSessionState?.session, window.index)}
                disabled={!$eventSourceConnected}
              >
                ✕
              </button>
            </p>
          </div>
        {/each}
      </div>
    {/if}
    <TerminalView
      {command}
      {fontSize}
      height={fullscreen ? "100%" : height}
      {fontFamily}
      {lineHeight}
      fullscreen={fullscreen === true}
      on:exit={() => {
        if (isRestartable) {
          showRestart = true;
        }
        hasExited = true;
        dispatch("exit");
      }}
    />
  </div>
{/key}

<style>
  .inline-terminal-wrapper {
    position: relative;
  }

  .inline-terminal-fullscreen {
    z-index: 5;
    background: black;
    height: 0px; /*flex still grows this */
  }

  #inline-restart-overlay {
    display: flex;
    flex-direction: column;
    background: rgba(20, 20, 20, 0.9);
    color: #fff;
    align-items: center;
    justify-content: center;
    z-index: 10;
  }

  #window-list {
    margin-left: 0.5em;
  }

  #window-list .button {
    height: 2em;
    padding-top: 0;
    padding-bottom: 0;
    display: flex;
    align-items: center;
  }

  #window-list .button.is-danger {
    padding-left: 0.4em;
    padding-right: 0.4em;
    min-width: auto;
  }

  #inline-restart-overlay p {
    margin-top: 1em;
  }
</style>
