<script>
  import { onMount, onDestroy, tick } from "svelte";
  import { page } from "$app/stores";
  import { isPaneDragging } from "$lib/stores";
  import { listenToServerEvents } from "$lib/listenToEvents.js";
  import { PaneGroup, Pane, PaneResizer } from "paneforge";
  import "bulma/css/bulma.min.css";
  import "../../static/styles.css";
  import ChatLLM from "$lib/ChatLLM.svelte";
  import {
    currentContext,
    dockerContexts,
    refreshDockerContexts,
  } from "$lib/stores";

  let showDockerDropdown = $state(false);
  let unsubscribe;

  const MIN_SIZES = [0, 0, 0];
  const STATE_ICONS = ["🗣️", "🏝️", "🏜️️"];
  let burgerActive = $state(false);
  let activeDropdown = $state(null);
  let agentViewState = $state(1);
  let minAgentSizePercent = MIN_SIZES[agentViewState];
  let width = window.innerWidth;
  let snapStateThreshold = 15;
  let leftPaneRef;
  let splitPaneToolIcon = $state(STATE_ICONS[agentViewState]);
  let defaultAgentSizePercent = $state(getDefaultSize(agentViewState));

  function getDefaultSize(state) {
    if (state === 0) {
      return 100;
    } else if (state === 1) {
      return window.innerHeight > window.innerWidth ? 50 : 25;
    } else {
      return 0;
    }
  }

  function cycleAgentView() {
    agentViewState = (agentViewState + 1) % MIN_SIZES.length;
    defaultAgentSizePercent = getDefaultSize(agentViewState);
    minAgentSizePercent = MIN_SIZES[agentViewState];
    splitPaneToolIcon = STATE_ICONS[agentViewState];
    leftPaneRef.resize(defaultAgentSizePercent);

    console.log("agent state", agentViewState);
    console.log("default size", defaultAgentSizePercent);
    console.log("min size", minAgentSizePercent);
    console.log("icon", splitPaneToolIcon);
    console.log("-------");
  }

  function setAgentView(state) {
    agentViewState = state;
    minAgentSizePercent = MIN_SIZES[agentViewState];
    if (state === 1) {
      defaultAgentSizePercent = leftPaneRef.getSize();
    } else {
      defaultAgentSizePercent = getDefaultSize(agentViewState);
    }
    leftPaneRef.resize(defaultAgentSizePercent);
  }

  function handleSplitToolIcon() {
    let splitPercent = leftPaneRef.getSize();
    if ($isPaneDragging) {
      splitPaneToolIcon = " ";
    } else {
      // Stopped dragging
      if (splitPercent > 100 - snapStateThreshold) {
        splitPaneToolIcon = STATE_ICONS[0];
      } else if (splitPercent < snapStateThreshold) {
        splitPaneToolIcon = STATE_ICONS[2];
      } else {
        splitPaneToolIcon = STATE_ICONS[1];
      }
    }
  }

  function handlePaneDrag(dragging) {
    isPaneDragging.set(dragging);
    let splitPercent = leftPaneRef.getSize();
    if (dragging) {
      // Start dragging
    } else {
      // Stopped dragging
      if (splitPercent > 85) {
        setAgentView(0);
      } else if (splitPercent < 15) {
        setAgentView(2);
      } else {
        setAgentView(1);
      }
    }
    handleSplitToolIcon();
  }

  $effect(() => {
    const isAgent = $page.url.pathname === "/";
    document.body.classList.toggle("no-scroll", isAgent);
  });

  onMount(() => {
    const cleanup = listenToServerEvents();
    return cleanup;
  });

  async function setDefaultContext(context) {
    const res = await fetch(`/api/docker_context/${context}/default`, {
      method: "PUT",
    });
    if (res.ok) {
      currentContext.set(context);
      showDockerDropdown = false;
    } else {
      console.error("Failed to set default Docker context");
    }
    handleDropdownItemClick();
  }

  function toggleBurger() {
    burgerActive = !burgerActive;
  }

  function toggleDropdown(name) {
    activeDropdown = activeDropdown === name ? null : name;
  }

  function handleDropdownItemClick() {
    activeDropdown = null;
    burgerActive = false;
  }

  // Close dropdown when clicking outside
  function handleClickOutside(event) {
    const dropdownElements = document.querySelectorAll(
      ".navbar-item.has-dropdown",
    );
    const clickedInside = Array.from(dropdownElements).some((el) =>
      el.contains(event.target),
    );
    if (!clickedInside) {
      activeDropdown = null;
    }
  }

  document.addEventListener("click", handleClickOutside);
</script>

<svelte:head>
  <meta charset="UTF-8" />
  <title>dry_agent</title>
  <link
    rel="icon"
    href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🏜️️</text></svg>"
  />
</svelte:head>

