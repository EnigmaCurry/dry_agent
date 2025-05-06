<script>
  import { onMount, onDestroy, tick } from "svelte";
  import { page } from "$app/stores";
  import {
    isPaneDragging,
    isLandscape,
    agentSizePercent,
    appSizePercent,
    userSplitSizePercent
  } from "$lib/stores";
  import { listenToServerEvents } from "$lib/listenToEvents.js";
  import { PaneGroup, Pane, PaneResizer } from "paneforge";
  import "../app.scss";
  import ChatLLM from "$lib/ChatLLM.svelte";
  import {
    currentContext,
    dockerContexts,
    refreshDockerContexts,
  } from "$lib/stores";

  let showDockerDropdown = $state(false);
  let unsubscribe;

  let innerWidth = $state(window.innerWidth);
  let innerHeight = $state(window.innerHeight);

  const MIN_SIZES = [0, 0, 0];
  const STATE_ICONS = ["🗣️", "🏝️", "🏜️️"];
  const SPLIT_ICON = "🗺️";
  let burgerActive = $state(false);
  let activeDropdown = $state(null);
  let agentViewState = $state(0);
  let minAgentSizePercent = MIN_SIZES[agentViewState];
  let snapStateThreshold = 15;
  let paneGroupRef;
  let leftPaneRef;
  let rightPaneRef;
  let splitPaneToolIcon = $state(STATE_ICONS[agentViewState]);
  let defaultAgentSizePercent = $state(getDefaultSize(agentViewState));

  function getDefaultSize(state) {
    if (state === 0) {
      return 100;
    } else if (state === 1) {
      if ($userSplitSizePercent === null) {
        userSplitSizePercent.set(innerHeight > innerWidth || innerWidth < 650 ? 50 : 25);
      }
      return $userSplitSizePercent;
    } else {
      return 0;
    }
  }
  agentSizePercent.set(getDefaultSize(agentViewState));
  userSplitSizePercent.set(getDefaultSize(1));

  function cycleAgentView() {
    agentViewState = (agentViewState + 1) % MIN_SIZES.length;
    defaultAgentSizePercent = getDefaultSize(agentViewState);
    minAgentSizePercent = MIN_SIZES[agentViewState];
    splitPaneToolIcon = STATE_ICONS[agentViewState];
    leftPaneRef.resize(defaultAgentSizePercent);
    agentSizePercent.set(getDefaultSize(agentViewState));
    appSizePercent.set(getDefaultSize(agentViewState));
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
    agentSizePercent.set(defaultAgentSizePercent);
    appSizePercent.set(100 - defaultAgentSizePercent);
  }

  function handleSplitToolIcon() {
    let splitPercent = leftPaneRef.getSize();
    if ($isPaneDragging) {
      splitPaneToolIcon = SPLIT_ICON;
    } else {
      // Stopped dragging
      if (splitPercent > 100 - snapStateThreshold) {
        splitPaneToolIcon = STATE_ICONS[2];
      } else if (splitPercent < snapStateThreshold) {
        splitPaneToolIcon = STATE_ICONS[0];
      } else {
        splitPaneToolIcon = STATE_ICONS[1];
      }
    }
  }

  function handlePaneDrag(dragging) {
    isPaneDragging.set(dragging);
    let splitPercent = leftPaneRef.getSize();
    agentSizePercent.set(splitPercent);
    appSizePercent.set(rightPaneRef.getSize());
    if (dragging) {
      // Start dragging
    } else {
      // Stopped dragging
      if (splitPercent > 85) {
        setAgentView(0);
        userSplitSizePercent.set(getDefaultSize(0));
      } else if (splitPercent < 15) {
        setAgentView(2);
        userSplitSizePercent.set(getDefaultSize(2));
      } else {
        setAgentView(1);
        userSplitSizePercent.set(splitPercent);
      }
    }
    handleSplitToolIcon();
  }

  $effect(() => {
    const isAgent = $page.url.pathname === "/";
    document.body.classList.toggle("no-scroll", isAgent);
  });

  $effect(() => {
    function update() {
      if (innerWidth >= innerHeight) {
        isLandscape.set(true);
      } else {
        isLandscape.set(false);
      }
    }
    update();
    window.addEventListener("resize", update);
    return () => window.removeEventListener("resize", update);
  });

  onMount(() => {
    cycleAgentView();
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
    handleMenuItemClick();
  }

  function toggleBurger() {
    burgerActive = !burgerActive;
  }

  function toggleDropdown(name) {
    activeDropdown = activeDropdown === name ? null : name;
  }

  function handleMenuItemClick() {
    activeDropdown = null;
    burgerActive = false;
    if ($agentSizePercent === 100) {
      setAgentView(2);
    }
  }

  function handlePaneDoubleClick() {
    if ($appSizePercent === 100) {
      setAgentView(0);
    } else if ($agentSizePercent === 100) {
      setAgentView(2);
    } if ($agentSizePercent > $appSizePercent) {
      setAgentView(0);
    } else {
      setAgentView(2);
    }
    handleSplitToolIcon();
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

<svelte:window bind:innerWidth bind:innerHeight />

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
      class:just-agent-logo={agentViewState === 0 && !$isPaneDragging}
      class:split-logo={agentViewState === 1 || $isPaneDragging}
      class:all-app-logo={agentViewState === 2 && !$isPaneDragging}
    >
      {#if $isPaneDragging === true}
        {SPLIT_ICON} dry_agent
      {:else}
        {STATE_ICONS[agentViewState]} dry_agent
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
            onclick={handleMenuItemClick}
          >
            Docker
          </a>
          <a
            class="navbar-item is-deep-red"
            href="/repository/"
            onclick={handleMenuItemClick}
          >
            Repository
          </a>
          <a
            class="navbar-item is-deep-red"
            href="/config/"
            onclick={handleMenuItemClick}
          >
            Config (Traefik)
          </a>
        </div>
      </div>

      <a
        class="navbar-item is-deep-red {'/projects/' === $page.url.pathname
          ? 'is-active'
          : ''}"
        onclick={handleMenuItemClick}
        href="/projects/"
      >
        Projects
      </a>
      <a
        class="navbar-item is-deep-red {'/workstation/' === $page.url.pathname
          ? 'is-active'
          : ''}"
        onclick={handleMenuItemClick}
        href="/workstation/"
      >
        Workstation
      </a>
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
      bind:pane={paneGroupRef}
      direction={innerWidth > innerHeight ? "horizontal" : "vertical"}
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
          ondblclick={handlePaneDoubleClick}
        >
          {splitPaneToolIcon}
        </div>
      </PaneResizer>
      <Pane
        bind:pane={rightPaneRef}
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
