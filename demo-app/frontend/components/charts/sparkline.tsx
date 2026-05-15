"use client";

import type { ScorePoint } from "@/lib/types";

export function Sparkline({
  data,
  width = 160,
  height = 40,
  peakRound,
  color,
}: {
  data: ScorePoint[];
  width?: number;
  height?: number;
  peakRound?: number;
  color?: string;
}) {
  if (!data || data.length === 0) return null;
  const xs = data.map((d) => d.round);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const yMin = 0.6;
  const yMax = 1.0;
  const px = (r: number) =>
    maxX === minX ? width / 2 : ((r - minX) / (maxX - minX)) * (width - 6) + 3;
  const py = (v: number) => height - 3 - ((v - yMin) / (yMax - yMin)) * (height - 6);
  const pts = data.map((d) => `${px(d.round)},${py(d.avg_score)}`).join(" ");
  const last = data[data.length - 1];
  const peak =
    data.find((d) => d.round === peakRound) ||
    data.reduce((a, b) => (b.avg_score > a.avg_score ? b : a));
  const stroke = color || "var(--primary)";

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      className="sparkline"
      aria-hidden="true"
    >
      <polyline
        fill="none"
        stroke={stroke}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        points={pts}
      />
      <circle cx={px(peak.round)} cy={py(peak.avg_score)} r="3" fill="var(--accent)" />
      <circle cx={px(last.round)} cy={py(last.avg_score)} r="2.2" fill={stroke} />
    </svg>
  );
}
