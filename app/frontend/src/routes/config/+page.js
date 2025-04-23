// @ts-check

/** @type {import('./$types').PageLoad} */
export async function load({ fetch }) {
  const res = await fetch('/api/d.rymcg.tech/config');
  const status = res.status;
  const json = await res.json();

  if (res.ok) {
    return {
      status,
      context: json.detail.context,
      config_path: json.detail.config_path
    };
  } else if (status == 404) {
    return {
      status,
      context: json.detail.context,
      config_path: null
    };
  } else {
    return {
      status,
      error: json.detail
    }
  }
}


