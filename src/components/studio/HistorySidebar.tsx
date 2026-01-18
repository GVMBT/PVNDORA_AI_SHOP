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
      initial={{ width: 0, opacity: 0 }}
      animate={{ width: isOpen ? 300 : 0, opacity: isOpen ? 1 : 0 }}
      className="h-full bg-[#050505]/95 backdrop-blur-xl border-r border-white/10 relative z-40 overflow-hidden flex flex-col shrink-0"
    >
      <div className="p-4 border-b border-white/10 flex justify-between items-center whitespace-nowrap bg-black/40">
        <span className="text-xs font-bold flex items-center gap-2 text-pandora-cyan tracking-widest">
          <History size={14} /> SESSION_LOGS
        </span>
        <button onClick={onClose} className="hover:text-red-400 transition-colors">
          <X size={14} />
        </button>
      </div>
      <div className="flex-1 overflow-y-auto p-2 space-y-2 scrollbar-hide">
        {history.map((task) => (
          <button
            key={task.id}
            onClick={() => onTaskSelect(task.id)}
            className={`
              w-full text-left p-3 rounded-sm border transition-all relative overflow-hidden group
              ${
                activeTaskId === task.id
                  ? "bg-white/5 border-pandora-cyan/50 shadow-[0_0_15px_rgba(0,255,255,0.1)]"
                  : "bg-black/20 border-white/5 hover:border-white/20"
              }
            `}
          >
            <div className="flex justify-between items-center mb-1">
              <span className="text-[9px] font-bold text-gray-400 flex items-center gap-1">
                {task.domain === "video" ? <Film size={8} /> : <ImageIcon size={8} />}
                {task.modelId.toUpperCase()}
              </span>
              <span
                className={`text-[8px] px-1.5 py-0.5 rounded font-mono ${
                  task.status === "completed"
                    ? "text-green-400 bg-green-900/20"
                    : "text-yellow-400 bg-yellow-900/20"
                }`}
              >
                {task.status.toUpperCase()}
              </span>
            </div>
            <p className="text-[10px] text-gray-300 truncate w-full opacity-80">
              {task.prompt ||
                (task.veoConfig ? `${task.veoConfig.mode.toUpperCase()} GEN` : "No prompt")}
            </p>
            {activeTaskId === task.id && (
              <div className="absolute left-0 top-0 bottom-0 w-0.5 bg-pandora-cyan box-shadow-[0_0_10px_#00FFFF]" />
            )}
          </button>
        ))}
      </div>
    </motion.div>
  );
};
