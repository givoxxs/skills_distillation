"use client";

import { useEffect, useMemo, useRef } from "react";

type Row =
  | { type: "same"; left: string; right: string; li: number; ri: number }
  | { type: "rem"; left: string; right: null; li: number; ri: null }
  | { type: "add"; left: null; right: string; li: null; ri: number };

function lcsLines(a: string[], b: string[]): Row[] {
  const m = a.length;
  const n = b.length;
  const dp: Uint16Array[] = Array.from({ length: m + 1 }, () => new Uint16Array(n + 1));
  for (let i = m - 1; i >= 0; i--) {
    for (let j = n - 1; j >= 0; j--) {
      if (a[i] === b[j]) dp[i][j] = dp[i + 1][j + 1] + 1;
      else dp[i][j] = Math.max(dp[i + 1][j], dp[i][j + 1]);
    }
  }
  const out: Row[] = [];
  let i = 0;
  let j = 0;
  while (i < m && j < n) {
    if (a[i] === b[j]) {
      out.push({ type: "same", left: a[i], right: b[j], li: i + 1, ri: j + 1 });
      i++;
      j++;
    } else if (dp[i + 1][j] >= dp[i][j + 1]) {
      out.push({ type: "rem", left: a[i], right: null, li: i + 1, ri: null });
      i++;
    } else {
      out.push({ type: "add", left: null, right: b[j], li: null, ri: j + 1 });
      j++;
    }
  }
  while (i < m) {
    out.push({ type: "rem", left: a[i], right: null, li: i + 1, ri: null });
    i++;
  }
  while (j < n) {
    out.push({ type: "add", left: null, right: b[j], li: null, ri: j + 1 });
    j++;
  }
  return out;
}

type Cell = { type: "same" | "rem" | "add" | "empty"; n?: number; text?: string };

export function DiffViewer({
  leftLabel,
  rightLabel,
  left,
  right,
}: {
  leftLabel: string;
  rightLabel: string;
  left: string;
  right: string;
}) {
  const rows = useMemo(() => {
    const a = (left || "").replace(/\r/g, "").split("\n");
    const b = (right || "").replace(/\r/g, "").split("\n");
    return lcsLines(a, b);
  }, [left, right]);

  const stats = useMemo(() => {
    let add = 0;
    let rem = 0;
    rows.forEach((r) => {
      if (r.type === "add") add++;
      else if (r.type === "rem") rem++;
    });
    return { add, rem };
  }, [rows]);

  const pairs: { l: Cell; r: Cell }[] = [];
  for (const r of rows) {
    if (r.type === "same")
      pairs.push({
        l: { type: "same", n: r.li, text: r.left },
        r: { type: "same", n: r.ri, text: r.right },
      });
    else if (r.type === "add")
      pairs.push({ l: { type: "empty" }, r: { type: "add", n: r.ri, text: r.right } });
    else pairs.push({ l: { type: "rem", n: r.li, text: r.left }, r: { type: "empty" } });
  }

  // ── Synchronised scroll: when the user scrolls one pane, mirror the
  // scrollTop + scrollLeft on the other (git-style side-by-side review).
  // Uses a single "driver" guard so we don't ping-pong infinitely between
  // the two scroll events. Native scroll listeners give us frame-perfect
  // sync without re-rendering React.
  const leftRef = useRef<HTMLDivElement | null>(null);
  const rightRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const lp = leftRef.current;
    const rp = rightRef.current;
    if (!lp || !rp) return;

    let driver: "l" | "r" | null = null;
    const clearDriver = () => {
      driver = null;
    };

    const onLeft = () => {
      if (driver === "r") return;
      driver = "l";
      rp.scrollTop = lp.scrollTop;
      rp.scrollLeft = lp.scrollLeft;
      // Release on next frame so the matched scroll event fires within the
      // same driver lock, then resets.
      requestAnimationFrame(clearDriver);
    };
    const onRight = () => {
      if (driver === "l") return;
      driver = "r";
      lp.scrollTop = rp.scrollTop;
      lp.scrollLeft = rp.scrollLeft;
      requestAnimationFrame(clearDriver);
    };

    lp.addEventListener("scroll", onLeft, { passive: true });
    rp.addEventListener("scroll", onRight, { passive: true });
    return () => {
      lp.removeEventListener("scroll", onLeft);
      rp.removeEventListener("scroll", onRight);
    };
  }, [left, right]);

  return (
    <div style={{ display: "flex", flexDirection: "column" }}>
      <div className="row-between" style={{ marginBottom: 12 }}>
        <div style={{ display: "flex", gap: 16, fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--fg-muted)" }}>
          <span>
            <span style={{ color: "var(--diff-add-fg)" }}>+{stats.add}</span> added
          </span>
          <span>
            <span style={{ color: "var(--diff-rem-fg)" }}>−{stats.rem}</span> removed
          </span>
        </div>
        <div style={{ fontSize: 12, color: "var(--fg-subtle)" }}>{rows.length} lines compared</div>
      </div>
      <div className="diff" role="region" aria-label="Diff between rounds">
        <div className="diff-pane" ref={leftRef}>
          <div className="diff-header">
            <span>{leftLabel}</span>
          </div>
          {pairs.map((p, i) => (
            <div
              key={"l" + i}
              className={
                "diff-row " + (p.l.type === "rem" ? "rem" : p.l.type === "empty" ? "empty" : "")
              }
            >
              <div className="diff-gutter">{p.l.n || ""}</div>
              <div className="diff-content">{p.l.text || ""}</div>
            </div>
          ))}
        </div>
        <div className="diff-pane" ref={rightRef}>
          <div className="diff-header">
            <span>{rightLabel}</span>
          </div>
          {pairs.map((p, i) => (
            <div
              key={"r" + i}
              className={
                "diff-row " + (p.r.type === "add" ? "add" : p.r.type === "empty" ? "empty" : "")
              }
            >
              <div className="diff-gutter">{p.r.n || ""}</div>
              <div className="diff-content">{p.r.text || ""}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
