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
    <main className="flex-1 relative flex items-center justify-center bg-transparent overflow-hidden">
      <AnimatePresence mode="wait">
        {activeTask ? (
          <motion.div
            key={activeTask.id}
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 1.05 }}
            className="relative w-full h-full max-w-[1400px] flex items-center justify-center p-4 pb-48"
          >
            {/* God Rays */}
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[80%] h-[80%] bg-pandora-cyan/5 blur-[100px] rounded-full pointer-events-none" />

            {/* VIEWPORT FRAME */}
            <div
              className={`
              relative w-full bg-black border border-white/10 group overflow-hidden shadow-[0_0_50px_rgba(0,0,0,0.5)] transition-all duration-500 rounded-sm
              ${activeTask.veoConfig?.aspect === "9:16" ? "max-w-[45vh] aspect-[9/16]" : "aspect-video max-h-[65vh]"}
            `}
            >
              <HUDCorner position="tl" active={activeTask.status === "processing"} />
              <HUDCorner position="tr" active={activeTask.status === "processing"} />
              <HUDCorner position="bl" active={activeTask.status === "processing"} />
              <HUDCorner position="br" active={activeTask.status === "processing"} />

              {/* PROCESSING STATE */}
              {activeTask.status === "processing" && (
                <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/90 backdrop-blur-sm z-20">
                  <div className="w-64 h-1 bg-white/10 mb-6 overflow-hidden relative rounded-full">
                    <motion.div
                      className="h-full bg-pandora-cyan shadow-[0_0_15px_#00FFFF]"
                      initial={{ left: "-100%" }}
                      animate={{ left: "100%" }}
                      transition={{ duration: 1.5, ease: "linear", repeat: Infinity }}
                      style={{ width: "50%", position: "absolute" }}
                    />
                  </div>

                  {/* Terminal Logs */}
                  <div className="font-mono text-[10px] text-pandora-cyan/80 w-64 space-y-1 h-32 overflow-hidden flex flex-col justify-end">
                    {generationLogs.map((log, i) => (
                      <motion.div
                        key={`log-${i}-${log.slice(0, 20)}`}
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        className="truncate"
                      >
                        <span className="text-gray-600 mr-2">{`>`}</span>
                        {log}
                      </motion.div>
                    ))}
                  </div>

                  <div className="flex gap-4 text-[9px] text-gray-500 uppercase font-mono border-t border-white/10 pt-4 mt-4 w-64 justify-center">
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
                <div className="w-full h-full bg-[#050505] flex items-center justify-center relative group/view">
                  {activeTask.domain === "video" ? (
                    <video
                      src={activeTask.outputs[0]}
                      autoPlay
                      loop
                      controls
                      aria-label="Generated video"
                      className="w-full h-full object-contain"
                    >
                      <track kind="captions" srcLang="en" label="English" />
                    </video>
                  ) : (
                    <img
                      src={activeTask.outputs[0]}
                      className="w-full h-full object-contain"
                      alt="Gen"
                    />
                  )}

                  {/* Result Actions Bar */}
                  <div className="absolute bottom-6 left-1/2 -translate-x-1/2 flex gap-2 bg-black/80 backdrop-blur-md border border-white/10 p-1.5 rounded-sm opacity-0 group-hover/view:opacity-100 transition-all translate-y-2 group-hover/view:translate-y-0">
                    <button
                      type="button"
                      className="p-2 hover:bg-white/10 rounded-sm text-gray-300 hover:text-white transition-colors"
                      title="Download"
                    >
                      <Download size={16} />
                    </button>
                    <button
                      type="button"
                      className="p-2 hover:bg-white/10 rounded-sm text-gray-300 hover:text-pandora-cyan transition-colors"
                      title="Share"
                    >
                      <Share2 size={16} />
                    </button>
                    <button
                      type="button"
                      className="p-2 hover:bg-white/10 rounded-sm text-gray-300 hover:text-white transition-colors"
                      title="Fullscreen"
                    >
                      <Maximize2 size={16} />
                    </button>
                    <div className="w-px bg-white/10 mx-1" />
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        ) : (
          /* IDLE STATE */
          <motion.div
            key="idle"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex flex-col items-center justify-center text-center select-none pointer-events-none pb-32"
          >
            <div className="w-40 h-40 border border-white/5 rounded-full flex items-center justify-center relative mb-8">
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 40, repeat: Infinity, ease: "linear" }}
                className="absolute inset-0 border-t border-r border-white/10 rounded-full"
              />
              <motion.div
                animate={{ rotate: -360 }}
                transition={{ duration: 30, repeat: Infinity, ease: "linear" }}
                className="absolute inset-4 border-b border-l border-pandora-cyan/20 rounded-full"
              />
              <div
                className={`text-6xl ${activeModel.color} opacity-80 drop-shadow-[0_0_30px_rgba(0,0,0,0.5)] transform hover:scale-110 transition-transform duration-500`}
              >
                {activeDomain === "video" ? (
                  <Film />
                ) : activeDomain === "image" ? (
                  <ImageIcon />
                ) : (
                  <Music />
                )}
              </div>
            </div>
            <h2 className="text-4xl md:text-6xl font-display font-bold text-white tracking-tighter mb-2">
              <DecryptText text={activeModel.name} />
            </h2>
            <div className="flex items-center gap-3 text-xs font-mono text-gray-500 uppercase tracking-widest bg-black/40 px-4 py-1.5 rounded-full border border-white/5 backdrop-blur-sm">
              <span className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse" />
              AWAITING INPUT
              <span className="text-white/20">|</span>
              READY
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </main>
  );
};
