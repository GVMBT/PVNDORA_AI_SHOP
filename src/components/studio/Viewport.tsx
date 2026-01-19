import { AnimatePresence, motion } from "framer-motion";
import { Download, Film, ImageIcon, Maximize2, Music, Share2 } from "lucide-react";
import type React from "react";
import type { GenerationTask, ModelConfig } from "./types";
import { DecryptText, HUDCorner } from "./VisualComponents";

interface ViewportProps {
  activeTask: GenerationTask | null;
  activeModel: ModelConfig;
  generationLogs: string[];
  activeDomain: "video" | "image" | "audio";
}

export const Viewport: React.FC<ViewportProps> = ({
  activeTask,
  activeModel,
  generationLogs,
  activeDomain,
}) => {
  return (
    <main className="relative flex flex-1 items-center justify-center overflow-hidden bg-transparent">
      <AnimatePresence mode="wait">
        {activeTask ? (
          <motion.div
            animate={{ opacity: 1, scale: 1 }}
            className="relative flex h-full w-full max-w-[1400px] items-center justify-center p-4 pb-48"
            exit={{ opacity: 0, scale: 1.05 }}
            initial={{ opacity: 0, scale: 0.95 }}
            key={activeTask.id}
          >
            {/* God Rays */}
            <div className="pointer-events-none absolute top-1/2 left-1/2 h-[80%] w-[80%] -translate-x-1/2 -translate-y-1/2 rounded-full bg-pandora-cyan/5 blur-[100px]" />

            {/* VIEWPORT FRAME */}
            <div
              className={`group relative w-full overflow-hidden rounded-sm border border-white/10 bg-black shadow-[0_0_50px_rgba(0,0,0,0.5)] transition-all duration-500 ${activeTask.veoConfig?.aspect === "9:16" ? "aspect-[9/16] max-w-[45vh]" : "aspect-video max-h-[65vh]"}
            `}
            >
              <HUDCorner active={activeTask.status === "processing"} position="tl" />
              <HUDCorner active={activeTask.status === "processing"} position="tr" />
              <HUDCorner active={activeTask.status === "processing"} position="bl" />
              <HUDCorner active={activeTask.status === "processing"} position="br" />

              {/* PROCESSING STATE */}
              {activeTask.status === "processing" && (
                <div className="absolute inset-0 z-20 flex flex-col items-center justify-center bg-black/90 backdrop-blur-sm">
                  <div className="relative mb-6 h-1 w-64 overflow-hidden rounded-full bg-white/10">
                    <motion.div
                      animate={{ left: "100%" }}
                      className="h-full bg-pandora-cyan shadow-[0_0_15px_#00FFFF]"
                      initial={{ left: "-100%" }}
                      style={{ width: "50%", position: "absolute" }}
                      transition={{
                        duration: 1.5,
                        ease: "linear",
                        repeat: Number.POSITIVE_INFINITY,
                      }}
                    />
                  </div>

                  {/* Terminal Logs */}
                  <div className="flex h-32 w-64 flex-col justify-end space-y-1 overflow-hidden font-mono text-[10px] text-pandora-cyan/80">
                    {generationLogs
                      .filter((log): log is string => typeof log === "string" && log.length > 0)
                      .map((log, i) => (
                        <motion.div
                          animate={{ opacity: 1, x: 0 }}
                          className="truncate"
                          initial={{ opacity: 0, x: -10 }}
                          key={`log-${i}-${log.slice(0, 20)}`}
                        >
                          <span className="mr-2 text-gray-600">{">"}</span>
                          {log}
                        </motion.div>
                      ))}
                  </div>

                  <div className="mt-4 flex w-64 justify-center gap-4 border-white/10 border-t pt-4 font-mono text-[9px] text-gray-500 uppercase">
                    <span>{activeTask.veoConfig?.resolution}</span>
                    <span className="text-white/20">|</span>
                    <span>{activeTask.veoConfig?.duration}</span>
                    <span className="text-white/20">|</span>
                    <span className="animate-pulse text-pandora-cyan">RENDERING</span>
                  </div>
                </div>
              )}

              {/* COMPLETED STATE */}
              {activeTask.status === "completed" && activeTask.outputs[0] && (
                <div className="group/view relative flex h-full w-full items-center justify-center bg-[#050505]">
                  {activeTask.domain === "video" ? (
                    <video
                      aria-label="Generated video"
                      autoPlay
                      className="h-full w-full object-contain"
                      controls
                      loop
                      src={activeTask.outputs[0]}
                    >
                      <track kind="captions" label="English" srcLang="en" />
                    </video>
                  ) : (
                    <img
                      alt="Gen"
                      className="h-full w-full object-contain"
                      src={activeTask.outputs[0]}
                    />
                  )}

                  {/* Result Actions Bar */}
                  <div className="absolute bottom-6 left-1/2 flex -translate-x-1/2 translate-y-2 gap-2 rounded-sm border border-white/10 bg-black/80 p-1.5 opacity-0 backdrop-blur-md transition-all group-hover/view:translate-y-0 group-hover/view:opacity-100">
                    <button
                      className="rounded-sm p-2 text-gray-300 transition-colors hover:bg-white/10 hover:text-white"
                      title="Download"
                      type="button"
                    >
                      <Download size={16} />
                    </button>
                    <button
                      className="rounded-sm p-2 text-gray-300 transition-colors hover:bg-white/10 hover:text-pandora-cyan"
                      title="Share"
                      type="button"
                    >
                      <Share2 size={16} />
                    </button>
                    <button
                      className="rounded-sm p-2 text-gray-300 transition-colors hover:bg-white/10 hover:text-white"
                      title="Fullscreen"
                      type="button"
                    >
                      <Maximize2 size={16} />
                    </button>
                    <div className="mx-1 w-px bg-white/10" />
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        ) : (
          /* IDLE STATE - Enhanced */
          <motion.div
            animate={{ opacity: 1 }}
            className="pointer-events-none flex select-none flex-col items-center justify-center pb-32 text-center"
            initial={{ opacity: 0 }}
            key="idle"
          >
            {/* Orbital System */}
            <div className="relative mb-10 h-48 w-48 md:h-56 md:w-56">
              {/* Outer glow */}
              <div className="absolute inset-0 rounded-full bg-pandora-cyan/5 blur-3xl" />

              {/* Outer ring - slow rotation */}
              <motion.div
                animate={{ rotate: 360 }}
                className="absolute inset-0"
                transition={{ duration: 60, repeat: Number.POSITIVE_INFINITY, ease: "linear" }}
              >
                <div className="absolute inset-0 rounded-full border border-white/5" />
                <div className="absolute top-0 left-1/2 h-1 w-1 -translate-x-1/2 rounded-full bg-pandora-cyan/50 shadow-[0_0_10px_#00FFFF]" />
              </motion.div>

              {/* Middle ring - medium rotation */}
              <motion.div
                animate={{ rotate: -360 }}
                className="absolute inset-4"
                transition={{ duration: 40, repeat: Number.POSITIVE_INFINITY, ease: "linear" }}
              >
                <div className="absolute inset-0 rounded-full border border-pandora-cyan/10" />
                <div className="absolute top-0 left-1/2 h-1.5 w-1.5 -translate-x-1/2 rounded-full bg-pandora-cyan/70 shadow-[0_0_15px_#00FFFF]" />
                <div className="absolute bottom-0 left-1/2 h-1 w-1 -translate-x-1/2 rounded-full bg-white/30" />
              </motion.div>

              {/* Inner ring - faster rotation */}
              <motion.div
                animate={{ rotate: 360 }}
                className="absolute inset-10"
                transition={{ duration: 20, repeat: Number.POSITIVE_INFINITY, ease: "linear" }}
              >
                <div className="absolute inset-0 rounded-full border border-pandora-cyan/20" />
                <div className="absolute top-0 left-1/2 h-2 w-2 -translate-x-1/2 rounded-full bg-pandora-cyan shadow-[0_0_20px_#00FFFF,0_0_40px_#00FFFF50]" />
              </motion.div>

              {/* Center icon */}
              <div className="absolute inset-0 flex items-center justify-center">
                <motion.div
                  animate={{ scale: [1, 1.1, 1] }}
                  className={`text-5xl md:text-6xl ${activeModel?.color || "text-pandora-cyan"} opacity-90 drop-shadow-[0_0_30px_currentColor]`}
                  transition={{ duration: 3, repeat: Number.POSITIVE_INFINITY, ease: "easeInOut" }}
                >
                  {activeDomain === "video" ? (
                    <Film />
                  ) : activeDomain === "image" ? (
                    <ImageIcon />
                  ) : (
                    <Music />
                  )}
                </motion.div>
              </div>
            </div>

            {/* Model name with decrypt effect */}
            {activeModel?.name && (
              <motion.h2
                animate={{ y: 0, opacity: 1 }}
                className="mb-4 font-bold text-3xl text-white tracking-tight md:text-5xl"
                initial={{ y: 20, opacity: 0 }}
                transition={{ delay: 0.2 }}
              >
                <DecryptText text={activeModel.name} />
              </motion.h2>
            )}

            {/* Status indicator - enhanced */}
            <motion.div
              animate={{ y: 0, opacity: 1 }}
              className="flex items-center gap-4 border border-white/10 bg-black/60 px-5 py-2.5 font-mono text-xs uppercase tracking-[0.2em] backdrop-blur-md"
              initial={{ y: 20, opacity: 0 }}
              transition={{ delay: 0.4 }}
            >
              <div className="flex items-center gap-2">
                <motion.span
                  animate={{ opacity: [0.5, 1, 0.5] }}
                  className="h-2 w-2 rounded-full bg-green-500 shadow-[0_0_10px_#22C55E]"
                  transition={{ duration: 2, repeat: Number.POSITIVE_INFINITY }}
                />
                <span className="text-gray-400">AWAITING INPUT</span>
              </div>
              <span className="h-4 w-px bg-white/20" />
              <span className="text-pandora-cyan">READY</span>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </main>
  );
};
