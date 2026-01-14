/**
 * PVNDORA Boot Sequence
 *
 * Terminal-style loading screen that performs REAL data preloading:
 * - Authenticates user
 * - Loads product catalog
 * - Initializes audio engine
 * - Preloads cart data
 * - Caches critical resources
 */

import { AnimatePresence, motion } from "framer-motion";
import type React from "react";
import { useCallback, useEffect, useRef, useState } from "react";
import { randomBoolWithProbability, randomFloat } from "../../utils/random";

// Helper: Simple delay function
const delay = (ms: number): Promise<void> => new Promise((r) => setTimeout(r, ms));

// Helper: Run initial boot messages (reduces cognitive complexity)
const runInitialMessages = async (
  addLog: (id: string, text: string, type: LogEntry["type"]) => void
): Promise<void> => {
  addLog("sys", "PVNDORA PROTOCOL v2.7.4", "system");
  await delay(150);
  addLog("sys", "Initializing secure uplink...", "info");
  await delay(100);
};

// Helper: Run final boot messages (reduces cognitive complexity)
const runFinalMessages = async (
  addLog: (id: string, text: string, type: LogEntry["type"]) => void,
  startTime: number,
  minDuration: number,
  setPhase: (phase: BootPhase) => void,
  isCancelled: () => boolean
): Promise<void> => {
  await delay(200);
  addLog("sys", "All systems operational", "success");
  addLog("sys", "SYSTEM READY", "system");

  const elapsed = Date.now() - startTime;
  const remainingTime = Math.max(0, minDuration - elapsed);
  await delay(remainingTime);

  if (!isCancelled()) {
    setPhase("ready");
  }
};

// Helper: Execute all boot tasks sequentially (reduces cognitive complexity)
const runAllTasks = async (
  tasks: BootTask[],
  addLog: (id: string, text: string, type: LogEntry["type"]) => void,
  resultsRef: React.MutableRefObject<Record<string, unknown>>,
  setErrorMessage: (msg: string | null) => void,
  setPhase: (phase: BootPhase) => void,
  setProgress: (progress: number) => void,
  isCancelled: () => boolean
): Promise<boolean> => {
  for (let i = 0; i < tasks.length; i++) {
    if (isCancelled()) return false;

    const shouldContinue = await executeTask(
      tasks[i],
      addLog,
      resultsRef,
      setErrorMessage,
      setPhase
    );

    if (!shouldContinue) return false;
    setProgress(((i + 1) / tasks.length) * 100);
    await delay(80);
  }
  return true;
};

// Helper: Main boot sequence orchestrator (reduces cognitive complexity)
interface BootSequenceParams {
  tasks: BootTask[];
  addLog: (id: string, text: string, type: LogEntry["type"]) => void;
  resultsRef: React.MutableRefObject<Record<string, unknown>>;
  setErrorMessage: (msg: string | null) => void;
  setPhase: (phase: BootPhase) => void;
  setProgress: (progress: number) => void;
  startTime: number;
  minDuration: number;
  isCancelled: () => boolean;
}

const runBootSequenceFlow = async (params: BootSequenceParams): Promise<void> => {
  const {
    tasks,
    addLog,
    resultsRef,
    setErrorMessage,
    setPhase,
    setProgress,
    startTime,
    minDuration,
    isCancelled,
  } = params;

  await runInitialMessages(addLog);

  const success = await runAllTasks(
    tasks,
    addLog,
    resultsRef,
    setErrorMessage,
    setPhase,
    setProgress,
    isCancelled
  );

  if (success && !isCancelled()) {
    await runFinalMessages(addLog, startTime, minDuration, setPhase, isCancelled);
  }
};

