<script>
  import DockerContext from "$lib/DockerContext.svelte";
  import { currentContext } from "$lib/stores";

  const contextKey = $derived($currentContext);
</script>

<svelte:head>
  <title>dry_agent - Context</title>
</svelte:head>

<h1 class="title">SSH Config and Docker Contexts</h1>
{#key contextKey}
  <DockerContext />
{/key}
