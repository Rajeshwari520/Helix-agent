# Helix Agent — React UI

The agent workspace (ticket queue, ticket detail with approve / edit / reject, audit trail) and the dashboard.
FastAPI serves the built files: `/agent` (queue + ticket pages) and `/dashboard` (same app, dashboard view).

| Path | What |
|---|---|
| `src/main.jsx` | entry point |
| `src/App.jsx` | header, "You are" name (stored with every decision), SLA clock, page switch |
| `src/pages/Queue.jsx` | queue: search, filters, sort, pages, new ticket form |
| `src/pages/Ticket.jsx` | ticket page: AI triage + AI reply with Approve / Edit / Reject, status, audit trail |
| `src/pages/Dashboard.jsx` | counts, charts, AI quality, human decisions, most urgent tickets |
| `src/api.js`, `src/hooks.js`, `src/util.js`, `src/components/` | API calls, small hooks, labels, shared bits |
| `build.mjs` | esbuild bundle -> `../app/static/ui/app.js` + `app.css` |

```powershell
npm install        # first time (Node.js 18+)
npm run dev        # rebuild on save; keep uvicorn running and refresh the browser
npm run build      # production build; commit app/static/ui/
```

Pages use hash URLs: `/agent#/` (queue), `/agent#/tickets/TCK-0011` (ticket), `/agent#/dashboard`.
