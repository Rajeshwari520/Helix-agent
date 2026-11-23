import { useMemo, useState } from "react";
import { get, post } from "../api.js";
import { useLoad, useStored } from "../hooks.js";
import { useSession } from "../App.jsx";
import { useToast } from "../components/Toast.jsx";
import { Loading, PriorityPill, StatusTag } from "../components/ui.jsx";
import { OPEN, PRIORITY_RANK, SLA_LABEL, fmt, pct, pretty } from "../util.js";

const PAGE_SIZE = 25;
export const DEFAULT_FILTERS = { q: "", status: "active", priority: "", category: "", team: "", escalated: false, pending: false, sort: "urgent" };
const SORTS = {
  urgent: (a, b) => (PRIORITY_RANK[a.priority] ?? 9) - (PRIORITY_RANK[b.priority] ?? 9) || a.created_at.localeCompare(b.created_at),
  sla: (a, b) => (a.sla_first_response_due || "~").localeCompare(b.sla_first_response_due || "~"),
  newest: (a, b) => b.created_at.localeCompare(a.created_at),
  oldest: (a, b) => a.created_at.localeCompare(b.created_at),
};

export default function Queue() {
  const { clock } = useSession();
  const state = useLoad(() => Promise.all([get(`/queue?clock=${clock}&include_closed=true`), get("/meta")]), [clock]);
  return (
    <Loading state={state}>
      {([queue, meta]) => <QueueView queue={queue} meta={meta} reload={state.reload} />}
    </Loading>
  );
}

