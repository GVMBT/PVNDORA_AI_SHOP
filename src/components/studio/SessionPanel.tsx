/**
 * Session Panel - Left sidebar for managing projects/canvases
 */

import { AnimatePresence, motion } from "framer-motion";
import {
  Archive,
  ChevronLeft,
  Edit3,
  FolderPlus,
  MoreVertical,
  Trash2,
  X,
} from "lucide-react";
import { useState } from "react";
import {
  selectActiveSession,
  useStudioStore,
} from "../../stores/studioStore";

interface SessionPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

export const SessionPanel: React.FC<SessionPanelProps> = ({ isOpen, onClose }) => {
  const {
    sessions,
    activeSessionId,
    sessionsLoading,
    createSession,
    renameSession,
    deleteSession,
    setActiveSession,
  } = useStudioStore();

  const activeSession = useStudioStore(selectActiveSession);

  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingName, setEditingName] = useState("");
  const [menuOpenId, setMenuOpenId] = useState<string | null>(null);

  const handleCreateSession = async () => {
    const session = await createSession();
    if (session) {
      setEditingId(session.id);
      setEditingName(session.name);
    }
  };

  const handleRename = async (sessionId: string) => {
    if (editingName.trim()) {
      await renameSession(sessionId, editingName.trim());
    }
    setEditingId(null);
    setEditingName("");
  };

  const handleDelete = async (sessionId: string) => {
    if (confirm("Удалить проект? Все генерации останутся.")) {
      await deleteSession(sessionId);
    }
    setMenuOpenId(null);
  };

  const startEditing = (session: typeof sessions[0]) => {
    setEditingId(session.id);
    setEditingName(session.name);
    setMenuOpenId(null);
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 lg:hidden"
            onClick={onClose}
          />

          {/* Panel */}
          <motion.div
            initial={{ x: -320 }}
            animate={{ x: 0 }}
            exit={{ x: -320 }}
            transition={{ type: "spring", damping: 25, stiffness: 300 }}
            className="fixed left-0 top-0 h-full w-80 bg-black/90 border-r border-pandora-cyan/20 z-50 flex flex-col"
          >
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-pandora-cyan/10">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-pandora-cyan rounded-full animate-pulse" />
                <span className="text-sm font-medium text-gray-300">PROJECTS</span>
              </div>
              <button
                onClick={onClose}
                className="p-2 hover:bg-white/5 rounded-lg transition-colors"
              >
                <ChevronLeft size={18} className="text-gray-400" />
              </button>
            </div>

            {/* New Project Button */}
            <div className="p-3 border-b border-pandora-cyan/10">
              <button
                onClick={handleCreateSession}
                className="w-full flex items-center gap-2 px-3 py-2 bg-pandora-cyan/10 hover:bg-pandora-cyan/20 border border-pandora-cyan/30 rounded-lg transition-colors text-sm"
              >
                <FolderPlus size={16} className="text-pandora-cyan" />
                <span className="text-pandora-cyan">Новый проект</span>
              </button>
            </div>

            {/* Sessions List */}
            <div className="flex-1 overflow-y-auto p-2 space-y-1">
              {sessionsLoading ? (
                <div className="flex items-center justify-center py-8">
                  <div className="w-6 h-6 border-2 border-pandora-cyan/30 border-t-pandora-cyan rounded-full animate-spin" />
                </div>
              ) : sessions.length === 0 ? (
                <div className="text-center py-8 text-gray-500 text-sm">
                  Нет проектов
                </div>
              ) : (
                sessions.map((session) => (
                  <div
                    key={session.id}
                    className={`
                      group relative rounded-lg transition-colors
                      ${
                        session.id === activeSessionId
                          ? "bg-pandora-cyan/10 border border-pandora-cyan/30"
                          : "hover:bg-white/5 border border-transparent"
                      }
                    `}
                  >
                    {editingId === session.id ? (
                      // Edit mode
                      <div className="p-3 flex items-center gap-2">
                        <input
                          type="text"
                          value={editingName}
                          onChange={(e) => setEditingName(e.target.value)}
                          onBlur={() => handleRename(session.id)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter") handleRename(session.id);
                            if (e.key === "Escape") {
                              setEditingId(null);
                              setEditingName("");
                            }
                          }}
                          autoFocus
                          className="flex-1 bg-black/50 border border-pandora-cyan/30 rounded px-2 py-1 text-sm text-white focus:outline-none focus:border-pandora-cyan"
                        />
                        <button
                          onClick={() => {
                            setEditingId(null);
                            setEditingName("");
                          }}
                          className="p-1 hover:bg-white/10 rounded"
                        >
                          <X size={14} className="text-gray-400" />
                        </button>
                      </div>
                    ) : (
                      // Normal mode
                      <button
                        onClick={() => setActiveSession(session.id)}
                        className="w-full p-3 text-left"
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex-1 min-w-0">
                            <div className="text-sm text-white truncate">
                              {session.name}
                            </div>
                            <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
                              <span>{session.total_generations} генераций</span>
                              <span>{session.total_spent}₽</span>
                            </div>
                          </div>

                          {/* Menu button */}
                          <div className="opacity-0 group-hover:opacity-100 transition-opacity">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                setMenuOpenId(menuOpenId === session.id ? null : session.id);
                              }}
                              className="p-1.5 hover:bg-white/10 rounded"
                            >
                              <MoreVertical size={14} className="text-gray-400" />
                            </button>
                          </div>
                        </div>
                      </button>
                    )}

                    {/* Dropdown menu */}
                    <AnimatePresence>
                      {menuOpenId === session.id && (
                        <motion.div
                          initial={{ opacity: 0, scale: 0.95 }}
                          animate={{ opacity: 1, scale: 1 }}
                          exit={{ opacity: 0, scale: 0.95 }}
                          className="absolute right-2 top-full mt-1 bg-black/95 border border-pandora-cyan/20 rounded-lg shadow-xl z-10 py-1 min-w-[140px]"
                        >
                          <button
                            onClick={() => startEditing(session)}
                            className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-300 hover:bg-white/5"
                          >
                            <Edit3 size={14} />
                            Переименовать
                          </button>
                          {!session.is_default && (
                            <>
                              <button
                                onClick={() => {
                                  // Archive functionality
                                  setMenuOpenId(null);
                                }}
                                className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-300 hover:bg-white/5"
                              >
                                <Archive size={14} />
                                Архивировать
                              </button>
                              <button
                                onClick={() => handleDelete(session.id)}
                                className="w-full flex items-center gap-2 px-3 py-2 text-sm text-red-400 hover:bg-red-500/10"
                              >
                                <Trash2 size={14} />
                                Удалить
                              </button>
                            </>
                          )}
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                ))
              )}
            </div>

            {/* Active Session Info */}
            {activeSession && (
              <div className="p-4 border-t border-pandora-cyan/10">
                <div className="text-xs text-gray-500 mb-1">Активный проект</div>
                <div className="text-sm text-pandora-cyan truncate">
                  {activeSession.name}
                </div>
              </div>
            )}
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};

export default SessionPanel;
