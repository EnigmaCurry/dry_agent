// src/lib/events/listenToEvents.js
import {
  currentContext,
  dockerContexts,
  userIsLoggedOut,
  agentViewState,
  conversationId,
  conversationTitle,
  terminalSessionState,
  eventSourceConnected
} from "$lib/stores";
import { goto } from "$app/navigation";
import { get } from "svelte/store";
import { tick } from "svelte";

/**
 * Starts listening to server-sent events from the backend.
 * Currently handles Docker context changes and updates the Svelte store.
 *
 * @returns {() => void} A cleanup function to close the EventSource connection.
 */
export function listenToServerEvents() {
  setTimeout(() => {
    const source = new EventSource("/api/events/");

    source.onopen = () => {
      console.log("SSE connection established");
      eventSourceConnected.set(true);
    };

    source.onerror = (err) => {
      console.error("SSE connection lost", err);
      eventSourceConnected.set(false);
    };

    source.addEventListener("context_changed", (event) => {
      /** @type {{ new_context: string }} */
      const payload = JSON.parse(event.data);
      console.log("context_changed", payload);
      currentContext.set(payload.new_context);
    });

    source.addEventListener("context_list", (event) => {
      /** @type {{ new_context: string }} */
      const payload = JSON.parse(event.data);
      //console.log("context_list", payload);
      dockerContexts.set(payload.contexts);
    });

    source.addEventListener("logout", (event) => {
      console.log("logout");
      userIsLoggedOut.set(true);
      window.location.reload();
    });

    source.addEventListener("open_app", (event) => {
      /** @type {{ page: string, app?: string }} */
      const payload = JSON.parse(event.data);
      if (get(agentViewState) === 0)
        // If agent is fullscreen, set split view:
        agentViewState.set(1);

      let targetPath;
      switch (payload.page) {
      case "settings":
        targetPath = "/settings";
        break;
      case "docker":
        targetPath = "/docker";
        break;
      case "projects":
        targetPath = "/projects";
        break;
      case "config":
        targetPath = "/config";
        break;
      case "repository":
        targetPath = "/repository";
        break;
      case "workstation":
        targetPath = "/workstation";
        break;
      case "instances":
        targetPath = `/instances?app=${payload.app}`;
        break;
      default:
        console.error("Unknown page", payload.page);
        return;
      }

      function normalizePathWithSearch(url) {
        const path = url.pathname.endsWith("/") && url.pathname !== "/"
          ? url.pathname.slice(0, -1)
          : url.pathname;
        return path + url.search;
      }

      const current = new URL(window.location.href);
      const target = new URL(targetPath, current.origin);

      if (normalizePathWithSearch(current) !== normalizePathWithSearch(target)) {
        goto(targetPath);
      }
    });

    source.addEventListener("open_instances", (event) => {
      /** @type {{ page: string }} */
      const payload = JSON.parse(event.data);
      //console.log("open_instances", payload.app);
      agentViewState.set(1);
      goto(`/instances?app=${payload.app}`);
    });

    source.addEventListener("open_url", (event) => {
      /** @type {{ page: string }} */
      const payload = JSON.parse(event.data);
      //console.log("open_url", payload.url);
      window.open(payload.url, '_blank');
    });

    source.addEventListener("conversation_updated", async (event) => {
      /** @type {{ page: string }} */
      const payload = JSON.parse(event.data);
      //console.log("conversation_updated", payload);
      conversationId.set(payload.conversation_id);
      conversationTitle.set(payload.title);
    });

    source.addEventListener("tmux_session_changed", async (event) => {
      /** @type {{ page: string }} */
      const payload = JSON.parse(event.data);
      console.log("tmux_session_changed", payload);
      terminalSessionState.set(payload);
    });

    source.onerror = (err) => {
      console.error("SSE connection lost", err);
    };
    listenToServerEvents._source = source;
  }, 3000);

  return () => {
    listenToServerEvents._source?.close();
    eventSourceConnected.set(false);
  };
}
