/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  Play,
  Settings2,
  ChevronDown,
  Terminal,
  Activity,
  Cpu,
  Zap,
  CheckCircle2,
  AlertCircle,
  Loader2
} from 'lucide-react';

// --- Types ---

type ColumnStatus = 'idle' | 'running' | 'done' | 'error';

interface Stats {
  score: number;
  tools: number;
  tokens: number;
}

interface ColumnState {
  enabled: boolean;
  status: ColumnStatus;
  output: string[];
  stats: Stats;
}

type ColumnId = 'baseline' | 'default' | 'distilled' | 'ceiling';

type TabId = 'live' | 'trajectory';

interface RunStep {
  type: 'assistant' | 'tool_call' | 'tool_result' | 'end_turn';
  content: string;
  toolName?: string;
  params?: any;
  result?: any;
}

interface RunRecord {
  id: string;
  model: string;
  badge: string;
  skill: string;
  status: 'pass' | 'fail';
  score: number;
  stepsCount: number;
  duration: string;
  trace: RunStep[];
}

const STUDENT_MODELS = [
  "google/gemma-4-26b-a4b-it",
  "qwen/qwen3-8b",
  "qwen/qwen3-14b",
  "mistral/mistral-7b"
];

const SKILLS = ["docx", "xlsx", "pptx", "pdf", "frontend-design"];

const CEILING_MODELS = ["claude-haiku-4-5", "claude-sonnet-4-5"];

// --- Mock Data ---

const MOCK_RUNS: RunRecord[] = [
  {
    id: 'run-1',
    model: STUDENT_MODELS[0],
    badge: 'Baseline',
    skill: 'docx',
    status: 'fail',
    score: 0.42,
    stepsCount: 8,
    duration: '3.1s',
    trace: [
      { type: 'assistant', content: "I need to list the files in the directory to find the document." },
      { type: 'tool_call', toolName: 'bash', params: { command: 'ls' }, content: "Listing files..." },
      { type: 'tool_result', content: "Found: report.txt, README.md", result: { files: ["report.txt", "README.md"] } },
      { type: 'assistant', content: "The docx file is missing. I will try to create one." },
      { type: 'tool_call', toolName: 'write_file', params: { path: 'test.docx', content: '...' }, content: "Creating file..." },
      { type: 'tool_result', content: "Error: Permission denied", result: { error: "Permission denied" } },
      { type: 'assistant', content: "I cannot proceed without file access." },
      { type: 'end_turn', content: "Mission failed." }
    ]
  },
  {
    id: 'run-2',
    model: STUDENT_MODELS[1],
    badge: 'Default',
    skill: 'docx',
    status: 'pass',
    score: 0.81,
    stepsCount: 10,
    duration: '5.2s',
    trace: [
      { type: 'assistant', content: "Initializing environment for docx processing." },
      { type: 'tool_call', toolName: 'bash', params: { command: 'npm install mammoth' }, content: "Installing dependencies..." },
      { type: 'tool_result', content: "mammoth@1.6.0 installed.", result: { status: "success" } },
      { type: 'assistant', content: "Now I can read the docx file." },
      { type: 'tool_call', toolName: 'read_file', params: { path: 'input.docx' }, content: "Reading file..." },
      { type: 'tool_result', content: "[Binary Data Header: PK...]", result: { data: "..." } },
      { type: 'assistant', content: "Processing content and generating summary." },
      { type: 'tool_call', toolName: 'write_file', params: { path: 'summary.txt', content: '...' }, content: "Saving result..." },
      { type: 'tool_result', content: "File saved.", result: { status: "ok" } },
      { type: 'end_turn', content: "Processing complete." }
    ]
  },
  {
    id: 'run-3',
    model: STUDENT_MODELS[2],
    badge: 'Distilled',
    skill: 'docx',
    status: 'pass',
    score: 0.94,
    stepsCount: 12,
    duration: '4.2s',
    trace: [
      { type: 'assistant', content: "Applying distilled heuristics for rapid docx extraction." },
      { type: 'tool_call', toolName: 'bash', params: { command: 'ls -R' }, content: "Scanning directory tree..." },
      { type: 'tool_result', content: "Found 2 docx files.", result: { files: ["a.docx", "b.docx"] } },
      { type: 'assistant', content: "Batch processing documents." },
      { type: 'tool_call', toolName: 'read_file', params: { path: 'a.docx' }, content: "Reading A..." },
      { type: 'tool_result', content: "A content loaded.", result: { status: "ok" } },
      { type: 'tool_call', toolName: 'read_file', params: { path: 'b.docx' }, content: "Reading B..." },
      { type: 'tool_result', content: "B content loaded.", result: { status: "ok" } },
      { type: 'assistant', content: "Concatenating data." },
      { type: 'tool_call', toolName: 'write_file', params: { path: 'merged.docx', content: '...' }, content: "Merging products..." },
      { type: 'tool_result', content: "Write successful.", result: { success: true } },
      { type: 'end_turn', content: "Distillation successful." }
    ]
  },
  {
    id: 'run-4',
    model: CEILING_MODELS[1],
    badge: 'Ceiling',
    skill: 'docx',
    status: 'pass',
    score: 0.98,
    stepsCount: 9,
    duration: '2.8s',
    trace: [
      { type: 'assistant', content: "High-compute mode active. Optimizing docx pipelines." },
      { type: 'tool_call', toolName: 'bash', params: { command: 'npm install docx-templates' }, content: "Pre-fetching libraries..." },
      { type: 'tool_result', content: "Ready.", result: { status: "ready" } },
      { type: 'assistant', content: "Executing parallel read." },
      { type: 'tool_call', toolName: 'read_file', params: { path: 'complex.docx' }, content: "Streaming input..." },
      { type: 'tool_result', content: "Parsed 150 pages.", result: { pages: 150 } },
      { type: 'assistant', content: "Formatting output." },
      { type: 'tool_call', toolName: 'write_file', params: { path: 'final_report.pdf', content: '...' }, content: "Generating PDF..." },
      { type: 'end_turn', content: "Finished successfully." }
    ]
  }
];

