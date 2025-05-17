<script>
  import { onMount, onDestroy, tick } from "svelte";
  import { page } from '$app/stores';
  import {
    agentViewState,
    isPaneDragging,
    isLandscape,
    agentSizePercent,
    appSizePercent,
    userSplitSizePercent,
  } from "$lib/stores";
  import { listenToServerEvents } from "$lib/listenToEvents.js";
  import { PaneGroup, Pane, PaneResizer } from "paneforge";
  import "../app.scss";
  import ChatLLM from "$lib/ChatLLM.svelte";
  import {
    currentContext,
    dockerContexts,
    refreshDockerContexts,
    conversationId,
  } from "$lib/stores";

  let unsubscribe;

  let innerWidth = $state(window.innerWidth);
  let innerHeight = $state(window.innerHeight);

  const MIN_SIZES = [0, 0, 0];
  const STATE_ICONS = ["🌵", "🏝️", "🏜️️"];
  const SPLIT_STATE_ICONS = ["🏜️️", "🏝️", "🌵"];
  const SPLIT_ICONS = ["⛺️", "🧭"];
  const DIRECTION_ICONS = ["⬆️", "➡️", "⬇️", "⬅️"];
  let burgerActive = $state(false);
  let activeDropdown = $state(null);
  let minAgentSizePercent = MIN_SIZES[$agentViewState];
  let snapStateThreshold = 10;
  let paneGroupRef;
  let leftPaneRef;
  let rightPaneRef;
  let splitPaneToolIcon = $state(SPLIT_STATE_ICONS[$agentViewState]);
  let defaultAgentSizePercent = $state(getDefaultSize($agentViewState));
  let previousAgentView = $agentViewState;

  function getDefaultSize(state) {
    if (state === 0) {
      return 100;
    } else if (state === 1) {
      let userSplit = $userSplitSizePercent;
      if (
        userSplit === null ||
        userSplit > 100 - snapStateThreshold ||
        userSplit < snapStateThreshold
      ) {
        userSplitSizePercent.set(
          innerHeight > innerWidth || innerWidth < 650 ? 50 : 25,
        );
      }
      return $userSplitSizePercent;
    } else {
      return 0;
    }
  }
  agentSizePercent.set(getDefaultSize($agentViewState));
  userSplitSizePercent.set(getDefaultSize(1));

  function cycleAgentView() {
    agentViewState.set(($agentViewState + 1) % MIN_SIZES.length);
    defaultAgentSizePercent = getDefaultSize($agentViewState);
    minAgentSizePercent = MIN_SIZES[$agentViewState];
    splitPaneToolIcon = SPLIT_STATE_ICONS[$agentViewState];
    leftPaneRef.resize(defaultAgentSizePercent);
    agentSizePercent.set(getDefaultSize($agentViewState));
    appSizePercent.set(100 - getDefaultSize($agentViewState));
    handleSplitToolIcon();
  }

  function setAgentView(state) {
    agentViewState.set(state);
    minAgentSizePercent = MIN_SIZES[$agentViewState];

    defaultAgentSizePercent = getDefaultSize($agentViewState);

    leftPaneRef.resize(defaultAgentSizePercent);
    agentSizePercent.set(defaultAgentSizePercent);
    appSizePercent.set(100 - defaultAgentSizePercent);
  }

  function handleSplitToolIcon() {
    let splitPercent = leftPaneRef.getSize();
    let directionIcon = DIRECTION_ICONS[0];
    if ($isLandscape) {
      if ($agentViewState == 0) {
        directionIcon = DIRECTION_ICONS[3];
      } else if ($agentViewState == 2) {
        directionIcon = DIRECTION_ICONS[1];
      }
    } else {
      if ($agentViewState == 0) {
        directionIcon = DIRECTION_ICONS[0];
      } else if ($agentViewState == 2) {
        directionIcon = DIRECTION_ICONS[2];
      }
    }
    if ($isPaneDragging) {
      splitPaneToolIcon = SPLIT_ICONS[1];
    } else {
      // Stopped dragging
      if (splitPercent > 100 - snapStateThreshold) {
        //  splitPaneToolIcon = directionIcon + SPLIT_STATE_ICONS[0];
        splitPaneToolIcon = SPLIT_STATE_ICONS[2];
      } else if (splitPercent < snapStateThreshold) {
        //  splitPaneToolIcon = directionIcon + SPLIT_STATE_ICONS[2];
        splitPaneToolIcon = SPLIT_STATE_ICONS[0];
      } else {
        splitPaneToolIcon = SPLIT_STATE_ICONS[1];
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
      if (splitPercent > 100 - snapStateThreshold) {
        setAgentView(0);
        //userSplitSizePercent.set(getDefaultSize(0));
      } else if (splitPercent < snapStateThreshold) {
        setAgentView(2);
        //userSplitSizePercent.set(getDefaultSize(2));
      } else {
        userSplitSizePercent.set(splitPercent);
        setAgentView(1);
      }
    }
    handleSplitToolIcon();
  }

  $effect(() => {
    const isAgent = $page.url.pathname === "/";
    document.body.classList.toggle("no-scroll", isAgent);
  });

  $effect(() => {
    const newState = $agentViewState;
    if (newState !== previousAgentView) {
      setAgentView(newState);
      previousAgentView = newState;
    }
  });

  $effect(() => {
    function update() {
      if (innerWidth >= innerHeight) {
        isLandscape.set(true);
      } else {
        isLandscape.set(false);
      }
      handleSplitToolIcon();
    }
    update();
    window.addEventListener("resize", update);
    return () => window.removeEventListener("resize", update);
  });

  $effect(() => {
	const currentId = $page.url.searchParams.get('id');
	const storeId = $conversationId;

	if (currentId && currentId !== storeId) {
	  conversationId.set(currentId);
	} else if (!currentId && storeId) {
	  // Reinsert the id into the URL if it's missing
	  const url = new URL(window.location.href);
	  url.searchParams.set('id', storeId);
	  window.history.replaceState({}, '', url.toString());
	}
  });

  onMount(() => {
    agentViewState.set(($agentViewState - 1) % MIN_SIZES.length);
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
    } else {
      console.error("Failed to set default Docker context");
    }
    activeDropdown = null;
    burgerActive = false;
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
    if ($agentSizePercent == 100) {
      setAgentView(2);
    }
  }

  function handlePaneDoubleClick() {
    if ($appSizePercent === 100) {
      setAgentView(0);
    } else if ($agentSizePercent === 100) {
      setAgentView(2);
    }
    if ($agentSizePercent > $appSizePercent) {
      setAgentView(0);
    } else {
      setAgentView(2);
    }
    handleSplitToolIcon();
  }

  // Close dropdown when clicking outside
  function handleClickOutside(event) {
    const dropdownElements = document.querySelectorAll(
      ".navbar-item.has-dropdown, .navbar-item.has-docker-dropdown",
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

<nav class="navbar is-deep-red" aria-label="main navigation">
  <div class="navbar-brand">
    <a
      class="navbar-item no-select"
      role="button"
      aria-label="Toggle agent view"
      onclick={cycleAgentView}
      class:just-agent-logo={$agentViewState === 0 && !$isPaneDragging}
      class:split-logo={$agentViewState === 1 || $isPaneDragging}
      class:all-app-logo={$agentViewState === 2 && !$isPaneDragging}
    >
      {#if $isPaneDragging === true}
        {SPLIT_ICONS[0]} dry_agent
      {:else}
        {STATE_ICONS[$agentViewState]} dry_agent
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
            href="/settings"
            onclick={handleMenuItemClick}
          >
            Settings
          </a>

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
        class:is-active={activeDropdown === "docker"}
      >
        <a class="navbar-link" onclick={() => toggleDropdown("docker")}>
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
      style="height: 100%;"
    >
      <Pane
        bind:pane={leftPaneRef}
        defaultSize={defaultAgentSizePercent}
        minSize={minAgentSizePercent}
        class="is-flex rounded-lg bg-muted"
        style="position: relative;"
      >
        <ChatLLM />
      </Pane>
      <PaneResizer
        class="relative is-flex w-2 items-center justify-center pane-resizer"
        onDraggingChange={handlePaneDrag}
        ondblclick={handlePaneDoubleClick}
      >
        <div
          class="z-10 is-flex h-7 w-5 items-center justify-center rounded-sm border bg-brand"
        >
          <span class:is-size-4={true}>
            {splitPaneToolIcon}
          </span>
        </div>
      </PaneResizer>
      <Pane
        bind:pane={rightPaneRef}
        defaultSize={100 - defaultAgentSizePercent}
        class="is-flex rounded-lg bg-muted"
      >
        <div
          class="is-flex is-flex-direction-column is-flex-grow-1 is-scrollable-y"
        >
          <slot />
        </div>
      </Pane>
    </PaneGroup>
  </div>
</section>

<style>
  .section {
    overflow: hidden;
    flex-grow: 1;
    min-height: calc(100vh - 4rem);
  }
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
  :global(.pane-resizer) {
    background: radial-gradient(circle, #000, #31222a 53%, #000);
  }
</style>
