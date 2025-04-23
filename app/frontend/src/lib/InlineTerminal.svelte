<script>
  import { onMount, onDestroy, createEventDispatcher } from "svelte";
  import TerminalView from "./TerminalView.svelte";

  const dispatch = createEventDispatcher();

  let {
    command = "/bin/bash",
    restartable = "false",
    fontSize = 14,
    height = "300px",
    fontFamily = "monospace",
    lineHeight = 1.0,
  } = $props();

  let isRestartable = $derived(restartable === "true" || restartable === true);

  let terminalKey = $state(Date.now());
  let showRestart = $state(false);
  let hasExited = $state(false);

  function handleKeydown(e) {
    if (e.key === "Escape" && hasExited) {
      dispatch("close");
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
  <div style="position: relative;">
    <TerminalView
      {command}
      {fontSize}
      {height}
      {fontFamily}
      {lineHeight}
      on:exit={() => {
        if (isRestartable) {
          showRestart = true;
        }
        hasExited = true;
        dispatch("exit");
      }}
    />
    {#if showRestart}
      <div
        id="inline-restart-overlay"
        style="display: flex; flex-direction: column; position: absolute; top: 0; left: 0; right: 0; bottom: 0; background: rgba(20,20,20,0.9); color: #fff; align-items: center; justify-content: center; z-index: 10;"
        >
        <button class="button is-primary" onclick={restartTerminal}>
          Restart Terminal?
        </button>
        <p style="margin-top: 1em;">
          Press ESC to close.
        </p>
      </div>
    {/if}
  </div>
{/key}
