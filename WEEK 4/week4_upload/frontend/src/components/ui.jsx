import { pretty } from "../util.js";

export const PriorityPill = ({ p }) => <span className={`pill p-${p}`}>{p || "-"}</span>;
export const StatusTag = ({ s }) => <span className={`st st-${String(s).split(" ")[0]}`}>{s}</span>;
export const AiTag = ({ children = "AI suggestion" }) => <span className="ai-tag">{children}</span>;

export function DecisionLine({ review, children }) {
  if (!review) return null;
  const word = { approved: "Approved", edited: "Edited", rejected: "Rejected" }[review.decision];
  return (
    <div className="decision">
      <span className={`badge b-${review.decision}`}>{word}</span> by {review.reviewer} · {new Date(review.created_at).toLocaleString("en-IN", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" })}
      {review.reason && <div className="note">Reason: {review.reason}</div>}
      {children}
    </div>
  );
}

export const Reasons = ({ list }) => (list && list.length ? list.map(pretty).join(", ") : "No");

export function Loading({ state, children }) {
  if (state.error && !state.data) return <div className="card"><p className="err">Could not load: {state.error.message}</p></div>;
  if (!state.data) return <div className="card"><p className="empty">Loading…</p></div>;
  return children(state.data);
}
