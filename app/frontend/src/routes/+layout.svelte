<script>
  import "bulma/css/bulma.min.css";
  import "../../static/styles.css";
  let burgerActive = false;
  function toggleBurger() {
    burgerActive = !burgerActive;
  }
</script>

<svelte:head>
  <meta charset="UTF-8" />
  <title>dry_agent - (base)</title>
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
      <div class="navbar-item has-dropdown is-hoverable">
        <button type="button" class="navbar-link">Docker</button>
        <div class="navbar-dropdown">
          <a class="navbar-item is-deep-red" href="#">Manage Contexts</a>
        </div>
      </div>
      <div class="navbar-item has-dropdown is-hoverable">
        <button type="button" class="navbar-link">Apps</button>
        <div class="navbar-dropdown">
          <!-- <a class="navbar-item" href="/app/apps/available">Available Apps</a> -->
          <!-- <a class="navbar-item" href="/app/apps/manage">Manage Apps</a> -->
        </div>
      </div>
      <div class="navbar-item has-dropdown is-hoverable">
        <button type="button" class="navbar-link">Git Tools</button>
        <div class="navbar-dropdown">
          <!-- <a class="navbar-item" href="/app/repo/pull">Pull remote</a> -->
          <!-- <a class="navbar-item" href="/app/repo/branch">Switch branch</a> -->
        </div>
      </div>
      <!-- <a class="navbar-item" href="/app/terminal">Terminal</a> -->
      <!-- <a class="navbar-item" href="/logout">Logout</a> -->
    </div>
  </div>
</nav>

<!-- Adjust the top margin so that the section isn't hidden behind the fixed navbar -->
<section class="section" style="margin-top: 3.25rem;">
  <div class="container">
    <slot />
  </div>
</section>