// ... existing code ...

// --- Mock Data Helpers ---

const MOCK_OUTPUTS = [
  "[SYSTEM] Initializing agent context for skill distillation...",
  "[AGENT] Received prompt. Analyzing instructions in SKILL.md...",
  "[TOOL_CALL] search_files({ query: 'financial report' })",
  "[TOOL_RESULT] Found 3 matching documents.",
  "[AGENT] Reading first document content...",
  "[TOOL_CALL] parse_docx({ path: '/docs/report1.docx' })",
  "[TOOL_RESULT] Document parsed. Extracted 42 tables and 15 paragraphs.",
  "[AGENT] Summarizing findings. Applying distilled heuristics...",
  "[SYSTEM] Validation checks passed. Output generation complete."
];

const generateRandomStats = (): Stats => ({
  score: parseFloat((Math.random() * (0.99 - 0.3) + 0.3).toFixed(2)),
  tools: Math.floor(Math.random() * 8) + 2,
  tokens: Math.floor(Math.random() * 650) + 150,
});

// --- Components ---

const Badge = ({ children, variant }: { children: React.ReactNode; variant: 'cyan' | 'grey' | 'white' }) => {
  const styles = {
    cyan: 'bg-accent/10 text-accent border-accent/20',
    grey: 'bg-white/5 text-gray-400 border-white/10',
    white: 'bg-white/10 text-white border-white/20',
  };
  return (
    <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider border ${styles[variant]}`}>
      {children}
    </span>
  );
};

const CustomToggle = ({ checked, onChange }: { checked: boolean; onChange: (v: boolean) => void }) => {
  return (
    <button
      onClick={() => onChange(!checked)}
      className={`relative w-8 h-4 rounded-full transition-colors duration-200 focus:outline-none ${
        checked ? 'bg-accent' : 'bg-gray-700'
      }`}
      aria-label="Toggle Column"
    >
      <div
        className={`absolute top-0.5 left-0.5 w-3 h-3 bg-white rounded-full transition-transform duration-200 ${
          checked ? 'translate-x-4' : 'translate-x-0'
        }`}
      />
    </button>
  );
};

// --- Sub-components for Trajectory ---

const TraceStep: React.FC<{ step: RunStep; initialExpanded: boolean }> = ({ step, initialExpanded }) => {
  const [expanded, setExpanded] = React.useState(initialExpanded);

  React.useEffect(() => {
    setExpanded(initialExpanded);
  }, [initialExpanded]);

  const getBorderColor = () => {
    switch (step.type) {
      case 'tool_call': return 'border-accent';
      case 'tool_result': return 'border-amber-500';
      case 'end_turn': return 'border-emerald-500';
      default: return 'border-transparent';
    }
  };

  const isTextOnly = step.type === 'assistant' || step.type === 'end_turn';

  return (
    <div className={`border-l-2 ${getBorderColor()} bg-white/5 mb-3 rounded-r overflow-hidden transition-all duration-200`}>
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full text-left px-4 py-2 hover:bg-white/5 flex items-center justify-between group"
      >
        <div className="flex items-center space-x-3">
          <span className="text-[10px] font-bold uppercase tracking-widest text-text-dim opacity-50">
            {step.type === 'assistant' ? '🤖 Assistant' :
             step.type === 'tool_call' ? `🔧 Assistant [${step.toolName}]` :
             step.type === 'tool_result' ? '📤 Tool Result' : '🏁 end_turn'}
          </span>
          {!isTextOnly && (
            <span className="text-[11px] text-text-dim truncate max-w-[200px]">
               {step.content}
            </span>
          )}
        </div>
        {!isTextOnly && (
          <ChevronDown className={`w-3 h-3 text-text-dim transition-transform ${expanded ? 'rotate-180' : ''}`} />
        )}
      </button>

      {(expanded || isTextOnly) && (
        <div className="px-4 pb-3">
          {step.type === 'assistant' && (
            <p className="text-[13px] text-text-main/80 leading-relaxed">{step.content}</p>
          )}

          {(step.type === 'tool_call') && (
            <div className="bg-black/40 rounded p-3 mt-1">
              <pre className="text-[11px] font-mono text-accent overflow-x-auto whitespace-pre-wrap">
                {JSON.stringify(step.params, null, 2)}
              </pre>
            </div>
          )}

          {(step.type === 'tool_result') && (
            <div className="bg-black/40 rounded p-3 mt-1">
              <pre className="text-[11px] font-mono text-amber-400 overflow-x-auto whitespace-pre-wrap line-clamp-3 hover:line-clamp-none transition-all">
                {JSON.stringify(step.result, null, 2)}
              </pre>
            </div>
          )}

          {step.type === 'end_turn' && (
            <p className="text-[12px] font-bold text-emerald-500">{step.content}</p>
          )}
        </div>
      )}
    </div>
  );
};

export default function App() {
  const [activeTab, setActiveTab] = useState<TabId>('live');
  const [selectedRunId, setSelectedRunId] = useState<string | null>(MOCK_RUNS[0].id);
  const [expandAll, setExpandAll] = useState(false);

  const [prompt, setPrompt] = useState("");
  const [studentModel, setStudentModel] = useState(STUDENT_MODELS[0]);
  const [skill, setSkill] = useState(SKILLS[0]);
  const [ceilingModel, setCeilingModel] = useState(CEILING_MODELS[1]);

  const [columns, setColumns] = useState<Record<ColumnId, ColumnState>>({
    baseline: { enabled: true, status: 'idle', output: [], stats: { score: 0, tools: 0, tokens: 0 } },
    default: { enabled: true, status: 'idle', output: [], stats: { score: 0, tools: 0, tokens: 0 } },
    distilled: { enabled: true, status: 'idle', output: [], stats: { score: 0, tools: 0, tokens: 0 } },
    ceiling: { enabled: true, status: 'idle', output: [], stats: { score: 0, tools: 0, tokens: 0 } },
  });

  const toggleColumn = (id: ColumnId) => {
    setColumns(prev => ({
      ...prev,
      [id]: { ...prev[id], enabled: !prev[id].enabled }
    }));
  };

  const simulateColumnRun = async (id: ColumnId) => {
    setColumns(prev => ({
      ...prev,
      [id]: { ...prev[id], status: 'running', output: [] }
    }));

    // Simulate streaming effect
    for (let i = 0; i < MOCK_OUTPUTS.length; i++) {
      await new Promise(resolve => setTimeout(resolve, Math.random() * 300 + 100));
      setColumns(prev => ({
        ...prev,
        [id]: { ...prev[id], output: [...prev[id].output, MOCK_OUTPUTS[i]] }
      }));
    }

    setColumns(prev => ({
      ...prev,
      [id]: {
        ...prev[id],
        status: 'done',
        stats: generateRandomStats()
      }
    }));
  };

  const handleRun = useCallback(async () => {
    const activeIds = (Object.keys(columns) as ColumnId[]).filter(id => columns[id].enabled);
    if (activeIds.length === 0) return;

    await Promise.all(activeIds.map(id => simulateColumnRun(id)));
  }, [columns]);

  const getScoreColor = (id: ColumnId, score: number) => {
    if (score === 0) return 'bg-gray-800';
    if (id === 'distilled') return 'bg-[#00ff9d]';
    if (id === 'ceiling') return 'bg-[#ff00ff]';
    if (id === 'default') return 'bg-[#00d4ff]';

    if (score < 0.5) return 'bg-red-500';
    if (score < 0.75) return 'bg-yellow-500';
    return 'bg-emerald-500';
  };

  return (
    <div className="min-h-screen flex flex-col p-6 space-y-6">
      {/* Header */}
      <header className="flex items-center justify-between border-b border-border pb-4">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 bg-accent rounded flex items-center justify-center glow-accent">
            <Settings2 className="text-bg-dark w-5 h-5" />
          </div>
          <div>
            <h1 className="text-lg font-bold tracking-widest text-accent uppercase font-sans">Skill Distillation Playground <span className="text-text-dim text-xs opacity-50 ml-2">// v.1.0.4</span></h1>
            <p className="text-[10px] text-text-dim font-mono tracking-wider">LAB_SESSION: AUTH_772-X</p>
          </div>
        </div>
        <div className="flex items-center space-x-8">
          <nav className="flex items-center space-x-6">
            {(['live', 'trajectory'] as TabId[]).map(tab => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`text-[11px] font-bold uppercase tracking-[0.2em] transition-all pb-1 border-b-2 ${
                  activeTab === tab ? 'text-accent border-accent' : 'text-text-dim border-transparent hover:text-text-main'
                }`}
              >
                {tab === 'live' ? 'Live Run' : 'Trajectory'}
              </button>
            ))}
          </nav>

          <div className="flex flex-col items-end border-l border-border pl-6">
            <span className="text-[10px] text-gray-500 uppercase tracking-widest font-bold">System Status</span>
            <span className="text-xs text-accent flex items-center space-x-1">
              <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse" />
              <span>STABLE</span>
            </span>
          </div>
        </div>
      </header>

      {activeTab === 'live' ? (
        <>
          <section className="bg-panel border border-border rounded-lg p-4 glow-accent/5 relative overflow-hidden grid grid-cols-[1fr_300px] gap-6">
        <div className="absolute inset-0 bg-gradient-to-b from-accent/[0.02] to-transparent pointer-events-none" />

        <div className="flex flex-col space-y-2 relative z-10">
          <label className="text-[11px] font-bold uppercase tracking-wider text-text-dim flex items-center space-x-2">
            <Terminal className="w-3 h-3" />
            <span>Experiment Prompt</span>
          </label>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Enter your prompt for the agent..."
            className="bg-[#0a0a0c] border border-border rounded p-3 text-[13px] font-mono focus:outline-none focus:border-accent transition-colors resize-none h-[90px] text-text-main"
          />
        </div>

        <div className="flex flex-col justify-between space-y-4 relative z-10">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <label className="text-[11px] font-bold uppercase tracking-wider text-text-dim flex items-center space-x-2">
                <Cpu className="w-3 h-3" />
                <span>Student</span>
              </label>
              <div className="relative group">
                <select
                  value={studentModel}
                  onChange={(e) => setStudentModel(e.target.value)}
                  className="w-full bg-[#0a0a0c] border border-border rounded px-2 py-2 text-xs appearance-none focus:outline-none focus:border-accent transition-colors cursor-pointer text-text-main"
                >
                  {STUDENT_MODELS.map(m => <option key={m} value={m}>{m.split('/').pop()}</option>)}
                </select>
                <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-3 h-3 text-text-dim pointer-events-none" />
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-[11px] font-bold uppercase tracking-wider text-text-dim flex items-center space-x-2">
                <Zap className="w-3 h-3" />
                <span>Skill</span>
              </label>
              <div className="relative group">
                <select
                  value={skill}
                  onChange={(e) => setSkill(e.target.value)}
                  className="w-full bg-[#0a0a0c] border border-border rounded px-2 py-2 text-xs appearance-none focus:outline-none focus:border-accent transition-colors cursor-pointer text-text-main"
                >
                  {SKILLS.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
                <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-3 h-3 text-text-dim pointer-events-none" />
              </div>
            </div>
          </div>

          <button
            onClick={handleRun}
            className="w-full bg-accent hover:opacity-90 text-bg-dark font-extrabold px-6 py-3 rounded flex items-center justify-center space-x-2 transition-all transform active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed text-xs tracking-widest uppercase"
            disabled={(Object.values(columns) as ColumnState[]).every(c => !c.enabled) || (Object.values(columns) as ColumnState[]).some(c => c.status === 'running')}
          >
            <Play className="w-3 h-3 fill-current" />
            <span>Execute Benchmark</span>
          </button>
        </div>
      </section>

      {/* Comparison Columns Section */}
      <section className="flex-1 grid grid-cols-4 gap-4 overflow-hidden">
        {([
          { id: 'baseline', name: 'No SKILL', badge: 'Baseline' },
          { id: 'default', name: 'SKILL v0', badge: 'Default' },
          { id: 'distilled', name: 'SKILL final', badge: 'Distilled' },
          { id: 'ceiling', name: 'Ceiling', badge: 'Ceiling' }
        ] as const).map((col) => {
          const state = columns[col.id];
          const isEnabled = state.enabled;
          const isRunning = state.status === 'running';

          return (
            <div
              key={col.id}
              className={`flex flex-col bg-panel border rounded-lg transition-all duration-500 relative overflow-hidden ${
                isEnabled ? 'border-border' : 'border-transparent opacity-40 grayscale'
              } ${isRunning ? 'glow-accent border-accent/40' : ''}`}
              style={{ opacity: isEnabled ? 1 : 0.4 }}
            >
              {isRunning && <div className="scanline scanline-moving z-10" />}

              {/* Column Header */}
              <div className="p-3 border-b border-border flex flex-col space-y-2">
                <div className="flex items-center justify-between">
                  <h3 className="text-white text-xs font-bold tracking-widest uppercase">{col.name}</h3>
                  <CustomToggle checked={state.enabled} onChange={() => toggleColumn(col.id)} />
                </div>
                <div className="flex items-center justify-between">
                  <Badge variant={col.id === 'distilled' ? 'cyan' : 'grey'}>{col.badge}</Badge>
                  {col.id === 'ceiling' && isEnabled && (
                    <select
                      value={ceilingModel}
                      onChange={(e) => setCeilingModel(e.target.value)}
                      className="bg-bg-dark border border-border/50 rounded px-1.5 py-0.5 text-[10px] text-gray-400 focus:outline-none focus:border-accent"
                    >
                      {CEILING_MODELS.map(m => <option key={m} value={m}>{m}</option>)}
                    </select>
                  )}
                </div>
              </div>

              {/* Status Indicator */}
              <div className="px-3 py-1.5 border-b border-border flex items-center gap-2 text-[9px] font-extrabold tracking-widest uppercase">
                {state.status === 'idle' && <span className="text-text-dim">IDLE</span>}
                {state.status === 'running' && (
                  <div className="flex items-center space-x-1.5 text-accent">
                    <div className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse" />
                    <span>RUNNING...</span>
                  </div>
                )}
                {state.status === 'done' && (
                  <span className="text-[#00ff9d]">● COMPLETED</span>
                )}
                {state.status === 'error' && (
                  <span className="text-red-500">● FAILED</span>
                )}
              </div>

              {/* Output Content */}
              <div className="flex-1 m-3 p-3 font-mono text-[11px] overflow-y-auto space-y-1 bg-[#050506] relative">
                <div className="scanline opacity-10" />
                <AnimatePresence mode="popLayout">
                  {state.output.map((line, idx) => (
                    <motion.div
                      key={`${col.id}-line-${idx}`}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className={`break-all relative z-10 ${
                        line.startsWith('[SYSTEM]') ? 'text-text-dim opacity-50' :
                        line.startsWith('[TOOL_CALL]') ? 'text-accent' :
                        line.startsWith('[TOOL_RESULT]') ? 'text-[#00ff9d]' :
                        'text-text-dim'
                      }`}
                    >
                      {line}
                    </motion.div>
                  ))}
                </AnimatePresence>
                {state.output.length === 0 && !isRunning && (
                  <div className="h-full flex items-center justify-center text-text-dim italic opacity-30 text-[10px]">
                    [WAITING_FOR_TRIGGER]
                  </div>
                )}
              </div>

              {/* Stats Footer */}
              <div className="mt-auto p-3 border-t border-border bg-bg-dark/20 relative">
                <div className="flex justify-between items-center text-[10px] font-mono">
                  <div className="flex items-center space-x-2">
                    <span className="text-text-dim">score:</span>
                    <span className={state.status === 'done' ? 'text-text-main' : 'text-text-dim opacity-50'}>
                      {state.status === 'done' ? state.stats.score.toFixed(2) : '--'}
                    </span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className="text-text-dim">tools:</span>
                    <span className={state.status === 'done' ? 'text-text-main' : 'text-text-dim opacity-50'}>
                      {state.status === 'done' ? state.stats.tools : '0'}
                    </span>
                  </div>
                </div>

                {/* Score Bar */}
                <div className="absolute bottom-0 left-0 w-full h-[2px] bg-[#222]">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: state.status === 'done' ? `${state.stats.score * 100}%` : 0 }}
                    className={`h-full transition-colors duration-500`}
                    style={{ backgroundColor: state.status === 'done' ?
                      (col.id === 'ceiling' ? '#ff00ff' : col.id === 'distilled' ? '#00ff9d' : '#00d4ff') : 'transparent' }}
                  />
                </div>
              </div>
            </div>
          );
        })}
      </section>
        </>
      ) : (
        <section className="flex-1 flex flex-col space-y-4 overflow-hidden">
          {/* Trajectory Header: Model Selectors */}
          <div className="bg-panel border border-border rounded-lg p-4 flex items-center justify-between">
            <div className="flex items-center space-x-6">
              <div className="space-y-1">
                <label className="text-[10px] font-bold uppercase tracking-widest text-text-dim block">Student Model</label>
                <div className="relative group">
                  <select
                    value={studentModel}
                    onChange={(e) => setStudentModel(e.target.value)}
                    className="bg-[#0a0a0c] border border-border rounded px-3 py-1.5 text-xs appearance-none focus:outline-none focus:border-accent transition-colors cursor-pointer text-text-main pr-8"
                  >
                    {STUDENT_MODELS.map(m => <option key={m} value={m}>{m.split('/').pop()}</option>)}
                  </select>
                  <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-3 h-3 text-text-dim pointer-events-none" />
                </div>
              </div>
              <div className="w-px h-8 bg-border" />
              <div className="space-y-1">
                <label className="text-[10px] font-bold uppercase tracking-widest text-text-dim block">Teacher Model</label>
                <div className="relative group">
                  <select
                    value={ceilingModel}
                    onChange={(e) => setCeilingModel(e.target.value)}
                    className="bg-[#0a0a0c] border border-border rounded px-3 py-1.5 text-xs appearance-none focus:outline-none focus:border-accent transition-colors cursor-pointer text-text-main pr-8"
                  >
                    {CEILING_MODELS.map(m => <option key={m} value={m}>{m}</option>)}
                  </select>
                  <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-3 h-3 text-text-dim pointer-events-none" />
                </div>
              </div>
            </div>

            <div className="flex items-center space-x-3">
              <span className="text-[10px] text-text-dim font-mono animate-pulse">MONITORING TRACE STREAM...</span>
              <button
                onClick={() => setExpandAll(!expandAll)}
                className="bg-bg-dark border border-gray-700 hover:border-accent text-accent text-[10px] font-bold px-4 py-2 rounded transition-colors tracking-widest uppercase"
              >
                {expandAll ? 'Collapse All' : 'Expand All'}
              </button>
            </div>
          </div>

          <div className="flex-1 flex gap-6 overflow-hidden">
            {/* Left Panel: Run Selector */}
            <div className="w-1/3 bg-panel border border-border rounded-lg flex flex-col overflow-hidden shadow-2xl">
              <div className="p-4 border-b border-border bg-bg-dark/20 flex items-center justify-between">
                <h3 className="text-[10px] font-bold uppercase tracking-widest text-accent flex items-center gap-2">
                  <Activity className="w-3 h-3" />
                  Available Traces
                </h3>
              </div>
              <div className="flex-1 overflow-y-auto p-4 space-y-3 custom-scrollbar">
                {MOCK_RUNS.map(run => (
                  <button
                    key={run.id}
                    onClick={() => setSelectedRunId(run.id)}
                    className={`w-full text-left p-3 rounded border transition-all relative group ${
                      selectedRunId === run.id ? 'bg-accent/10 border-accent' : 'bg-bg-dark/40 border-border hover:border-accent/40'
                    }`}
                  >
                    <div className="flex justify-between items-start mb-2">
                      <div className="flex flex-col">
                        <span className="text-[9px] text-text-dim font-mono tracking-tighter opacity-70">{run.id.toUpperCase()}</span>
                        <div className="flex items-center space-x-2 mt-0.5">
                          <Badge variant={run.badge === 'Distilled' ? 'cyan' : run.badge === 'Teacher' ? 'cyan' : 'grey'}>{run.badge}</Badge>
                          <span className="text-[11px] font-black text-text-main tracking-tight">{run.skill.toUpperCase()}</span>
                        </div>
                      </div>
                      <span className={`text-[9px] font-black px-1.5 py-0.5 rounded border ${
                        run.status === 'pass'
                          ? 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20'
                          : 'bg-red-500/10 text-red-500 border-red-500/20'
                      }`}>
                        {run.status === 'pass' ? 'PASSED' : 'FAILED'}
                      </span>
                    </div>

                    <div className="flex justify-between items-center text-[10px] font-mono mt-2">
                      <span className="text-text-dim">{run.stepsCount} steps · {run.duration}</span>
                      <span className="text-accent font-bold">SCR: {run.score}</span>
                    </div>

                    <div className="w-full h-1 bg-gray-900 rounded-full mt-2.5 overflow-hidden">
                      <div
                        className={`h-full transition-all duration-1000 ease-out ${
                          run.score > 0.85 ? 'bg-[#00ff9d]' :
                          run.score > 0.6 ? 'bg-[#00d4ff]' : 'bg-red-500'
                        }`}
                        style={{ width: `${run.score * 100}%` }}
                      />
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Right Panel: Detailed Execution Trace */}
            <div className="flex-1 bg-panel border border-border rounded-lg flex flex-col overflow-hidden shadow-2xl relative">
              <div className="absolute inset-0 scanline opacity-5 pointer-events-none" />

              {selectedRunId ? (() => {
                const run = MOCK_RUNS.find(r => r.id === selectedRunId)!;
                return (
                  <>
                    <div className="p-4 border-b border-border bg-[#0a0a0c] flex items-center justify-between z-10">
                      <div className="flex items-center space-x-8 text-[10px] font-mono whitespace-nowrap">
                        <div className="flex flex-col">
                          <span className="text-text-dim uppercase text-[8px] font-black tracking-widest mb-0.5">Model Identifier</span>
                          <span className="text-white font-bold">{run.model.split('/').pop()}</span>
                        </div>
                        <div className="flex flex-col border-l border-border pl-8">
                          <span className="text-text-dim uppercase text-[8px] font-black tracking-widest mb-0.5">Skill Heuristic</span>
                          <span className="text-accent font-bold">{run.skill}</span>
                        </div>
                        <div className="flex flex-col border-l border-border pl-8">
                          <span className="text-text-dim uppercase text-[8px] font-black tracking-widest mb-0.5">Metric Baseline</span>
                          <span className="text-white font-bold">{run.score} Index</span>
                        </div>
                      </div>
                      <div className="flex items-center gap-4">
                         <div className="flex items-center gap-1.5 px-3 py-1 bg-bg-dark rounded-full border border-border">
                            <div className="w-2 h-2 rounded-full bg-accent animate-pulse" />
                            <span className="text-[10px] font-bold text-accent tracking-widest uppercase">Inspect Mode</span>
                         </div>
                      </div>
                    </div>

                    <div className="flex-1 overflow-y-auto p-6 scroll-smooth custom-scrollbar relative z-10">
                      <div className="max-w-4xl mx-auto">
                        {run.trace.map((step, idx) => (
                          <TraceStep key={idx} step={step} initialExpanded={expandAll} />
                        ))}
                      </div>
                    </div>
                  </>
                );
              })() : (
                <div className="flex-1 flex flex-col items-center justify-center text-text-dim opacity-20 space-y-4">
                  <Terminal className="w-16 h-16 animate-pulse" />
                  <span className="text-sm font-black uppercase tracking-[0.4em]">Awaiting Trace Selection</span>
                </div>
              )}
            </div>
          </div>
        </section>
      )}

      {/* Global Style Inject for Fonts (if not already handled in index.css properly) */}
      <footer className="mt-auto py-2 flex justify-between items-center text-[10px] text-gray-600 font-mono border-t border-border">
        <span>ESTABLISHING SECURE CONNECTION TO DIST_SERVER...</span>
        <span>NODE ID: 771-BETA | HEURISTIC_OVERRIDE: FALSE</span>
      </footer>
    </div>
  );
}
