"use client";

import { useEffect, useRef, useState } from "react";
import type { ScorePoint } from "@/lib/types";

export function LearningCurve({
  data,
  peakRound,
  height = 320,
  variant = "smooth",
  showThreshold = true,
}: {
  data: ScorePoint[];
  peakRound?: number;
  height?: number;
  variant?: "smooth" | "line" | "step";
  showThreshold?: boolean;
}) {
  const ref = useRef<HTMLDivElement | null>(null);
  const [w, setW] = useState(640);
  const [hover, setHover] = useState<ScorePoint | null>(null);

  useEffect(() => {
    if (!ref.current) return;
    const ro = new ResizeObserver((entries) => {
      for (const e of entries) {
        const cw = Math.max(300, Math.floor(e.contentRect.width));
        setW(cw);
      }
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
  const yMin = 0.6;
  const yMax = 1.0;
  const xs = data.map((d) => d.round);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const px = (r: number) =>
    maxX === minX ? W / 2 : padL + ((r - minX) / (maxX - minX)) * (W - padL - padR);
  const py = (v: number) => padT + (1 - (v - yMin) / (yMax - yMin)) * (H - padT - padB);

  const yTicks = [0.6, 0.7, 0.8, 0.9, 1.0];
  const peak =
    data.find((d) => d.round === peakRound) ||
    data.reduce((a, b) => (b.avg_score > a.avg_score ? b : a));

  let line = "";
  let areaPath = "";
  const pts = data.map((p) => [px(p.round), py(p.avg_score)] as const);

  if (variant === "step") {
    let d = "";
    data.forEach((p, i) => {
      if (i === 0) d += `M ${px(p.round)} ${py(p.avg_score)}`;
      else {
        const prev = data[i - 1];
        d += ` L ${px(p.round)} ${py(prev.avg_score)} L ${px(p.round)} ${py(p.avg_score)}`;
      }
    });
    line = d;
  } else if (variant === "smooth" && pts.length >= 2) {
    let d = `M ${pts[0][0]} ${pts[0][1]}`;
    for (let i = 0; i < pts.length - 1; i++) {
      const p0 = pts[i - 1] || pts[i];
      const p1 = pts[i];
      const p2 = pts[i + 1];
      const p3 = pts[i + 2] || p2;
      const cp1x = p1[0] + (p2[0] - p0[0]) / 6;
      const cp1y = p1[1] + (p2[1] - p0[1]) / 6;
      const cp2x = p2[0] - (p3[0] - p1[0]) / 6;
      const cp2y = p2[1] - (p3[1] - p1[1]) / 6;
      d += ` C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${p2[0]} ${p2[1]}`;
    }
    line = d;
  } else {
    line = pts.map((p, i) => (i === 0 ? "M" : "L") + " " + p[0] + " " + p[1]).join(" ");
  }

  if (variant !== "step" && pts.length > 0) {
    const areaTop = pts.map((p, i) => (i === 0 ? "M" : "L") + " " + p[0] + " " + p[1]).join(" ");
    areaPath = `${areaTop} L ${pts[pts.length - 1][0]} ${H - padB} L ${pts[0][0]} ${H - padB} Z`;
  }

  function onMove(e: React.MouseEvent<SVGSVGElement>) {
    const svg = e.currentTarget;
    const r = svg.getBoundingClientRect();
    const x = ((e.clientX - r.left) / r.width) * W;
    let best = data[0];
    let bestDist = Infinity;
    for (const d of data) {
      const dist = Math.abs(px(d.round) - x);
      if (dist < bestDist) {
        best = d;
        bestDist = dist;
      }
    }
    setHover(best);
  }

  return (
    <div ref={ref} style={{ width: "100%", position: "relative" }}>
      <svg
        width="100%"
        height={H}
        viewBox={`0 0 ${W} ${H}`}
        onMouseMove={onMove}
        onMouseLeave={() => setHover(null)}
        style={{ display: "block" }}
      >
        {yTicks.map((t, i) => (
          <g key={i}>
            <line
              x1={padL}
              x2={W - padR}
              y1={py(t)}
              y2={py(t)}
              stroke="var(--line-faint)"
              strokeWidth="1"
            />
            <text
              x={padL - 8}
              y={py(t) + 4}
              fontSize="11"
              textAnchor="end"
              fill="var(--fg-faint)"
              fontFamily="var(--font-mono)"
            >
              {t.toFixed(1)}
            </text>
          </g>
        ))}
        {xs.map((r) => (
          <text
            key={r}
            x={px(r)}
            y={H - padB + 18}
            fontSize="11"
            textAnchor="middle"
            fill="var(--fg-faint)"
            fontFamily="var(--font-mono)"
          >
            R{r}
          </text>
        ))}
        {showThreshold && (
          <g>
            <line
              x1={padL}
              x2={W - padR}
              y1={py(0.7)}
              y2={py(0.7)}
              stroke="var(--danger)"
              strokeOpacity="0.5"
              strokeWidth="1"
              strokeDasharray="4 4"
            />
            <text
              x={W - padR - 4}
              y={py(0.7) - 6}
              fontSize="10"
              textAnchor="end"
              fill="var(--danger)"
              fontStyle="italic"
              opacity="0.75"
            >
              stop threshold · 0.70
            </text>
          </g>
        )}
        {variant !== "step" && (
          <path d={areaPath} fill="var(--primary)" fillOpacity="0.08" />
        )}
        <path
          d={line}
          fill="none"
          stroke="var(--primary)"
          strokeWidth="2"
          strokeLinejoin="round"
          strokeLinecap="round"
        />
        {data.map((d, i) => {
          const isPeak = d.round === peak.round;
          const isHover = hover && hover.round === d.round;
          return (
            <g key={i}>
              {isPeak && (
                <circle
                  cx={px(d.round)}
                  cy={py(d.avg_score)}
                  r="9"
                  fill="var(--accent)"
                  fillOpacity="0.18"
                />
              )}
              <circle
                cx={px(d.round)}
                cy={py(d.avg_score)}
                r={isPeak ? 6 : isHover ? 4.5 : 3.5}
                fill={isPeak ? "var(--accent)" : "var(--primary)"}
                stroke="var(--bg)"
                strokeWidth="2"
              />
            </g>
          );
        })}
        <g transform={`translate(${px(peak.round)}, ${py(peak.avg_score) - 18})`}>
          <rect x="-30" y="-14" width="60" height="18" rx="4" fill="var(--accent)" />
          <text
            x="0"
            y="-1"
            textAnchor="middle"
            fill="white"
            fontSize="11"
            fontWeight="600"
            fontFamily="var(--font-mono)"
          >
            peak {peak.avg_score.toFixed(3)}
          </text>
        </g>
        {hover && (
          <line
            x1={px(hover.round)}
            x2={px(hover.round)}
            y1={padT}
            y2={H - padB}
            stroke="var(--line-strong)"
            strokeWidth="1"
            strokeDasharray="3 3"
          />
        )}
      </svg>
      {hover && (
        <div
          style={{
            position: "absolute",
            left: Math.min(w - 160, Math.max(0, px(hover.round) + 12)),
            top: py(hover.avg_score) - 4,
            background: "var(--surface)",
            border: "1px solid var(--line)",
            borderRadius: 8,
            padding: "8px 12px",
            fontSize: 12,
            boxShadow: "var(--shadow-2)",
            pointerEvents: "none",
            minWidth: 140,
          }}
        >
          <div
            style={{
              color: "var(--fg-subtle)",
              fontSize: 11,
              textTransform: "uppercase",
              letterSpacing: "0.06em",
              marginBottom: 2,
            }}
          >
            Round {hover.round}
          </div>
          <div className="mono tnum" style={{ fontSize: 16, fontWeight: 600 }}>
            {hover.avg_score.toFixed(3)}
          </div>
          <div style={{ color: "var(--fg-subtle)", fontSize: 11, marginTop: 2 }}>
            avg hybrid score
          </div>
        </div>
      )}
    </div>
  );
}
