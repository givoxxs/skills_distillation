"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { Bi } from "@/components/bi";
import { Icon } from "@/components/icon";
import { LearningCurve } from "@/components/charts/learning-curve";
import { skillList, summaries } from "@/lib/mock-data";

type Phase = "idle" | "queued" | "running" | "judging" | "teacher" | "done" | "error";
type LogLine = {
  ts: string;
  tag: string;
  text: string;
  level: "info" | "error" | "success";
};
type RoundEntry = {
  round: number;
  avg_score: number;
  lines_added?: number;
  lines_removed?: number;
};

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
  const [rounds, setRounds] = useState<RoundEntry[]>([]);
  const [tcDoneCount, setTcDoneCount] = useState(0);
  const [currentRound, setCurrentRound] = useState<number>(0);
  const [totalRounds, setTotalRounds] = useState<number>(0);
  const [nTcsPerRound, setNTcsPerRound] = useState<number>(0);
  const [nBatchesPerRound, setNBatchesPerRound] = useState<number>(0);
  const [finalInfo, setFinalInfo] = useState<{
    final_score: number;
    best_round: number;
    best_score: number;
  } | null>(null);

  const eventSourceRef = useRef<EventSource | null>(null);
  const startTimeRef = useRef<number>(0);
  const logEndRef = useRef<HTMLDivElement | null>(null);

  function appendLog(line: LogLine) {
    setLogs((L) => [...L, line]);
  }

  function clearAll() {
    setLogs([]);
    setRounds([]);
    setTcDoneCount(0);
    setCurrentRound(0);
    setTotalRounds(0);
    setNTcsPerRound(0);
    setNBatchesPerRound(0);
    setFinalInfo(null);
    setPhase("idle");
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
  }

  // Auto-scroll log to bottom on new line.
  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [logs]);

  useEffect(() => {
    return () => {
      if (eventSourceRef.current) eventSourceRef.current.close();
    };
  }, []);

  async function start() {
    if (phase !== "idle" && phase !== "done" && phase !== "error") return;
    clearAll();

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
        if (data.phase === "done" || data.phase === "error") es.close();
      });

      es.addEventListener("log", (e) => {
        const data = JSON.parse((e as MessageEvent).data) as {
          line: string;
          tag?: string;
        };
        appendLog({
          ts: elapsed(),
          tag: data.tag || "system",
          text: data.line,
          level: "info",
        });
      });

      es.addEventListener("round_started", (e) => {
        const data = JSON.parse((e as MessageEvent).data) as {
          round: number;
          rounds_total: number;
          n_test_cases: number;
          n_batches: number;
        };
        setCurrentRound(data.round);
        setTotalRounds(data.rounds_total);
        setNTcsPerRound(data.n_test_cases);
        setNBatchesPerRound(data.n_batches);
        setTcDoneCount(0);
      });

      es.addEventListener("test_case_done", (e) => {
        const data = JSON.parse((e as MessageEvent).data) as {
          test_case_id: string;
          round: number;
          hybrid_score: number;
        };
        setTcDoneCount((n) => n + 1);
        appendLog({
          ts: elapsed(),
          tag: "judge",
          text: `${data.test_case_id} → hybrid ${data.hybrid_score.toFixed(3)}`,
          level: "info",
        });
      });

      es.addEventListener("round_done", (e) => {
        const data = JSON.parse((e as MessageEvent).data) as RoundEntry;
        setRounds((R) => [...R, data]);
      });

      es.addEventListener("complete", (e) => {
        const data = JSON.parse((e as MessageEvent).data) as {
          skill: string;
          final_score: number;
          best_round: number;
          best_score: number;
        };
        setFinalInfo({
          final_score: data.final_score,
          best_round: data.best_round,
          best_score: data.best_score,
        });
        setPhase("done");
        es.close();
      });

      es.onerror = () => {
        es.close();
        appendLog({
          ts: elapsed(),
          tag: "system",
          text: "stream closed",
          level: "info",
        });
      };
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      appendLog({
        ts: tsOf(0),
        tag: "system",
        text: `backend unavailable (${msg}). Đảm bảo backend đang chạy ở ${BACKEND_URL}.`,
        level: "error",
      });
      setPhase("error");
    }
  }

  const isRunning =
    phase !== "idle" && phase !== "done" && phase !== "error";
  const pickedSummary = summaries[picked];
  const roundProgress = totalRounds > 0 ? (rounds.length / totalRounds) * 100 : 0;
  const peakRound = useMemo(() => {
    if (!rounds.length) return 0;
    return rounds.reduce((a, b) => (b.avg_score > a.avg_score ? b : a)).round;
  }, [rounds]);

  return (
    <div className="page stack-lg" style={{ maxWidth: 1100 }}>
      {/* Header */}
      <div className="stack-sm">
        <div className="eyebrow">
          <Bi
            vi={`Replay full multi-round · ${pickedSummary.rounds_run} vòng`}
            en={`Live multi-round replay · ${pickedSummary.rounds_run} rounds`}
          />
        </div>
        <h1 className="h1">
          <Bi
            vi="Chạy lại pipeline trên dữ liệu thật, từng vòng một."
            en="Replay the pipeline on real data, round by round."
          />
        </h1>
        <p className="muted" style={{ maxWidth: 760, fontSize: 16 }}>
          <Bi
            vi={
              <>
                Backend đọc thật từ <span className="mono">distillation_v2/results/stable/</span>{" "}
                rồi stream lại qua SSE: Student → Judge → Teacher, lặp đến hết. Mỗi
                vòng chạy đủ ~26 test case trong batch song song 5. Tốc độ ~120 s
                wall-clock — đủ để xem learning curve mọc từng round.
              </>
            }
            en={
              <>
                The backend reads the real pipeline output from{" "}
                <span className="mono">distillation_v2/results/stable/</span> and replays
                it over SSE: Student → Judge → Teacher, looping per round. Each round
                covers all ~26 test cases in parallel batches of 5. About 120 s
                wall-clock — long enough to watch the learning curve grow.
              </>
            }
          />
        </p>
      </div>

      {/* Run configuration card OR running banner */}
      {!isRunning ? (
        <div className="card">
          <h3 className="h3" style={{ marginBottom: 16 }}>
            <Bi vi="Cấu hình lần chạy" en="Run configuration" />
          </h3>
          <div className="stack">
            <div>
              <div className="stat-label" style={{ marginBottom: 8 }}>
                Skill
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
                {skillList.map((s) => {
                  const sum = summaries[s];
                  const selected = picked === s;
                  return (
                    <label
                      key={s}
                      style={{
                        display: "flex",
                        flexDirection: "column",
                        gap: 6,
                        padding: "14px 16px",
                        border: "1px solid var(--line)",
                        borderRadius: "var(--radius-md)",
                        background: selected ? "var(--primary-tint)" : "var(--surface)",
                        borderColor: selected ? "var(--primary)" : "var(--line)",
                        cursor: "pointer",
                      }}
                    >
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <input
                          type="radio"
                          name="skill"
                          value={s}
                          checked={selected}
                          onChange={() => setPicked(s)}
                          style={{ accentColor: "var(--primary)" }}
                        />
                        <span className="mono" style={{ fontSize: 13 }}>
                          {s}
                        </span>
                      </div>
                      <div style={{ fontSize: 12, color: "var(--fg-subtle)" }}>
                        <Bi vi={sum.vi} en={sum.en || sum.vi} />
                      </div>
                      <div className="row" style={{ gap: 6, fontSize: 11 }}>
                        <span className="badge">
                          <span className="mono">{sum.rounds_run} rounds</span>
                        </span>
                        <span className="badge">
                          <span className="mono tnum">peak {sum.best_score.toFixed(3)}</span>
                        </span>
                      </div>
                    </label>
                  );
                })}
              </div>
            </div>

            <div>
              <div className="stat-label" style={{ marginBottom: 8 }}>
                <Bi vi="Tham số (cố định, từ summary.json thật)" en="Parameters (fixed, from real summary.json)" />
              </div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                <span className="badge">
                  <span className="mono">rounds = {pickedSummary.rounds_run}</span>
                </span>
                <span className="badge">
                  <span className="mono">test_cases ≈ 26 / round</span>
                </span>
                <span className="badge">
                  <span className="mono">batch_size = {pickedSummary.batch_size}</span>
                </span>
                <span className="badge">
                  <span className="mono">parallel = {pickedSummary.batch_size}</span>
                </span>
              </div>
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
              >
                <Icon name="play" size={16} />
                <Bi vi="Bắt đầu replay" en="Start replay" />
              </button>
            </div>
          </div>
        </div>
      ) : (
        <div
          className="card"
          style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16 }}
        >
          <div className="row" style={{ gap: 16 }}>
            <span className="badge badge-danger">
              <span className="pulse-dot" /> live
            </span>
            <div>
              <div style={{ fontSize: 14, fontWeight: 600 }}>
                <Bi vi="Đang replay" en="Replaying" />{" "}
                <span className="mono" style={{ color: "var(--primary)" }}>
                  {picked}
                </span>
                {currentRound > 0 && totalRounds > 0 && (
                  <>
                    {" "}· round{" "}
                    <span className="mono tnum">
                      {currentRound}/{totalRounds}
                    </span>
                  </>
                )}
              </div>
              <div className="muted" style={{ fontSize: 12 }}>
                {nTcsPerRound > 0 && (
                  <span>
                    {tcDoneCount}/{nTcsPerRound} TCs · {nBatchesPerRound} batches
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Progress bar + stepper (shown once started) */}
      {phase !== "idle" && (
        <div className="card">
          {/* Round progress */}
          <div style={{ marginBottom: 14 }}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                marginBottom: 6,
                fontSize: 12,
              }}
            >
              <span className="stat-label">
                <Bi vi="Tiến độ vòng" en="Round progress" />
              </span>
              <span className="mono tnum" style={{ color: "var(--fg-muted)" }}>
                {rounds.length} / {totalRounds || pickedSummary.rounds_run} rounds
              </span>
            </div>
            <div
              style={{
                height: 6,
                background: "var(--surface-3)",
                borderRadius: 999,
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  width: `${roundProgress}%`,
                  height: "100%",
                  background: "var(--primary)",
                  transition: "width 400ms ease",
                }}
              />
            </div>
          </div>

          <div className="stepper">
            {PHASES.map((p, i) => {
              const phaseIdx = PHASES.indexOf(phase as (typeof PHASES)[number]);
              const active = phase === p;
              // Stepper rotates each round; show "running phase" as active.
              const done = phase === "done" || phaseIdx > i;
              return (
                <div
                  key={p}
                  className={"step " + (active ? "active" : done ? "done" : "")}
                >
                  <span className="num">{i + 1}</span>
                  <span>{p}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Big learning curve growing per round_done */}
      {phase !== "idle" && (
        <div className="panel">
          <div className="panel-header">
            <div>
              <h3 className="panel-title">
                <Bi vi="Learning curve (real-time)" en="Learning curve (real-time)" />
              </h3>
              <div className="muted" style={{ fontSize: 13, marginTop: 2 }}>
                <Bi
                  vi="Mỗi dot xuất hiện khi một round complete; peak được đánh dấu vàng."
                  en="Each dot appears as a round completes; peak is highlighted in amber."
                />
              </div>
            </div>
            <div className="row">
              {finalInfo && (
                <span className="badge badge-success">
                  <Icon name="check" size={11} /> final {finalInfo.final_score.toFixed(3)}
                </span>
              )}
              {finalInfo && (
                <span className="badge badge-accent">
                  peak {finalInfo.best_score.toFixed(3)} @ R{finalInfo.best_round}
                </span>
              )}
            </div>
          </div>
          <div className="panel-body">
            {rounds.length === 0 ? (
              <div
                className="muted"
                style={{
                  height: 320,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontStyle: "italic",
                }}
              >
                <Bi
                  vi="Chưa có vòng nào hoàn thành. Curve sẽ mọc dần khi mỗi round done."
                  en="No rounds complete yet. The curve fills in as each round finishes."
                />
              </div>
            ) : (
              <LearningCurve
                data={rounds.map((r) => ({ round: r.round, avg_score: r.avg_score }))}
                peakRound={peakRound}
                variant="line"
                height={320}
                showThreshold={true}
              />
            )}
          </div>
        </div>
      )}

      {/* Per-round summary chips */}
      {rounds.length > 0 && (
        <div className="card">
          <div className="stat-label" style={{ marginBottom: 10 }}>
            <Bi vi="Tóm tắt từng round" en="Per-round summary" />
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {rounds.map((r) => {
              const r1 = rounds[0]?.avg_score ?? r.avg_score;
              const delta = ((r.avg_score - r1) / Math.max(r1, 1e-9)) * 100;
              const isPeak = r.round === peakRound;
              return (
                <div
                  key={r.round}
                  className="badge"
                  style={{
                    padding: "8px 12px",
                    background: isPeak ? "var(--accent-tint)" : "var(--surface-2)",
                    borderColor: isPeak ? "var(--accent)" : "var(--line)",
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "flex-start",
                    gap: 2,
                    minWidth: 90,
                  }}
                >
                  <div style={{ fontSize: 11, color: "var(--fg-subtle)" }}>
                    R{r.round}
                    {isPeak && " · peak"}
                  </div>
                  <div
                    className="mono tnum"
                    style={{
                      fontSize: 14,
                      fontWeight: 600,
                      color: isPeak ? "var(--accent)" : "var(--fg)",
                    }}
                  >
                    {r.avg_score.toFixed(3)}
                  </div>
                  {r.round > 1 && (
                    <div
                      className="mono tnum"
                      style={{
                        fontSize: 10,
                        color: delta >= 0 ? "var(--success)" : "var(--danger)",
                      }}
                    >
                      {delta >= 0 ? "+" : ""}
                      {delta.toFixed(1)}%
                    </div>
                  )}
                  {r.lines_added !== undefined && (
                    <div className="mono" style={{ fontSize: 10, color: "var(--fg-faint)" }}>
                      Δ SKILL.md +{r.lines_added} / −{r.lines_removed}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Big log stream */}
      {phase !== "idle" && (
        <div className="panel">
          <div className="panel-header">
            <h3 className="panel-title">
              <Bi vi="Log stream" en="Log stream" />
            </h3>
            <div className="row">
              <span className="badge">
                <span className="mono">{logs.length} lines</span>
              </span>
            </div>
          </div>
          <div className="panel-body" style={{ padding: 0 }}>
            <div
              className="log"
              style={{
                maxHeight: 540,
                minHeight: 420,
                borderRadius: 0,
                border: "none",
                fontSize: "var(--text-sm)",
              }}
            >
              {logs.length === 0 && (
                <div style={{ color: "var(--fg-faint)", fontStyle: "italic" }}>
                  <Bi vi="Chờ event đầu tiên…" en="Waiting for the first event…" />
                </div>
              )}
              {logs.map((l, i) => (
                <div key={i} className={"log-line " + (l.level === "error" ? "error" : "")}>
                  <span className="ts">{l.ts}</span>
                  <span className={"tag tag-" + l.tag}>{l.tag}</span>
                  <span>{l.text}</span>
                </div>
              ))}
              <div ref={logEndRef} />
            </div>
          </div>
        </div>
      )}

      {/* Done actions */}
      {phase === "done" && (
        <div className="row" style={{ justifyContent: "flex-end", gap: 8 }}>
          <button type="button" className="btn" onClick={clearAll}>
            <Bi vi="Chạy lại từ đầu" en="Reset" />
          </button>
          <Link className="btn btn-primary" href={`/skills/${picked}`}>
            <Icon name="external" size={14} />
            <Bi vi="Xem báo cáo đầy đủ →" en="View full report →" />
          </Link>
        </div>
      )}

      {/* Backend contract hint */}
      <div className="card" style={{ borderStyle: "dashed", background: "transparent" }}>
        <div className="row-between">
          <div>
            <div className="eyebrow">
              <Bi vi="Backend contract" en="Backend contract" />
            </div>
            <div className="muted" style={{ fontSize: 13, marginTop: 6 }}>
              <Bi
                vi="Schema event SSE backend phát ra (vẫn giữ nguyên hợp đồng cho lần wire-up subprocess thật tương lai)."
                en="SSE event schema the backend emits (kept stable for a future real-subprocess wire-up)."
              />
            </div>
          </div>
        </div>
        <pre className="code-block" style={{ maxHeight: "none", marginTop: 12, fontSize: 12 }}>{`POST /api/run                    → { run_id }
GET  /api/run/{id}/stream        → SSE
   event: status         { phase: queued|running|judging|teacher|done }
   event: log            { line, tag: system|student|judge|teacher|rule|status }
   event: round_started  { round, rounds_total, n_test_cases, n_batches }
   event: test_case_done { test_case_id, round, hybrid_score }
   event: round_done     { round, avg_score, lines_added, lines_removed }
   event: complete       { skill, final_score, best_round, best_score }`}</pre>
      </div>
    </div>
  );
}
