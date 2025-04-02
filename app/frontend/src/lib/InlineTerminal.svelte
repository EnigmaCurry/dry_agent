<script>
  import { onMount } from "svelte";
  import { Terminal } from "@xterm/xterm";
  import { FitAddon } from "@xterm/addon-fit";
  import "@xterm/xterm/css/xterm.css";

  let {
    command = "/bin/bash",
    restartable = false,
    fontSize = 14,
    height = "300px",
    fontFamily = "monospace",
    lineHeight = 1.0,
  } = $props();

  let terminalContainer;
  let showRestart = false;
  onMount(() => {
    const term = new Terminal({
      fontSize: parseInt(fontSize),
      lineHeight: parseFloat(lineHeight),
      fontFamily,
    });
    const fitAddon = new FitAddon();
    term.loadAddon(fitAddon);
    term.open(terminalContainer);
    fitAddon.fit();
    term.focus();

    // Refocus the terminal on container click
    terminalContainer.addEventListener("click", () => term.focus());

    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const socket = new WebSocket(
      `${protocol}://${window.location.host}/app/terminal/ws`,
    );

    socket.onopen = () => {
      console.log("Inline terminal WebSocket connected.");
      socket.send(JSON.stringify({ command }));
      sendResize();
      term.focus();
    };

    socket.onerror = (error) => {
      console.error("WebSocket error:", error);
    };

    window.addEventListener("resize", () => {
      fitAddon.fit();
      sendResize();
    });

    function sendResize() {
      const { cols, rows } = term;
      socket.send(JSON.stringify({ type: "resize", cols, rows }));
    }

    term.onData((data) => {
      socket.send(JSON.stringify({ type: "input", data }));
    });

    socket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        switch (message.type) {
          case "data":
            term.write(message.data);
            break;
          case "exit":
            term.writeln("");
            term.writeln("🛑 Process Finished.");
            showInlineRestartOverlay();
            break;
          default:
            console.warn("Unhandled message type:", message);
        }
      } catch (err) {
        console.error("Error parsing message:", err);
      }
    };

    socket.onclose = () => {
      showInlineRestartOverlay();
    };

    function showInlineRestartOverlay() {
      if (restartable === true) {
        showRestart = true;
      }
    }
  });
</script>

<!-- Terminal container -->
<div
  id="inline-terminal-container"
  bind:this={terminalContainer}
  style="width: 100%; height: {height}; border: 1px solid #ccc; margin: 1em 0;"
></div>

<!-- Conditional restart overlay -->
{#if showRestart}
  <div
    id="inline-restart-overlay"
    style="display: flex; position: absolute; top: 0; left: 0; right: 0; bottom: 0; background: rgba(20,20,20,0.9); color: #fff; align-items: center; justify-content: center; z-index: 10;"
  >
    <button class="button" on:click={() => location.reload()}>
      Restart Terminal
    </button>
  </div>
{/if}

<style>
  /* You can extract any inline styles here or adjust as needed */
</style>
