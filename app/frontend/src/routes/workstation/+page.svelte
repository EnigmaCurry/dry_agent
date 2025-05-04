<script>
  import Terminal from "../../lib/Terminal.svelte";
</script>

<svelte:head>
  <title>dry_agent - Terminal</title>
</svelte:head>

<Terminal
  fullscreen={false}
  fontSize={20}
  restartable="true"
  command="cd ~/git/vendor/enigmacurry/d.rymcg.tech && tmux new-session -A -s work"
/>
