<script>
  import { onMount, onDestroy, createEventDispatcher } from "svelte";
  import { Terminal } from "@xterm/xterm";
  import { FitAddon } from "@xterm/addon-fit";
  import "@xterm/xterm/css/xterm.css";
  import { debounce } from '$lib/utils';

  export let command = "/bin/bash";
  export let fontSize = 14;
  export let height = "300px";
  export let fontFamily = "monospace";
  export let lineHeight = 1.0;
  export let fullscreen = false;

  const dispatch = createEventDispatcher();
  let socket;
  let resizeHandler;
  let term;
  let terminalContainer;

  const debouncedFit = debounce(() => {
	resizeHandler();
  }, 300);

  onMount(() => {
    console.log("fontSize", fontSize);
    term = new Terminal({
      fontSize: parseInt(fontSize),
      lineHeight: parseFloat(lineHeight),
      fontFamily,
    });
    const fitAddon = new FitAddon();
    term.loadAddon(fitAddon);
    term.open(terminalContainer);
    fitAddon.fit();
    term.focus();

    terminalContainer.addEventListener("click", () => term.focus());

    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    socket = new WebSocket(
      `${protocol}://${window.location.host}/api/terminal/ws`,
    );

    socket.onopen = () => {
      socket.send(JSON.stringify({ command }));
      sendResize();
      term.focus();
    };

    socket.onerror = (error) => {
      console.error("WebSocket error:", error);
    };

    resizeHandler = () => {
      fitAddon.fit();
      sendResize();
    };

    window.addEventListener("resize", resizeHandler);

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
        if (message.type === "data") {
          term.write(message.data);
        } else if (message.type === "exit") {
          term.writeln("");
          term.writeln("🛑 Process Finished.");
          term.blur();
          dispatch("exit");
        } else {
          console.warn("Unhandled message type:", message);
        }
      } catch (err) {
        console.error("Error parsing message:", err);
      }
    };

    socket.onclose = () => {
      dispatch("exit");
      term.blur();
    };

	window.addEventListener('resize', debouncedFit);
  });

  onDestroy(() => {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.close(1000, "Component unmounted");
    }
    window.removeEventListener("resize", resizeHandler);
	window.removeEventListener('resize', debouncedFit);
    term.dispose();
  });
</script>

<div
  id="inline-terminal-container"
  bind:this={terminalContainer}
  class:inline-terminal-default-style={!fullscreen}
  style={fullscreen ? "width: 100%; height: 100%;" : `--terminal-height: ${height}`}
></div>

<style>
  .inline-terminal-default-style {
    width: 100%;
    height: var(--terminal-height, 300px); /* Fallback for inline use */
    border: 1px solid #ccc;
    margin: 1em 0;
    position: relative;
  }
</style>
