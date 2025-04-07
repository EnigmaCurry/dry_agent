<script lang="ts">
  import { onMount } from "svelte";

  interface AppInfo {
    name: string;
    description: string;
  }

  let apps: AppInfo[] = [];
  let loading = true;
  let error: string | null = null;

  onMount(async () => {
    try {
      const res = await fetch("/api/apps/available");
      if (!res.ok) throw new Error(`Error fetching apps: ${res.statusText}`);
      const data = await res.json();
      apps = data.apps;
    } catch (err) {
      error = err.message;
    } finally {
      loading = false;
    }
  });
</script>

{#if loading}
  <div class="notification is-info">Loading apps…</div>
{:else if error}
  <div class="notification is-danger">❌ {error}</div>
{:else}
  <table class="table is-striped is-hoverable is-fullwidth">
    <thead>
      <tr>
        <th>Configure</th>
        <th>README</th>
      </tr>
    </thead>
    <tbody>
      {#each apps as app}
        <tr>
          <td><strong>{app.name}</strong></td>
          <td>
            <a
              href={`https://github.com/EnigmaCurry/d.rymcg.tech/blob/master/${app.name}/README.md`}
              target="_blank"
              rel="noopener noreferrer"
              class="is-link"
            >
              {app.description}
            </a>
          </td>
        </tr>
      {/each}
    </tbody>
  </table>
{/if}
