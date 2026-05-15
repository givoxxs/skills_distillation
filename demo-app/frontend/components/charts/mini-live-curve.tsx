"use client";

type Point = { idx: number; score: number };

export function MiniLiveCurve({
  points,
  target = null,
  width = 360,
  height = 110,
}: {
  points: Point[];
  target?: number | null;
  width?: number;
  height?: number;
}) {
  const W = width;
  const H = height;
  const padL = 26;
  const padR = 8;
  const padT = 10;
  const padB = 18;
  const xs = points.map((p) => p.idx);
  const minX = 1;
  const maxX = Math.max(3, ...xs, 3);
  const yMin = 0.5;
  const yMax = 1.0;
  const px = (i: number) => padL + ((i - minX) / (maxX - minX)) * (W - padL - padR);
  const py = (v: number) => padT + (1 - (v - yMin) / (yMax - yMin)) * (H - padT - padB);
  const pts = points.map((p) => `${px(p.idx)},${py(p.score)}`).join(" ");

  return (
    <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} style={{ display: "block" }}>
      {[0.6, 0.8, 1.0].map((t, i) => (
        <g key={i}>
          <line x1={padL} x2={W - padR} y1={py(t)} y2={py(t)} stroke="var(--line-faint)" />
          <text
            x={padL - 4}
            y={py(t) + 3}
            fontSize="9"
            textAnchor="end"
            fill="var(--fg-faint)"
            fontFamily="var(--font-mono)"
          >
            {t.toFixed(1)}
          </text>
        </g>
      ))}
      {target !== null && target !== undefined && (
        <line
          x1={padL}
          x2={W - padR}
          y1={py(target)}
          y2={py(target)}
          stroke="var(--accent)"
          strokeWidth="1"
          strokeDasharray="3 3"
          opacity="0.6"
        />
      )}
      {points.length > 1 && (
        <polyline
          points={pts}
          fill="none"
          stroke="var(--primary)"
          strokeWidth="2"
          strokeLinejoin="round"
          strokeLinecap="round"
        />
      )}
      {points.map((p, i) => (
        <circle
          key={i}
          cx={px(p.idx)}
          cy={py(p.score)}
          r="3.5"
          fill="var(--primary)"
          stroke="var(--bg)"
          strokeWidth="2"
        />
      ))}
      {[1, 2, 3].map((i) => (
        <text
          key={i}
          x={px(i)}
          y={H - padB + 14}
          fontSize="9"
          textAnchor="middle"
          fill="var(--fg-faint)"
          fontFamily="var(--font-mono)"
        >
          tc {i}
        </text>
      ))}
    </svg>
  );
}
