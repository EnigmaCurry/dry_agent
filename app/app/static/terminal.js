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
        fitAddon.fit();
        sendResize();
        term.focus();
    };
    window.addEventListener("resize", () => {
        fitAddon.fit();
        sendResize();
    });
    function sendResize() {
        const { cols, rows } = term;
        socket.send(JSON.stringify({ type: "resize", cols, rows }));
    }
    term.onData(data => socket.send(data));
    socket.onmessage = event => {
        if (event.data === "__exit__") {
            term.writeln("");
            term.writeln("");
            term.writeln("🛑 Terminal Exited");
            showRestartOverlay();
            return;
        }
        term.write(event.data);
    };

    socket.onclose = () => {
        showRestartOverlay();
    };
});
function showRestartOverlay() {
  document.getElementById("restart-overlay").style.display = "flex";
}
