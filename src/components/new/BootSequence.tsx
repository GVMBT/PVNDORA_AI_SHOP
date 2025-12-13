/**
 * PVNDORA Boot Sequence
 * 
 * Terminal-style loading screen that mimics OS boot process.
 * Hides React loading and creates immersive cyberpunk atmosphere.
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface BootSequenceProps {
  onComplete: () => void;
  minDuration?: number; // Minimum display time in ms
}

interface LogEntry {
  id: number;
  text: string;
  type: 'info' | 'success' | 'warning' | 'error' | 'system';
  delay: number;
}

// Boot sequence messages - simulates system initialization
const BOOT_LOGS: Omit<LogEntry, 'id'>[] = [
  { text: 'PVNDORA PROTOCOL v2.7.4', type: 'system', delay: 0 },
  { text: 'Initializing secure uplink...', type: 'info', delay: 200 },
  { text: 'Loading cryptographic modules...', type: 'info', delay: 400 },
  { text: 'AES-256 encryption: ACTIVE', type: 'success', delay: 600 },
  { text: 'Establishing mesh network...', type: 'info', delay: 800 },
  { text: 'Node discovery: 847 nodes found', type: 'success', delay: 1100 },
  { text: 'Verifying operator credentials...', type: 'info', delay: 1400 },
  { text: 'WARNING: Unsecured connection detected', type: 'warning', delay: 1600 },
  { text: 'Routing through proxy layer...', type: 'info', delay: 1800 },
  { text: 'Connection secured via TOR relay', type: 'success', delay: 2100 },
  { text: 'Loading AI compute modules...', type: 'info', delay: 2300 },
  { text: 'Gemini 2.5 interface: ONLINE', type: 'success', delay: 2500 },
  { text: 'Syncing inventory database...', type: 'info', delay: 2700 },
  { text: 'Stock availability: VERIFIED', type: 'success', delay: 2900 },
  { text: 'SYSTEM READY', type: 'system', delay: 3200 },
];

const TypewriterText: React.FC<{ text: string; speed?: number; onComplete?: () => void }> = ({
  text,
  speed = 15,
  onComplete,
}) => {
  const [displayText, setDisplayText] = useState('');
  const [currentIndex, setCurrentIndex] = useState(0);

  useEffect(() => {
    if (currentIndex < text.length) {
      const timeout = setTimeout(() => {
        setDisplayText(prev => prev + text[currentIndex]);
        setCurrentIndex(prev => prev + 1);
      }, speed);
      return () => clearTimeout(timeout);
    } else if (onComplete) {
      onComplete();
    }
  }, [currentIndex, text, speed, onComplete]);

  return <span>{displayText}<span className="animate-pulse">_</span></span>;
};

const LogLine: React.FC<{ entry: LogEntry; isTyping?: boolean }> = ({ entry, isTyping }) => {
  const colorMap = {
    info: 'text-gray-400',
    success: 'text-pandora-cyan',
    warning: 'text-yellow-500',
    error: 'text-red-500',
    system: 'text-white font-bold',
  };

  const prefixMap = {
    info: '[INFO]',
    success: '[OK]',
    warning: '[WARN]',
    error: '[ERR]',
    system: '[SYS]',
  };

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      className={`font-mono text-xs sm:text-sm ${colorMap[entry.type]}`}
    >
      <span className="text-gray-600 mr-2">{prefixMap[entry.type]}</span>
      {isTyping ? (
        <TypewriterText text={entry.text} speed={10} />
      ) : (
        entry.text
      )}
    </motion.div>
  );
};

export const BootSequence: React.FC<BootSequenceProps> = ({
  onComplete,
  minDuration = 3500,
}) => {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [progress, setProgress] = useState(0);
  const [phase, setPhase] = useState<'boot' | 'ready' | 'fadeout'>('boot');
  const [glitchActive, setGlitchActive] = useState(false);

  // Progress calculation
  const totalDelay = useMemo(() => 
    Math.max(...BOOT_LOGS.map(l => l.delay)) + 500, 
    []
  );

  // Add logs progressively
  useEffect(() => {
    const timers: NodeJS.Timeout[] = [];
    
    BOOT_LOGS.forEach((log, index) => {
      const timer = setTimeout(() => {
        setLogs(prev => [...prev, { ...log, id: index }]);
        setProgress(((index + 1) / BOOT_LOGS.length) * 100);
      }, log.delay);
      timers.push(timer);
    });

    // Transition to ready phase
    const readyTimer = setTimeout(() => {
      setPhase('ready');
    }, totalDelay);
    timers.push(readyTimer);

    // Start fadeout
    const fadeTimer = setTimeout(() => {
      setPhase('fadeout');
    }, Math.max(minDuration, totalDelay + 500));
    timers.push(fadeTimer);

    // Complete
    const completeTimer = setTimeout(() => {
      onComplete();
    }, Math.max(minDuration, totalDelay + 500) + 800);
    timers.push(completeTimer);

    return () => timers.forEach(t => clearTimeout(t));
  }, [totalDelay, minDuration, onComplete]);

  // Random glitch effect
  useEffect(() => {
    const glitchInterval = setInterval(() => {
      if (Math.random() > 0.7) {
        setGlitchActive(true);
        setTimeout(() => setGlitchActive(false), 100 + Math.random() * 150);
      }
    }, 500);
    return () => clearInterval(glitchInterval);
  }, []);

  return (
    <AnimatePresence>
      {phase !== 'fadeout' ? (
        <motion.div
          initial={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.8 }}
          className="fixed inset-0 z-[9999] bg-[#050505] flex flex-col items-center justify-center overflow-hidden"
        >
          {/* Scanlines overlay */}
          <div 
            className="absolute inset-0 pointer-events-none opacity-[0.03]"
            style={{
              backgroundImage: 'repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0, 255, 255, 0.03) 2px, rgba(0, 255, 255, 0.03) 4px)',
            }}
          />

          {/* Grid background */}
          <div 
            className="absolute inset-0 pointer-events-none opacity-[0.02]"
            style={{ 
              backgroundImage: 'linear-gradient(#00FFFF 1px, transparent 1px), linear-gradient(90deg, #00FFFF 1px, transparent 1px)', 
              backgroundSize: '40px 40px',
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
                backgroundSize: '100% 4px',
                transform: `translateX(${Math.random() * 10 - 5}px)`,
              }}
            />
          )}

          {/* Main content container */}
          <motion.div 
            className={`w-full max-w-2xl px-6 transition-transform ${glitchActive ? 'translate-x-1' : ''}`}
            style={{ filter: glitchActive ? 'hue-rotate(90deg)' : 'none' }}
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
              <p className="font-mono text-xs text-gray-500 mt-3 tracking-widest">
                BLACK MARKET PROTOCOL
              </p>
            </div>

            {/* Terminal window */}
            <div className="bg-black/50 border border-gray-800 rounded-sm overflow-hidden backdrop-blur-sm">
              {/* Terminal header */}
              <div className="flex items-center gap-2 px-3 py-2 bg-gray-900/50 border-b border-gray-800">
                <div className="w-3 h-3 rounded-full bg-red-500/50" />
                <div className="w-3 h-3 rounded-full bg-yellow-500/50" />
                <div className="w-3 h-3 rounded-full bg-green-500/50" />
                <span className="ml-2 font-mono text-[10px] text-gray-500">
                  SECURE_TERMINAL — node://pvndora.mesh
                </span>
              </div>

              {/* Terminal content */}
              <div className="p-4 h-64 overflow-y-auto scrollbar-hide space-y-1">
                {logs.map((log, index) => (
                  <LogLine 
                    key={log.id} 
                    entry={log} 
                    isTyping={index === logs.length - 1 && phase === 'boot'}
                  />
                ))}
                
                {phase === 'ready' && (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="mt-4 pt-4 border-t border-gray-800"
                  >
                    <div className="text-pandora-cyan font-mono text-sm font-bold flex items-center gap-2">
                      <span className="w-2 h-2 bg-pandora-cyan rounded-full animate-pulse" />
                      UPLINK ESTABLISHED — WELCOME, OPERATOR
                    </div>
                  </motion.div>
                )}
              </div>
            </div>

            {/* Progress bar */}
            <div className="mt-6">
              <div className="flex justify-between font-mono text-[10px] text-gray-500 mb-2">
                <span>LOADING PROTOCOL</span>
                <span>{Math.round(progress)}%</span>
              </div>
              <div className="h-1 bg-gray-900 rounded-full overflow-hidden">
                <motion.div
                  className="h-full bg-gradient-to-r from-pandora-cyan/50 to-pandora-cyan"
                  initial={{ width: 0 }}
                  animate={{ width: `${progress}%` }}
                  transition={{ duration: 0.3, ease: 'easeOut' }}
                />
              </div>
            </div>

            {/* Skip hint */}
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 2 }}
              className="text-center font-mono text-[10px] text-gray-600 mt-6"
            >
              {phase === 'ready' ? 'PRESS ANY KEY TO CONTINUE' : 'ESTABLISHING SECURE CONNECTION...'}
            </motion.p>
          </motion.div>

          {/* Corner decorations */}
          <div className="absolute top-4 left-4 w-8 h-8 border-l-2 border-t-2 border-pandora-cyan/30" />
          <div className="absolute top-4 right-4 w-8 h-8 border-r-2 border-t-2 border-pandora-cyan/30" />
          <div className="absolute bottom-4 left-4 w-8 h-8 border-l-2 border-b-2 border-pandora-cyan/30" />
          <div className="absolute bottom-4 right-4 w-8 h-8 border-r-2 border-b-2 border-pandora-cyan/30" />
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
};

export default BootSequence;
