/** @type {import('./$types').PageLoad} */
export async function load({ url }) {
  return {
    tab: url.searchParams.get("tab") || "session",
  };
}
