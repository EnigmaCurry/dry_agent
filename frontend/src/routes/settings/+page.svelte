<script>
  import { tick } from "svelte";
  import { toTitleCase } from "$lib/utils.js";
  import { invalidateAll } from "$app/navigation";
  import ProjectsTable from "$lib/ProjectsTable.svelte";
  import { currentContext, terminalFontSize } from "$lib/stores";
  import GitRepository from "$lib/GitRepository.svelte";
  import DockerContext from "$lib/DockerContext.svelte";
  import Terminal from "$lib/Terminal.svelte";
  import { goto } from "$app/navigation";

  let { data } = $props();
  let selectedTab = $state(data.tab);

  $effect(() => {
    if (data.tab !== selectedTab) {
      selectedTab = data.tab;
    }
  });

  let loginUrl = $state("");
  let isLoading = $state(false);
  let transferError = $state("");
  let inputEl;

  function selectTab(tab) {
    selectedTab = tab;
    const url = new URL(window.location.href);
    url.searchParams.set("tab", tab);
    goto(`${url.pathname}?${url.searchParams.toString()}`, {
      replaceState: true,
    });
  }
  
  async function fetchTransferUrl() {
    if (loginUrl || isLoading) return;
    isLoading = true;
    transferError = "";

    try {
      const res = await fetch("/get-login-url");
      if (!res.ok) throw new Error("Failed to get login URL");
      const json = await res.json();
      loginUrl = json.login_url;

      await tick();
      inputEl.focus();
      inputEl.select();
    } catch (err) {
      transferError = err.message;
    } finally {
      isLoading = false;
    }
  }

  function copyToClipboard() {
    if (!loginUrl) return;

    navigator.clipboard.writeText(loginUrl).then(() => {
      loginUrl = "";
    });
  }
</script>

<svelte:head>
  <title>dry_agent - Settings</title>
</svelte:head>

<div class="is-flex is-flex-wrap-wrap">
  <h1 class="title m-4 is-flex-grow-1 is-no-text-wrap">
    {#if selectedTab === "docker"}
      Docker SSH contexts
    {:else}
      {toTitleCase(selectedTab)} Settings
    {/if}
  </h1>
  <div class="is-flex-grow-1"></div>
  <div class="tabs is-toggle m-4">
    <ul>
      <li class:is-active={selectedTab === "session"}>
        <a
          href="#"
          onclick={(e) => {
            e.preventDefault();
            selectTab("session");
          }}
        >
          <span class="is-small">
            <i class="fas fa-music" aria-hidden="true"></i>
          </span>
          <span>Session</span>
        </a>
      </li>
      <li class:is-active={selectedTab === "docker"}>
        <a
          href="#"
          onclick={(e) => {
            e.preventDefault();
            selectTab("docker");
          }}
        >
          <span class="is-small">
            <i class="fas fa-music" aria-hidden="true"></i>
          </span>
          <span>Docker</span>
        </a>
      </li>
      <li class:is-active={selectedTab === "repository"}>
        <a
          href="#"
          onclick={(e) => {
            e.preventDefault();
            selectTab("repository");
          }}
        >
          <span class="is-small">
            <i class="fas fa-music" aria-hidden="true"></i>
          </span>
          <span>Repository</span>
        </a>
      </li>
      <li class:is-active={selectedTab === "terminal"}>
        <a
          href="#"
          onclick={(e) => {
            e.preventDefault();
            selectTab("terminal");
          }}
        >
          <span class="is-small">
            <i class="fas fa-image" aria-hidden="true"></i>
          </span>
          <span>Terminal</span>
        </a>
      </li>
    </ul>
  </div>
</div>

{#if selectedTab === "session"}
  <section class="section is-flex-direction-column">
    <div class="box">
      <h2 class="subtitle">Transfer Session</h2>
      <ul style="list-style: disc;" class="mb-3">
        <li>
          Retrieves a one-time-use login URL to transfer this session to another
          device.
        </li>
        <li>Once the link is used, this session will log out automatically.</li>
      </ul>

      {#if !loginUrl}
        <button
          class="button is-link"
          onclick={fetchTransferUrl}
          disabled={isLoading}
        >
          {#if isLoading}
            <span class="icon is-small"
              ><i class="fas fa-spinner fa-spin"></i></span
            >
            <span>Generating…</span>
          {:else}
            <span>Transfer Session</span>
          {/if}
        </button>
      {:else}
        <div class="field has-addons">
          <div class="control is-expanded">
            <input
              class="input"
              type="text"
              bind:this={inputEl}
              readonly
              value={loginUrl}
            />
          </div>
          <div class="control">
            <button class="button is-info" onclick={copyToClipboard}>
              <span class="icon is-small"><i class="fas fa-copy"></i></span>
              <span>Copy</span>
            </button>
          </div>
        </div>
        <strong>Do <em>not</em> press End Session or Full Logout.</strong>.
      {/if}

      {#if transferError}
        <p class="help is-danger mt-2">{transferError}</p>
      {/if}
    </div>
    <div class="box">
      <h2 class="subtitle">End Session</h2>
      <ul class="mb-3" style="list-style: disc;">
        <li>Logs out from all sessions.</li>
        <li>Invalidates all login URLs.</li>
        <li>
          <strong
            >Keeps TOTP session cookie on this device for up to 7 days.</strong
          >
        </li>
      </ul>
      <a class="button is-primary" href="/logout">End Session</a>
    </div>
    <div class="box">
      <h2 class="subtitle">Full Logout</h2>
      <ul class="mb-3" style="list-style: disc;">
        <li>Logs out from all sessions.</li>
        <li>Invalidates all login URLs.</li>
        <li><strong>Deletes TOTP session cookie from this device.</strong></li>
      </ul>
      <a class="button is-danger" href="/logout?full=true">Full Logout</a>
    </div>
  </section>
{:else if selectedTab === "docker"}
  <DockerContext />
{:else if selectedTab === "repository"}
  <GitRepository />
{:else if selectedTab === "terminal"}
  <label class="label" for="terminalFontSize"
    >Font Size: {$terminalFontSize}</label
  >
  <div class="control">
    <input
      name="terminalFontSize"
      class="slider is-fullwidth is-info"
      type="range"
      min="8"
      max="30"
      step="1"
      bind:value={$terminalFontSize}
    />
  </div>
  {#key terminalFontSize}
    <Terminal command="neofetch" showWindowList={false} />
  {/key}
{/if}
