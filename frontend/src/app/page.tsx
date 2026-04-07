"use client";

import { useEffect, useState, useRef } from "react";
import { 
  fetchTasks, 
  runCleaning, 
  fetchDiagnostics, 
  uploadDataset, 
  fetchOriginalData, 
  reviewManualAudit,
  resetDataset,
  TaskInfo, 
  CleanResult, 
  StepLog, 
  Diagnostics,
  AuditResult
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
  Upload, 
  Search,
  ArrowRight,
  Trophy,
  LayoutGrid,
  FileText,
  MousePointer2,
  Medal,
  Award,
  Coins
} from "lucide-react";
import clsx from "clsx";

type Stage = "idle" | "loaded" | "initialized" | "cleaning" | "completed";
type ViewMode = "challenges" | "refiner";

export default function Home() {
  const [tasks, setTasks] = useState<TaskInfo[]>([]);
  const [selectedTask, setSelectedTask] = useState<string>("easy");
  const [stage, setStage] = useState<Stage>("idle");
  const [viewMode, setViewMode] = useState<ViewMode>("challenges");
  const [result, setResult] = useState<CleanResult | null>(null);
  const [originalData, setOriginalData] = useState<Record<string, any>[]>([]);
  const [auditInput, setAuditInput] = useState("");
  const [auditResult, setAuditResult] = useState<AuditResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isAuditing, setIsAuditing] = useState(false);
  const [bestScore, setBestScore] = useState<number>(0);
  
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    fetchTasks()
      .then((t) => setTasks(t))
      .catch(() => setError("Backend unreachable. Please restart the FastAPI server."));
    
    const saved = localStorage.getItem("openenv_best_score");
    if (saved) setBestScore(parseFloat(saved));
  }, []);

  const handleReset = () => {
    setStage("idle");
    setResult(null);
    setOriginalData([]);
    setAuditInput("");
    setAuditResult(null);
    setError(null);
  };

  const handleTaskSelect = async (task: string) => {
    handleReset();
    setSelectedTask(task);
    setIsAuditing(true); // Loading...
    try {
        await resetDataset(task);
        const data = await fetchOriginalData();
        setOriginalData(data);
        setStage("initialized");
    } catch (e: any) {
        setError("Failed to load dataset: " + e.message);
    } finally {
        setIsAuditing(false);
    }
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
      // Defensive: ensure reward field always exists
      if (!res.reward) {
        const s = res.score ?? 0;
        res.reward = s >= 1.0
          ? { tier: "Grand Slam", points: 1000, message: "🟡 GOLD MEDAL: Perfect Audit!" }
          : s >= 0.8
          ? { tier: "Expert", points: 500, message: "⚪ SILVER MEDAL: Excellent work." }
          : s >= 0.5
          ? { tier: "Contributor", points: 200, message: "🟤 BRONZE MEDAL: Good effort." }
          : { tier: "Novice", points: 50, message: "🔵 NOVICE: Keep practicing!" };
      }
      setAuditResult(res);
      if (res.score * 100 > bestScore) {
          setBestScore(res.score * 100);
          localStorage.setItem("openenv_best_score", (res.score * 100).toString());
      }
    } catch (e: any) {
      setError("AI Review failed: " + e.message);
    } finally {
      setIsAuditing(false);
    }
  };

  const handleRunRefiner = async () => {
    setStage("cleaning");
    setError(null);
    try {
      const res = await runCleaning(selectedTask);
      setResult(res);
      setStage("completed");
    } catch (e: any) {
      setError(e.message);
      setStage("loaded");
    }
  };

  return (
    <main className="min-h-screen bg-black text-zinc-200">
      <nav className="border-b border-zinc-900 px-6 py-4 bg-black/50 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-white rounded-xl flex items-center justify-center shadow-lg shadow-white/5">
              <Database className="w-5 h-5 text-black" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
                DataClean.io
                <span className="text-[10px] bg-zinc-800 text-zinc-400 px-1.5 py-0.5 rounded font-mono uppercase tracking-widest">v1.2</span>
              </h1>
            </div>
          </div>
          
          <div className="bg-zinc-900/50 p-1 rounded-xl border border-zinc-800 flex items-center gap-1">
                <button 
                    onClick={() => { setViewMode("challenges"); handleReset(); }}
                    className={clsx(
                        "px-4 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-2",
                        viewMode === "challenges" ? "bg-white text-black shadow-lg" : "text-zinc-500 hover:text-zinc-300"
                    )}
                >
                    <Trophy className="w-3.5 h-3.5" /> Challenges
                </button>
                <button 
                    onClick={() => { setViewMode("refiner"); handleReset(); }}
                    className={clsx(
                        "px-4 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-2",
                        viewMode === "refiner" ? "bg-white text-black shadow-lg" : "text-zinc-500 hover:text-zinc-300"
                    )}
                >
                    <Sparkles className="w-3.5 h-3.5" /> Auto-Refiner
                </button>
          </div>

          <div className="flex items-center gap-4">
            <DiagnosticsBadge />
          </div>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto p-6 flex flex-col gap-6">

        {viewMode === "challenges" && (
            <div className="grid grid-cols-12 gap-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
                <div className="col-span-12 flex items-center justify-between bg-zinc-950/40 border border-zinc-900 rounded-2xl p-6 backdrop-blur-sm">
                    <div>
                        <h2 className="text-2xl font-bold text-white mb-1">Pick a Challenge</h2>
                        <p className="text-xs text-zinc-500">Select a dataset and manually identify the missing or dirty values.</p>
                    </div>
                    <div className="flex items-center gap-10">
                        <div className="text-center">
                            <div className="text-[10px] uppercase font-bold text-zinc-600 mb-1">Current Task</div>
                            <div className="text-sm font-black text-indigo-400 uppercase tracking-widest">{selectedTask}</div>
                        </div>
                        <div className="text-center">
                            <div className="text-[10px] uppercase font-bold text-zinc-600 mb-1">Your All-Time Best</div>
                            <div className="text-sm font-black text-emerald-400">{bestScore.toFixed(0)}%</div>
                        </div>
                    </div>
                </div>

                <div className="col-span-12 lg:col-span-4 flex flex-col gap-4">
                    {tasks.map((info) => {
                        const level = info.task;
                        const isSelected = selectedTask === level;
                        return (
                            <button 
                                key={level}
                                onClick={() => handleTaskSelect(level)}
                                className={clsx(
                                    "text-left p-6 rounded-2xl border transition-all relative overflow-hidden group",
                                    isSelected 
                                        ? "bg-zinc-900 border-indigo-500/50 shadow-lg shadow-indigo-500/5" 
                                        : "bg-zinc-950 border-zinc-900 hover:border-zinc-700"
                                )}
                            >
                                <div className="flex items-center justify-between mb-2">
                                    <h3 className="font-bold text-white uppercase tracking-[0.2em] text-[11px]">{level}</h3>
                                    <div className={clsx(
                                        "px-2 py-0.5 rounded text-[10px] font-black uppercase",
                                        level === "easy" ? "bg-emerald-500/10 text-emerald-500" :
                                        level === "medium" ? "bg-yellow-500/10 text-yellow-500" :
                                        level === "hard" ? "bg-orange-500/10 text-orange-500" :
                                        level === "sprint" ? "bg-indigo-500/10 text-indigo-500" :
                                        "bg-red-500/10 text-red-500"
                                    )}>
                                        {level === "easy" ? "Beginner" : level === "medium" ? "Intermediate" : level === "hard" ? "Advanced" : level === "sprint" ? "Pro" : "Ultimate"}
                                    </div>
                                </div>
                                <p className="text-xs text-zinc-500 leading-relaxed italic mb-4 line-clamp-2">"{info?.description || 'Loading...'}"</p>
                                <div className="flex items-center gap-4 text-[10px] font-bold text-zinc-400">
                                    <span className="flex items-center gap-1"><Database className="w-3 h-3" /> {info?.row_count ?? 0} Rows</span>
                                    <span className="flex items-center gap-1 text-indigo-400"><AlertTriangle className="w-3 h-3" /> {info?.issue_count ?? 0} Issues</span>
                                </div>
                                
                                {isSelected && (
                                    <div className="absolute right-4 bottom-4">
                                        <ArrowRight className="w-5 h-5 text-indigo-500 animate-pulse" />
                                    </div>
                                )}
                            </button>
                        );
                    })}
                </div>

                <div className="col-span-12 lg:col-span-8 flex flex-col gap-6">
                    {/* Dataset Preview - Now at Top */}
                    <div className="bg-zinc-950 border border-zinc-900 rounded-2xl p-6 shadow-inner min-h-[300px]">
                        <DataTable label={`CHALLENGE DATASET: ${selectedTask.toUpperCase()}`} data={originalData} variant="before" />
                    </div>

                    {/* Manual Submission Area - Now at Bottom */}
                    <div className="bg-zinc-950 border border-zinc-900 rounded-2xl p-6 shadow-xl flex flex-col gap-4">
                        <div className="flex items-center justify-between">
                            <h2 className="text-[11px] font-bold uppercase tracking-widest text-zinc-400 flex items-center gap-2">
                                <Search className="w-4 h-4 text-indigo-400" /> Identification Audit
                            </h2>
                            {stage === "initialized" && <span className="text-[10px] font-black text-emerald-400 animate-pulse flex items-center gap-1"><CheckCircle2 className="w-3 h-3"/> DATA LOADED - START AUDIT</span>}
                        </div>
                        
                        <textarea 
                            value={auditInput}
                            onChange={(e) => setAuditInput(e.target.value)}
                            disabled={stage !== "initialized" || isAuditing}
                            placeholder="Type what's missing or wrong in the data above... e.g. Row 2 has a missing age, Row 5 email is invalid."
                            className="w-full h-32 bg-black border border-zinc-900 rounded-xl p-4 text-[13px] text-zinc-200 placeholder:text-zinc-700 focus:outline-none focus:border-indigo-500/50 transition-colors resize-none disabled:opacity-20"
                        />

                        <button 
                            onClick={handleRequestReview}
                            disabled={!auditInput.trim() || isAuditing || stage !== "initialized"}
                            className="w-full py-3 bg-zinc-100 text-black rounded-xl font-black uppercase text-xs tracking-widest hover:bg-white disabled:opacity-30 transition-all flex items-center justify-center gap-2"
                        >
                            {isAuditing ? <Activity className="w-4 h-4 animate-spin" /> : <Trophy className="w-4 h-4" />}
                            {isAuditing ? "Reviewing..." : "Submit Audit For Scoring"}
                        </button>

                        {auditResult && (
                            <div className="flex flex-col gap-4 animate-in slide-in-from-top-4 duration-500">
                                {/* Score and Critique Side-by-Side */}
                                <div className="grid grid-cols-12 gap-4">
                                    <div className={clsx(
                                        "col-span-12 md:col-span-3 p-6 rounded-2xl border flex flex-col items-center justify-center gap-2 shadow-xl",
                                        auditResult.score > 0.7 ? "bg-emerald-500/5 border-emerald-500/20" : "bg-red-500/5 border-red-500/20"
                                    )}>
                                        <div className="text-[10px] font-black uppercase tracking-[0.2em] text-zinc-500 mb-2">SCORE</div>
                                        <div className={clsx(
                                            "text-5xl font-black italic",
                                            auditResult.score > 0.7 ? "text-emerald-400" : "text-red-400"
                                        )}>
                                            {isNaN(auditResult.score) ? "0" : (auditResult.score * 100).toFixed(0)}
                                        </div>
                                        <div className="text-[10px] font-bold text-zinc-600">Normalization: [0, 1]</div>
                                    </div>

                                    <div className="col-span-12 md:col-span-9 p-6 rounded-2xl border border-zinc-900 bg-zinc-950/50 backdrop-blur-sm flex flex-col gap-2">
                                        <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-widest text-zinc-500">
                                            <FileText className="w-3.5 h-3.5" /> AI Review Critique
                                        </div>
                                        <p className="text-[14px] text-zinc-300 leading-relaxed italic">
                                            "{auditResult.critique}"
                                        </p>
                                        {/* AI Data Summary / Explanation */}
                                        {auditResult.explanation && (
                                            <div className="mt-4 p-4 bg-indigo-500/5 rounded-xl border border-indigo-500/10">
                                                <div className="text-[9px] font-black uppercase text-indigo-400 mb-1">AI DATA CONTEXT</div>
                                                <p className="text-[12px] text-zinc-400 leading-normal">{auditResult.explanation}</p>
                                            </div>
                                        )}
                                    </div>
                                </div>

                                {/* Data Visualization Graphs */}
                                {auditResult.stats && (
                                    <div className="grid grid-cols-12 gap-4">
                                        <div className="col-span-12 md:col-span-6 bg-zinc-950 border border-zinc-900 rounded-2xl p-6">
                                            <h3 className="text-[10px] font-black uppercase text-zinc-500 mb-4 flex items-center gap-2">
                                                <BarChart3 className="w-3.5 h-3.5 text-indigo-400" /> Age Distribution
                                            </h3>
                                            <div className="h-[200px] w-full">
                                                <RewardChart 
                                                    data={Object.entries(auditResult.stats.age_dist).map(([age, count]) => ({ 
                                                        name: `Age ${age}`, 
                                                        points: count as number 
                                                    }))} 
                                                />
                                            </div>
                                        </div>
                                        <div className="col-span-12 md:col-span-6 bg-zinc-950 border border-zinc-900 rounded-2xl p-6">
                                            <h3 className="text-[10px] font-black uppercase text-zinc-500 mb-4 flex items-center gap-2">
                                                <AlertTriangle className="w-3.5 h-3.5 text-red-400" /> Issue Frequency
                                            </h3>
                                            <div className="h-[200px] w-full">
                                                <RewardChart 
                                                    data={Object.entries(auditResult.stats.issue_types).map(([type, count]) => ({ 
                                                        name: type.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' '), 
                                                        points: count as number 
                                                    }))} 
                                                />
                                            </div>
                                        </div>
                                    </div>
                                )}

                                {/* Reward System Box */}
                                <div className="bg-gradient-to-r from-zinc-900 to-black border border-zinc-800 rounded-2xl p-6 relative overflow-hidden group">
                                    <div className="absolute top-0 right-0 p-8 opacity-5 group-hover:opacity-10 transition-opacity">
                                        <Trophy className="w-24 h-24 text-white" />
                                    </div>
                                    
                                    <div className="relative z-10 flex flex-col md:flex-row items-center justify-between gap-6">
                                        <div className="flex items-center gap-5">
                                            <div className={clsx(
                                                "w-16 h-16 rounded-2xl flex items-center justify-center shadow-2xl transition-transform group-hover:scale-110",
                                                auditResult.reward.tier === "Grand Slam" ? "bg-amber-400 text-amber-950" :
                                                auditResult.reward.tier === "Expert" ? "bg-zinc-300 text-zinc-900" :
                                                auditResult.reward.tier === "Contributor" ? "bg-orange-700 text-orange-50" :
                                                "bg-blue-600 text-white"
                                            )}>
                                                {auditResult.reward.tier === "Grand Slam" ? <Trophy className="w-8 h-8" /> :
                                                 auditResult.reward.tier === "Expert" ? <Medal className="w-8 h-8" /> :
                                                 auditResult.reward.tier === "Contributor" ? <Award className="w-8 h-8" /> :
                                                 <MousePointer2 className="w-8 h-8" />}
                                            </div>
                                            <div>
                                                <div className="text-[10px] font-black uppercase tracking-[0.3em] text-zinc-500 mb-1">HACKATHON REWARD</div>
                                                <h3 className="text-xl font-black text-white uppercase italic tracking-tighter">
                                                    {auditResult.reward.tier} TIER
                                                </h3>
                                                <p className="text-[11px] text-zinc-400 font-medium max-w-xs">{auditResult.reward.message}</p>
                                            </div>
                                        </div>

                                        <div className="flex flex-col items-end gap-2 pr-4">
                                            <div className="flex items-center gap-2 bg-zinc-800/50 px-4 py-2 rounded-xl border border-zinc-700">
                                                <Coins className="w-4 h-4 text-amber-400" />
                                                <span className="text-lg font-black text-white">+{isNaN(auditResult.reward.points) ? 0 : auditResult.reward.points} <span className="text-[10px] text-zinc-500 ml-1 uppercase">DP</span></span>
                                            </div>
                                            <div className="text-[10px] font-bold text-indigo-400 animate-pulse uppercase tracking-widest">Rewards Unlocked!</div>
                                        </div>
                                    </div>
                                </div>

                                {/* Cleaned Result Display */}
                                {auditResult.final_data && (
                                    <div className="bg-zinc-950 border border-zinc-900 rounded-2xl p-6 shadow-xl flex flex-col gap-4 animate-in fade-in duration-700">
                                        <div className="flex items-center justify-between">
                                            <h2 className="text-[11px] font-bold uppercase tracking-widest text-zinc-400 flex items-center gap-2">
                                                <Sparkles className="w-4 h-4 text-emerald-400" /> Post-Audit Cleaned Dataset
                                            </h2>
                                            <div className="flex items-center gap-2">
                                                <button 
                                                    onClick={() => setAuditResult(null)}
                                                    className="px-3 py-1 bg-zinc-900 text-zinc-400 text-[10px] font-bold rounded-lg border border-zinc-800 hover:bg-zinc-800 transition-all"
                                                >
                                                    Revise Audit
                                                </button>
                                                <button 
                                                    onClick={() => { handleReset(); handleTaskSelect(selectedTask); }}
                                                    className="px-3 py-1 bg-zinc-100 text-black text-[10px] font-bold rounded-lg hover:bg-white transition-all"
                                                >
                                                    Clear All
                                                </button>
                                            </div>
                                        </div>
                                        <DataTable label="VERIFIED OUTPUT" data={auditResult.final_data} variant="after" />
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                </div>
            </div>
        )}

        {viewMode === "refiner" && (
            <div className="grid grid-cols-12 gap-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
                <div className="col-span-12 flex items-center justify-between bg-zinc-950/40 border border-zinc-900 rounded-2xl p-6 backdrop-blur-sm shadow-xl">
                    <div>
                        <h2 className="text-2xl font-bold text-white mb-1">Automated Data Refiner</h2>
                        <p className="text-xs text-zinc-500 italic">"Deep cleaning for custom datasets using Gemini Pro Baseline."</p>
                    </div>
                </div>

                <div className="col-span-12 lg:col-span-4 flex flex-col gap-6">
                    <div className="bg-zinc-950 border border-zinc-900 rounded-2xl p-6 flex flex-col gap-4 shadow-inner">
                        <div className="flex items-center justify-between">
                            <h3 className="text-[10px] font-black uppercase text-zinc-500 tracking-widest">Custom Stream</h3>
                            <button 
                                onClick={() => fileInputRef.current?.click()}
                                className="px-3 py-1.5 bg-zinc-900 border border-zinc-800 text-zinc-400 rounded-lg text-[9px] font-black uppercase hover:bg-zinc-800 transition-all flex items-center gap-2"
                            >
                                <Upload className="w-3 h-3" /> Select File
                            </button>
                            <input type="file" ref={fileInputRef} onChange={handleFileUpload} accept=".csv,.json" className="hidden" />
                        </div>
                        <p className="text-[10px] text-zinc-600 italic">"Upload a CSV/JSON file to repair outliers and missing values in real-time."</p>
                    </div>

                    <button 
                        onClick={handleRunRefiner}
                        disabled={(stage !== "loaded" && stage !== "completed") || isAuditing}
                        className="w-full py-4 bg-emerald-600 text-white rounded-2xl font-bold uppercase text-xs tracking-widest hover:bg-emerald-500 disabled:opacity-40 transition-all flex items-center justify-center gap-2 shadow-xl shadow-emerald-900/10"
                    >
                        {stage === "cleaning" ? <Activity className="w-5 h-5 animate-spin" /> : <Sparkles className="w-5 h-5" />}
                        {stage === "cleaning" ? "Refining..." : "Trigger AI Refinement"}
                    </button>

                    {result && (
                        <div className="flex flex-col gap-4 animate-in slide-in-from-top-4 duration-500">
                            <div className="bg-zinc-950 border border-zinc-900 rounded-2xl p-6 flex flex-col gap-4 shadow-xl">
                                <h3 className="text-[10px] font-black uppercase text-zinc-600 flex items-center gap-2"><BarChart3 className="w-4 h-4"/> Refinement Metrics</h3>
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="p-4 bg-black/40 rounded-xl border border-zinc-900">
                                        <div className="text-[10px] text-zinc-500 uppercase mb-1">Quality Lift</div>
                                        <div className="text-2xl font-black text-emerald-400">{isNaN(result.score) ? 0 : (result.score * 100).toFixed(0)}%</div>
                                    </div>
                                    <div className="p-4 bg-black/40 rounded-xl border border-zinc-900">
                                        <div className="text-[10px] text-zinc-500 uppercase mb-1">Issues fixed</div>
                                        <div className="text-2xl font-black text-indigo-400">{result.actions.length}</div>
                                    </div>
                                </div>
                            </div>
                            
                            {/* Auto-Refiner Reward */}
                            <div className="bg-gradient-to-r from-zinc-900 to-black border border-zinc-800 rounded-2xl p-6 flex items-center justify-between">
                                <div className="flex items-center gap-4">
                                    <div className="w-12 h-12 bg-white/10 rounded-xl flex items-center justify-center">
                                        <Zap className="w-6 h-6 text-yellow-400" />
                                    </div>
                                    <div>
                                        <div className="text-[10px] font-black text-zinc-500 uppercase tracking-widest">Automation Bonus</div>
                                        <div className="text-lg font-bold text-white">Efficiency Points Earned</div>
                                    </div>
                                </div>
                                <div className="flex items-center gap-2 bg-zinc-800/50 px-4 py-2 rounded-xl border border-zinc-700">
                                    <Coins className="w-4 h-4 text-amber-400" />
                                    <span className="text-lg font-black text-white">+{Math.floor((result.score || 0) * 200)} <span className="text-[10px] text-zinc-500 ml-1 uppercase">DP</span></span>
                                </div>
                            </div>
                        </div>
                    )}
                </div>

                <div className="col-span-12 lg:col-span-8 bg-zinc-950 border border-zinc-900 rounded-2xl p-8 flex flex-col gap-8 shadow-inner">
                    <DataTable label="SOURCE (RAW)" data={originalData} variant="before" />
                    <div className="flex justify-center -my-4 relative z-10">
                        <div className="w-10 h-10 bg-zinc-900 border border-zinc-800 rounded-full flex items-center justify-center shadow-lg">
                            <ArrowRight className="w-5 h-5 text-indigo-500 rotate-90 lg:rotate-0" />
                        </div>
                    </div>
                    <DataTable label="AI REFINED (OUTPUT)" data={result?.final_data ?? []} variant="after" />
                </div>
            </div>
        )}

        {error && (
            <div className="bg-red-500/5 border border-red-500/20 rounded-2xl p-5 flex items-center gap-4 shadow-lg animate-in shake duration-500 fixed bottom-6 right-6 max-w-md z-50 backdrop-blur-xl">
                <XCircle className="w-8 h-8 text-red-500 shrink-0" />
                <div>
                    <div className="text-xs font-bold text-red-500 uppercase tracking-widest mb-1">Platform Error</div>
                    <div className="text-[11px] text-zinc-400">{error}</div>
                </div>
                <button onClick={() => setError(null)} className="ml-auto p-1 text-zinc-500 hover:text-white"><XCircle className="w-4 h-4"/></button>
            </div>
        )}
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
    <div className="flex items-center gap-2 pl-3 py-1 pr-1 bg-red-500/10 border border-red-500/20 rounded-full text-red-400 text-[10px] font-bold">
      OFFLINE
      <div className="w-5 h-5 rounded-full bg-red-500 flex items-center justify-center"><XCircle className="w-3 h-3 text-white"/></div>
    </div>
  );

  const keyIsOk = data.gemini_api_key === "Set";

  return (
    <div className={clsx(
        "flex items-center gap-2 px-3 py-1.5 rounded-full border text-[10px] font-bold transition-all",
        keyIsOk ? "bg-emerald-500/5 text-emerald-400 border-emerald-500/20" : "bg-yellow-500/5 text-yellow-400 border-yellow-500/20"
      )}>
        <Brain className={clsx("w-3.5 h-3.5", keyIsOk ? "text-emerald-400" : "text-yellow-400")} />
        AI ADAPTER: {keyIsOk ? "READY" : "NO KEY"}
    </div>
  );
}

function DataTable({ label, data, variant }: { label: string; data: Record<string, any>[]; variant: "before" | "after" }) {
  if (!data || data.length === 0) {
    return (
      <div className="flex-1 opacity-20 transition-opacity">
        <label className="text-[10px] uppercase font-bold text-zinc-600 mb-3 block tracking-widest">{label}</label>
        <div className="flex flex-col items-center justify-center p-8 border border-dashed border-zinc-900 rounded-3xl h-[150px]">
          <Database className="w-6 h-6 mb-2 text-zinc-800" />
          <div className="text-[10px] font-bold text-zinc-800 uppercase tracking-tighter">Empty Stream</div>
        </div>
      </div>
    );
  }
  return (
    <div className="flex-1 animate-in fade-in zoom-in-95 duration-700">
      <div className="flex items-center justify-between mb-4 px-1">
        <label className="text-[10px] uppercase font-black text-zinc-500 tracking-widest flex items-center gap-2">
          {variant === "after" ? <Sparkles className="w-3.5 h-3.5 text-emerald-400" /> : <div className="w-1.5 h-1.5 rounded-full bg-indigo-500 shadow-[0_0_8px_rgba(99,102,241,0.5)]" />}
          {label}
        </label>
        <span className="text-[10px] font-mono text-zinc-700">{data.length} records detected</span>
      </div>
      <div className={clsx(
          "overflow-hidden border rounded-3xl bg-black shadow-2xl transition-all duration-700",
          variant === "after" ? "border-emerald-500/20 shadow-emerald-500/5" : "border-zinc-900"
      )}>
        <div className="overflow-x-auto max-h-[240px] custom-scrollbar overflow-y-auto">
          <table className="w-full text-left border-collapse">
            <thead className="bg-zinc-900/10 text-[10px] uppercase text-zinc-600 font-black tracking-[0.2em] sticky top-0 backdrop-blur-md z-10 border-b border-zinc-900/30">
              <tr>
                <th className="px-6 py-4">Participant Name</th>
                <th className="px-6 py-4">Reported Age</th>
                <th className="px-6 py-4">Validated Email</th>
              </tr>
            </thead>
            <tbody className="text-[12px] text-zinc-400">
              {data.map((row, i) => {
                return (
                  <tr key={i} className="group hover:bg-zinc-900/30 transition-all border-b border-zinc-900/10">
                    <td className="px-6 py-3.5 text-zinc-100 font-medium">{row.name || <span className="opacity-20 flex items-center gap-1">---</span>}</td>
                    <td className="px-6 py-3.5">
                      {row.age === null || row.age === "" ? (
                        <span className="text-red-500 px-2 py-0.5 bg-red-400/5 rounded border border-red-500/20 font-black text-[10px]">MISSING</span>
                      ) : (
                        <span className={clsx(
                            "px-2.5 py-1 rounded-lg font-mono text-[11px]",
                            typeof row.age === "string" ? "text-yellow-400 bg-yellow-400/10 border border-yellow-400/20" : "text-emerald-400 bg-emerald-400/10 border border-emerald-500/20"
                        )}>
                          {row.age}
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-3.5 truncate max-w-[200px] opacity-70 group-hover:opacity-100 transition-opacity font-mono">
                      {row.email || <span className="opacity-10 italic">null</span>}
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
