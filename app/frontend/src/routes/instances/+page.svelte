<script>
  import { page } from "$app/state";

  const appName = $derived.by(() => page.url.searchParams.get("app"));
  const appTitle = $derived(appName.replace(/\b\w/g, (c) => c.toUpperCase()));
</script>

{#if appName != undefined}
  <h1 class="title">{appTitle}</h1>
{:else}
  <div class="notification is-warning">
    <strong>Error:</strong> App name is undefined.
  </div>
{/if}
