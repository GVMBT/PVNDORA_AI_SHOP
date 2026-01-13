/**
 * PVNDORA HUD Notifications
 *
 * Cyberpunk-style system logs that appear as side panel notifications.
 * Replaces boring alert() with immersive "system logs" experience.
 */

import { AnimatePresence, motion } from "framer-motion";
import {
  AlertTriangle,
  CheckCircle,
  Cpu,
  Database,
  Info,
  Shield,
  Terminal,
  Wifi,
  XCircle,
  Zap,
} from "lucide-react";
import type React from "react";
import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { AudioEngine } from "../../lib/AudioEngine";
import { generateId } from "../../utils/id";

// ============================================
// TYPES
// ============================================

type NotificationType = "success" | "error" | "warning" | "info" | "system";
type NotificationPosition = "top-right" | "top-left" | "bottom-right" | "bottom-left";

interface HUDNotification {
  id: string;
  type: NotificationType;
  title: string;
  message?: string;
  timestamp: Date;
  duration?: number; // ms, 0 = persistent
  icon?: React.ReactNode;
  progress?: number; // 0-100 for progress notifications
}

interface HUDContextType {
  notifications: HUDNotification[];
  addNotification: (notification: Omit<HUDNotification, "id" | "timestamp">) => string;
  removeNotification: (id: string) => void;
  clearAll: () => void;
  updateProgress: (id: string, progress: number) => void;

  // Convenience methods
  success: (title: string, message?: string) => void;
  error: (title: string, message?: string) => void;
  warning: (title: string, message?: string) => void;
  info: (title: string, message?: string) => void;
  system: (title: string, message?: string) => void;
}

// ============================================
// CONTEXT
// ============================================

const HUDContext = createContext<HUDContextType | null>(null);

export const useHUD = (): HUDContextType => {
  const context = useContext(HUDContext);
  if (!context) {
    throw new Error("useHUD must be used within HUDProvider");
  }
  return context;
};

// ============================================
// NOTIFICATION ITEM COMPONENT
// ============================================

interface NotificationItemProps {
  notification: HUDNotification;
  onRemove: (id: string) => void;
  position: NotificationPosition;
}

