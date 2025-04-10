<script>
  import { onMount, createEventDispatcher } from "svelte";
  import { Terminal } from "@xterm/xterm";
  import { FitAddon } from "@xterm/addon-fit";
  import "@xterm/xterm/css/xterm.css";

  export let command = "/bin/bash";
  export let fontSize = 14;
  export let height = "300px";
  export let fontFamily = "monospace";
  export let lineHeight = 1.0;

  const dispatch = createEventDispatcher();
  let terminalContainer;

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

    terminalContainer.addEventListener("click", () => term.focus());

    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const socket = new WebSocket(
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
        if (message.type === "data") {
          term.write(message.data);
        } else if (message.type === "exit") {
          term.writeln("");
          term.writeln("🛑 Process Finished.");
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
    };
  });
</script>

<div
  id="inline-terminal-container"
  bind:this={terminalContainer}
  style="width: 100%; height: {height}; border: 1px solid #ccc; margin: 1em 0; position: relative;"
></div>
