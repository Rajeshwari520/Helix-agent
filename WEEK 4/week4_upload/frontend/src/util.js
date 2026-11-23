export const LABELS = {
  hr_sensitive: "HR sensitive", security_or_fraud: "Security or fraud", legal_or_media: "Legal or media",
  prompt_injection: "Prompt injection", critical_priority: "Critical priority", privacy_request: "Privacy request",
  complaint_or_anger: "Complaint or anger", low_classifier_confidence: "Low AI confidence", web_form: "Web form",
  low_confidence: "Low confidence",
};
export const pretty = (s) => LABELS[s] || String(s ?? "").replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());
export const fmt = (iso) => iso
  ? new Date(iso).toLocaleString("en-IN", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" })
  : "-";
export const pct = (x) => (x == null ? "-" : `${Math.round(x * 100)}%`);
export const SLA_LABEL = { breached: "Overdue", due_soon: "Due < 4 h", on_track: "On track", closed: "Replied / closed" };
export const OPEN = new Set(["New", "Triaged", "Assigned", "Escalated", "In Progress"]);
export const PRIORITY_RANK = { Critical: 0, High: 1, Medium: 2, Low: 3 };
export const PRI_COLOR = { Critical: "#C8553D", High: "#F2A541", Medium: "#0B7A75", Low: "#7A9CA5" };
export const SLA_COLOR = { breached: "#C8553D", due_soon: "#F2A541", on_track: "#0B7A75" };

export const store = {
  get(k, fallback = null) { try { const v = localStorage.getItem(k); return v === null ? fallback : JSON.parse(v); } catch (e) { return fallback; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* private mode */ } },
};
