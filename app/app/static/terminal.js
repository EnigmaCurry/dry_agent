document.addEventListener("DOMContentLoaded", () => {
    const term = new Terminal({
        fontSize: 20,
        fontFamily: 'monospace',
        lineHeight: 1.0,
        letterSpacing: 0,
    });
    const fitAddon = new FitAddon.FitAddon();
    term.loadAddon(fitAddon);
    term.open(document.getElementById("terminal-container"));
    fitAddon.fit();
    term.focus();
    document.getElementById("terminal-container").addEventListener("click", () => {
        term.focus();
    });
    window.addEventListener("resize", () => fitAddon.fit());

    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const socket = new WebSocket(`${protocol}://${window.location.host}/app/terminal/ws`);

    socket.onopen = () => {
        console.log("WebSocket connected; sending initial command.");
        // Send the initial command.
        socket.send(JSON.stringify({ command: "/bin/bash" }));
        fitAddon.fit();
        sendResize();
        term.focus();
    };

    // Attach error handler if needed.
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

    // When user types, wrap it in an "input" JSON message.
    term.onData(data => {
        socket.send(JSON.stringify({ type: "input", data }));
    });

    socket.onmessage = event => {
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

    socket.onclose = () => {
        showRestartOverlay();
    };
});

function showRestartOverlay() {
    document.getElementById("restart-overlay").style.display = "flex";
}
