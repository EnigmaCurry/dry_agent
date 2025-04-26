/** @type {import('./$types').PageLoad} */
export async function load({ fetch }) {
  try {
    const res = await fetch('/api/d.rymcg.tech/config');
    if (res.status === 404) {
      return {
        configExists: false
      };
    }
    if (!res.ok) {
      throw new Error(`Unexpected error: ${res.status}`);
    }

    const config = await res.json();
    return {
      configExists: true,
      config
    };
  } catch (error) {
    console.error("Failed to load config:", error);
    return {
      configExists: false,
      error: error.message
    };
  }
}
