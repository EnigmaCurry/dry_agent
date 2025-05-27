export const ssr = false;
export const prerender = true;
export const trailingSlash = "always";
import { currentContext, dockerContexts } from "$lib/stores";

async function getDockerContextDefault(fetch) {
  let res = await fetch("/api/docker_context/default");
  if (!res.ok) throw new Error("failed to fetch default docker context.");
  return await res.json();
}

async function getDockerContexts(fetch) {
  let res = await fetch("/api/docker_context/");
  if (!res.ok) throw new Error("failed to fetch docker contexts.");
  return await res.json();
}

/** @type {import('./$types').LayoutServerLoad} */
export async function load({ fetch }) {
  dockerContexts.set(await getDockerContexts(fetch));
  currentContext.set((await getDockerContextDefault(fetch)).default_context);
}
