<script>
  import { onMount, createEventDispatcher, tick } from "svelte";
  import Terminal from "./Terminal.svelte";
  import { debounce } from "$lib/utils";

  export let command = "";
  export let appName = "";
  export let visible = false;

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
    <div class="modal-card" style="width: 80%; max-width: 80%; max-height: unset; height: auto;">
      <header class="modal-card-head" style="padding: 0em 0em 1em 0em;">
        <p class="modal-card-title">d make {appName} config</p>
        <button class="delete" aria-label="close" on:click={close}></button>
      </header>
      <section class="modal-card-body" style="padding: 0; margin: 0;">
        <Terminal
          restartable={false}
          height={`${terminalHeight}px`}
          {command}
          on:close={close}
        />
      </section>
    </div>
  </div>
{/if}
