"use client";

import { useEffect, useState, useRef } from "react";
import { 
  fetchTasks, 
  runCleaning, 
  fetchDiagnostics, 
  uploadDataset, 
  fetchOriginalData, 
  reviewManualAudit,
  TaskInfo, 
  CleanResult, 
  StepLog, 
  Diagnostics 
} from "@/lib/api";
import { PipelineStepper } from "@/components/PipelineStepper";
import { RewardChart } from "@/components/RewardChart";
import { 
  Play, 
  RotateCcw, 
  Database, 
  Zap, 
  ChevronRight, 
  Activity, 
  BarChart3, 
  AlertTriangle, 
  CheckCircle2, 
  XCircle, 
  Brain, 
  Sparkles, 
  Cpu, 
  Upload, 
  MessageSquare, 
  Search,
  ArrowRight
} from "lucide-react";
import clsx from "clsx";

type Stage = "idle" | "loaded" | "initialized" | "cleaning" | "completed";

export default function Home() {
  const [tasks, setTasks] = useState<TaskInfo[]>([]);
  const [selectedTask, setSelectedTask] = useState<string>("easy");
  const [stage, setStage] = useState<Stage>("idle");
  const [result, setResult] = useState<CleanResult | null>(null);
  const [originalData, setOriginalData] = useState<Record<string, any>[]>([]);
  const [auditInput, setAuditInput] = useState("");
  const [auditResult, setAuditResult] = useState<{ score: number; critique: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isAuditing, setIsAuditing] = useState(false);
  
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    fetchTasks()
      .then((t) => setTasks(t))
      .catch(() => setError("Backend unreachable. Please restart the FastAPI server."));
  }, []);

  const selectedInfo = tasks.find((t) => t.task === selectedTask);

  const handleReset = () => {
    setStage("idle");
    setResult(null);
    setOriginalData([]);
    setAuditInput("");
    setAuditResult(null);
    setError(null);
  };

  const handleLoad = async () => {
    setStage("loaded");
    setResult(null);
    setAuditResult(null);
    const data = await fetchOriginalData();
    setOriginalData(data);
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      setStage("idle");
      const res = await uploadDataset(file);
      setSelectedTask("custom");
      setStage("loaded");
      const data = await fetchOriginalData();
      setOriginalData(data);
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleRequestReview = async () => {
    if (!auditInput.trim()) return;
    setIsAuditing(true);
    try {
      const res = await reviewManualAudit(auditInput);
      setAuditResult(res);
    } catch (e: any) {
      setError("AI Review failed: " + e.message);
    } finally {
      setIsAuditing(false);
    }
  };

  const handleRun = async () => {
    setStage("cleaning");
    setError(null);
    try {
      const res = await runCleaning(selectedTask);
      setResult(res);
      setStage("completed");
    } catch (e: any) {
      setError(e.message);
      setStage("initialized");
    }
  };

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
                <span className="text-[10px] bg-zinc-800 text-zinc-400 px-1.5 py-0.5 rounded font-mono uppercase tracking-widest">Interactive Audit</span>
              </h1>
              <p className="text-xs text-zinc-500">Manual Identification & AI Correction Workflow</p>
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
        <section className="bg-zinc-950/50 border border-zinc-900 rounded-2xl p-8 backdrop-blur-sm shadow-xl relative overflow-hidden">
           <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-emerald-500/50 to-transparent opacity-30" />
           <PipelineStepper currentStage={stage} />
        </section>

        {/* Main Grid */}
        <div className="grid grid-cols-12 gap-6">

          {/* Left Sidebar — Controls & Audit */}
          <aside className="col-span-12 lg:col-span-3 flex flex-col gap-4">
            <div className="bg-zinc-950 border border-zinc-900 rounded-2xl p-6 flex flex-col gap-6 shadow-lg shadow-black/40">
              <h2 className="text-[10px] uppercase tracking-widest text-zinc-500 font-bold flex items-center gap-2">
                <Zap className="w-3.5 h-3.5" /> Simulation Controls
              </h2>

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

              {/* Custom Upload */}
              <div className="pt-2">
                   <button 
                    onClick={() => fileInputRef.current?.click()}
                    className="w-full py-3 text-[11px] font-bold border border-zinc-800 bg-zinc-900/50 text-zinc-300 rounded-xl hover:bg-zinc-800 hover:text-white transition-all flex items-center justify-center gap-2"
                   >
                     <Upload className="w-3.5 h-3.5" /> Upload Custom Data
                   </button>
                   <input 
                    type="file" 
                    ref={fileInputRef} 
                    onChange={handleFileUpload} 
                    accept=".csv,.json" 
                    className="hidden" 
                   />
              </div>

              <div className="h-[1px] bg-zinc-900 mx-2" />

              {/* Primary Actions */}
              <div className="flex flex-col gap-2">
                <button
                  onClick={handleLoad}
                  disabled={stage === "cleaning" || stage !== "idle"}
                  className="w-full py-3 text-xs font-bold bg-white text-black rounded-xl hover:bg-zinc-200 disabled:opacity-40 transition-all flex items-center justify-center gap-2 group"
                >
                  <Database className="w-3.5 h-3.5 group-hover:scale-110 transition-transform" /> Initialize Dataset
                </button>
                <button
                  onClick={handleRun}
                  disabled={stage !== "loaded" && stage !== "completed" && stage !== "initialized"}
                  className="w-full py-3 text-xs font-bold bg-emerald-600 text-white border border-emerald-500 hover:bg-emerald-500 disabled:opacity-40 transition-all shadow-lg shadow-emerald-900/10 flex items-center justify-center gap-2"
                >
                  {stage === "cleaning" ? <Activity className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                  {stage === "cleaning" ? "Running Baseline..." : "Trigger Baseline Run"}
                </button>
                <button
                  onClick={handleReset}
                  className="w-full py-2.5 text-[10px] font-bold text-zinc-600 hover:text-red-400 transition-colors flex items-center justify-center gap-1.5"
                >
                  <RotateCcw className="w-3 h-3" /> Clear Session
                </button>
              </div>
            </div>

            {/* Manual Audit Section */}
            <div className="bg-zinc-950 border border-zinc-900 rounded-2xl p-6 flex flex-col gap-4 shadow-lg shadow-black/40">
                <div className="flex items-center justify-between">
                    <h2 className="text-[10px] uppercase tracking-widest text-zinc-500 font-bold flex items-center gap-2">
                        <Search className="w-3.5 h-3.5" /> User Manual Audit
                    </h2>
                    <div className="px-2 py-0.5 bg-indigo-500/10 text-indigo-400 text-[9px] font-black rounded border border-indigo-500/20">NEW</div>
                </div>
                
                <p className="text-[10px] text-zinc-600 italic">"Manually describe what issues you found. The AI will review your accuracy."</p>

                <textarea 
                    value={auditInput}
                    onChange={(e) => setAuditInput(e.target.value)}
                    placeholder="e.g. Row 2 has a typo in email, Row 5 age is missing..."
                    className="w-full h-24 bg-black border border-zinc-900 rounded-xl p-3 text-[11px] text-zinc-300 placeholder:text-zinc-700 focus:outline-none focus:border-zinc-700 transition-colors resize-none"
                    disabled={stage === "idle" || stage === "cleaning"}
                />

                <button 
                    onClick={handleRequestReview}
                    disabled={!auditInput.trim() || isAuditing}
                    className="w-full py-2.5 text-[10px] font-black uppercase tracking-widest bg-zinc-100 text-black rounded-lg hover:bg-white disabled:opacity-30 transition-all flex items-center justify-center gap-2"
                >
                    {isAuditing ? <Activity className="w-3 h-3 animate-spin" /> : <Brain className="w-3 h-3" />}
                    {isAuditing ? "Analyzing..." : "Request AI Review"}
                </button>

                {auditResult && (
                    <div className={clsx(
                        "mt-2 p-3 rounded-xl border flex flex-col gap-1 transition-all animate-in fade-in slide-in-from-top-2",
                        auditResult.score > 0.7 ? "bg-emerald-500/10 border-emerald-500/20" : "bg-yellow-500/10 border-yellow-500/20"
                    )}>
                        <div className="flex items-center justify-between">
                            <span className="text-[10px] font-bold text-zinc-500">AI FEEDBACK</span>
                            <span className={clsx("text-[10px] font-black", auditResult.score > 0.7 ? "text-emerald-400" : "text-yellow-400")}>
                                SCORE: {(auditResult.score * 100).toFixed(0)}%
                            </span>
                        </div>
                        <p className="text-[11px] text-zinc-300 leading-tight">"{auditResult.critique}"</p>
                    </div>
                )}
            </div>
          </aside>

          {/* Main Workspace */}
          <div className="col-span-12 lg:col-span-9 flex flex-col gap-6">

            {/* Metrics Dashboard */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {[
                { label: "Audit Accuracy", value: auditResult ? (auditResult.score * 100).toFixed(0) + "%" : "--", icon: Brain, color: "text-zinc-400" },
                { label: "Cleanliness (Baseline)", value: result ? (result.score * 100).toFixed(0) + "%" : "--", icon: BarChart3, color: "text-zinc-400" },
                { label: "Issues Remaining", value: result ? result.final_issues.length : originalData.length > 0 ? "Analyzing..." : "--", icon: AlertTriangle, color: result?.final_issues.length === 0 ? "text-emerald-500" : "text-yellow-500" },
              ].map((m) => (
                <div key={m.label} className="bg-zinc-950 border border-zinc-900 rounded-2xl p-6 flex flex-col gap-2 relative overflow-hidden group hover:border-zinc-700 transition-colors shadow-lg">
                  <m.icon className="absolute top-4 right-4 w-10 h-10 text-zinc-900/50 group-hover:text-zinc-800 transition-colors" />
                  <div className="text-[10px] uppercase tracking-[0.15em] text-zinc-600 font-bold">{m.label}</div>
                  <div className={clsx("text-4xl font-bold tracking-tight", m.color)}>{m.value}</div>
                </div>
              ))}
            </div>

            {/* Data Comparison Views */}
            <div className="bg-zinc-950 border border-zinc-900 rounded-2xl p-6 shadow-xl relative">
              <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-indigo-500 to-transparent opacity-20" />
              <h2 className="text-[10px] uppercase tracking-widest text-zinc-500 font-bold mb-6 flex items-center gap-2">
                <Database className="w-3.5 h-3.5" /> Interactive Comparison Workspace
              </h2>
              <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
                <DataTable label="RAW ORIGINAL INPUT" data={originalData} variant="before" />
                <DataTable label="AI BASELINE OUTPUT" data={result?.final_data ?? []} variant="after" />
              </div>
            </div>

            {/* Log & Charts */}
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
              <div className="bg-zinc-950 border border-zinc-900 rounded-2xl p-6">
                <h2 className="text-[10px] uppercase tracking-widest text-zinc-500 font-bold mb-6 flex items-center gap-2 text-indigo-400">
                  <Activity className="w-3.5 h-3.5" /> Correction Reward Curve
                </h2>
                <div className="h-[240px] w-full">
                  <RewardChart rewards={result?.rewards ?? []} />
                </div>
              </div>

              <div className="bg-zinc-950 border border-zinc-900 rounded-2xl p-6">
                <h2 className="text-[10px] uppercase tracking-widest text-zinc-500 font-bold mb-6 flex items-center gap-2 text-emerald-400">
                  <Zap className="w-3.5 h-3.5" /> Baseline Action Log
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
                    <span className="text-[11px] font-medium italic">Waiting for baseline results...</span>
                  </div>
                )}
              </div>
            </div>

            {/* Error Message */}
            {error && (
              <div className="bg-red-500/5 border border-red-500/20 rounded-2xl p-5 flex items-center gap-4 shadow-lg animate-in zoom-in-95 duration-300">
                <div className="w-10 h-10 bg-red-500/10 rounded-xl flex items-center justify-center shrink-0">
                  <XCircle className="w-5 h-5 text-red-500" />
                </div>
                <div>
                  <div className="text-xs font-bold text-red-500 uppercase tracking-widest mb-1">System Error</div>
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
      NODE: OFFLINE
    </div>
  );

  const keyIsOk = data.gemini_api_key === "Set";

  return (
    <div className="flex items-center gap-2">
      <div className={clsx(
        "flex items-center gap-2 px-3 py-1.5 border rounded-lg text-[10px] font-bold transition-all",
        keyIsOk ? "bg-emerald-500/5 text-emerald-500 border-emerald-500/20" : "bg-yellow-500/5 text-yellow-500 border-yellow-500/20"
      )}>
        <Brain className="w-3 h-3" />
        AI ADAPTER: {keyIsOk ? "ONLINE" : "MISSING KEY"}
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
          {variant === "after" ? <Sparkles className="w-3 h-3 text-indigo-400" /> : <Database className="w-3 h-3 text-zinc-600" />}
          {label}
        </label>
        <span className="text-[10px] font-mono text-zinc-600">{data.length} records</span>
      </div>
      <div className={clsx(
          "overflow-hidden border rounded-2xl bg-zinc-950/80 shadow-2xl transition-all duration-500",
          variant === "after" ? "border-indigo-500/20" : "border-zinc-900"
      )}>
        <div className="overflow-x-auto max-h-[300px] custom-scrollbar">
          <table className="w-full text-left border-collapse">
            <thead className="bg-zinc-900/40 text-[10px] uppercase text-zinc-500 font-bold tracking-widest sticky top-0 backdrop-blur-md z-10">
              <tr>
                <th className="px-4 py-3 border-b border-zinc-900/50">Name</th>
                <th className="px-4 py-3 border-b border-zinc-900/50">Age</th>
                <th className="px-4 py-3 border-b border-zinc-900/50">Email Reference</th>
              </tr>
            </thead>
            <tbody className="text-[11px] text-zinc-400">
              {data.map((row, i) => {
                const isDirty = row.age === null || row.age === "" || typeof row.age === "string";
                return (
                  <tr key={i} className="group hover:bg-zinc-900/30 transition-all border-b border-zinc-900/30">
                    <td className="px-4 py-2.5 text-zinc-300 font-medium">{row.name || <span className="opacity-20 italic">null</span>}</td>
                    <td className="px-4 py-2.5">
                      {row.age === null || row.age === "" ? (
                        <span className="text-red-500/60 font-black italic underline decoration-red-500/20 underline-offset-4">MISSING</span>
                      ) : (
                        <span className={clsx(
                            "px-2 py-0.5 rounded",
                            typeof row.age === "string" ? "text-yellow-400/80 bg-yellow-400/5 border border-yellow-400/10 italic" : "text-emerald-400/80 bg-emerald-400/5 border border-emerald-500/10"
                        )}>
                          {row.age}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-2.5 truncate max-w-[180px] font-mono opacity-80 group-hover:opacity-100 transition-opacity">
                      {row.email || <span className="opacity-20 italic">no-mail</span>}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
