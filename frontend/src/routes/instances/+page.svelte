<script>
  import AppInstances from "$lib/AppInstances.svelte";
  import { page } from "$app/state";

  const appName = $derived.by(() => page.url.searchParams.get("app"));
</script>

{#if appName != undefined}
  <AppInstances app={appName} />
{:else}
  <div class="notification is-warning">
    <strong>Error:</strong> App name is undefined.
  </div>
{/if}
