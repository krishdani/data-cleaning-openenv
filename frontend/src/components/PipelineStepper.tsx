"use client";

import { Check, Circle, Loader2 } from "lucide-react";
import clsx from "clsx";

const STAGES = [
  { id: "loaded", label: "Load", num: 1 },
  { id: "initialized", label: "Init", num: 2 },
  { id: "cleaning", label: "Clean", num: 3 },
  { id: "completed", label: "Done", num: 4 },
];

const STAGE_INDEX: Record<string, number> = {
  idle: -1, loaded: 0, initialized: 1, cleaning: 2, completed: 3,
};

export function PipelineStepper({ currentStage }: { currentStage: string }) {
  const activeIdx = STAGE_INDEX[currentStage] ?? -1;

  return (
    <div className="flex items-center w-full">
      {STAGES.map((s, i) => {
        const isComplete = i < activeIdx || currentStage === "completed";
        const isActive = i === activeIdx && currentStage !== "completed";
        const isCleaning = isActive && currentStage === "cleaning";

        return (
          <div key={s.id} className="flex items-center flex-1 last:flex-none">
            <div className="flex items-center gap-2.5">
              <div className={clsx(
                "flex items-center justify-center w-8 h-8 rounded-full text-xs font-semibold transition-all duration-500 border",
                isComplete && "bg-emerald-500/15 border-emerald-500/40 text-emerald-400",
                isActive && !isCleaning && "bg-white border-white text-black",
                isCleaning && "bg-blue-500/15 border-blue-500/40 text-blue-400",
                !isComplete && !isActive && "bg-transparent border-zinc-800 text-zinc-600",
              )}>
                {isComplete ? <Check className="w-4 h-4" /> :
                 isCleaning ? <Loader2 className="w-4 h-4 animate-spin" /> :
                 s.num}
              </div>
              <span className={clsx(
                "text-sm font-medium tracking-wide transition-colors duration-300",
                isComplete && "text-emerald-400",
                isActive && "text-white",
                !isComplete && !isActive && "text-zinc-600",
              )}>
                {s.label}
              </span>
            </div>
            {i < STAGES.length - 1 && (
              <div className="flex-1 mx-5 h-px relative bg-zinc-900">
                <div
                  className={clsx(
                    "absolute top-0 left-0 h-full transition-all duration-700 ease-out",
                    isComplete ? "w-full bg-emerald-500/40" : "w-0 bg-zinc-700",
                  )}
                />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
