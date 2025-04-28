<script>
  import { onMount } from "svelte";
  import { currentContext } from "$lib/stores";
  import { get } from "svelte/store";

  let { context } = $props();

  /**
   * @typedef {Object} AppInfo
   * @property {string} name
   * @property {string} description
   */

  /** @type {AppInfo[]} */
  let apps = $state([]);

  let loading = $state(true);
  let error = $state(null);

  let configApp = $state(null);

  /** @type {Record<string, number>} */
  let instanceCounts = $state({});

  const instanceEmojis = [
    "🙂", // 2nd instance
    "😎", // 3rd instance
    "🚀", // 4th instance
    "🧙‍♂️", // 5th instance
  ];

  $effect(() => {
    if (context) {
      fetchApps();
      fetchInstanceCounts();
    }
  });

  async function fetchApps() {
    const res = await fetch("/api/apps/available");
    if (!res.ok) throw new Error(`Error fetching apps: ${res.statusText}`);
    const data = await res.json();
    apps = data.apps;
  }

  async function fetchInstanceCounts() {
    const res = await fetch("/api/instances/");
    if (!res.ok) throw new Error(`Error fetching instances: ${res.statusText}`);
    const data = await res.json();

    const context = get(currentContext) || "default";
    const instances = data[context] || {};

    /** @type {Record<string, number>} */
    const counts = {};
    for (const [appName, envFiles] of Object.entries(instances)) {
      counts[appName] = envFiles.length;
    }
    instanceCounts = counts;
  }

  function renderInstanceEmojis(appName) {
    const count = instanceCounts[appName] || 0;
    if (count === 0) return "";

    if (count > 5) {
      return "✅ 💯";
    }

    // Always start with ✅
    const emojis = ["✅"];

    // Add up to (count-1) more emojis from the list
    emojis.push(...instanceEmojis.slice(0, count - 1));

    return emojis.join(" ");
  }

  onMount(async () => {
    try {
      await Promise.all([fetchApps(), fetchInstanceCounts()]);
    } catch (err) {
      error = /** @type {Error} */ (err).message;
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
        <th>Instances</th>
        <th>README</th>
      </tr>
    </thead>
    <tbody>
      {#each apps as app}
        <tr>
          <td>
            <a href="/instances/?app={app.name}" class="button is-dark">
              {app.name}
            </a>
          </td>
          <td>
            <span
              title="{app.name} has {instanceCounts[app.name] ||
                0} configured instances"
              style="font-size: 1.5em;"
              class="noselect">{@html renderInstanceEmojis(app.name)}</span
            >
          </td>
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