// Helper: Execute a single boot task with error handling
const executeTask = async (
  task: BootTask,
  addLog: (id: string, text: string, type: LogEntry["type"]) => void,
  resultsRef: React.MutableRefObject<Record<string, unknown>>,
  setErrorMessage: (msg: string | null) => void,
  setPhase: (phase: BootPhase) => void
): Promise<boolean> => {
  addLog(task.id, task.label, "info");

  try {
    const result = await task.execute();
    resultsRef.current[task.id] = result;
    const successText = task.successLabel || `${task.label.replace("...", "")}: COMPLETE`;
    addLog(task.id, successText, "success");
    return true;
  } catch (error) {
    const errorText = task.errorLabel || `${task.label.replace("...", "")}: FAILED`;
    addLog(task.id, errorText, "error");

    if (task.critical) {
      setErrorMessage(
        `Critical error: ${error instanceof Error ? error.message : "Unknown error"}`
      );
      setPhase("error");
      return false;
    }

    addLog(task.id, "Continuing with degraded functionality...", "warning");
    return true;
  }
};

// Types for boot tasks
export type BootPhase = "boot" | "ready" | "error" | "fadeout";

export interface BootTask {
  id: string;
  label: string; // Display text while loading
  successLabel?: string; // Display text on success
  errorLabel?: string; // Display text on error
  execute: () => Promise<unknown>; // Actual async work
  critical?: boolean; // If true, boot fails on error
}

interface BootSequenceProps {
  onComplete: (results: Record<string, unknown>) => void;
  tasks: BootTask[];
  minDuration?: number; // Minimum display time in ms
}

interface LogEntry {
  id: string;
  text: string;
  type: "info" | "success" | "warning" | "error" | "system";
}

// Helper: Background effects component (reduces cognitive complexity)
const BootSequenceBackground: React.FC<{ glitchActive: boolean }> = ({ glitchActive }) => (
  <>
    {/* Scanlines overlay */}
    <div
      className="absolute inset-0 pointer-events-none opacity-[0.03]"
      style={{
        backgroundImage:
          "repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0, 255, 255, 0.03) 2px, rgba(0, 255, 255, 0.03) 4px)",
      }}
    />

    {/* Grid background */}
    <div
      className="absolute inset-0 pointer-events-none opacity-[0.02]"
      style={{
        backgroundImage:
          "linear-gradient(#00FFFF 1px, transparent 1px), linear-gradient(90deg, #00FFFF 1px, transparent 1px)",
        backgroundSize: "40px 40px",
      }}
    />

    {/* Glitch overlay */}
    {glitchActive && (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="absolute inset-0 pointer-events-none"
        style={{
          background: `linear-gradient(transparent 50%, rgba(0, 255, 255, 0.05) 50%)`,
          backgroundSize: "100% 4px",
          transform: `translateX(${randomFloat(-5, 5)}px)`,
        }}
      />
    )}
  </>
);

// Helper: Terminal header component (reduces cognitive complexity)
const TerminalHeader: React.FC<{ phase: BootPhase }> = ({ phase }) => (
  <div className="flex items-center gap-2 px-3 py-2 bg-gray-900/50 border-b border-gray-800">
    <div className={`w-3 h-3 rounded-full ${phase === "error" ? "bg-red-500" : "bg-red-500/50"}`} />
    <div
      className={`w-3 h-3 rounded-full ${phase === "boot" ? "bg-yellow-500 animate-pulse" : "bg-yellow-500/50"}`}
    />
    <div
      className={`w-3 h-3 rounded-full ${phase === "ready" ? "bg-green-500" : "bg-green-500/50"}`}
    />
    <span className="ml-2 font-mono text-[10px] text-gray-500">
      SECURE_TERMINAL — node://pvndora.mesh
    </span>
  </div>
);

// Helper: Terminal status messages component (reduces cognitive complexity)
const TerminalStatusMessages: React.FC<{
  phase: BootPhase;
  errorMessage: string | null;
}> = ({ phase, errorMessage }) => {
  if (phase === "ready") {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="mt-4 pt-4 border-t border-gray-800"
      >
        <div className="text-pandora-cyan font-mono text-sm font-bold flex items-center gap-2">
          <span className="w-2 h-2 bg-pandora-cyan rounded-full animate-pulse" />
          <span>UPLINK ESTABLISHED — WELCOME, OPERATOR</span>
        </div>
      </motion.div>
    );
  }

  if (phase === "error" && errorMessage) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="mt-4 pt-4 border-t border-red-800"
      >
        <div className="text-red-500 font-mono text-sm font-bold flex items-center gap-2">
          <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
          BOOT FAILURE: {errorMessage}
        </div>
        <button
          type="button"
          onClick={() => globalThis.location.reload()}
          className="mt-4 px-4 py-2 bg-red-500/20 border border-red-500 text-red-500 font-mono text-xs hover:bg-red-500/30 transition-colors"
        >
          RETRY CONNECTION
        </button>
      </motion.div>
    );
  }

  return null;
};

