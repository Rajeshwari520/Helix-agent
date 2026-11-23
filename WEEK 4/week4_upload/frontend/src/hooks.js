import { useCallback, useEffect, useState } from "react";
import { store } from "./util.js";

// Route from the URL: #/tickets/TCK-0001 -> ticket page, #/dashboard or /dashboard -> dashboard, else queue.
function readRoute() {
  const h = location.hash;
  const m = h.match(/^#\/tickets\/([A-Za-z0-9-]+)/);
  if (m) return { page: "ticket", id: decodeURIComponent(m[1]) };
  if (h.startsWith("#/dashboard")) return { page: "dashboard" };
  if (h.startsWith("#/backend")) return { page: "backend" };
  if (h.startsWith("#/")) return { page: "queue" };
  return { page: location.pathname.startsWith("/dashboard") ? "dashboard" : "queue" };
}

export function useRoute() {
  const [route, setRoute] = useState(readRoute);
  useEffect(() => {
    const on = () => { setRoute(readRoute()); window.scrollTo(0, 0); };
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);
  return route;
}

export function useStored(key, initial) {
  const [value, setValue] = useState(() => store.get(key, initial));
  useEffect(() => { store.set(key, value); }, [key, value]);
  return [value, setValue];
}

// Loads data; reload() fetches again. Keeps the old data while reloading.
export function useLoad(loader, deps) {
  const [state, setState] = useState({ data: null, error: null, loading: true });
  const run = useCallback(() => {
    setState((s) => ({ ...s, loading: true }));
    return loader().then(
      (data) => setState({ data, error: null, loading: false }),
      (error) => setState((s) => ({ ...s, error, loading: false })),
    );
  }, deps); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { run(); }, [run]);
  return { ...state, reload: run };
}
