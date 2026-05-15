"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { ApiCall } from "@/lib/types";

type Row = { round: number; student: number; judge: number; teacher: number; total: number };

export function CostStackedBar({
  apiCalls,
  height = 280,
}: {
  apiCalls: ApiCall[];
  height?: number;
}) {
  const stages = ["student", "judge", "teacher"] as const;
  const stageColors: Record<string, string> = {
    student: "var(--primary)",
    judge: "var(--accent)",
    teacher: "var(--success)",
  };

  const grouped: Row[] = useMemo(() => {
    const m: Record<number, Row> = {};
    for (const c of apiCalls) {
      if (!m[c.round]) m[c.round] = { round: c.round, student: 0, judge: 0, teacher: 0, total: 0 };
      m[c.round][c.stage] += c.cost_usd;
      m[c.round].total += c.cost_usd;
    }
    return Object.values(m).sort((a, b) => a.round - b.round);
  }, [apiCalls]);

  const ref = useRef<HTMLDivElement | null>(null);
  const [w, setW] = useState(640);
  const [hover, setHover] = useState<(Row & { x: number }) | null>(null);

  useEffect(() => {
    if (!ref.current) return;
    const ro = new ResizeObserver((entries) => {
      for (const e of entries) setW(Math.max(300, Math.floor(e.contentRect.width)));
    });
    ro.observe(ref.current);
    return () => ro.disconnect();
  }, []);

  const padL = 44;
  const padR = 18;
  const padT = 18;
  const padB = 32;
  const W = w;
  const H = height;
  const maxTotal = Math.max(0.0001, ...grouped.map((g) => g.total));
  const yMax = Math.max(0.01, Math.ceil(maxTotal * 10) / 10);
  const barW = Math.max(14, ((W - padL - padR) / Math.max(1, grouped.length)) * 0.6);
  const px = (i: number) => padL + (W - padL - padR) * ((i + 0.5) / Math.max(1, grouped.length));
  const py = (v: number) => padT + (1 - v / yMax) * (H - padT - padB);

  const ticks = 4;
  const yTicks: number[] = [];
  for (let i = 0; i <= ticks; i++) yTicks.push((yMax * i) / ticks);

  return (
    <div ref={ref} style={{ width: "100%", position: "relative" }}>
      <svg width="100%" height={H} viewBox={`0 0 ${W} ${H}`} style={{ display: "block" }}>
        {yTicks.map((t, i) => (
          <g key={i}>
            <line x1={padL} x2={W - padR} y1={py(t)} y2={py(t)} stroke="var(--line-faint)" />
            <text
              x={padL - 8}
              y={py(t) + 4}
              fontSize="11"
              textAnchor="end"
              fill="var(--fg-faint)"
              fontFamily="var(--font-mono)"
            >
              ${t.toFixed(2)}
            </text>
          </g>
        ))}
        {grouped.map((g, i) => {
          let y0 = py(0);
          return (
            <g
              key={g.round}
              onMouseEnter={() => setHover({ ...g, x: px(i) })}
              onMouseLeave={() => setHover(null)}
            >
              {stages.map((stage) => {
                const v = g[stage];
                const h = py(0) - py(v);
                const y = y0 - h;
                y0 = y;
                return (
                  <rect
                    key={stage}
                    x={px(i) - barW / 2}
                    y={y}
                    width={barW}
                    height={h}
                    fill={stageColors[stage]}
                    fillOpacity={hover && hover.round !== g.round ? 0.35 : 1}
                  />
                );
              })}
              <text
                x={px(i)}
                y={H - padB + 18}
                fontSize="11"
                textAnchor="middle"
                fill="var(--fg-faint)"
                fontFamily="var(--font-mono)"
              >
                R{g.round}
              </text>
            </g>
          );
        })}
      </svg>
      <div style={{ display: "flex", gap: 16, marginTop: 8, fontSize: 12, color: "var(--fg-muted)" }}>
        {stages.map((s) => (
          <div key={s} style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <span style={{ width: 10, height: 10, borderRadius: 2, background: stageColors[s] }} />
            <span style={{ textTransform: "capitalize" }}>{s}</span>
          </div>
        ))}
      </div>
      {hover && (
        <div
          style={{
            position: "absolute",
            left: Math.min(w - 200, hover.x + 12),
            top: 12,
            background: "var(--surface)",
            border: "1px solid var(--line)",
            borderRadius: 8,
            padding: "8px 12px",
            fontSize: 12,
            minWidth: 180,
            boxShadow: "var(--shadow-2)",
            pointerEvents: "none",
          }}
        >
          <div
            style={{
              color: "var(--fg-subtle)",
              fontSize: 11,
              textTransform: "uppercase",
              letterSpacing: "0.06em",
              marginBottom: 4,
            }}
          >
            Round {hover.round}
          </div>
          {stages.map((s) => (
            <div key={s} style={{ display: "flex", justifyContent: "space-between", marginTop: 2 }}>
              <span style={{ color: stageColors[s] }}>{s}</span>
              <span className="mono tnum">${hover[s].toFixed(3)}</span>
            </div>
          ))}
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              marginTop: 6,
              paddingTop: 4,
              borderTop: "1px solid var(--line-faint)",
              fontWeight: 600,
            }}
          >
            <span>Total</span>
            <span className="mono tnum">${hover.total.toFixed(3)}</span>
          </div>
        </div>
      )}
    </div>
  );
}
