import { useEffect, useMemo, useState } from "react";
import { get } from "../api.js";
import { useLoad, useStored } from "../hooks.js";
import { useSession } from "../App.jsx";
import { Loading, PriorityPill, StatusTag } from "../components/ui.jsx";
import { ColumnChart, Compare, HBars, SegmentBar, TipProvider } from "../components/charts.jsx";
import { OPEN, PRIORITY_RANK, SLA_LABEL, fmt, pretty } from "../util.js";

// Colours (validated for the cream card surface #faf6ef with the dataviz palette validator).
const C = {
  gold: "#a87b00", s1: "#a87b00", s2: "#6250d6", s3: "#0a9478", before: "#978a70",
  good: "#0ca30c", warn: "#fab219", crit: "#d03b3b",
};
const PRIORITIES = ["Critical", "High", "Medium", "Low"];
const DEFAULTS = { range: "all", from: "", to: "", category: "", team: "", priority: "", channel: "", status: "all" };
const DAY = 86400000;
const dayKey = (d) => new Date(d).toLocaleDateString("en-CA"); // yyyy-mm-dd, local time
const dayLabel = (d) => d.toLocaleDateString("en-IN", { day: "2-digit", month: "short" });

export default function Dashboard() {
  const { clock } = useSession();
  const state = useLoad(() => Promise.all([
    get(`/queue?clock=${clock}&include_closed=true`), get(`/dashboard/stats?clock=${clock}`),
  ]), [clock]);
  useEffect(() => {
    const t = setInterval(state.reload, 30000); // live refresh every 30 s
    return () => clearInterval(t);
  }, [state.reload]);
  return (
    <TipProvider>
      <div className="pv">
        <Loading state={state}>
          {([queue, stats]) => <View queue={queue} stats={stats} refreshing={state.loading} />}
        </Loading>
      </div>
    </TipProvider>
  );
}

