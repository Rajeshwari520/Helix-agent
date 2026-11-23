import { useState } from "react";
import { get, patch, post } from "../api.js";
import { useLoad } from "../hooks.js";
import { useSession } from "../App.jsx";
import { useToast } from "../components/Toast.jsx";
import { AiTag, DecisionLine, Loading, PriorityPill, Reasons, StatusTag } from "../components/ui.jsx";
import { fmt, pct, pretty } from "../util.js";

export default function Ticket({ id }) {
  const state = useLoad(() => Promise.all([
    get(`/tickets/${id}`), get(`/tickets/${id}/suggestions`), get(`/tickets/${id}/audit`), get("/meta"),
  ]), [id]);
  return (
    <>
      <a href="#/" className="back">← Back to queue</a>
      <Loading state={state}>
        {([ticket, suggestions, trail, meta]) => (
          <TicketView ticket={ticket} suggestions={suggestions} trail={trail} meta={meta} reload={state.reload} />
        )}
      </Loading>
    </>
  );
}

// Posts a human decision on one AI suggestion; reloads the page data on success.
function useDecide(ticketId, reload) {
  const { requireReviewer } = useSession();
  const toast = useToast();
  return async (suggestionId, body, message) => {
    const reviewer = requireReviewer();
    if (!reviewer) return false;
    try {
      await post(`/tickets/${ticketId}/suggestions/${suggestionId}/review`, { ...body, reviewer });
      toast(message);
      await reload();
      return true;
    } catch (e) { toast(e.message, true); return false; }
  };
}

function TicketView({ ticket: t, suggestions, trail, meta, reload }) {
  const latest = (kind) => [...suggestions].reverse().find((s) => s.kind === kind);
  const sent = suggestions.filter((s) => s.kind === "answer" && s.review?.final_payload?.reply);
  return (
    <div className="detail">
      <div>
        <div className="card ticket-head">
          <h1>{t.subject}</h1>
          <div className="meta">
            <span className="mono">{t.id}</span><span>Channel: {pretty(t.channel)}</span>
            <span>Customer: {t.customer_ref}</span><span>Created {fmt(t.created_at)}</span><StatusTag s={t.status} />
          </div>
          <div className="body">{t.body}</div>
        </div>
        <ReplyCard key={latest("answer")?.id ?? "none"} ticket={t} suggestion={latest("answer")} sent={sent} reload={reload} />
        <AuditTrail trail={trail} />
      </div>
      <div>
        <FieldsCard key={t.status} ticket={t} meta={meta} reload={reload} />
        <TriageCard key={`${latest("triage")?.id}-${t.category}-${t.priority}-${t.team}`} ticket={t} suggestion={latest("triage")} meta={meta} reload={reload} />
      </div>
    </div>
  );
}

function FieldsCard({ ticket: t, meta, reload }) {
  const { requireReviewer } = useSession();
  const toast = useToast();
  const [status, setStatus] = useState(t.status);
  const save = async () => {
    const who = requireReviewer();
    if (!who) return;
    if (status === t.status) { toast(`Status is already ${t.status}`); return; }
    try { await patch(`/tickets/${t.id}`, { status, changed_by: who }); toast(`Status changed to ${status}`); reload(); }
    catch (e) { toast(e.message, true); }
  };
  return (
    <div className="card">
      <h2>Ticket</h2>
      <dl className="kv">
        <dt>Category</dt><dd>{t.category || "-"}</dd>
        <dt>Priority</dt><dd><PriorityPill p={t.priority} /></dd>
        <dt>Team</dt><dd>{t.team || "-"}</dd>
        <dt>First reply due</dt><dd>{fmt(t.sla_first_response_due)}</dd>
        <dt>Resolve by</dt><dd>{fmt(t.sla_resolution_due)}</dd>
        <dt>Escalation</dt><dd>{t.needs_escalation ? <Reasons list={t.escalation_reasons} /> : "No"}</dd>
      </dl>
      <div className="form">
        <label htmlFor="statusSel">Change status
          <select id="statusSel" value={status} onChange={(e) => setStatus(e.target.value)}>
            {meta.statuses.map((s) => <option key={s}>{s}</option>)}
          </select>
        </label>
        <div><button type="button" className="btn btn-primary" onClick={save}>Save status</button></div>
      </div>
    </div>
  );
}

