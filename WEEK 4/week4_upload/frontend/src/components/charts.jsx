// Small SVG/HTML chart pieces for the premium dashboard. No chart library: thin marks, hairline grid,
// one hover tooltip, and every mark is a button (click = show those tickets, keyboard reachable).
import { createContext, useCallback, useContext, useLayoutEffect, useRef, useState } from "react";

const TipContext = createContext({ show() {}, hide() {} });
export const useTip = () => useContext(TipContext);

export function TipProvider({ children }) {
  const [tip, setTip] = useState(null);
  const show = useCallback((e, content) => {
    let x, y;
    if (e.clientX !== undefined && e.type !== "focus") { x = e.clientX; y = e.clientY; }
    else { const r = e.currentTarget.getBoundingClientRect(); x = r.left + r.width / 2; y = r.top; }
    setTip({ x, y, content });
  }, []);
  const hide = useCallback(() => setTip(null), []);
  const left = tip ? Math.min(tip.x + 14, window.innerWidth - 300) : 0;
  const top = tip ? Math.max(tip.y - 14, 8) : 0;
  return (
    <TipContext.Provider value={{ show, hide }}>
      {children}
      {tip && <div className="pv-tip" role="tooltip" style={{ left, top, transform: "translateY(-100%)" }}>{tip.content}</div>}
    </TipContext.Provider>
  );
}

// Tooltip body: value first, label second; optional rows keyed with a short line of the series colour.
export function TipBody({ value, label, rows }) {
  return (
    <>
      <div className="tv">{value}</div>
      <div className="tl">{label}</div>
      {rows?.map((r) => (
        <div className="row" key={r.label}><i style={{ background: r.color || "#8f9ab5" }} /><span className="tl">{r.label}</span><b>{r.value}</b></div>
      ))}
    </>
  );
}

function useWidth() {
  const ref = useRef(null);
  const [w, setW] = useState(600);
  useLayoutEffect(() => {
    if (!ref.current) return undefined;
    const ro = new ResizeObserver(([e]) => setW(Math.max(260, Math.floor(e.contentRect.width))));
    ro.observe(ref.current);
    return () => ro.disconnect();
  }, []);
  return [ref, w];
}

const niceMax = (m) => {
  if (m <= 4) return 4;
  const p = 10 ** Math.floor(Math.log10(m));
  const n = [1, 2, 2.5, 5, 10].find((k) => k * p >= m);
  return n * p;
};

// Column chart over time. data: [{key, label, short, value, rows}] ; colour: one series colour.
export function ColumnChart({ data, color, height = 220, onPick, valueName = "tickets" }) {
  const [ref, width] = useWidth();
  const { show, hide } = useTip();
  const [hover, setHover] = useState(null);
  const pad = { l: 34, r: 8, t: 10, b: 26 };
  const innerW = width - pad.l - pad.r;
  const innerH = height - pad.t - pad.b;
  const max = niceMax(Math.max(1, ...data.map((d) => d.value)));
  const slot = data.length ? innerW / data.length : innerW;
  const barW = Math.max(2, Math.min(22, slot - 2));
  const y = (v) => pad.t + innerH - (v / max) * innerH;
  const ticks = [0, max / 2, max];
  const labelEvery = Math.max(1, Math.ceil(data.length / Math.max(2, Math.floor(innerW / 56))));
  const peak = data.reduce((a, d) => (d.value > (a?.value ?? -1) ? d : a), null);

  return (
    <div className="col-chart" ref={ref}>
      <svg width={width} height={height} role="img" aria-label={`Tickets per ${data[0]?.unit || "day"}`}>
        {ticks.map((t) => (
          <g key={t}>
            <line x1={pad.l} x2={width - pad.r} y1={y(t)} y2={y(t)} stroke={t === 0 ? "var(--pv-axis)" : "var(--pv-grid)"} strokeWidth="1" />
            <text className="tick" x={pad.l - 6} y={y(t) + 4} textAnchor="end">{Number.isInteger(t) ? t : t.toFixed(1)}</text>
          </g>
        ))}
        {data.map((d, i) => {
          const x = pad.l + i * slot + (slot - barW) / 2;
          const h = Math.max(0, pad.t + innerH - y(d.value));
          const r = Math.min(4, barW / 2, h);
          const top = pad.t + innerH - h;
          const path = h > 0
            ? `M${x},${pad.t + innerH} V${top + r} Q${x},${top} ${x + r},${top} H${x + barW - r} Q${x + barW},${top} ${x + barW},${top + r} V${pad.t + innerH} Z`
            : "";
          const active = hover === d.key;
          const tip = (e) => { setHover(d.key); show(e, <TipBody value={`${d.value} ${valueName}`} label={d.label} rows={d.rows} />); };
          return (
            <g key={d.key}>
              {path && <path d={path} fill={color} opacity={hover && !active ? 0.55 : 1} />}
              {i % labelEvery === 0 && <text className="tick" x={pad.l + i * slot + slot / 2} y={height - 8} textAnchor="middle">{d.short}</text>}
              <rect x={pad.l + i * slot} y={pad.t} width={slot} height={innerH} fill="transparent"
                tabIndex={0} role="button" aria-label={`${d.label}: ${d.value} ${valueName}`} style={{ cursor: onPick ? "pointer" : "default", outline: "none" }}
                onPointerMove={tip} onFocus={tip} onPointerLeave={() => { setHover(null); hide(); }} onBlur={() => { setHover(null); hide(); }}
                onClick={() => onPick?.(d)} onKeyDown={(e) => { if (e.key === "Enter") onPick?.(d); }} />
            </g>
          );
        })}
        {peak && peak.value > 0 && (() => {
          const i = data.indexOf(peak);
          return <text x={pad.l + i * slot + slot / 2} y={y(peak.value) - 6} textAnchor="middle" fill="var(--pv-ink)" fontSize="11" fontWeight="700">{peak.value}</text>;
        })()}
      </svg>
    </div>
  );
}

