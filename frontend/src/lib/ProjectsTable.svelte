<script>
  import { onMount } from "svelte";
  import { currentContext } from "$lib/stores";

  /**
   * @typedef {Object} AppInfo
   * @property {string} name
   * @property {string} description
   */

  let { show_all } = $props();

  let projects = $state([]);
  let loading = $state(true);
  let error = $state(null);
  let configApp = $state(null);
  /** @type {Record<string, number>} */
  let instanceCounts = $state({});

  const instanceEmojis = [
    "1️⃣",
    "2️⃣",
    "3️⃣",
    "4️⃣",
    "5️⃣",
    "6️⃣",
    "7️⃣",
    "8️⃣",
    "9️⃣",
    "🔟",
  ];

  async function fetchProjects() {
    const res = await fetch("/api/projects/available/");
    if (!res.ok) throw new Error(`Error fetching projects: ${res.statusText}`);
    const data = await res.json();
    projects = data.projects;
  }

  async function fetchInstanceCounts() {
    const res = await fetch("/api/instances/");
    if (!res.ok) throw new Error(`Error fetching instances: ${res.statusText}`);
    const data = await res.json();

    const context = $currentContext || "default";
    const instances = data[context] || {};

    const counts = {};
    for (const [appName, envFiles] of Object.entries(instances)) {
      counts[appName] = envFiles.length;
    }
    instanceCounts = counts;
    // console.log($state.snapshot(instanceCounts));
    // console.log(
    //   "instance counts",
    //   Object.keys($state.snapshot(instanceCounts)).length,
    // );
  }

  function renderInstanceEmojis(appName) {
    const count = instanceCounts[appName] || 0;
    if (count === 0) return "";
    if (count > 10) return "💯";
    return instanceEmojis[count - 1];
  }

  // ✅ Key the load to currentContext
  $effect(async () => {
    if (!$currentContext) return;

    loading = true;
    error = null;

    try {
      await Promise.all([fetchProjects(), fetchInstanceCounts()]);
    } catch (err) {
      error = /** @type {Error} */ (err).message;
    } finally {
      loading = false;
    }
  });
</script>

{#if loading}
  <div class="notification is-info">Loading projects…</div>
{:else if error}
  <div class="notification is-danger">❌ {error}</div>
{:else if show_all != true && Object.keys(instanceCounts).length === 0}
  <div class="notification is-warning">No projects configured.</div>
{:else}
  <div class="projects-table is-scrollable-y">
    <table class="table is-striped is-hoverable is-fullwidth">
      <thead>
        <tr>
          <th>Configure</th>
          <th>Instances</th>
          <th>README</th>
        </tr>
      </thead>
      <tbody>
        {#each projects.filter((app) => show_all || (instanceCounts[app.name] || 0) > 0) as app}
          <tr>
            <td>
              <a
                href="/instances/?app={app.name}"
                class="button is-dark is-fullwidth"
              >
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
  </div>
{/if}
