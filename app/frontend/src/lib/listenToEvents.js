// src/lib/events/listenToEvents.js
import {
  currentContext,
  dockerContexts,
  userIsLoggedOut,
  agentViewState,
  conversationId,
  conversationTitle,
  terminalSessionState,
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
      /** @type {{ page: string }} */
      const payload = JSON.parse(event.data);
      //console.log("open_app", payload.page);
      agentViewState.set(1);
      switch (payload.page) {
      case "settings":
        goto("/settings");
        break;
      case "docker":
        goto("/docker");
        break;
      case "projects":
        goto("/projects");
        break;
      case "config":
        goto("/config");
        break;
      case "repository":
        goto("/repository");
        break;
      case "workstation":
        goto("/workstation");
        break;
      case "instances":
        goto(`/instances?app=${payload.app}`);
        break;
      default:
        console.error("Unknown page", payload.page);
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
  }, 3000);

  return () => {
    source.close();
  };
}