function TriageCard({ ticket: t, suggestion: s, meta, reload }) {
  const decide = useDecide(t.id, reload);
  const [mode, setMode] = useState(null); // null | "edit" | "reject"
  const [edit, setEdit] = useState({ category: t.category, priority: t.priority, team: t.team, reason: "" });
  const [reason, setReason] = useState("");

  if (!s) return <div className="card"><h2>AI triage</h2><p className="empty">No AI triage for this ticket.</p></div>;
  const p = s.payload;
  const rv = s.review;
  const changed = rv?.decision === "edited" && rv.final_payload
    ? ["category", "priority", "team"].filter((k) => rv.final_payload[k] !== p[k]).map((k) => `${k}: ${p[k]} → ${rv.final_payload[k]}`)
    : [];

  return (
    <div className="card">
      <h2>AI triage <AiTag /></h2>
      <dl className="kv">
        <dt>Category</dt><dd>{p.category}{p.category_confidence != null && ` (${pct(p.category_confidence)} sure)`}</dd>
        <dt>Priority</dt><dd><PriorityPill p={p.priority} />{p.priority_reasons?.length > 0 && <div className="note">{p.priority_reasons.join(", ")}</div>}</dd>
        <dt>Team</dt><dd>{p.team}</dd>
        <dt>Escalate</dt><dd>{p.needs_escalation ? <Reasons list={p.escalation_reasons} /> : "No"}</dd>
        <dt>Personal data</dt><dd>{p.pii_found?.length ? `${p.pii_found.join(", ")} (hidden from the AI)` : "None found"}</dd>
      </dl>
      {p.needs_human_review && <div className="warn">The AI is unsure about the category. Please check it.</div>}

      {rv ? (
        <DecisionLine review={rv}>{changed.length > 0 && <div className="note">Changed {changed.join(", ")}</div>}</DecisionLine>
      ) : (
        <>
          <div className="actions">
            <button type="button" className="btn btn-approve" onClick={() => decide(s.id, { decision: "approve" }, "Triage approved")}>Approve</button>
            <button type="button" className="btn btn-edit" onClick={() => setMode(mode === "edit" ? null : "edit")}>Edit</button>
            <button type="button" className="btn btn-reject" onClick={() => setMode(mode === "reject" ? null : "reject")}>Reject</button>
          </div>
          {mode === "edit" && (
            <div className="form">
              <div className="row3">
                <label htmlFor="eCat">Category
                  <select id="eCat" value={edit.category} onChange={(e) => setEdit({
                    ...edit, category: e.target.value, team: t.needs_escalation ? edit.team : meta.category_team[e.target.value] })}>
                    {meta.categories.map((c) => <option key={c}>{c}</option>)}
                  </select>
                </label>
                <label htmlFor="ePri">Priority
                  <select id="ePri" value={edit.priority} onChange={(e) => setEdit({ ...edit, priority: e.target.value })}>
                    {meta.priorities.map((x) => <option key={x}>{x}</option>)}
                  </select>
                </label>
                <label htmlFor="eTeam">Team
                  <select id="eTeam" value={edit.team} onChange={(e) => setEdit({ ...edit, team: e.target.value })}>
                    {meta.teams.map((x) => <option key={x}>{x}</option>)}
                  </select>
                </label>
              </div>
              <label htmlFor="eReason">Reason<input id="eReason" maxLength={500} placeholder="Why? (optional)" value={edit.reason} onChange={(e) => setEdit({ ...edit, reason: e.target.value })} /></label>
              <div className="actions">
                <button type="button" className="btn btn-approve" onClick={() => decide(s.id, { decision: "edit", ...edit }, "Triage corrected")}>Save changes</button>
                <button type="button" className="btn btn-plain" onClick={() => setMode(null)}>Cancel</button>
              </div>
            </div>
          )}
          {mode === "reject" && (
            <div className="form">
              <label htmlFor="rReason">Reason (required)
                <textarea id="rReason" className="short" maxLength={500} placeholder="What is wrong with this triage?" value={reason} onChange={(e) => setReason(e.target.value)} />
              </label>
              <div className="actions">
                <button type="button" className="btn btn-reject" onClick={() => decide(s.id, { decision: "reject", reason }, "Triage rejected")}>Reject triage</button>
                <button type="button" className="btn btn-plain" onClick={() => setMode(null)}>Cancel</button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function ReplyCard({ ticket: t, suggestion: s, sent, reload }) {
  const toast = useToast();
  const decide = useDecide(t.id, reload);
  const [mode, setMode] = useState(null); // null | "edit" | "reject"
  const [text, setText] = useState("");
  const [why, setWhy] = useState("");
  const [busy, setBusy] = useState(false);

  const draft = async () => {
    setBusy(true);
    try { await post(`/tickets/${t.id}/answer`); setMode(null); await reload(); }
    catch (e) { toast(e.message, true); }
    setBusy(false);
  };
  const DraftButton = ({ label }) => (
    <button type="button" className="btn btn-primary" disabled={busy} onClick={draft}>{busy ? "Drafting…" : label}</button>
  );

  const sentBlocks = sent.map((r) => (
    <div key={r.id} style={{ marginBottom: 12 }}>
      <div className="draft sent">{r.review.final_payload.reply}</div>
      <div className="note" style={{ marginTop: 2 }}>
        Sent by {r.review.reviewer} · {fmt(r.review.created_at)} · {r.review.decision === "approved" ? "AI draft used as is" : "written / edited by a person"}
        {r.review.final_payload.citations?.length > 0 && ` · sources ${r.review.final_payload.citations.join(", ")}`} · simulated: no email is sent in this prototype
      </div>
    </div>
  ));

  let body;
  if (!s) {
    body = <><p className="empty">No reply drafted yet.</p><div className="actions"><DraftButton label="Draft reply from FAQs" /></div></>;
  } else if (s.review) {
    const nothingSent = !s.review.final_payload?.reply;
    body = (
      <>
        {nothingSent && <><div className="note">Latest AI draft:</div><DecisionLine review={s.review} />
          <div className="note">Nothing was sent. Make a new draft; if the AI cannot answer, choose “Write reply” to write it yourself.</div></>}
        <div className="actions"><DraftButton label={nothingSent ? "New draft / write reply" : "Draft again"} /></div>
      </>
    );
  } else {
    const p = s.payload;
    body = (
      <>
        <div className="note" style={{ margin: "0 0 8px" }}><AiTag>AI draft</AiTag> {pretty(p.status)} · {pct(p.confidence || 0)} match · {fmt(s.created_at)}</div>
        {p.draft_reply
          ? <div className="draft">{p.draft_reply}</div>
          : <div className="warn">{p.message || "The AI did not draft a reply."} A person must write this reply.</div>}
        {p.citations?.length > 0 && <div className="cites">Sources: {p.citations.map((c) => `${c.faq_id} v${c.version} (${pct(c.score)})`).join(", ")}</div>}
        {p.draft_reply && p.message?.includes("Note") && <div className="warn">{p.message}</div>}
        <div className="actions">
          <button type="button" className="btn btn-approve" disabled={!p.draft_reply} title={p.draft_reply ? "" : "There is no AI draft to approve"}
            onClick={() => decide(s.id, { decision: "approve" }, "Reply sent (simulated)")}>Approve &amp; send</button>
          <button type="button" className="btn btn-edit" onClick={() => { setText(p.draft_reply || ""); setMode(mode === "edit" ? null : "edit"); }}>
            {p.draft_reply ? "Edit & send" : "Write reply"}
          </button>
          <button type="button" className="btn btn-reject" onClick={() => setMode(mode === "reject" ? null : "reject")}>Reject</button>
        </div>
        {mode === "edit" && (
          <div className="form">
            <label htmlFor="replyTxt">{p.draft_reply ? "Edit the reply before sending" : "Write the reply"}
              <textarea id="replyTxt" maxLength={5000} value={text} onChange={(e) => setText(e.target.value)} autoFocus />
            </label>
            <input aria-label="Reason" maxLength={500} placeholder="What did you change and why? (optional)" value={why} onChange={(e) => setWhy(e.target.value)} />
            <div className="actions">
              <button type="button" className="btn btn-approve" onClick={() => decide(s.id, { decision: "edit", reply: text, reason: why }, "Reply sent (simulated)")}>Send this reply</button>
              <button type="button" className="btn btn-plain" onClick={() => setMode(null)}>Cancel</button>
            </div>
          </div>
        )}
        {mode === "reject" && (
          <div className="form">
            <label htmlFor="ansReason">Reason (required)
              <textarea id="ansReason" className="short" maxLength={500} placeholder="Why is this draft not usable?" value={why} onChange={(e) => setWhy(e.target.value)} />
            </label>
            <div className="actions">
              <button type="button" className="btn btn-reject" onClick={() => decide(s.id, { decision: "reject", reason: why }, "Draft rejected, nothing sent")}>Reject draft</button>
              <button type="button" className="btn btn-plain" onClick={() => setMode(null)}>Cancel</button>
            </div>
          </div>
        )}
        <div className="note">Nothing reaches the customer until you approve or send it. Sending is simulated in this prototype.</div>
      </>
    );
  }

  return (
    <div className="card">
      <h2>Reply to customer <small>AI drafts, a person decides</small></h2>
      {sentBlocks}
      {body}
    </div>
  );
}

const EVENT_TEXT = {
  ticket_created: "Ticket created", ai_triage: "AI triaged the ticket", ai_answer_drafted: "AI drafted a reply",
  suggestion_approved: "Approved the AI suggestion", suggestion_edited: "Edited the AI suggestion",
  suggestion_rejected: "Rejected the AI suggestion", reply_sent: "Sent a reply to the customer",
  ticket_updated: "Updated the ticket", ticket_deleted: "Deleted the ticket",
};

function eventDetail(e) {
  const d = e.details || {};
  switch (e.event) {
    case "ai_triage": return `${d.category} · ${d.priority} · ${d.team}${d.confidence != null ? ` · ${pct(d.confidence)} sure` : ""}${d.escalated ? " · escalated" : ""}`;
    case "ai_answer_drafted": return `${pretty(d.status)}${d.citations?.length ? ` · ${d.citations.slice(0, 3).join(", ")}` : ""}`;
    case "ticket_updated": return Object.entries(d).map(([k, v]) => `${k}: ${v.from ?? "-"} → ${v.to}`).join(" · ");
    case "suggestion_approved": case "suggestion_edited": case "suggestion_rejected":
      return [d.kind, d.changes && Object.entries(d.changes).map(([k, v]) => `${k} → ${v}`).join(", "), d.reason && `reason: ${d.reason}`].filter(Boolean).join(" · ");
    case "reply_sent": return `${d.ai_draft_used ? "AI draft as approved" : "written or edited by a person"}${d.simulated ? " · simulated" : ""}`;
    case "ticket_created": return d.channel ? `via ${pretty(d.channel)}` : "";
    default: return "";
  }
}

function AuditTrail({ trail }) {
  return (
    <div className="card">
      <h2>Audit trail <small>every AI suggestion and human decision, oldest first</small></h2>
      {trail.length ? (
        <ol className="timeline">
          {trail.map((e) => (
            <li key={e.id}>
              <time dateTime={e.created_at}>{fmt(e.created_at)}</time>
              <div>
                <span className={`who${e.actor === "ai" ? " ai" : ""}`}>{e.actor === "ai" ? "AI" : e.actor}</span> · {EVENT_TEXT[e.event] || e.event}
                {eventDetail(e) && <div className="d">{eventDetail(e)}</div>}
              </div>
            </li>
          ))}
        </ol>
      ) : <p className="empty">No events yet.</p>}
    </div>
  );
}