// Ranked horizontal bars (one series = one colour). rows: [{key, label, value}]
export function HBars({ rows, color, total, onPick, unit = "tickets", empty = "None" }) {
  const { show, hide } = useTip();
  if (!rows.length) return <p className="empty">{empty}</p>;
  const max = Math.max(1, ...rows.map((r) => r.value));
  const sum = total ?? rows.reduce((n, r) => n + r.value, 0);
  return rows.map((r) => {
    const share = sum ? Math.round((r.value / sum) * 100) : 0;
    const tip = (e) => show(e, <TipBody value={`${r.value} ${unit}`} label={`${r.label} · ${share}% of ${sum}`} />);
    const inner = (
      <>
        <span className="hb-lab">{r.label}</span>
        <span className="hb-track"><span className="hb-fill" style={{ display: "block", width: `${(r.value / max) * 100}%`, background: r.color || color }} /></span>
        <span className="hb-n">{r.value}<small>{share}%</small></span>
      </>
    );
    return onPick ? (
      <button type="button" key={r.key} className="hb" onClick={() => onPick(r)} onPointerMove={tip} onFocus={tip} onPointerLeave={hide} onBlur={hide}
        aria-label={`${r.label}: ${r.value} ${unit}, ${share}%. Show these tickets`}>{inner}</button>
    ) : <div key={r.key} className="hb" onPointerMove={tip} onPointerLeave={hide}>{inner}</div>;
  });
}

// Tall segmented bar (part-to-whole, <= 6 parts) with a legend that is also clickable.
export function SegmentBar({ parts, onPick, unit = "tickets", inkOn = () => "#ffffff" }) {
  const { show, hide } = useTip();
  const total = parts.reduce((n, p) => n + p.value, 0);
  if (!total) return <p className="empty">No tickets in this view.</p>;
  return (
    <>
      <div className="seg-bar" role="list">
        {parts.filter((p) => p.value).map((p) => {
          const share = Math.round((p.value / total) * 100);
          const tip = (e) => show(e, <TipBody value={`${p.value} ${unit}`} label={`${p.label} · ${share}%`} />);
          return (
            <div key={p.key} role="listitem" tabIndex={0} aria-label={`${p.label}: ${p.value} (${share}%)`}
              style={{ flex: p.value, background: p.color, color: inkOn(p) }}
              onPointerMove={tip} onFocus={tip} onPointerLeave={hide} onBlur={hide}
              onClick={() => onPick?.(p)} onKeyDown={(e) => { if (e.key === "Enter") onPick?.(p); }}>
              {share >= 12 ? `${p.icon ? `${p.icon} ` : ""}${p.value}` : ""}
            </div>
          );
        })}
      </div>
      <div className="seg-legend">
        {parts.map((p) => (
          <button type="button" key={p.key} onClick={() => onPick?.(p)} disabled={!onPick || !p.value}>
            <span className="sw" style={{ background: p.color }} />
            <span>{p.icon ? `${p.icon} ` : ""}{p.label}</span>
            <b>{p.value}</b>
            <span className="pct">{Math.round((p.value / total) * 100)}%</span>
          </button>
        ))}
      </div>
    </>
  );
}

// Before / now comparison for model quality (emphasis: "now" in the series colour, "before" muted).
export function Compare({ rows, beforeColor, nowColor }) {
  const { show, hide } = useTip();
  return rows.map((r) => (
    <div className="cmp" key={r.label}
      onPointerMove={(e) => show(e, <TipBody value={r.now == null ? "-" : `${Math.round(r.now * 100)}%`} label={r.label}
        rows={[{ label: "Week 1 rules", value: r.before == null ? "-" : `${Math.round(r.before * 100)}%`, color: beforeColor },
               { label: "Now", value: r.now == null ? "-" : `${Math.round(r.now * 100)}%`, color: nowColor }]} />)}
      onPointerLeave={hide}>
      <span style={{ color: "var(--pv-ink-2)" }}>{r.label}</span>
      <span className="bars">
        <span className="bar-line before"><span className="t"><i style={{ width: `${(r.before ?? 0) * 100}%`, background: beforeColor }} /></span><b>{r.before == null ? "-" : `${Math.round(r.before * 100)}%`}</b></span>
        <span className="bar-line"><span className="t"><i style={{ width: `${(r.now ?? 0) * 100}%`, background: nowColor }} /></span><b>{r.now == null ? "-" : `${Math.round(r.now * 100)}%`}</b></span>
      </span>
    </div>
  ));
}
