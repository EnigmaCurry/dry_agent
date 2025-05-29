<script>
  import { onMount, createEventDispatcher, tick } from "svelte";
  import Terminal from "./Terminal.svelte";
  import { debounce } from "$lib/utils";

  export let command = "";
  export let title = "";
  export let visible = false;
  export let restartable = false;

  // Allow parent to change title/command reactively
  const updateTitle = (newTitle) => (title = newTitle);
  const updateCommand = (newCmd) => (command = newCmd);
  // Expose control to parent
  export let update = {
    setTitle: updateTitle,
    setCommand: updateCommand,
  };

  const dispatch = createEventDispatcher();

  let terminalHeight = 300;

  const debouncedSetTerminalHeight = debounce(() => {
    terminalHeight = Math.min(window.innerHeight * 0.75, 700);
  }, 300);

  onMount(async () => {
    window.addEventListener("resize", debouncedSetTerminalHeight);
    debouncedSetTerminalHeight();

    return () => {
      window.removeEventListener("resize", debouncedSetTerminalHeight);
    };
  });

  function close() {
    dispatch("close");
  }
</script>

{#if visible}
  <div class="modal is-active">
    <div class="modal-background" on:click={close}></div>
    <div
      class="modal-card"
      style="width: 80%; max-width: 80%; max-height: unset; height: auto;"
    >
      <header class="modal-card-head" style="padding: 0em 0em 1em 0em;">
        <p class="modal-card-title m-4">{title}</p>
        <button class="delete mr-4" aria-label="close" on:click={close}
        ></button>
      </header>
      <section class="modal-card-body" style="padding: 0; margin: 0;">
        <!-- Optional Form supplied by parent -->
        <slot name="form" />
        <!-- Show Terminal -->
        <div class="box mt-4">
          {#key command}
            <Terminal
              {restartable}
              height={`${terminalHeight}px`}
              {command}
              showWindowList={false}
              on:close={close}
            />
          {/key}
        </div>
      </section>
    </div>
  </div>
{/if}
