<script>
  import { onMount } from "svelte";
  import { page } from "$app/stores";

  import "bulma/css/bulma.min.css";
  import "../../static/styles.css";
  import {
    currentContext,
    dockerContexts,
    refreshDockerContexts,
  } from "$lib/stores";

  let showDockerDropdown = $state(false);
  let unsubscribe;

  let burgerActive = $state(false);
  let activeDropdown = $state(null);

  $effect(() => {
    const isAgent = $page.url.pathname === "/agent/";
    document.body.classList.toggle("no-scroll", isAgent);
  });

  onMount(async () => {
    await refreshDockerContexts();
    try {
      const defaultRes = await fetch("/api/docker_context/default");
      if (defaultRes.ok) {
        const data = await defaultRes.json();
        currentContext.set(data.default_context);
      }

      const res = await fetch("/api/docker_context/");
      if (res.ok) {
        const contexts = (await res.json()).filter((ctx) => ctx !== "default");
        dockerContexts.set(contexts);
        // fallback in case default context not yet set
        if (!$currentContext && contexts.length > 0) {
          currentContext.set(contexts[0]);
        }
      }
    } catch (err) {
      console.error("Failed to fetch docker contexts", err);
    }
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
    <a class="navbar-item" href="/"> 🏜️️ dry_agent </a>
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
        class="navbar-item is-deep-red {'/apps/' === $page.url.pathname
          ? 'is-active'
          : ''}"
        onclick={handleDropdownItemClick}
        href="/apps/"
      >
        Apps
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
      <a
        class="navbar-item is-deep-red {'/agent/' === $page.url.pathname
          ? 'is-active'
          : ''}"
        onclick={handleDropdownItemClick}
        href="/agent/"
      >
        Agent
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
        class="navbar-item has-dropdown is-hoverable mr-2"
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
    <slot />
  </div>
</section>
