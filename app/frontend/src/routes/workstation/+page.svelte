<script>
  import Terminal from "../../lib/Terminal.svelte";
</script>

<svelte:head>
  <title>dry_agent - Terminal</title>
</svelte:head>

<Terminal fullscreen=true fontSize=20 restartable=true command="tmux new-session -A -s work"/>
