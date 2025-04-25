<script>
  import { onMount } from "svelte";
  import "bulma/css/bulma.min.css";
  import "../../static/styles.css";
  import { currentContext } from "$lib/stores";

  let dockerContexts = $state([]);
  let showDockerDropdown = false;

  let burgerActive = false;
  let activeDropdown = null;

  onMount(async () => {
    try {
      const defaultRes = await fetch("/api/docker_context/default");
      if (defaultRes.ok) {
        const data = await defaultRes.json();
        currentContext.set(data.default_context);
      }

      const res = await fetch("/api/docker_context/");
      if (res.ok) {
        dockerContexts = (await res.json()).filter(ctx => ctx !== "default");
        // fallback in case default context not yet set
        if (!currentContext && dockerContexts.length > 0) {
          currentContext.set(dockerContexts[0]);
        }
      }
    } catch (err) {
      console.error("Failed to fetch docker contexts", err);
    }
  });

  async function setDefaultContext(context) {
    const res = await fetch(`/api/docker_context/${context}/default`, {
      method: "PUT"
    });
    if (res.ok) {
      currentContext.set(context);
      showDockerDropdown = false;
    } else {
      console.error("Failed to set default Docker context");
    }
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
      on:click={toggleBurger}
    >
      <span aria-hidden="true"></span>
      <span aria-hidden="true"></span>
      <span aria-hidden="true"></span>
      <span aria-hidden="true"></span>
    </button>
  </div>

  <div id="main-navbar" class="navbar-menu" class:is-active={burgerActive}>
    <div class="navbar-start">
      <a class="navbar-item is-deep-red" href="/context"> Context </a>
      <a class="navbar-item is-deep-red" href="/config"> Config </a>

      <!-- Apps Dropdown -->
      <!-- <div -->
      <!--   class="navbar-item has-dropdown" -->
      <!--   class:is-active={activeDropdown === "apps"} -->
      <!-- > -->
      <!--   <button -->
      <!--     type="button" -->
      <!--     class="navbar-link" -->
      <!--     on:click={() => toggleDropdown("apps")} -->
      <!--   > -->
      <!--     Apps -->
      <!--   </button> -->
      <!--   <div class="navbar-dropdown"> -->
      <!--     <a -->
      <!--       class="navbar-item is-deep-red" -->
      <!--       href="/apps" -->
      <!--       on:click={handleDropdownItemClick} -->
      <!--     > -->
      <!--       Available Apps -->
      <!--     </a> -->
      <!--   </div> -->
      <!-- </div> -->
      <a class="navbar-item is-deep-red" href="/repository"> Repository </a>
      <a class="navbar-item is-deep-red" href="/workstation"> Workstation </a>
    </div>
    <div class="navbar-end">
      <div class="navbar-item has-dropdown is-hoverable" class:is-active={showDockerDropdown}>
        <a class="navbar-link" on:click={() => (showDockerDropdown = !showDockerDropdown)}>
          Context: {$currentContext ?? "Loading..."}
        </a>
        <div class="navbar-dropdown is-right">
          {#each dockerContexts as context}
            <a
              class="navbar-item"
              on:click={() => setDefaultContext(context)}
              >
            {#if context === $currentContext}✅{/if} {context}
              </a>
            {/each}
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
