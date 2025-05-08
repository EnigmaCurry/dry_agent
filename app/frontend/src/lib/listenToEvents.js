// src/lib/events/listenToEvents.js
import { currentContext, dockerContexts } from "$lib/stores";
import { get } from "svelte/store";

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
      //console.log("context_changed", payload);
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
      window.location.reload();
    });

    source.onerror = (err) => {
      console.error("SSE connection lost", err);
    };
  }, 3000);

  // return () => {
  //   source.close();
  // };
  return () => {

  };
}
