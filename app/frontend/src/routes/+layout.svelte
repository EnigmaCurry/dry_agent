<script>
  import "bulma/css/bulma.min.css";
  import "../../static/styles.css";

  let burgerActive = false;
  let dockerDropdownActive = false;

  function toggleBurger() {
    burgerActive = !burgerActive;
  }

  function openDockerDropdown() {
    dockerDropdownActive = true;
  }

  function closeDockerDropdown() {
    dockerDropdownActive = false;
  }

  function handleDockerSubItemClick() {
    dockerDropdownActive = false;
    // Optionally close the burger menu on mobile
    burgerActive = false;
  }
</script>

<svelte:head>
  <meta charset="UTF-8" />
  <title>dry_agent</title>
  <link
    rel="icon"
    href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🏜️️</text></svg>"
  />
  <!-- <link rel="stylesheet" href="/static/styles.css"> -->
  <!-- <script src="/static/htmx.min.js" defer></script> -->
  <!-- <script src="/static/command-button.js" defer></script> -->
  <!-- <link rel="stylesheet" href="/static/xterm.min.css"> -->
  <!-- <script src="/static/xterm.min.js" defer></script> -->
  <!-- <script src="/static/xterm-addon-fit.min.js" defer></script> -->
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
      <div
        class="navbar-item has-dropdown"
        class:is-active={dockerDropdownActive}
        on:mouseenter={openDockerDropdown}
        on:mouseleave={closeDockerDropdown}
      >
        <button type="button" class="navbar-link">Docker</button>
        <div class="navbar-dropdown">
          <a
            class="navbar-item is-deep-red"
            href="/context"
            on:click={handleDockerSubItemClick}
          >
            Manage Contexts
          </a>
        </div>
      </div>
      <!-- Similar adjustments for other dropdowns -->
    </div>
  </div>
</nav>

<section class="section">
  <div class="container">
    <slot />
  </div>
</section>
