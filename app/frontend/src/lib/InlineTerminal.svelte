<script>
  import { onMount, onDestroy, createEventDispatcher } from "svelte";
  import TerminalView from "./TerminalView.svelte";

  const dispatch = createEventDispatcher();

  export let command = "/bin/bash";
  export let restartable = "false";
  export let fontSize = 14;
  export let height = "300px";
  export let fontFamily = "monospace";
  export let lineHeight = 1.0;
  export let fullscreen = false;

  let isRestartable = restartable === "true" || restartable === true;
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

  onMount(() => {
    window.addEventListener("keydown", handleKeydown);
  });

  onDestroy(() => {
    window.removeEventListener("keydown", handleKeydown);
  });
</script>

{#key terminalKey}
  <div class={fullscreen ? 'inline-terminal-fullscreen' : 'inline-terminal-wrapper'}>
    <TerminalView
      {command}
      {fontSize}
      height={fullscreen ? "100%" : height}
      {fontFamily}
      {lineHeight}
      {fullscreen}
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
        <p>Press ESC to close.</p>
      </div>
    {/if}
  </div>
{/key}

<style>
  .inline-terminal-wrapper {
    position: relative;
  }

  .inline-terminal-fullscreen {
    position: fixed;
    top: 4rem;
    bottom: 0;
    left: 0;
    right: 0;
    z-index: 5;
    background: black;
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
