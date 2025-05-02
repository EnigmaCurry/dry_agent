<script>
  import { onMount, tick } from "svelte";
  import Markdown from "svelte-exmarkdown";
  import { currentContext, dockerContexts } from "$lib/stores";
  import { get } from "svelte/store";

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
  import rehypeHighlight from "rehype-highlight";
  import "highlight.js/styles/github-dark.css";

  let sidebarOpen = $state(true);
  let conversationTitle = $state("");

  let conversationId = $state(null);
  let messages = $state([]);
  let input = $state("");
  let loading = $state(false);
  let controller;
  let scrollAnchor;
  let inputElement;
  let isAtBottom = $state(true);
  let showScrollButton = $state(false);
  let chatContainer;
  let scrollTimeout;
  let lockScroll = $state(false);

  let conversationHistory = $state([]);
  let currentHistoryPage = $state(1);
  let hasMoreConversations = $state(true);
  let loadingConversations = $state(false);

  const AUTO_SCROLL_THRESHOLD = 10;
  const SCROLL_BUTTON_DISPLAY_THRESHOLD = 100;

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

  function toggleSidebar() {
    sidebarOpen = !sidebarOpen;
    if (sidebarOpen) fetchConversations();
  }

  onMount(async () => {
    const params = new URLSearchParams(window.location.search);
    const id = params.get("id");
    conversationId = id || crypto.randomUUID();
    if (id) {
      try {
        const res = await fetch(`/api/chat/conversation/${id}`);
        if (!res.ok) throw new Error(res.status);
        const data = await res.json();
        messages = data.messages || [];
      } catch {
        messages = [];
      }
    }
    await fetchConversations();
    updateTitle();
    await tick();
    adjustTextareaHeight();
    inputElement?.focus();
    scrollToBottom();
  });

  // handle browser back/forward
  onMount(() => {
    window.addEventListener("popstate", () => {
      const params = new URLSearchParams(window.location.search);
      const id = params.get("id");
      if (id) loadConversation(id);
    });
  });

  // Fetch and append conversation list pages
  async function fetchConversations() {
    if (loadingConversations || !hasMoreConversations) return;
    loadingConversations = true;
    try {
      const res = await fetch(
        `/api/chat/conversations?page=${currentHistoryPage}&page_size=10`,
      );
      const json = await res.json();
      if (json.conversations.length) {
        conversationHistory = [...conversationHistory, ...json.conversations];
        currentHistoryPage++;
        updateTitle();
      } else {
        hasMoreConversations = false;
      }
    } catch {
      console.error("Error loading conversations");
    } finally {
      loadingConversations = false;
    }
  }

  async function loadConversation(id) {
    if (loading) return;
    loading = true;
    try {
      const res = await fetch(`/api/chat/conversation/${id}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      messages = data.messages || [];
      conversationId = id;
      updateTitle(); // re-compute conversationTitle
      // update the URL without a reload
      const u = new URL(window.location.href);
      u.searchParams.set("id", id);
      window.history.pushState({}, "", u);
    } catch (err) {
      console.error("Failed loading conversation", err);
    } finally {
      loading = false;
    }
  }

  // Update the displayed title when history loads
  function updateTitle() {
    const found = conversationHistory.find((c) => c.id === conversationId);
    conversationTitle = found ? found.title : "";
  }

  function getRelativeTime(ts) {
    const now = Date.now();
    const then = Date.parse(ts + "Z");
    const delta = Math.floor((now - then) / 1000);
    const rtf = new Intl.RelativeTimeFormat("en", { numeric: "auto" });
    const units = [
      [60, "seconds", 1],
      [3600, "minutes", 60],
      [86400, "hours", 3600],
      [604800, "days", 86400],
      [2629800, "weeks", 604800],
      [31557600, "months", 2629800],
      [Infinity, "years", 31557600],
    ];
    for (const [limit, unit, div] of units)
      if (delta < limit) return rtf.format(-Math.floor(delta / div), unit);
  }

  function handleScroll() {
    clearTimeout(scrollTimeout);
    scrollTimeout = setTimeout(() => {
      const pos = chatContainer.scrollTop + chatContainer.clientHeight;
      const dist = chatContainer.scrollHeight - pos;
      isAtBottom = dist < AUTO_SCROLL_THRESHOLD;
      showScrollButton = dist >= SCROLL_BUTTON_DISPLAY_THRESHOLD;
    }, 100);
  }

  async function send() {
    if (!input.trim()) return;
    messages = [
      ...messages,
      { role: "user", content: input },
      { role: "assistant", content: "" },
    ];
    const idx = messages.length - 1;
    input = "";
    await tick();
    adjustTextareaHeight();
    loading = true;
    controller = new AbortController();
    try {
      const res = await fetch(`/api/chat/stream/${conversationId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: messages[idx - 1].content }),
        signal: controller.signal,
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const reader = res.body.getReader();
      const dec = new TextDecoder();
      await tick();
      scrollToBottom();
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        messages[idx].content += dec.decode(value);
        if (isAtBottom) scrollToBottom();
      }
    } catch (e) {
      messages[idx].content +=
        e.name === "AbortError" ? "\n\n_⛔️ Stopped_" : `\n\n❌ ${e.message}`;
      messages[idx].is_error = true;
    } finally {
      loading = false;
      controller = null;
      const u = new URL(window.location.href);
      if (!u.searchParams.get("id")) {
        u.searchParams.set("id", conversationId);
        window.history.replaceState({}, "", u);
        conversationHistory = [];
        currentHistoryPage = 1;
        hasMoreConversations = true;
        await fetchConversations();
      }
    }
  }

  function stop() {
    controller?.abort();
  }
  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  }
  function adjustTextareaHeight() {
    if (!inputElement) return;
    inputElement.style.height = "auto";
    const maxH = window.innerHeight * 0.3;
    inputElement.style.height =
      Math.min(inputElement.scrollHeight, maxH) + "px";
  }
  function scrollToBottom() {
    lockScroll = true;
    scrollAnchor?.scrollIntoView({ behavior: "smooth" });
    setTimeout(() => (lockScroll = false), 300);
  }

  $effect(() => {
    const obs = new MutationObserver(addClipboardButtons);
    const cb = document.querySelector(".chat-box");
    if (cb) obs.observe(cb, { childList: true, subtree: true });
    tick().then(addClipboardButtons);
    return () => obs.disconnect();
  });
  function addClipboardButtons() {
    document.querySelectorAll(".assistant-message pre code").forEach((code) => {
      const pre = code.parentElement;
      if (pre.querySelector(".copy-button")) return;
      const btn = document.createElement("button");
      btn.textContent = "📋";
      btn.className = "copy-button is-size-5";
      btn.onclick = () =>
        navigator.clipboard.writeText(code.innerText).then(() => {
          btn.textContent = "✅";
          setTimeout(() => (btn.textContent = "📋"), 1000);
        });
      pre.style.position = "relative";
      pre.appendChild(btn);
    });
  }
