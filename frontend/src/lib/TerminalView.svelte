<script>
  import { onMount, onDestroy, createEventDispatcher } from "svelte";
  import { Terminal } from "@xterm/xterm";
  import { FitAddon } from "@xterm/addon-fit";
  import { get } from "svelte/store";
  import { tick } from "svelte";
  import {
    isPaneDragging,
    isLandscape,
    agentSizePercent,
    appSizePercent,
    userCurrentWorkingDirectory,
    userIsLoggedOut,
  } from "$lib/stores";
  import "@xterm/xterm/css/xterm.css";

  let {
    command = "/bin/bash",
    fontSize = 14,
    height = "300px",
    fontFamily = "monospace",
    lineHeight = 1.0,
    fullscreen = false,
  } = $props();

  const dispatch = createEventDispatcher();
  /**
   * @type {WebSocket}
   */
  let socket;
  /**
   * @type {Terminal}
   */
  let term;
  /**
   * @type {HTMLElement}
   */
  let terminalContainer;
  const fitAddon = new FitAddon();
  /**
   * @type {ResizeObserver}
   */
  let resizeObserver;

  let terminalStyle = $state("");
  $effect(() => {
    if (!fullscreen) {
      terminalStyle = "";
      return;
    }
    // subtract your agentSizePercent (with %!) from the viewport height
    terminalStyle = ``;
  });

  const fit = () => {
    fitAddon.fit();
    sendResize();
  };

  const beforeUnloadHandler = (
    /** @type {{ preventDefault: () => void; returnValue: string; }} */ event,
  ) => {
    if (!$userIsLoggedOut) {
      event.preventDefault();
      event.returnValue = "";
    }
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
      if ($appSizePercent != 0)  term.focus();
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
        } else if (message.type === "cwd") {
          userCurrentWorkingDirectory.set(message.path);
          console.log("user changed directory: ", $userCurrentWorkingDirectory);
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

    $effect(() => {
      if (term && fontSize) {
        term.options.fontSize = parseInt(fontSize);
        fit();
      }
    });
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

  const splitSizeSubscriber = appSizePercent.subscribe((split) => {
    if (split != 0) {
      term?.focus();
    }
  });
  onDestroy(splitSizeSubscriber);

  export function focus() {
    term?.focus();
  }

</script>

<div
  id="inline-terminal-container"
  bind:this={terminalContainer}
  class="is-flex is-flex-grow-1"
  style={terminalStyle}
  class:inline-terminal-default-style={!fullscreen}
></div>

<style>
  #inline-terminal-container {
    max-height: 95%;
  }
  .inline-terminal-default-style {
    width: 100%;
    border: 1px solid #ccc;
    margin: 1em 0;
    position: relative;
  }
</style>