// Helper: Main content component (reduces cognitive complexity)
const BootSequenceContent: React.FC<{
  glitchActive: boolean;
  phase: BootPhase;
  logs: LogEntry[];
  progress: number;
  errorMessage: string | null;
  logsContainerRef: React.RefObject<HTMLDivElement>;
  onEnterSystem: () => void;
}> = ({ glitchActive, phase, logs, progress, errorMessage, logsContainerRef, onEnterSystem }) => (
  <motion.div
    className={`w-full max-w-2xl px-6 transition-transform ${glitchActive ? "translate-x-1" : ""}`}
    style={{ filter: glitchActive ? "hue-rotate(90deg)" : "none" }}
  >
    {/* Header */}
    <div className="mb-8 text-center">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="inline-block"
      >
        <h1 className="font-['Orbitron'] text-3xl sm:text-5xl font-black tracking-wider text-transparent bg-clip-text bg-gradient-to-r from-pandora-cyan to-white mb-2">
          PVNDORA
        </h1>
        <div className="h-[2px] bg-gradient-to-r from-transparent via-pandora-cyan to-transparent" />
      </motion.div>
      <p className="font-mono text-xs text-gray-500 mt-3 tracking-widest">BLACK MARKET PROTOCOL</p>
    </div>

    {/* Terminal window */}
    <div className="bg-black/50 border border-gray-800 rounded-sm overflow-hidden backdrop-blur-sm">
      <TerminalHeader phase={phase} />

      {/* Terminal content */}
      <div ref={logsContainerRef} className="p-4 h-64 overflow-y-auto scrollbar-hide space-y-1">
        {logs.map((log) => (
          <LogLine key={log.id} entry={log} />
        ))}

        <TerminalStatusMessages phase={phase} errorMessage={errorMessage} />
      </div>
    </div>

    {/* Progress bar */}
    <div className="mt-6">
      <div className="flex justify-between font-mono text-[10px] text-gray-500 mb-2">
        <span>{phase === "error" ? "BOOT FAILED" : "LOADING PROTOCOL"}</span>
        <span>{Math.round(progress)}%</span>
      </div>
      <div className="h-1 bg-gray-900 rounded-full overflow-hidden">
        <motion.div
          className={`h-full ${phase === "error" ? "bg-red-500" : "bg-gradient-to-r from-pandora-cyan/50 to-pandora-cyan"}`}
          initial={{ width: 0 }}
          animate={{ width: `${progress}%` }}
          transition={{ duration: 0.3, ease: "easeOut" }}
        />
      </div>
    </div>

    {/* Status hint */}
    {phase === "ready" ? (
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex justify-center mt-6"
      >
        <button
          type="button"
          onClick={onEnterSystem}
          className="px-8 py-3 bg-pandora-cyan text-black font-display font-bold text-sm tracking-wider hover:bg-white transition-colors shadow-[0_0_20px_rgba(0,255,255,0.3)]"
          style={{
            clipPath:
              "polygon(10px 0, 100% 0, 100% calc(100% - 10px), calc(100% - 10px) 100%, 0 100%, 0 10px)",
          }}
        >
          АКТИВИРОВАТЬ ПРОТОКОЛ
        </button>
      </motion.div>
    ) : (
      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.5 }}
        className="text-center font-mono text-[10px] text-gray-600 mt-6"
      >
        {phase === "boot" && "ESTABLISHING SECURE CONNECTION..."}
        {phase === "error" && "CONNECTION TERMINATED"}
      </motion.p>
    )}
  </motion.div>
);

