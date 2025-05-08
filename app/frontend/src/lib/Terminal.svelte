<script>
  import { onMount, onDestroy, createEventDispatcher } from "svelte";
  import { terminalFontSize } from "$lib/stores";
  import TerminalView from "./TerminalView.svelte";

  const dispatch = createEventDispatcher();

  let {
    command = "/bin/bash",
    restartable = false,
    height = "300px",
    fontFamily = "monospace",
    lineHeight = 1.0,
    fullscreen = false
  } = $props();

  /**
     * @type {any}
     */
  let fontSize = $state($terminalFontSize);

  let isRestartable = restartable === true;
  let terminalKey = Date.now();
  let showRestart = false;
  let hasExited = false;

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

  $effect(() => {
    const unsubscribe = terminalFontSize.subscribe((val) => {
      fontSize = val;
    });
    return unsubscribe;
  });

  onMount(() => {
    window.addEventListener("keydown", handleKeydown);
  });

  onDestroy(() => {
    window.removeEventListener("keydown", handleKeydown);
  });
</script>

{#key terminalKey}
  <div
    class="is-flex is-flex-grow-1"
    class:inline-terminal-fullscreen={fullscreen === true}
    class:inline-terminal-wrapper={fullscreen != true}
  >
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
    {#if showRestart}
      <div id="inline-restart-overlay">
        <button class="button is-primary" on:click={restartTerminal}>
          Restart Terminal?
        </button>
        {#if !fullscreen}
          <p>Press ESC to close.</p>
        {/if}
      </div>
    {/if}
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
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(20, 20, 20, 0.9);
    color: #fff;
    align-items: center;
    justify-content: center;
    z-index: 10;
  }

  #inline-restart-overlay p {
    margin-top: 1em;
  }
</style>
