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
    <footer className="absolute bottom-0 left-0 right-0 z-40 p-4 flex justify-center pointer-events-none">
      <div className="w-full max-w-5xl flex flex-col gap-2 pointer-events-auto">
        {/* ADVANCED CONFIG PANEL */}
        <AnimatePresence>
          {showAdvanced && activeModel.isVeo && (
            <motion.div
              initial={{ height: 0, opacity: 0, y: 20 }}
              animate={{ height: "auto", opacity: 1, y: 0 }}
              exit={{ height: 0, opacity: 0, y: 20 }}
              className="bg-[#0a0a0a]/95 backdrop-blur-xl border border-white/10 p-4 grid grid-cols-2 md:grid-cols-4 gap-4 mb-2 shadow-2xl rounded-sm"
            >
              {/* Resolution */}
              <div>
                <div className="text-[9px] text-gray-500 font-bold block mb-2 flex justify-between">
                  RESOLUTION
                  {veoResolution === "4k" && (
                    <span className="text-red-400 flex items-center gap-1">
                      <AlertTriangle size={8} /> HIGH COST
                    </span>
                  )}
                </div>
                <div className="flex border border-white/10 bg-black/50 rounded-sm overflow-hidden">
                  {(["720p", "1080p", "4k"] as const).map((r) => (
                    <button
                      type="button"
                      key={r}
                      onClick={() => setVeoResolution(r)}
                      disabled={veoMode === "extend" && r !== "720p"}
                      className={`
                        flex-1 py-1.5 text-[10px] font-mono transition-colors
                        ${veoResolution === r ? "bg-white/10 text-white font-bold" : "text-gray-500 hover:text-white"}
                        ${veoMode === "extend" && r !== "720p" ? "opacity-30 cursor-not-allowed" : ""}
                      `}
                    >
                      {r}
                    </button>
                  ))}
                </div>
              </div>

              {/* Aspect */}
              <div>
                <div className="text-[9px] text-gray-500 font-bold block mb-2">ASPECT RATIO</div>
                <div className="flex border border-white/10 bg-black/50 rounded-sm overflow-hidden">
                  {(["16:9", "9:16"] as const).map((r) => (
                    <button
                      type="button"
                      key={r}
                      onClick={() => setAspectRatio(r)}
                      disabled={veoMode === "reference" && r !== "16:9"}
                      className={`
                        flex-1 py-1.5 text-[10px] font-mono transition-colors
                        ${aspectRatio === r ? "bg-white/10 text-white font-bold" : "text-gray-500 hover:text-white"}
                        ${veoMode === "reference" && r !== "16:9" ? "opacity-30 cursor-not-allowed" : ""}
                      `}
                    >
                      {r}
                    </button>
                  ))}
                </div>
              </div>

              {/* Duration */}
              <div>
                <div className="text-[9px] text-gray-500 font-bold block mb-2">DURATION</div>
                <div className="flex border border-white/10 bg-black/50 rounded-sm overflow-hidden">
                  {(["4s", "6s", "8s"] as const).map((d) => {
                    const isLocked =
                      (veoResolution !== "720p" || veoMode === "reference") && d !== "8s";
                    return (
                      <button
                        type="button"
                        key={d}
                        onClick={() => setVeoDuration(d)}
                        disabled={isLocked}
                        className={`
                          flex-1 py-1.5 text-[10px] font-mono transition-colors
                          ${veoDuration === d ? "bg-white/10 text-white font-bold" : "text-gray-500 hover:text-white"}
                          ${isLocked ? "opacity-30 cursor-not-allowed" : ""}
                        `}
                      >
                        {d}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Model Selector */}
              <div className="relative">
                <div className="text-[9px] text-gray-500 font-bold block mb-2">MODEL</div>
                <button
                  type="button"
                  onClick={() => setShowModelSelector(!showModelSelector)}
                  className="w-full flex items-center justify-between px-3 py-1.5 border border-white/10 bg-black/50 text-[10px] font-mono text-white hover:border-white/30 rounded-sm"
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
                      initial={{ opacity: 0, y: 5 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: 5 }}
                      className="absolute bottom-full left-0 right-0 mb-1 bg-[#0a0a0a] border border-white/20 z-50 shadow-xl max-h-48 overflow-y-auto rounded-sm"
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
        <div className="bg-[#0a0a0a]/90 backdrop-blur-xl border border-white/10 p-2 flex flex-col gap-2 shadow-[0_0_50px_rgba(0,0,0,0.5)] rounded-md">
          {/* VEO MODE TABS */}
          {activeModel.isVeo && (
            <div className="flex gap-1 overflow-x-auto scrollbar-hide pb-1 border-b border-white/5 mb-1">
              {[
                { id: "text", label: "TEXT TO VIDEO", icon: Type },
                { id: "image", label: "IMAGE TO VIDEO", icon: ImageIconLucide },
                { id: "cinematic", label: "CINEMATIC", icon: Film },
                { id: "reference", label: "REFERENCE", icon: Layers },
                { id: "extend", label: "EXTEND", icon: ArrowLeft },
              ].map((m) => (
                <button
                  type="button"
                  key={m.id}
                  onClick={() => setVeoMode(m.id)}
                  className={`
                    flex items-center gap-2 px-3 py-1.5 text-[9px] font-bold uppercase transition-all whitespace-nowrap rounded-sm
                    ${
                      veoMode === m.id
                        ? "bg-white text-black shadow-[0_0_10px_rgba(255,255,255,0.2)]"
                        : "bg-transparent text-gray-500 hover:text-white hover:bg-white/5"
                    }
                  `}
                >
                  <m.icon size={12} /> {m.label}
                </button>
              ))}

              <div className="flex-1" />
              <button
                type="button"
                onClick={() => setShowAdvanced(!showAdvanced)}
                className={`px-3 py-1.5 text-[9px] font-bold uppercase rounded-sm transition-all flex items-center gap-2 ${showAdvanced ? "text-pandora-cyan bg-pandora-cyan/10" : "text-gray-500 hover:text-white"}`}
              >
                <Settings2 size={12} /> CONFIG
              </button>
            </div>
          )}

          {/* DYNAMIC UPLOAD ZONES */}
          {activeModel.isVeo && veoMode !== "text" && (
            <div className="grid grid-cols-4 gap-2 mb-1 p-1">
              {/* Upload zones would go here */}
            </div>
          )}

          {/* PROMPT & RUN */}
          <div className="flex items-center gap-2 bg-black/50 border border-white/10 p-1 rounded-sm">
            <div className="flex-1 relative">
              <textarea
                value={prompt}
                onChange={(e) => onPromptChange(e.target.value)}
                placeholder={
                  veoMode === "extend"
                    ? "Describe how to extend..."
                    : "Describe your imagination..."
                }
                className="w-full bg-transparent border-none outline-none text-xs text-white placeholder:text-gray-600 font-mono resize-none h-10 py-2.5 px-3"
                spellCheck={false}
              />
            </div>
            <div className="h-8 w-px bg-white/10" />
            <div className="flex flex-col items-end px-3 min-w-[80px]">
              <span className="text-[8px] text-gray-500 font-mono uppercase">Cost</span>
              <span
                className={`text-xs font-bold font-mono ${userBalance < estimatedCost ? "text-red-500" : "text-pandora-cyan"}`}
              >
                {estimatedCost} CR
              </span>
            </div>
            <button
              type="button"
              onClick={onGenerate}
              disabled={isGenerating || (!prompt.trim() && veoMode === "text")}
              className={`
                h-10 px-6 font-bold text-xs uppercase tracking-wider flex items-center gap-2 transition-all rounded-sm
                ${
                  isGenerating
                    ? "bg-white/5 text-gray-500 cursor-not-allowed"
                    : "bg-white text-black hover:bg-pandora-cyan hover:shadow-[0_0_20px_#00FFFF] active:scale-95"
                }
              `}
            >
              {isGenerating ? <RefreshCw size={14} className="animate-spin" /> : <span>RUN</span>}
            </button>
          </div>
        </div>
      </div>
    </footer>
  );
};
