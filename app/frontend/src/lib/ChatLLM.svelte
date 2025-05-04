<script>
  import { onMount, tick } from "svelte";
  import Markdown from "svelte-exmarkdown";
  import {
    currentContext,
    dockerContexts,
    conversationId as convoIdStore,
  } from "$lib/stores";
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

  let sidebarOpen = $state(false);
  let conversationTitle = $state("");

  let conversationId = $state(null);
  let messages = $state([]);
  let input = $state("");
  let loading = $state(false);
  let isNew = $state(true);
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
    const idParam = params.get("id");
    if (idParam) {
      // 1) URL says “?id=…” → load that
      await loadConversation(idParam);
    } else {
      // 2) no URL → see if our store already has one
      const stored = get(convoIdStore);
      if (stored) {
        await loadConversation(stored);
      } else {
        newConversation();
      }
    }
    // now load your history (for the sidebar), then do your usual focus/scroll/tick magic
    await fetchConversations();
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
      } else {
        hasMoreConversations = false;
      }
    } catch {
      console.error("Error loading conversations");
    } finally {
      loadingConversations = false;
    }
  }

  function newConversation() {
    messages = [];
    conversationId = crypto.randomUUID();
    conversationTitle = "New Conversation";
    isNew = true;
    convoIdStore.set(null);
    // drop the `id` param from the URL
    const u = new URL(window.location.href);
    u.searchParams.delete("id");
    window.history.pushState({}, "", u);
    // reset focus/scroll if you like
    inputElement?.focus();
    scrollToBottom();
  }

  async function loadConversation(id) {
    if (loading) return;
    loading = true;

    try {
      const res = await fetch(`/api/chat/conversation/${id}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      const data = await res.json();
      messages = data.messages || [];
      conversationTitle = data.title ?? "Untitled";
      conversationId = id;

      // Update URL without reloading
      const u = new URL(window.location.href);
      u.searchParams.set("id", id);
      window.history.pushState({}, "", u);
      isNew = false;
    } catch (err) {
      console.error("Failed loading conversation", err);
    } finally {
      loading = false;
    }
  }

  async function deleteConversation(id) {
    try {
      const res = await fetch(`/api/chat/conversation/${id}`, {
        method: "DELETE",
      });
      if (!res.ok)
        throw new Error(`Failed to delete conversation: ${res.status}`);

      conversationHistory = conversationHistory.filter((c) => c.id !== id);

      if (id === conversationId) {
        newConversation();
      }
    } catch (e) {
      console.error("Error deleting conversation:", e);
      alert("Failed to delete conversation.");
    }
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
      const storedId = get(convoIdStore);
      loading = false;
      controller = null;
      const u = new URL(window.location.href);
      if (!u.searchParams.get("id")) {
        // New conversation saved
        u.searchParams.set("id", conversationId);
        window.history.replaceState({}, "", u);
        conversationHistory = [];
        currentHistoryPage = 1;
        hasMoreConversations = true;
        convoIdStore.set(conversationId);
        await fetchConversations();
        await updateTitle();
      } else if (conversationId != storedId) {
        // Saved existing conversation that wasn't the last one we saved to
        convoIdStore.set(conversationId);
        conversationHistory = [];
        currentHistoryPage = 1;
        hasMoreConversations = true;
        await fetchConversations();
      }
    }
  }

  async function updateTitle() {
    if (conversationId != null) {
      try {
        const res = await fetch(`/api/chat/conversation/${conversationId}`);
        if (res.ok) {
          const data = await res.json();
          conversationTitle = data.title;
        }
      } catch (e) {
        console.error("Failed to fetch conversation title:", e);
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
  <!-- Sidebar -->
  <aside class="sidebar" class:collapsed={!sidebarOpen}>
    <div class="sidebar-header">
      <button
        class="button is-link m-2 is-pulled-right"
        on:click={newConversation}
      >
        New Conversation
      </button>
    </div>
    <div
      class="sidebar-body"
      on:scroll={(e) => {
        const el = e.target;
        if (el.scrollTop + el.clientHeight >= el.scrollHeight - 50)
          fetchConversations();
      }}
    >
      {#each conversationHistory as { id, title, preview, modified_at }}
        <div class="sidebar-item-wrapper">
          <button
            class="button is-fullwidth sidebar-item"
            on:click={() => loadConversation(id)}
            disabled={loading}
          >
            <div>
              <strong>{title}</strong><br />
              <small class="has-text-grey">{preview}</small><br />
              <small class="has-text-grey is-size-7">
                {getRelativeTime(modified_at)}
              </small>
            </div>
          </button>
          <button
            class="delete-button mr-2"
            on:click={() => deleteConversation(id)}
            title="Delete conversation"
          >
            ✕
          </button>
        </div>
      {/each}
      {#if loadingConversations}
        <div class="has-text-centered has-text-grey mt-2">Loading…</div>
      {/if}
    </div>
  </aside>

  <!-- Main area -->
  <main class="main-content" class:expanded={!sidebarOpen}>
    <!-- Separate toggle, own blur wrapper -->
    <button class="sidebar-toggle" on:click={toggleSidebar}>
      {#if sidebarOpen}◀{:else}☰{/if}
    </button>

    <!-- Shifting blur + title -->
    <div class="top-bar" style:left={sidebarOpen ? "300px" : "2rem"}>
      {#if conversationTitle}
        <div class="chat-header">
          {#if !isNew}
            {conversationTitle}
          {/if}
        </div>
      {/if}
    </div>

    <!-- Chat messages container -->
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
      {#if loading}
        <div class="mt-4 assistant-message loading-message">
          Assistant is typing...
        </div>
      {/if}
      <div bind:this={scrollAnchor}></div>
    </div>

    <!-- Scroll‐to‐bottom button -->
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

    <!-- Input form -->
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
          <button class="button is-link" type="submit" disabled={loading}>
            Send
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
  </main>
</div>

<style>
  .chat-wrapper {
    posotion: relative;
    display: flex;
    flex-grow: 1;
    overflow: hidden;
  }

  aside.sidebar {
    display: flex;
    flex-direction: column;
    width: 300px;
    background: #222;
    color: #fff;
    padding: 0;
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
  }
  .sidebar-header button {
    z-index: 210;
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

  .sidebar-item-wrapper {
    position: relative;
  }

  .sidebar-item-wrapper .delete-button {
    position: absolute;
    top: 0.4rem;
    right: 0.4rem;
    background: transparent;
    border: none;
    color: #b58690;
    font-weight: bold;
    font-size: 1.2rem;
    cursor: pointer;
    z-index: 5;
  }

  .sidebar-item-wrapper .delete-button:hover {
    color: #ff3860;
  }

  .main-content {
    flex: 1;
    overflow: hidden;
    transition: margin-left 0.3s ease;
  }
  .main-content.expanded {
    margin-left: 0;
  }

  .top-bar {
    position: absolute;
    top: 4rem;
    height: 4rem;
    right: 0;
    left: var(--top-bar-left);
    backdrop-filter: blur(4px);
    z-index: 200;
    margin-right: 1em;
    mask-image: linear-gradient(
      to bottom,
      black 0%,
      black 50%,
      transparent 100%
    );
    -webkit-mask-image: linear-gradient(
      to bottom,
      black 0%,
      black 50%,
      transparent 100%
    );
  }

  .sidebar-toggle {
    position: absolute;
    top: 1rem;
    left: 1rem;
    z-index: 210;
    background: none;
    backdrop-filter: blur(4px);
    border: none;
    color: #e0e0e0;
    padding: 0.5rem;
    border-radius: 0.5rem;
    mask-image: linear-gradient(
      to bottom,
      black 0%,
      black 50%,
      transparent 100%
    );
    -webkit-mask-image: linear-gradient(
      to bottom,
      black 0%,
      black 50%,
      transparent 100%
    );
  }

  .chat-header {
    position: absolute;
    top: 0;
    left: 1rem;
    padding: 0.75rem 1rem;
    color: #e0e0e0;
    font-size: 1.25rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    z-index: 201;
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
    overflow-y: auto;
    padding-top: 3rem;
  }
  .chat-form {
    position: absolute;
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
    position: absolute;
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
  :global(.assistant-message p) {
    padding: 0 0 1em 0;
  }
  :global(.assistant-message ul) {
    list-style: disc;
    padding-bottom: 0.5em;
    margin-left: 1.5em;
  }
  :global(.assistant-message ol) {
    list-style: integer;
    padding-bottom: 0.5em;
    margin-left: 1.5em;
  }

  :global(.markdown-body table),
  :global(.markdown-body thead),
  :global(.markdown-body tbody),
  :global(.markdown-body tfoot),
  :global(.markdown-body tr),
  :global(.markdown-body th),
  :global(.markdown-body td) {
    margin: 0;
    padding: 0;
    border: 0;
    font: inherit;
    vertical-align: top;
    border-collapse: collapse;
    border-spacing: 0;
  }

  :global(.markdown-body table) {
    width: 100%;
    border-collapse: collapse;
    background-color: #1e1e1e;
    color: #e0e0e0;
  }

  :global(.markdown-body thead) {
    background-color: #2a2a2a;
  }

  :global(.markdown-body th) {
    text-align: left;
    padding: 0.75rem;
    font-weight: bold;
    border-bottom: 1px solid #444;
  }

  :global(.markdown-body td) {
    padding: 0.75rem;
    border-bottom: 1px solid #333;
  }

  :global(.markdown-body tbody tr:nth-child(odd)) {
    background-color: #1e1e1e;
  }

  :global(.markdown-body tbody tr:nth-child(even)) {
    background-color: #2b2b2b;
  }

  :global(.markdown-body tbody tr:hover) {
    background-color: #3a3a3a;
  }
</style>