// Helper: Corner decorations component (reduces cognitive complexity)
const BootSequenceDecorations: React.FC = () => (
  <>
    <div className="absolute top-4 left-4 w-8 h-8 border-l-2 border-t-2 border-pandora-cyan/30" />
    <div className="absolute top-4 right-4 w-8 h-8 border-r-2 border-t-2 border-pandora-cyan/30" />
    <div className="absolute bottom-4 left-4 w-8 h-8 border-l-2 border-b-2 border-pandora-cyan/30" />
    <div className="absolute bottom-4 right-4 w-8 h-8 border-r-2 border-b-2 border-pandora-cyan/30" />
  </>
);

const LogLine: React.FC<{ entry: LogEntry }> = ({ entry }) => {
  const colorMap = {
    info: "text-gray-400",
    success: "text-pandora-cyan",
    warning: "text-yellow-500",
    error: "text-red-500",
    system: "text-white font-bold",
  };

  const prefixMap = {
    info: "[...]",
    success: "[OK]",
    warning: "[WARN]",
    error: "[ERR]",
    system: "[SYS]",
  };

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      className={`font-mono text-xs sm:text-sm ${colorMap[entry.type]}`}
    >
      <span className="text-gray-600 mr-2">{prefixMap[entry.type]}</span>
      {entry.text}
    </motion.div>
  );
};

export const BootSequence: React.FC<BootSequenceProps> = ({
  onComplete,
  tasks,
  minDuration = 2000,
}) => {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [progress, setProgress] = useState(0);
  const [phase, setPhase] = useState<BootPhase>("boot");
  const [glitchActive, setGlitchActive] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const resultsRef = useRef<Record<string, unknown>>({});
  const startTimeRef = useRef<number>(Date.now());

  // Add log entry - use crypto for unique IDs to avoid duplicate keys
  const logCounter = useRef(0);
  const addLog = useCallback((id: string, text: string, type: LogEntry["type"]) => {
    logCounter.current += 1;
    const uniqueId = `${id}-${Date.now()}-${logCounter.current}`;
    setLogs((prev) => [...prev, { id: uniqueId, text, type }]);
  }, []);

  // Execute all boot tasks sequentially
  useEffect(() => {
    let cancelled = false;
    const isCancelled = () => cancelled;

    runBootSequenceFlow({
      tasks,
      addLog,
      resultsRef,
      setErrorMessage,
      setPhase,
      setProgress,
      startTime: startTimeRef.current,
      minDuration,
      isCancelled,
    });

    return () => {
      cancelled = true;
    };
  }, [tasks, addLog, minDuration]);

  const handleEnterSystem = async () => {
    setPhase("fadeout");
    // Complete after fade animation
    await new Promise((r) => setTimeout(r, 800));
    onComplete(resultsRef.current);
  };

  // Random glitch effect
  useEffect(() => {
    const glitchInterval = setInterval(() => {
      if (randomBoolWithProbability(0.3)) {
        setGlitchActive(true);
        setTimeout(() => setGlitchActive(false), 100 + randomFloat(0, 150));
      }
    }, 500);
    return () => clearInterval(glitchInterval);
  }, []);

  // Auto-scroll logs container
  const logsContainerRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (logsContainerRef.current) {
      logsContainerRef.current.scrollTop = logsContainerRef.current.scrollHeight;
    }
  }, []);

  if (phase === "fadeout") {
    return null;
  }

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.8 }}
        className="fixed inset-0 z-[9999] bg-[#050505] flex flex-col items-center justify-center overflow-hidden"
      >
        <BootSequenceBackground glitchActive={glitchActive} />
        <BootSequenceContent
          glitchActive={glitchActive}
          phase={phase}
          logs={logs}
          progress={progress}
          errorMessage={errorMessage}
          logsContainerRef={logsContainerRef}
          onEnterSystem={handleEnterSystem}
        />
        <BootSequenceDecorations />
      </motion.div>
    </AnimatePresence>
  );
};

export default BootSequence;
