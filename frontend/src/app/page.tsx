"use client";

import { useEffect, useState } from "react";
import { fetchTasks, runCleaning, fetchDiagnostics, TaskInfo, CleanResult, StepLog, Diagnostics, API_BASE } from "@/lib/api";
import { PipelineStepper } from "@/components/PipelineStepper";
import { RewardChart } from "@/components/RewardChart";
import { Play, RotateCcw, Database, Zap, ChevronRight, Activity, BarChart3, AlertTriangle, CheckCircle2, XCircle, Brain, Sparkles, Cpu } from "lucide-react";
import clsx from "clsx";

type Stage = "idle" | "loaded" | "initialized" | "cleaning" | "completed";

export default function Home() {
  const [tasks, setTasks] = useState<TaskInfo[]>([]);
  const [selectedTask, setSelectedTask] = useState<string>("easy");
  const [mode, setMode] = useState<string>("deterministic");
  const [stage, setStage] = useState<Stage>("idle");
  const [result, setResult] = useState<CleanResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchTasks()
      .then((t) => setTasks(t))
      .catch((e) => setError("Backend unreachable. Please restart the FastAPI server."));
  }, []);

  const selectedInfo = tasks.find((t) => t.task === selectedTask);

  const handleReset = () => {
    setStage("idle");
    setResult(null);
    setError(null);
  };

  const handleLoad = () => {
    setStage("loaded");
    setResult(null);
    setError(null);
  };

  const handleInit = () => {
    setStage("initialized");
  };

  const handleRun = async () => {
    setStage("cleaning");
    setError(null);
    try {
      const res = await runCleaning(selectedTask, mode);
      setResult(res);
      setStage("completed");
    } catch (e: any) {
      setError(e.message);
      setStage("initialized");
    }
  };

  const scoreColor = (s: number) =>
    s > 0.8 ? "text-emerald-400" : s > 0.4 ? "text-yellow-400" : "text-red-400";
  const scoreBg = (s: number) =>
    s > 0.8 ? "bg-emerald-500/10 border-emerald-500/20" : s > 0.4 ? "bg-yellow-500/10 border-yellow-500/20" : "bg-red-500/10 border-red-500/30";
  const scoreLabel = (s: number) =>
    s > 0.8 ? "Excellent" : s > 0.4 ? "Partial" : "Needs Work";

  return (
    <main className="min-h-screen bg-black text-zinc-200">
      {/* Top Bar */}
      <nav className="border-b border-zinc-900 px-6 py-4 bg-black/50 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-white rounded-xl flex items-center justify-center shadow-lg shadow-white/5">
              <Database className="w-5 h-5 text-black" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
                Data Cleaning OpenEnv
                <span className="text-[10px] bg-zinc-800 text-zinc-400 px-1.5 py-0.5 rounded font-mono uppercase tracking-widest">Hackathon</span>
              </h1>
              <p className="text-xs text-zinc-500">Real-world Data Cleaning for AI Agents</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <DiagnosticsBadge />
            <div className="h-8 w-px bg-zinc-800 mx-1" />
            <span className={clsx("px-3 py-1 text-xs font-semibold rounded-full border transition-all duration-500",
              stage === "completed" ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" :
                stage === "cleaning" ? "bg-blue-500/10 text-blue-400 border-blue-500/20 animate-pulse" :
                  "bg-zinc-900 text-zinc-500 border-zinc-800")}>
              {stage.toUpperCase()}
            </span>
          </div>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto p-6 flex flex-col gap-6">

        {/* Pipeline Stepper */}
        <section className="bg-zinc-950/50 border border-zinc-900 rounded-2xl p-8 backdrop-blur-sm shadow-xl">
          <PipelineStepper currentStage={stage} />
        </section>

        {/* Main Grid */}
        <div className="grid grid-cols-12 gap-6">

          {/* Left Sidebar — Controls */}
          <aside className="col-span-12 lg:col-span-3 flex flex-col gap-4">
            <div className="bg-zinc-950 border border-zinc-900 rounded-2xl p-6 flex flex-col gap-6 shadow-lg shadow-black/40">
              <h2 className="text-[10px] uppercase tracking-widest text-zinc-500 font-bold flex items-center gap-2">
                <Zap className="w-3.5 h-3.5" /> Simulation Controls
              </h2>

              {/* Mode Toggle */}
              <div>
                <label className="text-[10px] uppercase font-bold text-zinc-600 mb-2 block">Agent Mode</label>
                <div className="grid grid-cols-2 p-1 bg-black border border-zinc-900 rounded-xl">
                  <button
                    onClick={() => setMode("deterministic")}
                    className={clsx(
                      "py-2 text-[11px] font-bold rounded-lg transition-all flex items-center justify-center gap-1.5",
                      mode === "deterministic" ? "bg-white text-black" : "text-zinc-500 hover:text-zinc-300"
                    )}
                  >
                    <Cpu className="w-3 h-3" /> Baseline
                  </button>
                  <button
                    onClick={() => setMode("gemini")}
                    className={clsx(
                      "py-2 text-[11px] font-bold rounded-lg transition-all flex items-center justify-center gap-1.5",
                      mode === "gemini" ? "bg-indigo-600 text-white" : "text-zinc-500 hover:text-zinc-300"
                    )}
                  >
                    <Sparkles className="w-3 h-3" /> Gemini
                  </button>
                </div>
              </div>

              {/* Task Selector */}
              <div>
                <label className="text-[10px] uppercase font-bold text-zinc-600 mb-2 block">Dataset Task</label>
                <div className="grid grid-cols-3 gap-2">
                  {["easy", "medium", "hard"].map((t) => (
                    <button
                      key={t}
                      onClick={() => { setSelectedTask(t); handleReset(); }}
                      className={clsx(
                        "py-2.5 text-[11px] font-bold rounded-xl border transition-all capitalize",
                        selectedTask === t
                          ? "bg-zinc-100 text-black border-white"
                          : "bg-transparent text-zinc-500 border-zinc-800 hover:border-zinc-700 hover:text-zinc-300"
                      )}
                    >
                      {t}
                    </button>
                  ))}
                </div>
              </div>

              {/* Task Info Snapshot */}
              {selectedInfo && (
                <div className="text-[11px] text-zinc-400 bg-black/40 border border-zinc-900 rounded-xl p-4 flex flex-col gap-2">
                  <div className="flex justify-between"><span>Rows</span> <span className="text-zinc-100">{selectedInfo.row_count}</span></div>
                  <div className="flex justify-between"><span>Issues</span> <span className="text-zinc-100">{selectedInfo.issue_count}</span></div>
                  <div className="h-px bg-zinc-900 my-1" />
                  <p className="text-[10px] text-zinc-600 leading-relaxed italic">"{selectedInfo.description}"</p>
                </div>
              )}

              {/* Primary Actions */}
              <div className="flex flex-col gap-2 pt-2">
                <button
                  onClick={handleLoad}
                  disabled={stage === "cleaning" || stage !== "idle"}
                  className="w-full py-3 text-xs font-bold bg-white text-black rounded-xl hover:bg-zinc-200 disabled:opacity-40 transition-all flex items-center justify-center gap-2 group"
                >
                  <Database className="w-3.5 h-3.5 group-hover:scale-110 transition-transform" /> Load Data
                </button>
                <button
                  onClick={handleInit}
                  disabled={stage !== "loaded" && stage !== "completed"}
                  className="w-full py-3 text-xs font-bold border border-zinc-800 text-zinc-400 rounded-xl hover:bg-zinc-900 hover:text-white disabled:opacity-40 transition-all"
                >
                  Init Workspace
                </button>
                <button
                  onClick={handleRun}
                  disabled={stage !== "initialized"}
                  className={clsx(
                    "w-full py-3 text-xs font-bold rounded-xl transition-all flex items-center justify-center gap-2 shadow-lg",
                    mode === "gemini"
                      ? "bg-indigo-600 text-white border border-indigo-500 hover:bg-indigo-500 disabled:bg-indigo-900/50"
                      : "bg-emerald-600 text-white border border-emerald-500 hover:bg-emerald-500 disabled:bg-emerald-900/50"
                  )}
                >
                  {stage === "cleaning" ? <Activity className="w-4 h-4 animate-spin" /> : mode === "gemini" ? <Sparkles className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                  {stage === "cleaning" ? "Cleaning..." : "Start Agent Run"}
                </button>
                <button
                  onClick={handleReset}
                  className="w-full py-2.5 text-[10px] font-bold text-zinc-600 hover:text-red-400 transition-colors flex items-center justify-center gap-1.5"
                >
                  <RotateCcw className="w-3 h-3" /> Clear Session
                </button>
              </div>
            </div>

            {/* AI Run Badge */}
            {result && result.model_used?.includes("gemini") && (
              <div className="bg-indigo-500/10 border border-indigo-500/20 rounded-xl p-4 flex items-center gap-3">
                <div className="w-8 h-8 bg-indigo-500 rounded-lg flex items-center justify-center">
                  <Brain className="w-4 h-4 text-white" />
                </div>
                <div>
                  <div className="text-[10px] uppercase font-bold text-indigo-400">AI Verified Clean</div>
                  <div className="text-[11px] text-zinc-500 italic">Powered by {result.model_used}</div>
                </div>
              </div>
            )}
          </aside>

          {/* Main Workspace */}
          <div className="col-span-12 lg:col-span-9 flex flex-col gap-6">

            {/* Metrics Dashboard */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {[
                { label: "Pipeline Quality", value: result ? (result.score * 100).toFixed(0) + "%" : "--", icon: BarChart3, color: "text-zinc-400" },
                { label: "Steps Taken", value: result ? result.actions.length : 0, icon: Cpu, color: "text-zinc-400" },
                { label: "Unresolved Issues", value: result ? result.final_issues.length : selectedInfo?.issue_count ?? "--", icon: AlertTriangle, color: result?.final_issues.length === 0 ? "text-emerald-500" : "text-yellow-500" },
              ].map((m) => (
                <div key={m.label} className="bg-zinc-950 border border-zinc-900 rounded-2xl p-6 flex flex-col gap-2 relative overflow-hidden group hover:border-zinc-700 transition-colors">
                  <m.icon className="absolute top-4 right-4 w-10 h-10 text-zinc-900/50 group-hover:text-zinc-800 transition-colors" />
                  <div className="text-[10px] uppercase tracking-[0.15em] text-zinc-600 font-bold">{m.label}</div>
                  <div className={clsx("text-4xl font-bold tracking-tight", m.color)}>{m.value}</div>
                </div>
              ))}
            </div>

            {/* Data Comparison Views */}
            <div className="bg-zinc-950 border border-zinc-900 rounded-2xl p-6 shadow-inner">
              <h2 className="text-[10px] uppercase tracking-widest text-zinc-500 font-bold mb-6 flex items-center gap-2">
                <Database className="w-3.5 h-3.5" /> Dataset Diff Viewer
              </h2>
              <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
                <DataTable label="INPUT (DIRTY)" data={result?.original_data ?? []} variant="before" />
                <DataTable label="OUTPUT (CLEAN)" data={result?.final_data ?? []} variant="after" />
              </div>
            </div>

            {/* Log & Charts */}
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
              <div className="bg-zinc-950 border border-zinc-900 rounded-2xl p-6">
                <h2 className="text-[10px] uppercase tracking-widest text-zinc-500 font-bold mb-6 flex items-center gap-2 text-indigo-400">
                  <Activity className="w-3.5 h-3.5" /> Performance Reward Map
                </h2>
                <div className="h-[240px] w-full">
                  <RewardChart rewards={result?.rewards ?? []} />
                </div>
              </div>

              <div className="bg-zinc-950 border border-zinc-900 rounded-2xl p-6">
                <h2 className="text-[10px] uppercase tracking-widest text-zinc-500 font-bold mb-6 flex items-center gap-2 text-emerald-400">
                  <Zap className="w-3.5 h-3.5" /> Real-time Action Trace
                </h2>
                {result ? (
                  <div className="space-y-3 max-h-[220px] overflow-y-auto pr-3 custom-scrollbar">
                    {result.steps_log.map((s: StepLog) => (
                      <div key={s.step} className="flex items-center gap-4 text-xs bg-black/40 border border-zinc-900 rounded-xl p-3.5 hover:border-zinc-700 transition-all">
                        <div className={clsx(
                          "w-7 h-7 rounded-lg flex items-center justify-center text-[10px] font-black shrink-0",
                          s.reward > 0 ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" : "bg-red-500/10 text-red-400 border border-red-500/20",
                        )}>
                          #{s.step}
                        </div>
                        <div className="flex-1">
                          <div className="text-zinc-100 font-bold uppercase tracking-wide">{s.action.replace(/_/g, " ")}</div>
                          <div className="text-[10px] text-zinc-600 mt-0.5">{s.issues_remaining} issues remaining after op</div>
                        </div>
                        <div className={clsx(
                          "font-mono font-black text-[11px]",
                          s.reward > 0 ? "text-emerald-400" : "text-red-400",
                        )}>
                          {s.reward > 0 ? "+" : ""}{s.reward.toFixed(1)}pts
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center h-[200px] text-zinc-700 border border-dashed border-zinc-900 rounded-xl">
                    <Database className="w-6 h-6 mb-2 opacity-20" />
                    <span className="text-[11px] font-medium italic">Waiting for simulation launch...</span>
                  </div>
                )}
              </div>
            </div>

            {/* Error Message */}
            {error && (
              <div className="bg-red-500/5 border border-red-500/20 rounded-2xl p-5 flex items-center gap-4 shadow-lg">
                <div className="w-10 h-10 bg-red-500/10 rounded-xl flex items-center justify-center shrink-0">
                  <XCircle className="w-5 h-5 text-red-500" />
                </div>
                <div>
                  <div className="text-xs font-bold text-red-500 uppercase tracking-widest mb-1">Runtime Fault</div>
                  <div className="text-sm text-zinc-400">{error}</div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}

function DiagnosticsBadge() {
  const [data, setData] = useState<Diagnostics | null>(null);

  useEffect(() => {
    const timer = setInterval(() => {
      fetchDiagnostics()
        .then(setData)
        .catch(() => setData(null));
    }, 5000);
    fetchDiagnostics().then(setData).catch(() => { });
    return () => clearInterval(timer);
  }, []);

  if (!data) return (
    <div className="flex items-center gap-2 px-3 py-1.5 bg-red-500/10 border border-red-500/20 rounded-lg text-red-500 text-[10px] font-bold">
      <div className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse" />
      SERVER OFFLINE
    </div>
  );

  const keyIsOk = data.gemini_api_key === "Set";

  return (
    <div className="flex items-center gap-2">
      <div className={clsx(
        "flex items-center gap-2 px-3 py-1.5 border rounded-lg text-[10px] font-bold transition-all",
        keyIsOk ? "bg-emerald-500/5 text-emerald-500 border-emerald-500/20" : "bg-yellow-500/5 text-yellow-500 border-yellow-500/20"
      )}>
        <Sparkles className="w-3 h-3" />
        AI ADAPTER: {keyIsOk ? "READY" : "MISSING KEY"}
      </div>
      <div className="px-3 py-1.5 bg-zinc-900 border border-zinc-800 rounded-lg text-[10px] font-bold text-zinc-500 flex items-center gap-2">
        <Cpu className="w-3 h-3" />
        TASKS: {data.tasks?.length ?? 0}
      </div>
    </div>
  );
}

/* ------- Sub-component: Data Table ------- */
function DataTable({ label, data, variant }: { label: string; data: Record<string, any>[]; variant: "before" | "after" }) {
  if (!data || data.length === 0) {
    return (
      <div className="flex-1 opacity-40 grayscale">
        <div className="text-[10px] uppercase font-bold text-zinc-600 mb-3 tracking-widest">{label}</div>
        <div className="flex flex-col items-center justify-center p-8 border border-dashed border-zinc-900 rounded-2xl h-[300px]">
          <Database className="w-8 h-8 mb-2 text-zinc-800" />
          <div className="text-[11px] font-bold text-zinc-800">NO DATA STREAM</div>
        </div>
      </div>
    );
  }
  return (
    <div className="flex-1">
      <div className="flex items-center justify-between mb-3 px-1">
        <label className="text-[10px] uppercase font-bold text-zinc-500 tracking-widest flex items-center gap-2">
          {variant === "after" ? <Sparkles className="w-3 h-3 text-indigo-400" /> : <div className="w-3 h-3 rounded-full bg-zinc-800" />}
          {label}
        </label>
        <span className="text-[10px] font-mono text-zinc-600">{data.length} records</span>
      </div>
      <div className="overflow-hidden border border-zinc-900 rounded-2xl bg-zinc-950/80 shadow-2xl">
        <div className="overflow-x-auto max-h-[300px] custom-scrollbar">
          <table className="w-full text-left border-collapse">
            <thead className="bg-zinc-900/40 text-[10px] uppercase text-zinc-500 font-bold tracking-widest sticky top-0 backdrop-blur-md z-10">
              <tr>
                <th className="px-4 py-3 border-b border-zinc-900">Name</th>
                <th className="px-4 py-3 border-b border-zinc-900">Age</th>
                <th className="px-4 py-3 border-b border-zinc-900">Email Reference</th>
              </tr>
            </thead>
            <tbody className="text-[11px] text-zinc-400">
              {data.map((row, i) => (
                <tr key={i} className="group hover:bg-zinc-900/30 transition-all border-b border-zinc-900/30">
                  <td className="px-4 py-2.5 text-zinc-300 font-medium">{row.name || <span className="opacity-20 italic">null</span>}</td>
                  <td className="px-4 py-2.5">
                    {row.age === null || row.age === "" ? (
                      <span className="text-red-500/40 font-black italic underline decoration-red-500/20 underline-offset-4">MISSING</span>
                    ) : (
                      <span className={clsx(typeof row.age === "string" ? "text-yellow-400/70 italic" : "text-emerald-400/70")}>
                        {row.age}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-2.5 truncate max-w-[180px] font-mono opacity-80 group-hover:opacity-100 transition-opacity">
                    {row.email || <span className="opacity-20 italic">no-mail</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
