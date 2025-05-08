export const ssr = false;
export const prerender = true;
export const trailingSlash = "always";
import { currentContext } from "$lib/stores";

// async function getDockerContexts(fetch) {
//     let res = await fetch('/api/docker_context/');
//     if (!res.ok) throw new Error('failed to fetch docker contexts.')
//     return await res.json();
// }

/** @type {import('./$types').LayoutServerLoad} */
export async function load({ fetch }) {
  //const docker_contexts = await getDockerContexts(fetch);
}
