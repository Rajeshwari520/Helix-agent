import { createContext, useContext, useEffect, useRef } from "react";
import { useRoute, useStored } from "./hooks.js";
import { ToastProvider, useToast } from "./components/Toast.jsx";
import Queue from "./pages/Queue.jsx";
import Ticket from "./pages/Ticket.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Backend from "./pages/Backend.jsx";

// Who is working (stored with every decision) and which SLA clock to use.
const SessionContext = createContext(null);
export const useSession = () => useContext(SessionContext);

function Shell() {
  const route = useRoute();
  const toast = useToast();
  const [reviewer, setReviewer] = useStored("helix.reviewer", "");
  const [clock, setClock] = useStored("helix.clock", "demo");
  const nameRef = useRef();

  // Returns the reviewer name, or null after asking for it.
  const requireReviewer = () => {
    const name = reviewer.trim();
    if (name.length >= 2) return name;
    nameRef.current?.classList.add("missing");
    nameRef.current?.focus();
    toast("Type your name in “You are” first. Every decision is recorded with it.", true);
    return null;
  };

  const session = { reviewer, requireReviewer, clock };
  const title = { queue: "Ticket queue", ticket: route.id, dashboard: "Dashboard", backend: "Backend" }[route.page];
  const premium = route.page === "dashboard" || route.page === "backend";
  useEffect(() => {
    document.title = `${title} · Helix Agent`;
    document.body.dataset.theme = premium ? "premium" : "light";
  }, [title, premium]);

  return (
    <SessionContext.Provider value={session}>
      <header className="top">
        <h1>Helix Agent<span>Agent workspace · KGIT helpdesk</span></h1>
        <nav aria-label="Main">
          <a href="#/" className={route.page === "queue" || route.page === "ticket" ? "on" : ""}>Ticket queue</a>
          <a href="#/dashboard" className={route.page === "dashboard" ? "on" : ""}>Dashboard</a>
          <a href="#/backend" className={route.page === "backend" ? "on" : ""}>Backend</a>
          <a href="/docs" target="_blank" rel="noreferrer">API docs ↗</a>
        </nav>
        <div className="spacer" />
        <label htmlFor="reviewer">You are
          <input id="reviewer" ref={nameRef} placeholder="Your name" maxLength={80} autoComplete="name" value={reviewer}
            onChange={(e) => { e.target.classList.remove("missing"); setReviewer(e.target.value); }} />
        </label>
        <label>SLA clock
          <span className="seg" role="group" aria-label="SLA clock">
            <button type="button" className={clock === "demo" ? "on" : ""} onClick={() => setClock("demo")}>Demo</button>
            <button type="button" className={clock === "now" ? "on" : ""} onClick={() => setClock("now")}>Real</button>
          </span>
        </label>
      </header>
      <main>
        {route.page === "ticket" && <Ticket key={route.id} id={route.id} />}
        {route.page === "queue" && <Queue />}
        {route.page === "dashboard" && <Dashboard />}
        {route.page === "backend" && <Backend />}
      </main>
    </SessionContext.Provider>
  );
}

export default function App() {
  return <ToastProvider><Shell /></ToastProvider>;
}