<nav class="navbar is-deep-red is-fixed-top" aria-label="main navigation">
  <div class="navbar-brand">
    <a
      class="navbar-item no-select"
      role="button"
      aria-label="Toggle agent view"
      onclick={cycleAgentView}
      class:just-agent-logo={agentViewState === 0}
      class:split-logo={agentViewState === 1}
      class:all-app-logo={agentViewState === 2}
    >
      {#if agentViewState === 1}
        🏝️ dry_agent
      {:else if agentViewState === 2}
        🏜️️ dry_agent
      {:else}
        🗣️ dry_agent
      {/if}
    </a>
    <button
      type="button"
      class="navbar-burger"
      aria-label="menu"
      aria-expanded="false"
      data-target="main-navbar"
      onclick={toggleBurger}
    >
      <span aria-hidden="true"></span>
      <span aria-hidden="true"></span>
      <span aria-hidden="true"></span>
      <span aria-hidden="true"></span>
    </button>
  </div>

  <div id="main-navbar" class="navbar-menu" class:is-active={burgerActive}>
    <div class="navbar-start">
      <!-- Setup -->
      <div
        class="navbar-item has-dropdown"
        class:is-active={activeDropdown === "setup"}
      >
        <button
          type="button"
          class="navbar-link"
          onclick={() => toggleDropdown("setup")}
        >
          Setup
        </button>
        <div class="navbar-dropdown">
          <a
            class="navbar-item is-deep-red"
            href="/docker"
            onclick={handleDropdownItemClick}
          >
            Docker
          </a>
          <a
            class="navbar-item is-deep-red"
            href="/repository/"
            onclick={handleDropdownItemClick}
          >
            Repository
          </a>
          <a
            class="navbar-item is-deep-red"
            href="/config/"
            onclick={handleDropdownItemClick}
          >
            Config (Traefik)
          </a>
        </div>
      </div>

      <a
        class="navbar-item is-deep-red {'/projects/' === $page.url.pathname
          ? 'is-active'
          : ''}"
        onclick={handleDropdownItemClick}
        href="/projects/"
      >
        Projects
      </a>
      <a
        class="navbar-item is-deep-red {'/workstation/' === $page.url.pathname
          ? 'is-active'
          : ''}"
        onclick={handleDropdownItemClick}
        href="/workstation/"
      >
        Workstation
      </a>

      <!-- <\!-- Dropdown Example -\-> -->
      <!-- <div -->
      <!--   class="navbar-item has-dropdown is-hoverable" -->
      <!--   class:is-active={activeDropdown === "apps"} -->
      <!-- > -->
      <!--   <button -->
      <!--     type="button" -->
      <!--     class="navbar-link" -->
      <!--     onclick={() => toggleDropdown("apps")} -->
      <!--   > -->
      <!--     Apps -->
      <!--   </button> -->
      <!--   <div class="navbar-dropdown"> -->
      <!--     <a -->
      <!--       class="navbar-item is-deep-red" -->
      <!--       href="/apps" -->
      <!--       onclick={handleDropdownItemClick} -->
      <!--     > -->
      <!--       Available Apps -->
      <!--     </a> -->
      <!--   </div> -->
      <!-- </div> -->
    </div>
    <div class="navbar-end">
      <div
        class="navbar-item has-dropdown mr-2"
        class:is-active={showDockerDropdown}
      >
        <a
          class="navbar-link"
          onclick={() => (showDockerDropdown = !showDockerDropdown)}
        >
          {#if $dockerContexts.length > 0}
            {$currentContext}
          {:else}
            <span title="No context set!">No Context</span>
          {/if}
        </a>

        <div class="navbar-dropdown is-right">
          {#if $dockerContexts.length > 0}
            <div class="has-text-weight-semibold ml-2 mr-1">Set context:</div>
            <hr class="is-light-red ml-3 mr-3 navbar-divider" />

            {#each $dockerContexts as context}
              <a class="navbar-item" onclick={() => setDefaultContext(context)}>
                {#if context === $currentContext}✅
                {/if}{context}
              </a>
            {/each}
          {:else}
            <div class="navbar-item has-text-grey-light">
              No contexts available
            </div>
          {/if}
        </div>
      </div>
    </div>
  </div>
</nav>

<section class="section">
  <div class="container">
    <PaneGroup
      direction="horizontal"
      class="w-full rounded-lg"
      style="margin-top: 4em;"
    >
      <Pane
        bind:pane={leftPaneRef}
        defaultSize={defaultAgentSizePercent}
        minSize={minAgentSizePercent}
        class="is-flex rounded-lg bg-muted"
        style="position: relative;"
      >
        <ChatLLM autofocus={agentViewState === 2} />
      </Pane>
      <PaneResizer
        class="relative is-flex w-2 items-center justify-center bg-background"
        onDraggingChange={handlePaneDrag}
      >
        <div
          class="z-10 is-flex h-7 w-5 items-center justify-center rounded-sm border bg-brand"
        >
          {splitPaneToolIcon}
        </div>
      </PaneResizer>
      <Pane
        defaultSize={100 - defaultAgentSizePercent}
        class="is-flex rounded-lg bg-muted"
      >
        <div class="is-flex is-flex-direction-column is-flex-grow-1">
          <slot />
        </div>
      </Pane>
    </PaneGroup>
  </div>
</section>

<style>
  .navbar-item.just-agent-logo {
    /* 135deg makes the “cut” run from bottom-left to top-right */
    background: #290b0b;
  }
  .navbar-item.split-logo {
    /* 135deg makes the “cut” run from bottom-left to top-right */
    background: linear-gradient(135deg, #370e0e 50%, #822222 50%);
  }
  .navbar-item.all-app-logo {
    /* 135deg makes the “cut” run from bottom-left to top-right */
    background: #822222;
  }
</style>
