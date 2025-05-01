// src/lib/events/listenToEvents.js
import { currentContext } from "$lib/stores";

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
      currentContext.set(payload.new_context);
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
