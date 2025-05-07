<script>
  import Terminal from "../../lib/Terminal.svelte";
</script>

<svelte:head>
  <title>dry_agent - Terminal</title>
</svelte:head>

<Terminal
  restartable={true}
  fullscreen={true}
  fontSize={20}
  autofocus={true}
  command="cd ~/git/vendor/enigmacurry/d.rymcg.tech && tmux new-session -A -s work"
/>
