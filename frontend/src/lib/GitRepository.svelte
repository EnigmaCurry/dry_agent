<script lang="ts">
  import { onMount } from "svelte";
  import { writable } from "svelte/store";

  const branches = writable<string[]>([]);
  const current = writable<string>("");
  const loading = writable<boolean>(false);
  const error = writable<string | null>(null);
  const successMessage = writable<string | null>(null);
  const statusMessage = writable<string | null>(null);
  const behind = writable<boolean>(false);
  const gitOutput = writable<string | null>(null);
  const localHead = writable<string | null>(null);

  onMount(() => {
    loadAll();
  });

  async function loadAll() {
    error.set(null);
    successMessage.set(null);
    statusMessage.set(null);
    behind.set(false);
    await Promise.all([refreshBranches(), fetchStatus()]);
  }

  async function refreshBranches() {
    try {
      const res = await fetch("/api/repo/branches");
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to load branches");
      branches.set(data.branches);
      current.set(data.current);
    } catch (e) {
      error.set(e.message);
    }
  }

  async function fetchStatus() {
    try {
      const res = await fetch("/api/repo/fetch-status", { method: "POST" });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to fetch status");
      statusMessage.set(data.message);
      behind.set(data.message?.includes("behind"));
      localHead.set(data.local_head || null);
    } catch (e) {
      error.set(e.message);
    }
  }

  async function checkoutBranch(branch: string) {
    loading.set(true);
    error.set(null);
    successMessage.set(null);
    gitOutput.set(null);

    const formData = new FormData();
    formData.append("branch", branch);

    try {
      const res = await fetch("/api/repo/checkout", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Checkout failed");

      successMessage.set(`✅ Switched to branch "${branch}"`);
      await loadAll();
    } catch (e) {
      error.set(e.message);
    } finally {
      loading.set(false);
    }
  }

  async function pullBranch() {
    loading.set(true);
    error.set(null);
    successMessage.set(null);
    gitOutput.set(null);

    try {
      const res = await fetch("/api/repo/pull", { method: "POST" });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Pull failed");

      successMessage.set(`✅ Pulled latest changes for branch "${$current}"`);
      gitOutput.set(data.output || "(no output)");
      await loadAll();
    } catch (e) {
      error.set(e.message);
    } finally {
      loading.set(false);
    }
  }
</script>

<div class="space-y-2 m-4">
  {#if $branches.length > 0}
    <label for="branch-select" class="block font-semibold">Switch Branch</label>
    <select
      id="branch-select"
      class="border rounded px-2 py-1"
      bind:value={$current}
      on:change={(e) => checkoutBranch(e.target.value)}
      disabled={$loading}
    >
      {#each $branches as branch}
        <option value={branch}>{branch}</option>
      {/each}
    </select>
  {/if}
  <hr />

  {#if $statusMessage}
    <p class="text-sm mt-2 text-gray-700">📡 {$statusMessage}</p>
  {/if}

  {#if $localHead}
    <p class="is-size-7 has-text-grey ml-1">
      HEAD:
      <a
        href={"https://github.com/EnigmaCurry/d.rymcg.tech/commit/" +
          $localHead}
        target="_blank"
        rel="noopener noreferrer"
        class="has-text-link has-text-weight-semibold"
        title={$localHead}
      >
        {@html $localHead.slice(0, 7)}
      </a>
    </p>
  {/if}

  {#if $behind}
    <button
      class="button is-warning is-small"
      on:click={pullBranch}
      disabled={$loading}
    >
      Pull latest changes
    </button>
  {/if}

  {#if $loading}
    <p class="text-gray-500">Working…</p>
  {/if}

  {#if $successMessage}
    <p class="text-green-600">{$successMessage}</p>
  {/if}

  {#if $error}
    <p class="text-red-600">{$error}</p>
  {/if}

  {#if $gitOutput}
    <div class="mt-2">
      <label class="block font-semibold">Git Output:</label>
      <pre
        class="p-2 border rounded bg-gray-100 overflow-auto max-h-64 whitespace-pre-wrap text-sm">
      {$gitOutput}
      </pre>
    </div>
  {/if}
</div>
