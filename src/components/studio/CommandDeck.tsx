import { AnimatePresence, motion } from "framer-motion";
import {
  AlertTriangle,
  ArrowLeft,
  ChevronRight,
  Film,
  ImageIcon as ImageIconLucide,
  Layers,
  RefreshCw,
  Settings2,
  Type,
} from "lucide-react";
import type React from "react";
import type {
  DomainType,
  ModelConfig,
  VeoAspect,
  VeoDuration,
  VeoInputMode,
  VeoResolution,
} from "./types";

interface CommandDeckProps {
  userBalance: number;
  onTopUp: () => void;
  estimatedCost: number;
  isGenerating: boolean;
  prompt: string;
  onPromptChange: (value: string) => void;
  onGenerate: () => void;
  activeModel: ModelConfig;
  veoMode: VeoInputMode;
  setVeoMode: (mode: VeoInputMode) => void;
  showAdvanced: boolean;
  setShowAdvanced: (show: boolean) => void;
  veoResolution: VeoResolution;
  setVeoResolution: (resolution: VeoResolution) => void;
  aspectRatio: VeoAspect;
  setAspectRatio: (ratio: VeoAspect) => void;
  veoDuration: VeoDuration;
  setVeoDuration: (duration: VeoDuration) => void;
  showModelSelector: boolean;
  setShowModelSelector: (show: boolean) => void;
  activeModelId: string;
  setActiveModelId: (id: string) => void;
  activeDomain: DomainType;
  startFrame: string | null;
  endFrame: string | null;
  videoInput: string | null;
  refImages: string[];
  triggerUpload: (target: "start" | "end" | "ref" | "video") => void;
}

