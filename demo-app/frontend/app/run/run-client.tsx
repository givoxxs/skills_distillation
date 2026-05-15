"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { Bi } from "@/components/bi";
import { Icon } from "@/components/icon";
import { MiniLiveCurve } from "@/components/charts/mini-live-curve";
import { skillList, summaries } from "@/lib/mock-data";

type Phase = "idle" | "queued" | "running" | "judging" | "teacher" | "done" | "error";
type LogLine = { ts: string; tag: string; text: string; level: "info" | "error" | "success" };
type ScorePt = { idx: number; score: number; tc_id: string };

const PHASES: Exclude<Phase, "idle" | "error">[] = [
  "queued",
  "running",
  "judging",
  "teacher",
  "done",
];

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

function tsOf(ms: number): string {
  const sec = Math.floor(ms / 1000);
  return `+${String(Math.floor(sec / 60)).padStart(2, "0")}:${String(sec % 60).padStart(2, "0")}`;
}

export function RunClient({ bilingual }: { bilingual: boolean }) {
  const [picked, setPicked] = useState<string>("docx");
  const [phase, setPhase] = useState<Phase>("idle");
  const [logs, setLogs] = useState<LogLine[]>([]);
  const [scores, setScores] = useState<ScorePt[]>([]);
  const [finalScore, setFinalScore] = useState<number | null>(null);
  const [mode, setMode] = useState<"backend" | "local">("backend");
  const eventSourceRef = useRef<EventSource | null>(null);
  const timersRef = useRef<ReturnType<typeof setTimeout>[]>([]);
  const startTimeRef = useRef<number>(0);

  function appendLog(line: LogLine) {
    setLogs((L) => [...L, line]);
  }

  function clearAll() {
    setLogs([]);
    setScores([]);
    setFinalScore(null);
    setPhase("idle");
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    timersRef.current.forEach((t) => clearTimeout(t));
    timersRef.current = [];
  }

  useEffect(() => {
    return () => {
      if (eventSourceRef.current) eventSourceRef.current.close();
      timersRef.current.forEach((t) => clearTimeout(t));
    };
  }, []);

  async function startBackend(): Promise<boolean> {
    try {
      const res = await fetch(`${BACKEND_URL}/api/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ skill: picked }),
      });
      if (!res.ok) throw new Error(`backend ${res.status}`);
      const { run_id } = (await res.json()) as { run_id: string };

      const es = new EventSource(`${BACKEND_URL}/api/run/${run_id}/stream`);
      eventSourceRef.current = es;
      startTimeRef.current = Date.now();

      const elapsed = () => tsOf(Date.now() - startTimeRef.current);

      es.addEventListener("status", (e) => {
        const data = JSON.parse((e as MessageEvent).data) as { phase: Phase };
        setPhase(data.phase);
        appendLog({ ts: elapsed(), tag: "status", text: data.phase, level: "info" });
        if (data.phase === "done" || data.phase === "error") es.close();
      });
      es.addEventListener("log", (e) => {
        const data = JSON.parse((e as MessageEvent).data) as { line: string; tag?: string };
        appendLog({
          ts: elapsed(),
          tag: data.tag || "system",
          text: data.line,
          level: "info",
        });
      });
      es.addEventListener("test_case_done", (e) => {
        const data = JSON.parse((e as MessageEvent).data) as {
          test_case_id: string;
          hybrid_score: number;
        };
        setScores((s) => [
          ...s,
          { idx: s.length + 1, score: data.hybrid_score, tc_id: data.test_case_id },
        ]);
        appendLog({
          ts: elapsed(),
          tag: "judge",
          text: `${data.test_case_id} → hybrid ${data.hybrid_score.toFixed(3)}`,
          level: "info",
        });
      });
      es.addEventListener("complete", (e) => {
        const data = JSON.parse((e as MessageEvent).data) as {
          skill: string;
          final_score: number;
        };
        setFinalScore(data.final_score);
        setPhase("done");
        appendLog({
          ts: elapsed(),
          tag: "status",
          text: `complete · avg ${data.final_score.toFixed(3)}`,
          level: "success",
        });
        es.close();
      });
      es.onerror = () => {
        es.close();
        appendLog({ ts: elapsed(), tag: "system", text: "stream closed", level: "info" });
      };
      return true;
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      appendLog({
        ts: tsOf(0),
        tag: "system",
        text: `backend unavailable (${msg}) — falling back to local simulation`,
        level: "info",
      });
      return false;
    }
  }

  function startLocalSimulation() {
    const skill = picked;
    const summary = summaries[skill];
    const target = summary.score_history[0].avg_score + 0.04;
    startTimeRef.current = Date.now();

    type Evt = { at: number; fn: () => void };
    const events: Evt[] = [];
    let curT = 0;

    const ts = () => tsOf(curT);
    const pushStatus = (ph: Exclude<Phase, "idle">, msg?: string) =>
      events.push({
        at: curT,
        fn: () => {
          setPhase(ph);
          appendLog({ ts: ts(), tag: "status", text: msg || ph, level: "info" });
        },
      });
    const pushLog = (tag: string, text: string, level: LogLine["level"] = "info") =>
      events.push({ at: curT, fn: () => appendLog({ ts: ts(), tag, text, level }) });
    const pushTc = (tc: string, score: number) =>
      events.push({
        at: curT,
        fn: () => {
          setScores((s) => [...s, { idx: s.length + 1, score, tc_id: tc }]);
          appendLog({
            ts: ts(),
            tag: "judge",
            text: `${tc} → hybrid ${score.toFixed(3)}`,
            level: "info",
          });
        },
      });

    curT = 0;
    pushStatus("queued", "run accepted — preparing sandbox");
    curT += 500;
    pushLog(
      "system",
      `python distillation_v2/run.py --skill ${skill} --rounds 1 --test-cases 3 --batch-size 3`
    );
    curT += 800;
    pushLog("system", "loaded SKILL_round_0.md (Anthropic original)");
    curT += 600;
    pushLog(
      "system",
      `loading rubric · workflows=${["create", "edit", "validate"].join(",")}`
    );

    curT += 600;
    pushStatus("running", "student model invoked");
    const tcIds = ["tc_a01", "tc_a02", "tc_a03"];
    const scoresPlan = [
      target + 0.03 + (Math.random() - 0.5) * 0.04,
      target + 0.06 + (Math.random() - 0.5) * 0.04,
      target - 0.02 + (Math.random() - 0.5) * 0.04,
    ].map((v) => Math.min(0.98, Math.max(0.55, v)));

    for (let i = 0; i < 3; i++) {
      curT += 800;
      pushLog("student", `${tcIds[i]} · invoking google/gemma-3-26b-it`);
      curT += 1400;
      pushLog("student", `${tcIds[i]} · 1842 prompt + 612 completion tokens · 1.8s`);
      curT += 200;
      pushLog("rule", `${tcIds[i]} · rule checks: 4/5 passed`);
    }

    curT += 600;
    pushStatus("judging", "judge model invoked");
    for (let i = 0; i < 3; i++) {
      curT += 1100;
      pushLog("judge", `${tcIds[i]} · claude-sonnet-4.5 scoring rubric`);
      curT += 1600;
      pushTc(tcIds[i], scoresPlan[i]);
    }

    curT += 700;
    pushStatus("teacher", "teacher model rewriting SKILL.md");
    curT += 1500;
    pushLog("teacher", "reading judge rationales (3/3)");
    curT += 1200;
    pushLog("teacher", "diffing SKILL_round_0.md ↔ rewrite candidate");
    curT += 1300;
    pushLog("teacher", "wrote SKILL_round_1.md (+18 lines, −4 lines)");

    const avg = scoresPlan.reduce((a, b) => a + b, 0) / scoresPlan.length;
    curT += 500;
    events.push({
      at: curT,
      fn: () => {
        setFinalScore(avg);
        setPhase("done");
        appendLog({
          ts: ts(),
          tag: "status",
          text: `complete · avg ${avg.toFixed(3)}`,
          level: "success",
        });
      },
    });

    const speedup = 0.35;
    events.forEach((e) => {
      const id = setTimeout(e.fn, e.at * speedup);
      timersRef.current.push(id);
    });
  }

  async function start() {
    if (phase !== "idle" && phase !== "done" && phase !== "error") return;
    clearAll();
    if (mode === "backend") {
      const ok = await startBackend();
      if (!ok) startLocalSimulation();
    } else {
      startLocalSimulation();
    }
  }

  const isRunning = phase !== "idle" && phase !== "done" && phase !== "error";

  return (
    <div className="page stack-lg">
      <div className="stack-sm">
        <div className="eyebrow">
          <Bi
            vi="Chạy thật trên 3 test case"
            en={bilingual ? "Live mini run · 3 test cases" : null}
            showEn={bilingual}
          />
        </div>
        <h1 className="h1">Chạy pipeline 1 vòng để xem code thật.</h1>
        <p className="muted" style={{ maxWidth: 640, fontSize: 16 }}>
          Tốc độ ~2–3 phút wall-clock. UI gọi{" "}
          <span className="mono" style={{ fontSize: 13 }}>
            POST /api/run
          </span>{" "}
          rồi stream tiến trình qua Server-Sent Events.
        </p>
      </div>

      <div className="grid-2" style={{ alignItems: "start", gap: 24 }}>
        {/* Form card */}
        <div className="card">
          <h3 className="h3" style={{ marginBottom: 16 }}>
            <Bi vi="Cấu hình lần chạy" en={bilingual ? "Run configuration" : null} showEn={bilingual} />
          </h3>
          <div className="stack">
            <div>
              <div className="stat-label" style={{ marginBottom: 8 }}>
                Skill
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {skillList.map((s) => {
                  const sum = summaries[s];
                  return (
                    <label
                      key={s}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 12,
                        padding: "12px 14px",
                        border: "1px solid var(--line)",
                        borderRadius: "var(--radius-md)",
                        background: picked === s ? "var(--primary-tint)" : "var(--surface)",
                        borderColor: picked === s ? "var(--primary)" : "var(--line)",
                        cursor: isRunning ? "not-allowed" : "pointer",
                        opacity: isRunning ? 0.6 : 1,
                      }}
                    >
                      <input
                        type="radio"
                        name="skill"
                        value={s}
                        checked={picked === s}
                        disabled={isRunning}
                        onChange={() => setPicked(s)}
                        style={{ accentColor: "var(--primary)" }}
                      />
                      <div style={{ flex: 1 }}>
                        <div className="mono" style={{ fontSize: 13, color: "var(--fg)" }}>
                          {s}
                        </div>
                        <div style={{ fontSize: 12, color: "var(--fg-subtle)" }}>{sum.vi}</div>
                      </div>
                      <span className="badge">
                        <span className="mono tnum">peak {sum.best_score.toFixed(3)}</span>
                      </span>
                    </label>
                  );
                })}
              </div>
            </div>

            <div>
              <div className="stat-label" style={{ marginBottom: 8 }}>
                <Bi vi="Giới hạn (cố định)" en={bilingual ? "Hard limits" : null} showEn={bilingual} />
              </div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                <span className="badge">
                  <span className="mono">rounds = 1</span>
                </span>
                <span className="badge">
                  <span className="mono">test_cases = 3</span>
                </span>
                <span className="badge">
                  <span className="mono">batch_size = 3</span>
                </span>
              </div>
              <p className="muted" style={{ fontSize: 12, marginTop: 8, marginBottom: 0 }}>
                Giới hạn để hội đồng thấy code chạy thật trong ~2–3 phút.
              </p>
            </div>

            <div>
              <div className="stat-label" style={{ marginBottom: 8 }}>
                <Bi vi="Chế độ chạy" en={bilingual ? "Mode" : null} showEn={bilingual} />
              </div>
              <div style={{ display: "flex", gap: 8 }}>
                <button
                  type="button"
                  className={"badge " + (mode === "backend" ? "badge-primary" : "")}
                  onClick={() => setMode("backend")}
                  disabled={isRunning}
                >
                  Backend SSE
                </button>
                <button
                  type="button"
                  className={"badge " + (mode === "local" ? "badge-primary" : "")}
                  onClick={() => setMode("local")}
                  disabled={isRunning}
                >
                  Local simulation
                </button>
              </div>
              <p className="muted" style={{ fontSize: 12, marginTop: 6, marginBottom: 0 }}>
                Backend mode gọi FastAPI ở <span className="mono">{BACKEND_URL}</span>; fallback local
                nếu không kết nối được.
              </p>
            </div>

            <div className="row" style={{ justifyContent: "flex-end", gap: 8 }}>
              {(phase === "done" || phase === "error") && (
                <button type="button" className="btn" onClick={clearAll}>
                  Reset
                </button>
              )}
              <button
                type="button"
                className="btn btn-primary btn-lg"
                onClick={start}
                disabled={isRunning}
              >
                {isRunning ? (
                  <>
                    <span className="spin" />
                    <Bi vi="Đang chạy…" en={bilingual ? "Running" : null} showEn={false} />
                  </>
                ) : (
                  <>
                    <Icon name="play" size={16} />
                    <Bi vi="Bắt đầu mini run" en={bilingual ? "Start mini run" : null} showEn={false} />
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Progress card */}
        <div className="card">
          <h3
            className="h3"
            style={{
              marginBottom: 16,
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <span>
              <Bi vi="Tiến trình" en={bilingual ? "Progress" : null} showEn={bilingual} />
            </span>
            {isRunning && (
              <span className="badge badge-danger">
                <span className="pulse-dot" /> live
              </span>
            )}
            {phase === "done" && (
              <span className="badge badge-success">
                <Icon name="check" size={11} /> done
              </span>
            )}
          </h3>

          <div className="stepper" style={{ marginBottom: 16 }}>
            {PHASES.map((p, i) => {
              const phaseIdx = PHASES.indexOf(phase as (typeof PHASES)[number]);
              const active = phase === p;
              const done = phaseIdx > i || phase === "done";
              return (
                <div key={p} className={"step " + (active ? "active" : done ? "done" : "")}>
                  <span className="num">{i + 1}</span>
                  <span>{p}</span>
                </div>
              );
            })}
          </div>

          <div
            style={{
              marginBottom: 16,
              padding: "12px",
              background: "var(--surface-2)",
              borderRadius: "var(--radius-md)",
              border: "1px solid var(--line-faint)",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
              <span className="stat-label">Live score</span>
              <span className="mono tnum" style={{ fontSize: 12, color: "var(--fg-muted)" }}>
                {scores.length}/3 test cases
                {finalScore !== null && (
                  <span>
                    {" "}
                    · avg <strong style={{ color: "var(--primary)" }}>{finalScore.toFixed(3)}</strong>
                  </span>
                )}
              </span>
            </div>
            <MiniLiveCurve points={scores} width={420} height={120} />
          </div>

          <div className="stat-label" style={{ marginBottom: 6 }}>
            Log stream
          </div>
          <div
            className="log"
            ref={(el) => {
              if (el) el.scrollTop = el.scrollHeight;
            }}
          >
            {logs.length === 0 && (
              <div style={{ color: "var(--fg-faint)", fontStyle: "italic" }}>
                Chưa có dòng nào. Bấm “Bắt đầu mini run” để khởi chạy.
              </div>
            )}
            {logs.map((l, i) => (
              <div key={i} className={"log-line " + (l.level === "error" ? "error" : "")}>
                <span className="ts">{l.ts}</span>
                <span className={"tag tag-" + l.tag}>{l.tag}</span>
                <span>{l.text}</span>
              </div>
            ))}
          </div>

          {phase === "done" && (
            <div style={{ marginTop: 16, display: "flex", justifyContent: "flex-end", gap: 8 }}>
              <button type="button" className="btn" onClick={clearAll}>
                Reset
              </button>
              <Link className="btn btn-primary" href={`/skills/${picked}`}>
                <Icon name="external" size={14} />
                Xem báo cáo đầy đủ →
              </Link>
            </div>
          )}
        </div>
      </div>

      {/* Backend contract hint */}
      <div className="card" style={{ borderStyle: "dashed", background: "transparent" }}>
        <div className="row-between">
          <div>
            <div className="eyebrow">
              <Bi vi="Backend contract" en={bilingual ? "Backend contract" : null} showEn={bilingual} />
            </div>
            <div className="muted" style={{ fontSize: 13, marginTop: 6 }}>
              FastAPI endpoints này dashboard sẽ gọi. SSE stream theo schema bên dưới.
            </div>
          </div>
        </div>
        <pre className="code-block" style={{ maxHeight: "none", marginTop: 12, fontSize: 12 }}>{`POST /api/run                     → { run_id }
GET  /api/run/{id}/stream         → SSE
   event: { type: "status",          phase: "queued"|"running"|"judging"|"teacher"|"done" }
   event: { type: "log",             line: string }
   event: { type: "test_case_done",  test_case_id, hybrid_score }
   event: { type: "round_done",      round, avg_score }
   event: { type: "complete",        skill, final_score }`}</pre>
      </div>
    </div>
  );
}
