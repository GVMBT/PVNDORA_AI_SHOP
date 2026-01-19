import { motion } from "framer-motion";
import { Film, History, ImageIcon, X } from "lucide-react";
import type React from "react";
import type { GenerationTask } from "./types";

interface HistorySidebarProps {
  isOpen: boolean;
  onClose: () => void;
  history: GenerationTask[];
  activeTaskId: string | null;
  onTaskSelect: (taskId: string) => void;
}

export const HistorySidebar: React.FC<HistorySidebarProps> = ({
  isOpen,
  onClose,
  history,
  activeTaskId,
  onTaskSelect,
}) => {
  return (
    <motion.div
      animate={{ width: isOpen ? 300 : 0, opacity: isOpen ? 1 : 0 }}
      className="relative z-40 flex h-full shrink-0 flex-col overflow-hidden border-white/10 border-r bg-[#050505]/95 backdrop-blur-xl"
      initial={{ width: 0, opacity: 0 }}
    >
      <div className="flex items-center justify-between whitespace-nowrap border-white/10 border-b bg-black/40 p-4">
        <span className="flex items-center gap-2 font-bold text-pandora-cyan text-xs tracking-widest">
          <History size={14} /> SESSION_LOGS
        </span>
        <button className="transition-colors hover:text-red-400" onClick={onClose} type="button">
          <X size={14} />
        </button>
      </div>
      <div className="scrollbar-hide flex-1 space-y-2 overflow-y-auto p-2">
        {history.map((task) => (
          <button
            className={`group relative w-full overflow-hidden rounded-sm border p-3 text-left transition-all ${
              activeTaskId === task.id
                ? "border-pandora-cyan/50 bg-white/5 shadow-[0_0_15px_rgba(0,255,255,0.1)]"
                : "border-white/5 bg-black/20 hover:border-white/20"
            }
            `}
            key={task.id}
            onClick={() => onTaskSelect(task.id)}
            type="button"
          >
            <div className="mb-1 flex items-center justify-between">
              <span className="flex items-center gap-1 font-bold text-[9px] text-gray-400">
                {task.domain === "video" ? <Film size={8} /> : <ImageIcon size={8} />}
                {task.modelId.toUpperCase()}
              </span>
              <span
                className={`rounded px-1.5 py-0.5 font-mono text-[8px] ${
                  task.status === "completed"
                    ? "bg-green-900/20 text-green-400"
                    : "bg-yellow-900/20 text-yellow-400"
                }`}
              >
                {task.status.toUpperCase()}
              </span>
            </div>
            <p className="w-full truncate text-[10px] text-gray-300 opacity-80">
              {task.prompt ||
                (task.veoConfig ? `${task.veoConfig.mode.toUpperCase()} GEN` : "No prompt")}
            </p>
            {activeTaskId === task.id && (
              <div className="box-shadow-[0_0_10px_#00FFFF] absolute top-0 bottom-0 left-0 w-0.5 bg-pandora-cyan" />
            )}
          </button>
        ))}
      </div>
    </motion.div>
  );
};