const NotificationItem: React.FC<NotificationItemProps> = ({
  notification,
  onRemove,
  position,
}) => {
  const [isHovered, setIsHovered] = useState(false);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  // Auto-dismiss logic
  useEffect(() => {
    if (notification.duration && notification.duration > 0 && !isHovered) {
      timerRef.current = setTimeout(() => {
        onRemove(notification.id);
      }, notification.duration);
    }
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [notification.id, notification.duration, onRemove, isHovered]);

  // Pause timer on hover
  useEffect(() => {
    if (isHovered && timerRef.current) {
      clearTimeout(timerRef.current);
    }
  }, [isHovered]);

  const isRight = position.includes("right");

  const typeConfig = {
    success: {
      borderColor: "border-l-pandora-cyan",
      bgColor: "bg-pandora-cyan/5",
      textColor: "text-pandora-cyan",
      icon: notification.icon || <CheckCircle size={14} />,
      prefix: "[OK]",
    },
    error: {
      borderColor: "border-l-red-500",
      bgColor: "bg-red-500/5",
      textColor: "text-red-500",
      icon: notification.icon || <XCircle size={14} />,
      prefix: "[ERR]",
    },
    warning: {
      borderColor: "border-l-yellow-500",
      bgColor: "bg-yellow-500/5",
      textColor: "text-yellow-500",
      icon: notification.icon || <AlertTriangle size={14} />,
      prefix: "[WARN]",
    },
    info: {
      borderColor: "border-l-blue-400",
      bgColor: "bg-blue-400/5",
      textColor: "text-blue-400",
      icon: notification.icon || <Info size={14} />,
      prefix: "[INFO]",
    },
    system: {
      borderColor: "border-l-white",
      bgColor: "bg-white/5",
      textColor: "text-white",
      icon: notification.icon || <Terminal size={14} />,
      prefix: "[SYS]",
    },
  };

  const config = typeConfig[notification.type];
  const timestamp = notification.timestamp.toLocaleTimeString("en-US", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });

  return (
    <motion.div
      layout
      initial={{
        opacity: 0,
        x: isRight ? 100 : -100,
        scale: 0.9,
      }}
      animate={{
        opacity: 1,
        x: 0,
        scale: 1,
      }}
      exit={{
        opacity: 0,
        x: isRight ? 100 : -100,
        scale: 0.9,
      }}
      transition={{
        type: "spring",
        stiffness: 500,
        damping: 30,
      }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onClick={() => onRemove(notification.id)}
      className={`
        relative cursor-pointer group
        border-l-2 ${config.borderColor} ${config.bgColor}
        backdrop-blur-md border border-white/5
        p-3 min-w-[280px] max-w-[360px]
        shadow-[0_4px_20px_rgba(0,0,0,0.5)]
        hover:border-white/10 transition-colors
      `}
    >
      {/* Scanline effect */}
      <div
        className="absolute inset-0 pointer-events-none opacity-[0.02]"
        style={{
          backgroundImage:
            "repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(255,255,255,0.1) 2px, rgba(255,255,255,0.1) 4px)",
        }}
      />

      {/* Header row */}
      <div className="flex items-center gap-2 mb-1">
        <span className={`${config.textColor}`}>{config.icon}</span>
        <span className="font-mono text-[10px] text-gray-500">{config.prefix}</span>
        <span className="font-mono text-[10px] text-gray-600 ml-auto">{timestamp}</span>
      </div>

      {/* Title */}
      <div className={`font-mono text-xs font-bold uppercase tracking-wide ${config.textColor}`}>
        {notification.title}
      </div>

      {/* Message */}
      {notification.message && (
        <div className="font-mono text-[11px] text-gray-400 mt-1 leading-relaxed">
          {notification.message}
        </div>
      )}

      {/* Progress bar */}
      {notification.progress !== undefined && (
        <div className="mt-2">
          <div className="h-1 bg-gray-800 rounded-full overflow-hidden">
            <motion.div
              className={`h-full ${notification.type === "success" ? "bg-pandora-cyan" : "bg-white/50"}`}
              initial={{ width: 0 }}
              animate={{ width: `${notification.progress}%` }}
              transition={{ duration: 0.3 }}
            />
          </div>
          <div className="font-mono text-[9px] text-gray-500 mt-1 text-right">
            {notification.progress}%
          </div>
        </div>
      )}

      {/* Auto-dismiss progress indicator */}
      {notification.duration && notification.duration > 0 && !isHovered && (
        <motion.div
          className="absolute bottom-0 left-0 h-[2px] bg-white/20"
          initial={{ width: "100%" }}
          animate={{ width: "0%" }}
          transition={{ duration: notification.duration / 1000, ease: "linear" }}
        />
      )}

      {/* Close hint */}
      <div className="absolute top-1 right-1 opacity-0 group-hover:opacity-100 transition-opacity">
        <XCircle size={12} className="text-gray-500" />
      </div>
    </motion.div>
  );
};

// ============================================
// PROVIDER COMPONENT
// ============================================

interface HUDProviderProps {
  children: React.ReactNode;
  position?: NotificationPosition;
  maxNotifications?: number;
  defaultDuration?: number;
}

export const HUDProvider: React.FC<HUDProviderProps> = ({
  children,
  position = "top-right",
  maxNotifications = 5,
  defaultDuration = 4000,
}) => {
  const [notifications, setNotifications] = useState<HUDNotification[]>([]);

  const addNotification = useCallback(
    (notification: Omit<HUDNotification, "id" | "timestamp">): string => {
      const id = generateId("hud");
      const newNotification: HUDNotification = {
        ...notification,
        id,
        timestamp: new Date(),
        duration: notification.duration ?? defaultDuration,
      };

      // Play sound
      AudioEngine.resume();
      switch (notification.type) {
        case "success":
          AudioEngine.success();
          break;
        case "error":
          AudioEngine.error();
          break;
        case "warning":
          AudioEngine.warning();
          break;
        case "system":
          AudioEngine.notification();
          break;
        default:
          AudioEngine.notification();
      }

      setNotifications((prev) => {
        const updated = [newNotification, ...prev];
        // Limit max notifications
        return updated.slice(0, maxNotifications);
      });

      return id;
    },
    [defaultDuration, maxNotifications]
  );

  const removeNotification = useCallback((id: string) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  }, []);

  const clearAll = useCallback(() => {
    setNotifications([]);
  }, []);

  const updateProgress = useCallback((id: string, progress: number) => {
    setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, progress } : n)));
  }, []);

  // Convenience methods
  const success = useCallback(
    (title: string, message?: string) => {
      addNotification({ type: "success", title, message });
    },
    [addNotification]
  );

  const error = useCallback(
    (title: string, message?: string) => {
      addNotification({ type: "error", title, message });
    },
    [addNotification]
  );

  const warning = useCallback(
    (title: string, message?: string) => {
      addNotification({ type: "warning", title, message });
    },
    [addNotification]
  );

  const info = useCallback(
    (title: string, message?: string) => {
      addNotification({ type: "info", title, message });
    },
    [addNotification]
  );

  const system = useCallback(
    (title: string, message?: string) => {
      addNotification({ type: "system", title, message });
    },
    [addNotification]
  );

  // Position classes
  const positionClasses = {
    "top-right": "top-4 right-4",
    "top-left": "top-4 left-4",
    "bottom-right": "bottom-4 right-4",
    "bottom-left": "bottom-4 left-4",
  };

  const contextValue: HUDContextType = {
    notifications,
    addNotification,
    removeNotification,
    clearAll,
    updateProgress,
    success,
    error,
    warning,
    info,
    system,
  };

  return (
    <HUDContext.Provider value={contextValue}>
      {children}

      {/* Notifications Container */}
      <div
        className={`
          fixed ${positionClasses[position]} z-[9998]
          flex flex-col gap-2
          pointer-events-none
        `}
      >
        <AnimatePresence mode="popLayout">
          {notifications.map((notification) => (
            <div key={notification.id} className="pointer-events-auto">
              <NotificationItem
                notification={notification}
                onRemove={removeNotification}
                position={position}
              />
            </div>
          ))}
        </AnimatePresence>
      </div>
    </HUDContext.Provider>
  );
};

// ============================================
// PRESET NOTIFICATION ICONS
// ============================================

export const HUDIcons = {
  CPU: <Cpu size={14} />,
  Zap: <Zap size={14} />,
  Shield: <Shield size={14} />,
  Database: <Database size={14} />,
  Wifi: <Wifi size={14} />,
  Terminal: <Terminal size={14} />,
};

export default HUDProvider;
