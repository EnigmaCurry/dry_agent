<script>
  import TerminalView from "./TerminalView.svelte";

  let {
    command = "/bin/bash",
    restartable = "false",
    fontSize = 14,
    height = "300px",
    fontFamily = "monospace",
    lineHeight = 1.0,
  } = $props();

  // Convert restartable to a boolean.
  let isRestartable = $derived(restartable === "true" || restartable === true);

  let terminalKey = $state(Date.now());
  let showRestart = $state(false);

  function restartTerminal() {
    terminalKey = Date.now();
    showRestart = false;
  }
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
        console.log("Received exit event in InlineTerminal.");
        if (isRestartable) {
          showRestart = true;
          console.log("here");
        }
      }}
    />
    {#if showRestart}
      <div
        id="inline-restart-overlay"
        style="display: flex; position: absolute; top: 0; left: 0; right: 0; bottom: 0; background: rgba(20,20,20,0.9); color: #fff; align-items: center; justify-content: center; z-index: 10;"
      >
        <button class="button" onclick={restartTerminal}>
          Restart Terminal
        </button>
      </div>
    {/if}
  </div>
{/key}
