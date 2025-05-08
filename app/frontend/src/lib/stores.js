// src/lib/stores.js
import { writable } from "svelte/store";

export const currentContext = writable(null);
export const dockerContexts = writable([]);
export const conversationId = writable(null);
export const isPaneDragging = writable(false);
export const isLandscape = writable(true);

export const agentSizePercent = writable(null);
export const appSizePercent = writable(null);
export const userCurrentWorkingDirectory = writable(null);
export const userIsLoggedOut = writable(false);

export const userSplitSizePercent = persisted('userSplitSizePercent', null)
export const agentViewState = persisted('agentViewState', 0);

export const terminalFontSize = persisted('terminalFontSize', 14);

/**
 * Create a writable store that persists to localStorage under `key`.
 * @param {string} key - localStorage key
 * @param {any} initialValue - fallback initial value
 */
function persisted(key, initialValue) {
  // Try to get from localStorage; fall back to initialValue
  let storedValue;
  try {
    const json = localStorage.getItem(key);
    storedValue = json === null ? initialValue : JSON.parse(json);
  } catch {
    storedValue = initialValue;
  }

  const store = writable(storedValue);

  // Subscribe and write any changes back to localStorage
  store.subscribe((value) => {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch {
      // quota exceeded or private mode: silently fail
    }
  });

  return store;
}


export async function refreshDockerContexts() {
  try {
    const res = await fetch("/api/docker_context/");
    if (res.ok) {
      const data = await res.json();
      dockerContexts.set(data);
    } else {
      dockerContexts.set([]);
    }
  } catch (err) {
    dockerContexts.set([]);
  }
}
