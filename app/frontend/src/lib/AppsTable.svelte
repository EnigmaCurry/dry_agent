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
        <th>Name</th>
        <th>Description</th>
        <th>Actions</th>
      </tr>
    </thead>
    <tbody>
      {#each apps as app}
        <tr>
          <td><strong>{app.name}</strong></td>
          <td>{app.description}</td>
          <td>
            <!-- Future actions go here -->
            <div class="buttons">
              <a
                href={`https://github.com/EnigmaCurry/d.rymcg.tech/blob/master/${app.name}/README.md`}
                target="_blank"
                rel="noopener noreferrer"
                class="button is-link is-small"
              >
                README
              </a>
              <button class="button is-small is-primary is-light" disabled
                >Action 2</button
              >
            </div>
          </td>
        </tr>
      {/each}
    </tbody>
  </table>
{/if}
