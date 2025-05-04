<script>
  import { onMount, onDestroy, createEventDispatcher } from "svelte";
  import { Terminal } from "@xterm/xterm";
  import { FitAddon } from "@xterm/addon-fit";
  import { get } from "svelte/store";
  import { tick } from "svelte";
  import "@xterm/xterm/css/xterm.css";
  import { isPaneDragging } from "$lib/stores";

  export let command = "/bin/bash";
  export let fontSize = 14;
  export let height = "300px";
  export let fontFamily = "monospace";
  export let lineHeight = 1.0;
  export let fullscreen = false;

  const dispatch = createEventDispatcher();
  let socket;
  let term;
  let terminalContainer;
  const fitAddon = new FitAddon();
  let resizeObserver;

  const fit = () => {
    fitAddon.fit();
    sendResize();
  };

  const beforeUnloadHandler = (event) => {
    event.preventDefault();
    event.returnValue = "";
  };

  function sendResize() {
    if (socket?.readyState === WebSocket.OPEN) {
      const { cols, rows } = term;
      socket.send(JSON.stringify({ type: "resize", cols, rows }));
    }
  }

  onMount(() => {
    term = new Terminal({
      fontSize: parseInt(fontSize),
      lineHeight: parseFloat(lineHeight),
      fontFamily,
    });

    term.loadAddon(fitAddon);
    term.open(terminalContainer);

    terminalContainer.addEventListener("click", () => term.focus());

    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    socket = new WebSocket(
      `${protocol}://${window.location.host}/api/terminal/ws`,
    );

    socket.onopen = () => {
      socket.send(JSON.stringify({ command }));
      fitAddon.fit();
      sendResize();
      term.focus();
      window.addEventListener("beforeunload", beforeUnloadHandler);
    };

    socket.onerror = (error) => {
      console.error("WebSocket error:", error);
    };

    term.onData((data) => {
      socket.send(JSON.stringify({ type: "input", data }));
    });

    socket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        if (message.type === "data") {
          term.write(message.data);
        } else if (message.type === "exit") {
          term.writeln("\n🛑 Process Finished.");
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
      window.removeEventListener("beforeunload", beforeUnloadHandler);
    };

    resizeObserver = new ResizeObserver(() => {
      if (get(isPaneDragging)) return;
      fit();
    });
    resizeObserver.observe(terminalContainer);
  });

  const paneDragUnsubscribe = isPaneDragging.subscribe((dragging) => {
    if (!dragging) {
      fit();
    }
  });

  onDestroy(() => {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.close(1000, "Component unmounted");
    }
    resizeObserver?.disconnect();
    window.removeEventListener("beforeunload", beforeUnloadHandler);
    term?.dispose();
  });
</script>

<div
  id="inline-terminal-container"
  bind:this={terminalContainer}
  class:inline-terminal-default-style={!fullscreen}
  style={fullscreen === true ? "height: calc(100vh - 4rem);" : ""}
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
