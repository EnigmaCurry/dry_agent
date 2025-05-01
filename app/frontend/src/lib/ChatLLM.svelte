<script>
  import { onMount, tick } from "svelte";
  import Markdown from "svelte-exmarkdown";

  import langPython from "highlight.js/lib/languages/python";
  import langMakefile from "highlight.js/lib/languages/makefile";
  import langJson from "highlight.js/lib/languages/json";
  import langShell from "highlight.js/lib/languages/shell";
  import langJavascript from "highlight.js/lib/languages/javascript";
  import langMarkdown from "highlight.js/lib/languages/markdown";
  import langSvelte from "highlight.svelte";
  import langRust from "highlight.js/lib/languages/rust";
  import langC from "highlight.js/lib/languages/c";
  import langJava from "highlight.js/lib/languages/java";

  import { gfmPlugin } from "svelte-exmarkdown/gfm";
  import rehypeExternalLinks from "rehype-external-links";
  import "highlight.js/styles/github-dark.css";
  import rehypeHighlight from "rehype-highlight";

  let conversationId;
  let messages = $state([
    { role: "system", content: "You are a helpful assistant." },
  ]);
  let input = $state("");
  let loading = $state(false);
  let controller;
  let scrollAnchor;
  let inputElement;
  let renderers;
  let isAtBottom = $state(true);
  let showScrollButton = $state(false);
  let chatContainer;
  let scrollTimeout;
  let lockScroll = $state(false);
  let showMenuModal = $state(false);

  const AUTO_SCROLL_THRESHOLD = 10; // user scroll tolerance
  const SCROLL_BUTTON_DISPLAY_THRESHOLD = 100; // when to show the button

  //TODO: placeholder:
  const conversationHistory = [
    {
      id: "1",
      title: "Docker issue",
      synopsis: "Troubleshooting container networking...",
    },
    {
      id: "2",
      title: "Svelte help",
      synopsis: "How to bind class dynamically...",
    },
    {
      id: "3",
      title: "Makefile pipeline",
      synopsis: "Fixing a broken build step...",
    },
    {
      id: "1",
      title: "Docker issue",
      synopsis: "Troubleshooting container networking...",
    },
    {
      id: "2",
      title: "Svelte help",
      synopsis: "How to bind class dynamically...",
    },
    {
      id: "3",
      title: "Makefile pipeline",
      synopsis: "Fixing a broken build step...",
    },
    {
      id: "1",
      title: "Docker issue",
      synopsis: "Troubleshooting container networking...",
    },
    {
      id: "2",
      title: "Svelte help",
      synopsis: "How to bind class dynamically...",
    },
    {
      id: "3",
      title: "Makefile pipeline",
      synopsis: "Fixing a broken build step...",
    },
    {
      id: "1",
      title: "Docker issue",
      synopsis: "Troubleshooting container networking...",
    },
    {
      id: "2",
      title: "Svelte help",
      synopsis: "How to bind class dynamically...",
    },
    {
      id: "3",
      title: "Makefile pipeline",
      synopsis: "Fixing a broken build step...",
    },
  ];

  const markdownPlugins = [
    gfmPlugin(),
    {
      rehypePlugin: [
        rehypeHighlight,
        {
          ignoreMissing: true,
          languages: {
            python: langPython,
            makefile: langMakefile,
            shell: langShell,
            json: langJson,
            javascript: langJavascript,
            svelte: langSvelte,
            markdown: langMarkdown,
            rust: langRust,
            c: langC,
            java: langJava,
          },
        },
      ],
    },
    {
      rehypePlugin: [
        rehypeExternalLinks,
        { rel: ["nofollow", "noopener", "noreferrer"], target: "_blank" },
      ],
    },
  ];

  function toggleMenuModal() {
    showMenuModal = !showMenuModal;
  }

  function closeMenuModal() {
    showMenuModal = false;
  }

  function scrollToBottom() {
    lockScroll = true;
    scrollAnchor?.scrollIntoView({ behavior: "smooth" });

    setTimeout(() => {
      if (chatContainer) {
        const position = chatContainer.scrollTop + chatContainer.clientHeight;
        const height = chatContainer.scrollHeight;
        isAtBottom = height - position < AUTO_SCROLL_THRESHOLD;
      }
      lockScroll = false;
    }, 300); // or match your scroll duration
  }

  function handleScroll() {
    clearTimeout(scrollTimeout);
    scrollTimeout = setTimeout(() => {
      const position = chatContainer.scrollTop + chatContainer.clientHeight;
      const height = chatContainer.scrollHeight;

      const distanceFromBottom = height - position;

      isAtBottom = distanceFromBottom < AUTO_SCROLL_THRESHOLD;
      showScrollButton = distanceFromBottom >= SCROLL_BUTTON_DISPLAY_THRESHOLD;
    }, 100);
  }

  onMount(async () => {
    conversationId = crypto.randomUUID();
    await tick();
    adjustTextareaHeight();
    inputElement?.focus();
  });

  async function send() {
    if (!input.trim()) return;

    messages.push({ role: "user", content: input });
    messages.push({ role: "assistant", content: "" });

    const index = messages.length - 1;
    input = "";
    await tick();
    adjustTextareaHeight();
    loading = true;
    controller = new AbortController();

    try {
      const res = await fetch(`/api/chat/stream/${conversationId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: messages[index - 1].content }),
        signal: controller.signal,
      });

      const reader = res.body.getReader();
      const decoder = new TextDecoder("utf-8");

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        messages[index].content += decoder.decode(value);
        if (isAtBottom) scrollToBottom();
      }
    } catch (err) {
      if (err.name === "AbortError") {
        messages[index].content += "\n\n_⛔️ Response stopped by user._";
      } else {
        messages[index].content += "\n\n❌ Error occurred: " + err.message;
      }
    } finally {
      loading = false;
      controller = null;
    }
  }

  function stop() {
    if (controller) controller.abort();
  }

  function handleKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      send();
    }
  }

  function adjustTextareaHeight() {
    if (!inputElement) return;

    inputElement.style.height = "auto"; // reset
    const maxHeight = window.innerHeight * 0.3;
    inputElement.style.height =
      Math.min(inputElement.scrollHeight, maxHeight) + "px";
  }
</script>

<div class="chat-wrapper">
  <div
    class="box chat-box chat-container"
    on:scroll={handleScroll}
    bind:this={chatContainer}
  >
    {#each messages as { role, content } (role + content)}
      {#if role === "user"}
        <div class="user-message">{content}</div>
      {:else if role === "assistant"}
        <div class="assistant-message markdown-body">
          <Markdown md={content} plugins={markdownPlugins} />
        </div>
      {/if}
    {/each}

    {#if loading}
      <div class="mt-4 assistant-message loading-message">
        Assistant is typing...
      </div>
    {/if}

    <div bind:this={scrollAnchor}></div>
  </div>

  {#if showScrollButton}
    <button
      class="scroll-to-bottom"
      type="button"
      on:click={scrollToBottom}
      aria-label="Scroll to bottom"
    >
      ⬇️
    </button>
  {/if}

  <form on:submit|preventDefault={send} class="chat-form">
    <div class="field is-grouped is-grouped-multiline">
      <div class="control is-expanded">
        <textarea
          class="textarea"
          bind:this={inputElement}
          bind:value={input}
          placeholder="Ask something..."
          on:keydown={handleKeyDown}
          on:input={adjustTextareaHeight}
          rows="1"
          style="resize: none; overflow: hidden"
        />
      </div>

      <div class="control">
        <button class="button is-link" type="submit" disabled={loading}>
          Send
        </button>
      </div>

      <div class="control">
        <button class="button is-info" type="button" on:click={toggleMenuModal}>
          Menu
        </button>
      </div>

      {#if loading}
        <div class="control">
          <button class="button is-danger" type="button" on:click={stop}>
            Stop
          </button>
        </div>
      {/if}
    </div>
  </form>
</div>

{#if showMenuModal}
  <div class="menu modal is-active">
    <div class="modal-background" on:click={closeMenuModal}></div>
    <div class="modal-card">
      <header class="modal-card-head">
        <p class="modal-card-title">Conversations</p>
        <div class="pr-4">
          <button class="button is-link">New Conversation</button>
        </div>
        <button class="delete" aria-label="close" on:click={closeMenuModal}
        ></button>
      </header>
      <section class="modal-card-body">
        <div class="buttons is-flex is-flex-direction-column">
          {#each conversationHistory as { id, title, synopsis }}
            <button
              class="button is-dark is-fullwidth is-justify-content-flex-start history-item"
              on:click={() => console.log("Selected conversation:", id)}
            >
              <div class="has-text-left">
                <strong>{title}</strong><br />
                <small class="has-text-grey">{synopsis}</small>
              </div>
            </button>
          {/each}
        </div>
      </section>
      <footer class="modal-card-foot">
        <hr />
      </footer>
    </div>
  </div>
{/if}

<style>
  html,
  body {
    margin: 0;
    padding: 0;
    height: 100%;
  }

  .chat-wrapper {
    display: flex;
    flex-direction: column;
    height: 100%;
    min-height: 0;
  }

  .box.chat-box {
    padding-bottom: 130px; /* matches .chat-form height */
    display: flex;
    flex-direction: column;
    align-items: flex-start;
  }

  .chat-container {
    position: fixed;
    top: 4rem;
    bottom: 0;
    left: 0;
    right: 0;
    overflow-y: auto;
  }

  .chat-form {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background: #5e1515;
    border-top: 1px solid #d90000;
    border-radius: 1rem 1rem 0 0;
    padding: 1rem;
    z-index: 100;
    box-shadow: 0 -4px 10px rgba(0, 0, 0, 0.25);
  }

  .user-message {
    align-self: flex-end;
    background-color: #209cee;
    color: white;
    padding: 0.75rem 1rem;
    border-radius: 1rem;
    max-width: 70%;
    word-wrap: break-word;
    margin: 0.25rem 0;
    border-bottom-right-radius: 0;
    white-space: pre-wrap;
  }

  .assistant-message {
    width: 100%;
    max-width: 100%;
    word-wrap: break-word;
    white-space: pre-wrap;
    margin: 0.5rem 0;
  }

  textarea.textarea {
    font-family: inherit;
    line-height: 1.4;
    resize: none;
    overflow: hidden;
    max-height: 30vh;
    width: 100%;
  }

  .scroll-to-bottom {
    position: fixed;
    bottom: 6.5rem; /* adjust to hover just above .chat-form */
    right: 1.5rem;
    background: #209cee;
    color: white;
    border: none;
    border-radius: 50%;
    padding: 0.5rem 0.6rem;
    font-size: 1.5rem;
    cursor: pointer;
    z-index: 150;
    box-shadow: 0 0 10px rgba(0, 0, 0, 0.4);
    transition: opacity 0.2s ease;
  }

  .scroll-to-bottom:hover {
    background: #1075c2;
  }

  .menu .modal-card-body {
    max-height: 75%;
  }

  .history-item {
    text-align: left;
    user-select: none;
    white-space: normal;
    padding: 0.75rem 1rem;
  }

  .modal-card-foot {
    padding: 0;
    max-height: 1em;
  }

  :global(.markdown-body) {
    line-height: 1.6;
    word-break: break-word;
    color: #e0e0e0;
    font-size: 1rem;
  }

  :global(.markdown-body h1) {
    font-size: 2rem;
    font-weight: bold;
    margin: 1.5rem 0 1rem;
    border-bottom: 1px solid #444;
    padding-bottom: 0.3rem;
  }

  :global(.markdown-body h2) {
    font-size: 1.5rem;
    font-weight: bold;
    margin: 1.25rem 0 0.75rem;
    border-bottom: 1px solid #444;
    padding-bottom: 0.25rem;
  }

  :global(.markdown-body h3) {
    font-size: 1.25rem;
    font-weight: bold;
    margin: 1rem 0 0.5rem;
  }

  :global(.markdown-body p) {
    white-space: normal;
    word-break: normal;
    overflow-wrap: break-word;
  }

  :global(.markdown-body ul) {
    list-style-type: disc;
  }

  :global(.markdown-body ol) {
    list-style-type: decimal;
  }

  :global(.markdown-body ul),
  :global(.markdown-body ol) {
    margin: 1em 0 1em 1.5em;
    padding-left: 1.25em;
  }

  :global(.markdown-body li) {
    margin: 0.1em 0;
    line-height: 1;
    display: list-item;
    white-space: normal;
    word-break: normal;
    overflow-wrap: break-word;
  }

  :global(.markdown-body blockquote) {
    border-left: 4px solid #666;
    padding-left: 1em;
    color: #aaa;
    font-style: italic;
    margin: 1em 0;
  }

  :global(.markdown-body pre) {
    background: #151111;
    padding: 1rem;
    border-radius: 0.5rem;
    overflow-x: auto;
    margin: 1em 0;
  }

  :global(.markdown-body code) {
    padding: 0.25em 0.5em;
    border-radius: 4px;
    font-family: monospace;
    font-size: 0.95em;
  }

  :global(.markdown-body table) {
    width: 100%;
    border-collapse: collapse;
    margin: 1.5rem 0;
    font-size: 0.95rem;
    background-color: #1e1e1e;
    color: #e0e0e0;
    border: 1px solid #444;
    border-radius: 0.5rem;
    overflow: hidden;
  }

  :global(.markdown-body thead) {
    background-color: #2a2a2a;
    font-weight: bold;
  }

  :global(.markdown-body thead th),
  :global(.markdown-body tbody td) {
    padding: 0.75rem 1rem;
    border-bottom: 1px solid #444;
    text-align: left;
  }

  :global(.markdown-body tbody tr:last-child td) {
    border-bottom: none;
  }

  :global(.markdown-body tbody tr:nth-child(even)) {
    background-color: #252525;
  }

  :global(.markdown-body tbody tr:hover) {
    background-color: #333;
  }

  :global(.markdown-body th),
  :global(.markdown-body td) {
    vertical-align: top;
    white-space: normal;
    word-break: normal;
    overflow-wrap: break-word;
  }

  :global(.markdown-body table caption) {
    caption-side: top;
    text-align: left;
    font-weight: bold;
    margin-bottom: 0.5rem;
    color: #ccc;
  }
</style>
