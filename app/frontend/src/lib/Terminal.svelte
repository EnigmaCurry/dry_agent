<script>
  import { onMount } from "svelte";
  import { Terminal } from "@xterm/xterm";
  import { FitAddon } from "@xterm/addon-fit";
  import '@xterm/xterm/css/xterm.css';

  let terminalContainer;
  let showRestart = false;

  onMount(() => {
    const term = new Terminal({
      fontSize: 20,
      fontFamily: "monospace",
      lineHeight: 1.0,
      letterSpacing: 0,
    });
    const fitAddon = new FitAddon();
    term.loadAddon(fitAddon);
    term.open(terminalContainer);
    fitAddon.fit();
    term.focus();

    // Refocus terminal on container click
    terminalContainer.addEventListener("click", () => {
      term.focus();
    });

    // Re-fit terminal on window resize
    window.addEventListener("resize", () => {
      fitAddon.fit();
    });

    // Establish the WebSocket connection
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const socket = new WebSocket(
      `${protocol}://${window.location.host}/api/terminal/ws`,
    );

    socket.onopen = () => {
      console.log("WebSocket connected; sending initial command.");
      socket.send(JSON.stringify({ command: "cd ~/git/vendor/enigmacurry/d.rymcg.tech && /bin/bash" }));
      fitAddon.fit();
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

    // Send input data to the WebSocket
    term.onData((data) => {
      socket.send(JSON.stringify({ type: "input", data }));
    });

    // Handle incoming WebSocket messages
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
            showRestartOverlay();
            break;
          default:
            console.warn("Unhandled message type:", message);
        }
      } catch (err) {
        console.error("Error parsing message:", err);
      }
    };

    // Show restart overlay on socket close
    socket.onclose = () => {
      showRestartOverlay();
    };

    function showRestartOverlay() {
      showRestart = true;
    }
  });
</script>

<!-- Terminal container -->
<div id="terminal-container" bind:this={terminalContainer}></div>

<!-- Conditional Restart Overlay -->
{#if showRestart}
  <div id="restart-overlay">
    <button
      class="button is-large is-danger"
      on:click={() => location.reload()}
    >
      🔁 Restart Terminal
    </button>
  </div>
{/if}

<!-- Unused dimmer (kept for compatibility) -->
<div id="terminal-dimmer" style="display: none;"></div>

<style>
  html,
  body {
    overflow: hidden !important;
  }
  .section {
    padding: 1rem 0 0 0 !important;
  }
  .container {
    position: relative;
    max-width: 100% !important;
  }
  #terminal-container {
    background-color: #000;
    position: fixed;
    top: 4rem;
    bottom: 0;
    left: 0;
    right: 0;
    overflow: hidden;
  }
  /* Restart overlay positioned over the terminal */
  #restart-overlay {
    position: absolute;
    top: 4rem;
    left: 0;
    right: 0;
    bottom: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(20, 20, 20, 0.9);
    z-index: 10;
  }
</style>
