<script>
  import { onMount, onDestroy, tick } from "svelte";
  let { text } = $props();
  const GLITCH_CHARS = "!@#$%^&*()_+-=[]{}|;:',.<>?/\\";
  let displayed = $state("");
  let frame = $state(0);
  let interval;

  function glitchChar(realChar, forceGlitch = false) {
    return forceGlitch || Math.random() < 0.1
      ? GLITCH_CHARS[Math.floor(Math.random() * GLITCH_CHARS.length)]
      : realChar;
  }

  function countWords(str) {
    return str.trim().split(/\s+/).length;
  }

  $effect(() => {
    if (!text) return;
    clearInterval(interval);
    frame = 0;
    displayed = "";

    const target = text.split("");
    const wordCount = countWords(text);
    const totalDurationMs = Math.max(500, wordCount * 500); // min 0.5s
    const steps = target.length + 5;
    const intervalMs = totalDurationMs / steps;

    interval = setInterval(() => {
      let out = "";

      for (let i = 0; i < target.length; i++) {
        if (i < frame) {
          out += glitchChar(target[i]);
        } else if (i === frame) {
          out += glitchChar(target[i], true);
        } else {
          out += " ";
        }
      }

      displayed = out;
      frame++;

      if (frame > steps) {
        clearInterval(interval);
        displayed = text;
      }
    }, intervalMs);
  });

  onDestroy(() => clearInterval(interval));
</script>

<span class="glitchy-title">{displayed}</span>

<style>
  .glitchy-title {
    font-family: monospace;
    letter-spacing: 0.05em;
    white-space: nowrap;
    display: inline-block;
    min-height: 1em;
  }
</style>