function QueueView({ queue, meta, reload }) {
  const [f, setF] = useStored("helix.queueFilters", DEFAULT_FILTERS);
  const [page, setPage] = useState(0);
  const [showNew, setShowNew] = useState(false);
  const set = (key) => (e) => { setF({ ...f, [key]: e.target.type === "checkbox" ? e.target.checked : e.target.value }); setPage(0); };

  const rows = useMemo(() => {
    const q = f.q.trim().toLowerCase();
    return queue.tickets
      .filter((t) => (f.status === "all" || (f.status === "active" ? OPEN.has(t.status) : t.status === f.status))
        && (!f.priority || t.priority === f.priority) && (!f.category || t.category === f.category)
        && (!f.team || t.team === f.team) && (!f.escalated || t.escalated) && (!f.pending || t.pending_decisions > 0)
        && (!q || t.id.toLowerCase().includes(q) || t.subject.toLowerCase().includes(q)))
      .sort(SORTS[f.sort] || SORTS.urgent);
  }, [queue, f]);

  const pages = Math.max(1, Math.ceil(rows.length / PAGE_SIZE));
  const current = Math.min(page, pages - 1);
  const slice = rows.slice(current * PAGE_SIZE, current * PAGE_SIZE + PAGE_SIZE);
  const open = rows.filter((t) => OPEN.has(t.status));
  const go = (id) => { location.hash = `#/tickets/${id}`; };

  return (
    <>
      <div className="card">
        <h2>Ticket queue
          <small>{queue.sla_clock.mode === "demo" ? `SLA measured at demo time ${fmt(queue.sla_clock.as_of)}` : "SLA measured now"}</small>
          <span style={{ flex: 1 }} />
          <button type="button" className="btn btn-primary" onClick={() => setShowNew(!showNew)} aria-expanded={showNew}>
            {showNew ? "Close" : "+ New ticket"}
          </button>
        </h2>
        {showNew && <NewTicket onCreated={(t) => { setShowNew(false); reload(); go(t.id); }} />}

        <div className="filters" role="search">
          <label>Search<input type="search" placeholder="ID or subject" value={f.q} onChange={set("q")} /></label>
          <label>Status
            <select value={f.status} onChange={set("status")}>
              <option value="active">Active (open)</option><option value="all">All</option>
              {meta.statuses.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </label>
          <label>Priority
            <select value={f.priority} onChange={set("priority")}>
              <option value="">Any</option>{meta.priorities.map((p) => <option key={p}>{p}</option>)}
            </select>
          </label>
          <label>Category
            <select value={f.category} onChange={set("category")}>
              <option value="">Any</option>{meta.categories.map((c) => <option key={c}>{c}</option>)}
            </select>
          </label>
          <label>Team
            <select value={f.team} onChange={set("team")}>
              <option value="">Any</option>{meta.teams.map((t) => <option key={t}>{t}</option>)}
            </select>
          </label>
          <label>Sort
            <select value={f.sort} onChange={set("sort")}>
              <option value="urgent">Most urgent first</option><option value="sla">Reply due soonest</option>
              <option value="newest">Newest first</option><option value="oldest">Oldest first</option>
            </select>
          </label>
          <label className="check"><input type="checkbox" checked={f.escalated} onChange={set("escalated")} />Escalated only</label>
          <label className="check"><input type="checkbox" checked={f.pending} onChange={set("pending")} />Awaiting a decision</label>
          <button type="button" className="btn btn-plain" onClick={() => { setF(DEFAULT_FILTERS); setPage(0); }}>Reset</button>
        </div>

        <div className="summary">
          <span><b>{rows.length}</b> tickets</span>
          <span><b>{open.filter((t) => t.sla === "breached").length}</b> overdue</span>
          <span><b>{rows.filter((t) => t.escalated).length}</b> escalated</span>
          <span><b>{rows.filter((t) => t.pending_decisions > 0).length}</b> awaiting a human decision</span>
        </div>

        <table>
          <caption className="sr">Tickets</caption>
          <thead><tr>{["ID", "Subject", "Category", "Priority", "Team", "Status", "Reply due", "AI", "Decision"].map((h) => <th key={h} scope="col">{h}</th>)}</tr></thead>
          <tbody>
            {slice.map((t) => (
              <tr key={t.id} className="link" tabIndex={0} title={`Open ${t.id}`}
                onClick={() => go(t.id)} onKeyDown={(e) => { if (e.key === "Enter") go(t.id); }}>
                <td className="mono">{t.id}</td>
                <td>{t.subject}</td>
                <td>{t.category || "-"}</td>
                <td><PriorityPill p={t.priority} /></td>
                <td>{t.team || "-"}</td>
                <td><StatusTag s={t.status} /></td>
                <td className={`nowrap s-${t.sla}`} title={`First response due ${fmt(t.sla_first_response_due)}`}>
                  {t.sla === "closed" ? SLA_LABEL.closed : `${fmt(t.sla_first_response_due)} · ${SLA_LABEL[t.sla]}`}
                </td>
                <td className="nowrap">{pct(t.confidence)}</td>
                <td>
                  {t.escalated && <span className="badge b-esc" title={t.escalation_reasons.map(pretty).join(", ")}>Escalated</span>}
                  {t.pending_decisions ? <span className="badge b-pending">{t.pending_decisions} to review</span> : <span className="empty">done</span>}
                </td>
              </tr>
            ))}
            {!slice.length && <tr><td colSpan={9} className="empty">No tickets match these filters.</td></tr>}
          </tbody>
        </table>

        <div className="pager">
          <button type="button" className="btn btn-plain" disabled={current === 0} onClick={() => setPage(current - 1)}>← Previous</button>
          <span>Page {current + 1} of {pages}</span>
          <button type="button" className="btn btn-plain" disabled={current >= pages - 1} onClick={() => setPage(current + 1)}>Next →</button>
        </div>
      </div>
    </>
  );
}

function NewTicket({ onCreated }) {
  const toast = useToast();
  const [form, setForm] = useState({ subject: "", body: "", channel: "web_form", customer_ref: "CUST-ANON" });
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });
  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const t = await post("/tickets", form);
      toast(`Created ${t.id} → ${t.category}, ${t.priority}, ${t.team}${t.needs_escalation ? " (escalated)" : ""}`);
      onCreated(t);
    } catch (err) { toast(err.message, true); setBusy(false); }
  };
  return (
    <form className="form" onSubmit={submit} style={{ marginBottom: 14 }}>
      <label htmlFor="nSubject">Subject<input id="nSubject" required minLength={3} maxLength={200} value={form.subject} onChange={set("subject")} placeholder="e.g. Cannot open LMS" /></label>
      <label htmlFor="nBody">Problem<textarea id="nBody" className="short" required minLength={3} maxLength={5000} value={form.body} onChange={set("body")} placeholder="Describe the problem" /></label>
      <div className="row3">
        <label htmlFor="nChannel">Channel
          <select id="nChannel" value={form.channel} onChange={set("channel")}>
            <option value="web_form">Web form</option><option value="email">Email</option><option value="chat">Chat</option>
          </select>
        </label>
        <label htmlFor="nCust">Customer / employee ID<input id="nCust" maxLength={50} value={form.customer_ref} onChange={set("customer_ref")} /></label>
      </div>
      <div className="actions" style={{ marginTop: 0 }}>
        <button className="btn btn-approve" type="submit" disabled={busy}>{busy ? "Creating…" : "Create and triage"}</button>
        <span className="note" style={{ marginTop: 0 }}>The AI sets category, priority, team and SLA at once; you review it on the ticket page.</span>
      </div>
    </form>
  );
}