function View({ queue, stats, refreshing }) {
  const [f, setF] = useStored("helix.dashFilters", DEFAULTS);
  const [pick, setPick] = useState(null); // { title, test(ticket) }
  const asOf = new Date(queue.sla_clock.as_of);
  const all = queue.tickets;
  const options = useMemo(() => ({
    categories: [...new Set(all.map((t) => t.category).filter(Boolean))].sort(),
    teams: [...new Set(all.map((t) => t.team).filter(Boolean))].sort(),
    channels: [...new Set(all.map((t) => t.channel))].sort(),
  }), [all]);

  // ---- filters scope everything below ----
  const [start, end] = useMemo(() => {
    if (f.range === "custom") {
      return [f.from ? new Date(`${f.from}T00:00:00`) : null, f.to ? new Date(`${f.to}T23:59:59`) : null];
    }
    if (f.range === "all") return [null, null];
    return [new Date(asOf.getTime() - Number(f.range) * DAY), asOf];
  }, [f.range, f.from, f.to, queue.sla_clock.as_of]); // eslint-disable-line react-hooks/exhaustive-deps

  const rows = useMemo(() => all.filter((t) => {
    const c = new Date(t.created_at);
    return (!start || c >= start) && (!end || c <= end)
      && (!f.category || t.category === f.category) && (!f.team || t.team === f.team)
      && (!f.priority || t.priority === f.priority) && (!f.channel || t.channel === f.channel)
      && (f.status === "all" || (f.status === "open" ? OPEN.has(t.status) : !OPEN.has(t.status)));
  }), [all, start, end, f]);
  const open = rows.filter((t) => OPEN.has(t.status));
  const set = (k) => (e) => { setF({ ...f, [k]: e.target.value }); setPick(null); };
  const preset = (r) => { setF({ ...f, range: r }); setPick(null); };
  const activeCount = ["category", "team", "priority", "channel"].filter((k) => f[k]).length
    + (f.range !== "all" ? 1 : 0) + (f.status !== "all" ? 1 : 0);

  const drill = (title, test) => {
    setPick({ title, test });
    setTimeout(() => document.getElementById("drill")?.scrollIntoView({ behavior: "smooth", block: "start" }), 50);
  };

  // ---- aggregates ----
  const kpis = [
    { key: "all", label: "Tickets in view", value: rows.length, sub: `${open.length} open`, color: C.gold, test: () => true },
    { key: "esc", label: "Escalated to team lead", value: open.filter((t) => t.escalated).length, sub: "open, risky or critical", color: C.crit, test: (t) => OPEN.has(t.status) && t.escalated },
    { key: "over", label: "SLA overdue", value: open.filter((t) => t.sla === "breached").length, sub: "first reply is late", color: C.crit, test: (t) => OPEN.has(t.status) && t.sla === "breached" },
    { key: "soon", label: "Due within 4 hours", value: open.filter((t) => t.sla === "due_soon").length, sub: "reply soon", color: C.warn, test: (t) => OPEN.has(t.status) && t.sla === "due_soon" },
    { key: "wait", label: "Awaiting a human decision", value: open.filter((t) => t.pending_decisions > 0).length, sub: "AI suggestions to review", color: C.warn, test: (t) => OPEN.has(t.status) && t.pending_decisions > 0 },
    { key: "done", label: "Replied / closed", value: rows.length - open.length, sub: `${rows.length ? Math.round(((rows.length - open.length) / rows.length) * 100) : 0}% of view`, color: C.good, test: (t) => !OPEN.has(t.status) },
  ];

  const trend = useMemo(() => {
    if (!rows.length) return [];
    const times = rows.map((t) => new Date(t.created_at).getTime());
    const lo = start ? start.getTime() : Math.min(...times);
    const hi = end ? end.getTime() : Math.max(...times);
    const days = [];
    for (let d = new Date(new Date(lo).toDateString()); d.getTime() <= hi; d = new Date(d.getTime() + DAY)) days.push(d);
    const weekly = days.length > 45;
    const keyOf = (date) => {
      if (!weekly) return dayKey(date);
      const m = new Date(date); m.setDate(m.getDate() - ((m.getDay() + 6) % 7)); return dayKey(m);
    };
    const buckets = new Map();
    for (const d of days) if (!buckets.has(keyOf(d))) buckets.set(keyOf(d), { date: weekly ? new Date(`${keyOf(d)}T00:00:00`) : d, list: [] });
    for (const t of rows) buckets.get(keyOf(new Date(t.created_at)))?.list.push(t);
    return [...buckets.entries()].map(([k, b]) => ({
      key: k, unit: weekly ? "week" : "day", short: dayLabel(b.date),
      label: weekly ? `Week of ${dayLabel(b.date)}` : b.date.toLocaleDateString("en-IN", { weekday: "short", day: "2-digit", month: "short" }),
      value: b.list.length,
      rows: [...PRIORITIES.map((p) => ({ label: p, value: b.list.filter((t) => t.priority === p).length })),
        { label: "Escalated", value: b.list.filter((t) => t.escalated).length, color: C.crit }].filter((r) => r.value),
      test: (t) => keyOf(new Date(t.created_at)) === k,
    }));
  }, [rows, start, end]);

  const countBy = (key, order) => {
    const m = new Map();
    for (const t of rows) { const v = t[key] || "Unassigned"; m.set(v, (m.get(v) || 0) + 1); }
    const list = [...m.entries()].map(([k, v]) => ({ key: k, label: pretty(k), value: v }));
    return order ? list.sort((a, b) => order(a.key) - order(b.key)) : list.sort((a, b) => b.value - a.value);
  };
  const byPriority = countBy("priority", (k) => PRIORITY_RANK[k] ?? 9);
  const byCategory = countBy("category");
  const byTeam = countBy("team");
  const reasons = (() => {
    const m = new Map();
    for (const t of open) for (const r of t.escalation_reasons) m.set(r, (m.get(r) || 0) + 1);
    return [...m.entries()].sort((a, b) => b[1] - a[1]).map(([k, v]) => ({ key: k, label: pretty(k), value: v }));
  })();
  const channelColor = { web_form: C.s1, email: C.s2, chat: C.s3 };
  const darkInk = () => "#ffffff"; // white clears 3:1 on deep gold, violet and teal
  const channels = options.channels.map((c) => ({ key: c, label: pretty(c), value: rows.filter((t) => t.channel === c).length, color: channelColor[c] || C.before }));
  const sla = [
    { key: "breached", label: "Overdue", icon: "⚠", value: open.filter((t) => t.sla === "breached").length, color: C.crit },
    { key: "due_soon", label: "Due within 4 h", icon: "◷", value: open.filter((t) => t.sla === "due_soon").length, color: C.warn },
    { key: "on_track", label: "On track", icon: "✓", value: open.filter((t) => t.sla === "on_track").length, color: C.good },
  ];
  const m = stats.model_metrics || {};
  const base = m.baseline?.week1_rules_on_frozen_test;
  const quality = [
    { label: "Category", before: base?.category_accuracy, now: m.classifier?.category_accuracy },
    { label: "Priority", before: base?.priority_accuracy, now: m.classifier?.priority_accuracy },
    { label: "Risky caught", before: base?.risky_tickets_caught, now: m.classifier?.risky_tickets_caught },
    { label: "Answer precision", before: null, now: m.rag?.metrics?.answer_precision },
    { label: "Answer coverage", before: null, now: m.rag?.metrics?.answer_coverage },
  ].filter((q) => q.now != null);
  const decisions = (kind) => {
    const h = stats.human_decisions?.[kind] || { approved: 0, edited: 0, rejected: 0 };
    return [
      { key: "approved", label: "Approved as is", value: h.approved, color: C.s1 },
      { key: "edited", label: "Edited by a person", value: h.edited, color: C.s2 },
      { key: "rejected", label: "Rejected", value: h.rejected, color: C.s3 },
    ];
  };

  const drillRows = pick ? rows.filter(pick.test).sort((a, b) => (PRIORITY_RANK[a.priority] ?? 9) - (PRIORITY_RANK[b.priority] ?? 9) || a.created_at.localeCompare(b.created_at)) : [];
  const exportCsv = () => {
    const list = pick ? drillRows : rows;
    const cols = ["id", "subject", "status", "category", "priority", "team", "channel", "created_at", "sla_first_response_due", "sla", "escalated", "pending_decisions"];
    const esc = (v) => `"${String(v ?? "").replace(/"/g, '""')}"`;
    const csv = [cols.join(","), ...list.map((t) => cols.map((c) => esc(t[c])).join(","))].join("\r\n");
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
    a.download = `helix-tickets-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  };
  const rangeText = f.range === "all" ? "all time" : f.range === "custom" ? `${f.from || "start"} → ${f.to || "today"}` : `last ${f.range} days`;

  return (
    <div className={refreshing ? "loading-dim" : ""}>
      <div style={{ display: "flex", alignItems: "end", gap: 12, flexWrap: "wrap" }}>
        <div style={{ flex: 1 }}>
          <h1 className="pv-title">Helpdesk dashboard</h1>
          <p className="pv-sub">
            {rows.length} of {all.length} tickets · {rangeText} · SLA measured {queue.sla_clock.mode === "demo" ? `at demo time ${fmt(queue.sla_clock.as_of)}` : "now"} · refreshes every 30 s
          </p>
        </div>
        <button type="button" className="pv-btn" onClick={exportCsv}>Download CSV{pick ? " (selection)" : ""}</button>
      </div>

      <div className="pv-filters" role="search" aria-label="Dashboard filters">
        <label>Date range
          <span className="pv-presets" role="group">
            {[["all", "All"], ["7", "7 days"], ["14", "14 days"], ["30", "30 days"], ["custom", "Custom"]].map(([k, l]) => (
              <button type="button" key={k} className={f.range === k ? "on" : ""} aria-pressed={f.range === k} onClick={() => preset(k)}>{l}</button>
            ))}
          </span>
        </label>
        {f.range === "custom" && <>
          <label>From<input type="date" value={f.from} onChange={set("from")} /></label>
          <label>To<input type="date" value={f.to} onChange={set("to")} /></label>
        </>}
        {[["category", "Category", options.categories], ["team", "Team", options.teams], ["priority", "Priority", PRIORITIES], ["channel", "Channel", options.channels]].map(([k, l, list]) => (
          <label key={k}>{l}
            <select value={f[k]} onChange={set(k)} className={f[k] ? "active" : ""}>
              <option value="">All</option>{list.map((x) => <option key={x} value={x}>{pretty(x)}</option>)}
            </select>
          </label>
        ))}
        <label>Status
          <select value={f.status} onChange={set("status")} className={f.status !== "all" ? "active" : ""}>
            <option value="all">All</option><option value="open">Open</option><option value="closed">Replied / closed</option>
          </select>
        </label>
        {activeCount > 0 && <button type="button" className="pv-btn" onClick={() => { setF(DEFAULTS); setPick(null); }}>Clear {activeCount} filter{activeCount > 1 ? "s" : ""}</button>}
      </div>

      <section className="pv-kpis">
        {kpis.map((k) => (
          <button type="button" key={k.key} className="pv-kpi" onClick={() => drill(k.label, k.test)} aria-label={`${k.label}: ${k.value}. Show these tickets`}>
            <div className="v">{k.value}</div>
            <div className="l"><span className="dot" style={{ background: k.color }} />{k.label}</div>
            <div className="s">{k.sub}</div>
          </button>
        ))}
      </section>

      <section className="pv-grid pv-g2">
        <div className="pv-card">
          <h2>Ticket volume <small>created per {trend[0]?.unit || "day"} · hover for the priority mix · click a column to list them</small></h2>
          {trend.length ? <ColumnChart data={trend} color={C.gold} onPick={(d) => drill(d.label, d.test)} /> : <p className="empty">No tickets in this view.</p>}
        </div>
        <div className="pv-card">
          <h2>SLA health <small>open tickets, first reply</small></h2>
          <SegmentBar parts={sla} onPick={(p) => drill(`SLA: ${p.label}`, (t) => OPEN.has(t.status) && t.sla === p.key)}
            inkOn={(p) => (p.key === "due_soon" ? "#0b0b0b" : "#ffffff")} />
          <p className="note">First reply within: Critical 1 h · High 4 h · Medium 8 h · Low 24 h.</p>
        </div>
      </section>

      <section className="pv-grid pv-g3">
        <div className="pv-card"><h2>By priority <small>click to list</small></h2>
          <HBars rows={byPriority} color={C.gold} onPick={(r) => drill(`Priority: ${r.label}`, (t) => t.priority === r.key)} /></div>
        <div className="pv-card"><h2>By category <small>click to list</small></h2>
          <HBars rows={byCategory} color={C.gold} onPick={(r) => drill(`Category: ${r.label}`, (t) => (t.category || "Unassigned") === r.key)} /></div>
        <div className="pv-card"><h2>By team <small>click to list</small></h2>
          <HBars rows={byTeam} color={C.gold} onPick={(r) => drill(`Team: ${r.label}`, (t) => (t.team || "Unassigned") === r.key)} /></div>
      </section>

      <section className="pv-grid pv-g3">
        <div className="pv-card"><h2>Why tickets were escalated <small>open tickets</small></h2>
          <HBars rows={reasons} color={C.gold} total={open.filter((t) => t.escalated).length} unit="escalated tickets" empty="No open escalations in this view."
            onPick={(r) => drill(`Escalated: ${r.label}`, (t) => OPEN.has(t.status) && t.escalation_reasons.includes(r.key))} /></div>
        <div className="pv-card"><h2>Channel <small>where tickets came from</small></h2>
          <SegmentBar parts={channels} inkOn={darkInk} onPick={(p) => drill(`Channel: ${p.label}`, (t) => t.channel === p.key)} /></div>
        <div className="pv-card"><h2>Human decisions on AI <small>all time</small></h2>
          <div className="note" style={{ margin: "0 0 4px" }}>Triage</div><SegmentBar parts={decisions("triage")} inkOn={darkInk} unit="decisions" />
          <div className="note" style={{ margin: "4px 0" }}>Replies</div><SegmentBar parts={decisions("answer")} inkOn={darkInk} unit="decisions" />
        </div>
      </section>

      <section className="pv-grid pv-g2">
        <div className="pv-card">
          <h2>AI quality <small>frozen 50-ticket test set, never used for training</small></h2>
          {quality.length ? <>
            <Compare rows={quality} beforeColor={C.before} nowColor={C.gold} />
            <div className="legend-row"><span><span className="sw" style={{ background: C.before }} /> Week 1 keyword rules</span><span><span className="sw" style={{ background: C.gold }} /> Now (ML + RAG)</span></div>
          </> : <p className="empty">Metric files not found in docs/kgit/.</p>}
        </div>
        <div className="pv-card">
          <h2>Knowledge base</h2>
          <div className="stat-grid" style={{ gridTemplateColumns: "1fr 1fr" }}>
            <div className="stat"><div className="v">{stats.knowledge.approved_faqs}</div><div className="l">approved FAQs</div></div>
            <div className="stat"><div className="v">{all.length}</div><div className="l">tickets in total</div></div>
          </div>
          <p className="note">Answers come only from approved FAQs. Corpus <code>{stats.knowledge.corpus_version}</code></p>
          <p className="note"><a href="#/backend">See how the backend works →</a></p>
        </div>
      </section>

      <div className="pv-card" id="drill" style={{ scrollMarginTop: 80 }}>
        <h2>
          {pick ? <>Tickets · <span className="pv-chip">{pick.title}<button type="button" className="pv-btn" style={{ padding: "0 6px", border: 0 }} aria-label="Clear selection" onClick={() => setPick(null)}>✕</button></span></> : "Tickets"}
          <small>{pick ? `${drillRows.length} match · click a row to open it` : "click any number, bar or column above to list its tickets here"}</small>
        </h2>
        {pick && (
          <table>
            <thead><tr>{["ID", "Subject", "Category", "Priority", "Team", "Status", "Reply due"].map((h) => <th key={h}>{h}</th>)}</tr></thead>
            <tbody>
              {drillRows.map((t) => (
                <tr key={t.id} className="link" tabIndex={0} onClick={() => { location.hash = `#/tickets/${t.id}`; }}
                  onKeyDown={(e) => { if (e.key === "Enter") location.hash = `#/tickets/${t.id}`; }}>
                  <td className="mono">{t.id}</td><td>{t.subject}</td><td>{t.category}</td><td><PriorityPill p={t.priority} /></td>
                  <td>{t.team}</td><td><StatusTag s={t.status} /></td><td className={`nowrap s-${t.sla}`}>{SLA_LABEL[t.sla]}</td>
                </tr>
              ))}
              {!drillRows.length && <tr><td colSpan={7} className="empty">No tickets.</td></tr>}
            </tbody>
          </table>
        )}
      </div>
      <footer>Helix Agent · {String(stats.domain).toUpperCase()} · synthetic data · every AI suggestion needs a person's approval</footer>
    </div>
  );
}