</script>

<div class="chat-wrapper">
  <button class="button sidebar-toggle" on:click={toggleSidebar}>
    {#if sidebarOpen}❌{:else}☰{/if}
  </button>

  <aside class="sidebar" class:collapsed={!sidebarOpen}>
    <div class="sidebar-header">
      <button
        class="button is-link mt-1 is-pulled-right"
        on:click={() => (window.location.href = "/agent/")}
        >New Conversation</button
      >
    </div>
    <div
      class="sidebar-body"
      on:scroll={(e) => {
        const el = e.target;
        if (el.scrollTop + el.clientHeight >= el.scrollHeight - 50)
          fetchConversations();
      }}
    >
      {#each conversationHistory as { id, title, preview, created_at }}
        <button
          class="button is-fullwidth sidebar-item"
          on:click={() => loadConversation(id)}
          disabled={loading}
        >
          <div>
            <strong>{title}</strong><br />
            <small class="has-text-grey">{preview}</small><br />
            <small class="has-text-grey is-size-7">
              {getRelativeTime(created_at)}
            </small>
          </div>
        </button>
      {/each}
      {#if loadingConversations}
        <div class="has-text-centered has-text-grey mt-2">Loading…</div>
      {/if}
    </div>
  </aside>

  <main class="main-content" class:expanded={!sidebarOpen}>
    <!-- Conversation title -->
    {#if conversationTitle}
      <div class="chat-header" style:left={sidebarOpen ? "16rem" : "2rem"}>
        {conversationTitle}
      </div>
    {/if}

    <div
      class="box chat-box chat-container"
      style:left={sidebarOpen ? "300px" : "0px"}
      on:scroll={handleScroll}
      bind:this={chatContainer}
    >
      {#each messages as message, idx (idx)}
        {#if message.role === "user"}
          <div class="user-message">{message.content}</div>
        {:else if message.role === "assistant"}
          {#if message.is_error}
            <div class="notification is-danger" data-msg-index={idx}>
              {message.content}
            </div>
          {:else}
            <div class="assistant-message markdown-body" data-msg-index={idx}>
              <Markdown md={message.content} plugins={markdownPlugins} />
            </div>
          {/if}
        {/if}
      {/each}
      {#if loading}<div class="mt-4 assistant-message loading-message">
          Assistant is typing...
        </div>{/if}
      <div bind:this={scrollAnchor}></div>
    </div>
    {#if showScrollButton}<button
        class="scroll-to-bottom"
        type="button"
        on:click={scrollToBottom}
        aria-label="Scroll to bottom">⬇️</button
      >{/if}
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
            style="resize:none;overflow:hidden"
          />
        </div>
        <div class="control">
          <button class="button is-link" type="submit" disabled={loading}
            >Send</button
          >
        </div>
        {#if loading}<div class="control">
            <button class="button is-danger" type="button" on:click={stop}
              >Stop</button
            >
          </div>{/if}
      </div>
    </form>
  </main>
</div>

<style>
  .chat-wrapper {
    display: flex;
    height: 100vh;
    overflow: hidden;
    margin: -3.25rem 0 0 -3.25rem;
  }
  .sidebar-toggle {
    position: fixed;
    top: 4.25rem;
    left: 1rem;
    z-index: 200;
  }
  aside.sidebar {
    display: flex;
    flex-direction: column;
    width: 300px;
    background: #222;
    color: #fff;
    padding: 1rem;
    overflow-y: auto;
    transition: width 0.3s ease;
  }
  .sidebar.collapsed {
    width: 0;
    padding: 0;
    overflow: hidden;
  }
  .sidebar-header {
    margin: 0 0 1rem 0;
    position: sticky;
    top: 0;
    background: #222;
    z-index: 10;
    padding-bottom: 1rem;
  }
  .sidebar-body {
    flex: 1;
    overflow-y: auto;
    margin: 0 0 7rem 0;
  }
  .sidebar-body .button div {
    width: 100%;
  }
  .sidebar-item {
    text-align: left;
    margin-bottom: 0.5rem;
    white-space: normal;
  }
  .main-content {
    flex: 1;
    overflow: hidden;
    transition: margin-left 0.3s ease;
  }
  .main-content.expanded {
    margin-left: 0;
  }
  .chat-header {
    position: absolute;
    top: 1rem;
    left: 1rem;
    right: 0;
    height: 3rem;
    padding: 0.75rem 1rem;
    color: #e0e0e0;
    font-size: 1.25rem;
    z-index: 50;
    backdrop-filter: blur(4px);
    background: none;
    width: fit-content;
    max-width: 75%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  html,
  body {
    margin: 0;
    padding: 0;
    height: 100%;
  }
  .box.chat-box {
    padding-bottom: 130px;
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    padding-left: 3rem;
  }
  .chat-container {
    position: fixed;
    top: 4rem; /* navbar height */
    bottom: 0;
    left: 0;
    right: 0;
    overflow-y: auto;
    padding-top: 3rem; /* equal to chat-header height */
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
    bottom: 6.5rem;
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
  :global(.assistant-message pre) {
    position: relative;
    padding-top: 2.2rem;
  }
  :global(.assistant-message .copy-button) {
    position: absolute;
    top: 0.6rem;
    right: 0.8rem;
    background: #444;
    color: white;
    border: none;
    cursor: pointer;
    padding: 0.3rem 0.5rem;
    font-size: 0.8rem;
    border-radius: 4px;
    opacity: 0.6;
    transition: opacity 0.2s ease;
    z-index: 10;
  }
  :global(.assistant-message .copy-button:hover) {
    opacity: 1;
  }
  :global(.markdown-body) {
    line-height: 1.6;
    word-break: break-word;
    color: #e0e0e0;
    font-size: 1rem;
  }
</style>
