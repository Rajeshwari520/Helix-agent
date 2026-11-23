// Small fetch wrapper: throws an Error with the API's "detail" message on 4xx/5xx.
export async function api(method, url, body) {
  const r = await fetch(url, {
    method,
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!r.ok) {
    let msg = `${r.status} ${r.statusText}`;
    try {
      const j = await r.json();
      msg = typeof j.detail === "string" ? j.detail : (j.detail || []).map((d) => d.msg).join("; ") || msg;
    } catch (e) { /* not JSON */ }
    throw new Error(msg);
  }
  return r.status === 204 ? null : r.json();
}

export const get = (url) => api("GET", url);
export const post = (url, body) => api("POST", url, body);
export const patch = (url, body) => api("PATCH", url, body);
