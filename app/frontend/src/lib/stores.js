// src/lib/stores.js
import { writable } from "svelte/store";

export const currentContext = writable(null);
export const dockerContexts = writable([]);

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
