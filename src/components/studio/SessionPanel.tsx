/**
 * Session Panel - Left sidebar for managing projects/canvases
 */

import { AnimatePresence, motion } from "framer-motion";
import { Archive, ChevronLeft, Edit3, FolderPlus, MoreVertical, Trash2, X } from "lucide-react";
import { useState } from "react";
import { selectActiveSession, useStudioStore } from "../../stores/studioStore";

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

  const startEditing = (session: (typeof sessions)[0]) => {
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
            animate={{ opacity: 1 }}
            className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
            exit={{ opacity: 0 }}
            initial={{ opacity: 0 }}
            onClick={onClose}
          />

          {/* Panel */}
          <motion.div
            animate={{ x: 0 }}
            className="fixed top-0 left-0 z-50 flex h-full w-80 flex-col border-pandora-cyan/20 border-r bg-black/90"
            exit={{ x: -320 }}
            initial={{ x: -320 }}
            transition={{ type: "spring", damping: 25, stiffness: 300 }}
          >
            {/* Header */}
            <div className="flex items-center justify-between border-pandora-cyan/10 border-b p-4">
              <div className="flex items-center gap-2">
                <div className="h-2 w-2 animate-pulse rounded-full bg-pandora-cyan" />
                <span className="font-medium text-gray-300 text-sm">PROJECTS</span>
              </div>
              <button
                className="rounded-lg p-2 transition-colors hover:bg-white/5"
                onClick={onClose}
                type="button"
              >
                <ChevronLeft className="text-gray-400" size={18} />
              </button>
            </div>

            {/* New Project Button */}
            <div className="border-pandora-cyan/10 border-b p-3">
              <button
                className="flex w-full items-center gap-2 rounded-lg border border-pandora-cyan/30 bg-pandora-cyan/10 px-3 py-2 text-sm transition-colors hover:bg-pandora-cyan/20"
                onClick={handleCreateSession}
                type="button"
              >
                <FolderPlus className="text-pandora-cyan" size={16} />
                <span className="text-pandora-cyan">Новый проект</span>
              </button>
            </div>

            {/* Sessions List */}
            <div className="flex-1 space-y-1 overflow-y-auto p-2">
              {sessionsLoading && (
                <div className="flex items-center justify-center py-8">
                  <div className="h-6 w-6 animate-spin rounded-full border-2 border-pandora-cyan/30 border-t-pandora-cyan" />
                </div>
              )}
              {!sessionsLoading && sessions.length === 0 && (
                <div className="py-8 text-center text-gray-500 text-sm">Нет проектов</div>
              )}
              {!sessionsLoading &&
                sessions.length > 0 &&
                sessions.map((session) => (
                  <div
                    className={`group relative rounded-lg transition-colors ${
                      session.id === activeSessionId
                        ? "border border-pandora-cyan/30 bg-pandora-cyan/10"
                        : "border border-transparent hover:bg-white/5"
                    }
                    `}
                    key={session.id}
                  >
                    {editingId === session.id ? (
                      // Edit mode
                      <div className="flex items-center gap-2 p-3">
                        <input
                          autoFocus
                          className="flex-1 rounded border border-pandora-cyan/30 bg-black/50 px-2 py-1 text-sm text-white focus:border-pandora-cyan focus:outline-none"
                          onBlur={() => handleRename(session.id)}
                          onChange={(e) => setEditingName(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter") {
                              handleRename(session.id);
                            }
                            if (e.key === "Escape") {
                              setEditingId(null);
                              setEditingName("");
                            }
                          }}
                          // biome-ignore lint/a11y/noAutofocus: Auto-focus is intentional for better UX when editing session name
                          type="text"
                          value={editingName}
                        />
                        <button
                          className="rounded p-1 hover:bg-white/10"
                          onClick={() => {
                            setEditingId(null);
                            setEditingName("");
                          }}
                          type="button"
                        >
                          <X className="text-gray-400" size={14} />
                        </button>
                      </div>
                    ) : (
                      // Normal mode
                      <button
                        className="w-full p-3 text-left"
                        onClick={() => setActiveSession(session.id)}
                        type="button"
                      >
                        <div className="flex items-center justify-between">
                          <div className="min-w-0 flex-1">
                            <div className="truncate text-sm text-white">{session.name}</div>
                            <div className="mt-1 flex items-center gap-3 text-gray-500 text-xs">
                              <span>{session.total_generations} генераций</span>
                              <span>{session.total_spent}₽</span>
                            </div>
                          </div>

                          {/* Menu button */}
                          <div className="opacity-0 transition-opacity group-hover:opacity-100">
                            <button
                              className="rounded p-1.5 hover:bg-white/10"
                              onClick={(e) => {
                                e.stopPropagation();
                                setMenuOpenId(menuOpenId === session.id ? null : session.id);
                              }}
                              type="button"
                            >
                              <MoreVertical className="text-gray-400" size={14} />
                            </button>
                          </div>
                        </div>
                      </button>
                    )}

                    {/* Dropdown menu */}
                    <AnimatePresence>
                      {menuOpenId === session.id && (
                        <motion.div
                          animate={{ opacity: 1, scale: 1 }}
                          className="absolute top-full right-2 z-10 mt-1 min-w-[140px] rounded-lg border border-pandora-cyan/20 bg-black/95 py-1 shadow-xl"
                          exit={{ opacity: 0, scale: 0.95 }}
                          initial={{ opacity: 0, scale: 0.95 }}
                        >
                          <button
                            className="flex w-full items-center gap-2 px-3 py-2 text-gray-300 text-sm hover:bg-white/5"
                            onClick={() => startEditing(session)}
                            type="button"
                          >
                            <Edit3 size={14} />
                            Переименовать
                          </button>
                          {!session.is_default && (
                            <>
                              <button
                                className="flex w-full items-center gap-2 px-3 py-2 text-gray-300 text-sm hover:bg-white/5"
                                onClick={() => {
                                  // Archive functionality
                                  setMenuOpenId(null);
                                }}
                                type="button"
                              >
                                <Archive size={14} />
                                Архивировать
                              </button>
                              <button
                                className="flex w-full items-center gap-2 px-3 py-2 text-red-400 text-sm hover:bg-red-500/10"
                                onClick={() => handleDelete(session.id)}
                                type="button"
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
                ))}
            </div>

            {/* Active Session Info */}
            {activeSession && (
              <div className="border-pandora-cyan/10 border-t p-4">
                <div className="mb-1 text-gray-500 text-xs">Активный проект</div>
                <div className="truncate text-pandora-cyan text-sm">{activeSession.name}</div>
              </div>
            )}
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};

export default SessionPanel;