export const CommandDeck: React.FC<CommandDeckProps> = ({
  userBalance,
  estimatedCost,
  isGenerating,
  prompt,
  onPromptChange,
  onGenerate,
  activeModel,
  veoMode,
  setVeoMode,
  showAdvanced,
  setShowAdvanced,
  veoResolution,
  setVeoResolution,
  aspectRatio,
  setAspectRatio,
  veoDuration,
  setVeoDuration,
  showModelSelector,
  setShowModelSelector,
  triggerUpload: _triggerUpload,
}) => {
  return (
    <footer className="pointer-events-none absolute right-0 bottom-0 left-0 z-40 flex justify-center p-4">
      <div className="pointer-events-auto flex w-full max-w-5xl flex-col gap-2">
        {/* ADVANCED CONFIG PANEL */}
        <AnimatePresence>
          {showAdvanced && activeModel.isVeo && (
            <motion.div
              animate={{ height: "auto", opacity: 1, y: 0 }}
              className="mb-2 grid grid-cols-2 gap-4 rounded-sm border border-white/10 bg-[#0a0a0a]/95 p-4 shadow-2xl backdrop-blur-xl md:grid-cols-4"
              exit={{ height: 0, opacity: 0, y: 20 }}
              initial={{ height: 0, opacity: 0, y: 20 }}
            >
              {/* Resolution */}
              <div>
                <div className="mb-2 block flex justify-between font-bold text-[9px] text-gray-500">
                  RESOLUTION
                  {veoResolution === "4k" && (
                    <span className="flex items-center gap-1 text-red-400">
                      <AlertTriangle size={8} /> HIGH COST
                    </span>
                  )}
                </div>
                <div className="flex overflow-hidden rounded-sm border border-white/10 bg-black/50">
                  {(["720p", "1080p", "4k"] as const).map((r) => (
                    <button
                      className={`flex-1 py-1.5 font-mono text-[10px] transition-colors ${veoResolution === r ? "bg-white/10 font-bold text-white" : "text-gray-500 hover:text-white"}
                        ${veoMode === "extend" && r !== "720p" ? "cursor-not-allowed opacity-30" : ""}
                      `}
                      disabled={veoMode === "extend" && r !== "720p"}
                      key={r}
                      onClick={() => setVeoResolution(r)}
                      type="button"
                    >
                      {r}
                    </button>
                  ))}
                </div>
              </div>

              {/* Aspect */}
              <div>
                <div className="mb-2 block font-bold text-[9px] text-gray-500">ASPECT RATIO</div>
                <div className="flex overflow-hidden rounded-sm border border-white/10 bg-black/50">
                  {(["16:9", "9:16"] as const).map((r) => (
                    <button
                      className={`flex-1 py-1.5 font-mono text-[10px] transition-colors ${aspectRatio === r ? "bg-white/10 font-bold text-white" : "text-gray-500 hover:text-white"}
                        ${veoMode === "reference" && r !== "16:9" ? "cursor-not-allowed opacity-30" : ""}
                      `}
                      disabled={veoMode === "reference" && r !== "16:9"}
                      key={r}
                      onClick={() => setAspectRatio(r)}
                      type="button"
                    >
                      {r}
                    </button>
                  ))}
                </div>
              </div>

              {/* Duration */}
              <div>
                <div className="mb-2 block font-bold text-[9px] text-gray-500">DURATION</div>
                <div className="flex overflow-hidden rounded-sm border border-white/10 bg-black/50">
                  {(["4s", "6s", "8s"] as const).map((d) => {
                    const isLocked =
                      (veoResolution !== "720p" || veoMode === "reference") && d !== "8s";
                    return (
                      <button
                        className={`flex-1 py-1.5 font-mono text-[10px] transition-colors ${veoDuration === d ? "bg-white/10 font-bold text-white" : "text-gray-500 hover:text-white"}
                          ${isLocked ? "cursor-not-allowed opacity-30" : ""}
                        `}
                        disabled={isLocked}
                        key={d}
                        onClick={() => setVeoDuration(d)}
                        type="button"
                      >
                        {d}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Model Selector */}
              <div className="relative">
                <div className="mb-2 block font-bold text-[9px] text-gray-500">MODEL</div>
                <button
                  className="flex w-full items-center justify-between rounded-sm border border-white/10 bg-black/50 px-3 py-1.5 font-mono text-[10px] text-white hover:border-white/30"
                  onClick={() => setShowModelSelector(!showModelSelector)}
                  type="button"
                >
                  {activeModel.name}
                  <ChevronRight
                    className={`transition-transform ${showModelSelector ? "-rotate-90" : "rotate-90"}`}
                    size={10}
                  />
                </button>
                <AnimatePresence>
                  {showModelSelector && (
                    <motion.div
                      animate={{ opacity: 1, y: 0 }}
                      className="absolute right-0 bottom-full left-0 z-50 mb-1 max-h-48 overflow-y-auto rounded-sm border border-white/20 bg-[#0a0a0a] shadow-xl"
                      exit={{ opacity: 0, y: 5 }}
                      initial={{ opacity: 0, y: 5 }}
                    >
                      {/* Model list would go here */}
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* MAIN INPUT CAPSULE */}
        <div className="flex flex-col gap-2 rounded-md border border-white/10 bg-[#0a0a0a]/90 p-2 shadow-[0_0_50px_rgba(0,0,0,0.5)] backdrop-blur-xl">
          {/* VEO MODE TABS */}
          {activeModel.isVeo && (
            <div className="scrollbar-hide mb-1 flex gap-1 overflow-x-auto border-white/5 border-b pb-1">
              {[
                { id: "text", label: "TEXT TO VIDEO", icon: Type },
                { id: "image", label: "IMAGE TO VIDEO", icon: ImageIconLucide },
                { id: "cinematic", label: "CINEMATIC", icon: Film },
                { id: "reference", label: "REFERENCE", icon: Layers },
                { id: "extend", label: "EXTEND", icon: ArrowLeft },
              ].map((m) => (
                <button
                  className={`flex items-center gap-2 whitespace-nowrap rounded-sm px-3 py-1.5 font-bold text-[9px] uppercase transition-all ${
                    veoMode === m.id
                      ? "bg-white text-black shadow-[0_0_10px_rgba(255,255,255,0.2)]"
                      : "bg-transparent text-gray-500 hover:bg-white/5 hover:text-white"
                  }
                  `}
                  key={m.id}
                  onClick={() => setVeoMode(m.id)}
                  type="button"
                >
                  <m.icon size={12} /> {m.label}
                </button>
              ))}

              <div className="flex-1" />
              <button
                className={`flex items-center gap-2 rounded-sm px-3 py-1.5 font-bold text-[9px] uppercase transition-all ${showAdvanced ? "bg-pandora-cyan/10 text-pandora-cyan" : "text-gray-500 hover:text-white"}`}
                onClick={() => setShowAdvanced(!showAdvanced)}
                type="button"
              >
                <Settings2 size={12} /> CONFIG
              </button>
            </div>
          )}

          {/* DYNAMIC UPLOAD ZONES */}
          {activeModel.isVeo && veoMode !== "text" && (
            <div className="mb-1 grid grid-cols-4 gap-2 p-1">
              {/* Upload zones would go here */}
            </div>
          )}

          {/* PROMPT & RUN */}
          <div className="flex items-center gap-2 rounded-sm border border-white/10 bg-black/50 p-1">
            <div className="relative flex-1">
              <textarea
                className="h-10 w-full resize-none border-none bg-transparent px-3 py-2.5 font-mono text-white text-xs outline-none placeholder:text-gray-600"
                onChange={(e) => onPromptChange(e.target.value)}
                placeholder={
                  veoMode === "extend"
                    ? "Describe how to extend..."
                    : "Describe your imagination..."
                }
                spellCheck={false}
                value={prompt}
              />
            </div>
            <div className="h-8 w-px bg-white/10" />
            <div className="flex min-w-[80px] flex-col items-end px-3">
              <span className="font-mono text-[8px] text-gray-500 uppercase">Cost</span>
              <span
                className={`font-bold font-mono text-xs ${userBalance < estimatedCost ? "text-red-500" : "text-pandora-cyan"}`}
              >
                {estimatedCost} CR
              </span>
            </div>
            <button
              className={`flex h-10 items-center gap-2 rounded-sm px-6 font-bold text-xs uppercase tracking-wider transition-all ${
                isGenerating
                  ? "cursor-not-allowed bg-white/5 text-gray-500"
                  : "bg-white text-black hover:bg-pandora-cyan hover:shadow-[0_0_20px_#00FFFF] active:scale-95"
              }
              `}
              disabled={isGenerating || (!prompt.trim() && veoMode === "text")}
              onClick={onGenerate}
              type="button"
            >
              {isGenerating ? <RefreshCw className="animate-spin" size={14} /> : <span>RUN</span>}
            </button>
          </div>
        </div>
      </div>
    </footer>
  );
};
