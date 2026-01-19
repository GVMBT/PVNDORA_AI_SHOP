/**
 * Crystallization Animation
 *
 * "Энергетический сгусток" который кристаллизуется в готовый контент.
 * Используется во время генерации для создания "вау-эффекта".
 *
 * Стадии:
 * 1. SPAWNING - Шар появляется из центра
 * 2. PULSING - Шар пульсирует во время генерации
 * 3. CRYSTALLIZING - Шар трансформируется в карточку
 * 4. COMPLETE - Готовая карточка с результатом
 */

import { AnimatePresence, motion } from "framer-motion";
import { AlertCircle, Download, Play, RefreshCw } from "lucide-react";
import type React from "react";
import { useEffect, useState } from "react";

type CrystallizationStage = "spawning" | "pulsing" | "crystallizing" | "complete" | "failed";

interface CrystallizationAnimationProps {
  /** Generation status */
  status: "queued" | "processing" | "completed" | "failed";
  /** Progress percentage (0-100) */
  progress: number;
  /** Result URL when completed */
  resultUrl?: string | null;
  /** Thumbnail URL */
  thumbnailUrl?: string | null;
  /** Content type */
  type: "video" | "image" | "audio";
  /** Error message if failed */
  errorMessage?: string | null;
  /** Unique ID for layout animation */
  layoutId: string;
  /** Callback when retry is clicked */
  onRetry?: () => void;
  /** Callback when download is clicked */
  onDownload?: () => void;
}

export const CrystallizationAnimation: React.FC<CrystallizationAnimationProps> = ({
  status,
  progress,
  resultUrl,
  thumbnailUrl,
  type,
  errorMessage,
  layoutId,
  onRetry,
  onDownload,
}) => {
  const [stage, setStage] = useState<CrystallizationStage>("spawning");
  const [showContent, setShowContent] = useState(false);

  // Determine stage based on status
  useEffect(() => {
    if (status === "queued") {
      setStage("spawning");
    } else if (status === "processing") {
      // Start pulsing after spawn animation
      const timer = setTimeout(() => setStage("pulsing"), 500);
      return () => clearTimeout(timer);
    } else if (status === "completed") {
      // Crystallize then show content
      setStage("crystallizing");
      const timer = setTimeout(() => {
        setStage("complete");
        setShowContent(true);
      }, 800);
      return () => clearTimeout(timer);
    } else if (status === "failed") {
      setStage("failed");
    }
  }, [status]);

  return (
    <motion.div
      animate={{ scale: 1, opacity: 1 }}
      className="relative"
      initial={{ scale: 0, opacity: 0 }}
      layoutId={layoutId}
      transition={{ type: "spring", damping: 20, stiffness: 300 }}
    >
      <AnimatePresence mode="wait">
        {/* SPAWNING & PULSING: Energy Orb */}
        {(stage === "spawning" || stage === "pulsing") && (
          <motion.div
            animate={{ scale: 1 }}
            className="relative flex h-48 w-48 items-center justify-center"
            exit={{ scale: 0.8, opacity: 0 }}
            initial={{ scale: 0 }}
            key="orb"
            transition={{ duration: 0.3 }}
          >
            {/* Outer glow rings */}
            <motion.div
              animate={{
                scale: stage === "pulsing" ? [1, 1.3, 1] : 1,
                opacity: stage === "pulsing" ? [0.5, 0.8, 0.5] : 0.5,
              }}
              className="absolute inset-0 rounded-full"
              style={{
                background: "radial-gradient(circle, rgba(0,255,255,0.15) 0%, transparent 70%)",
              }}
              transition={{
                duration: 2,
                repeat: Number.POSITIVE_INFINITY,
                ease: "easeInOut",
              }}
            />

            {/* Middle ring */}
            <motion.div
              animate={{
                scale: stage === "pulsing" ? [1, 1.2, 1] : 1,
                rotate: 360,
              }}
              className="absolute h-32 w-32 rounded-full border border-pandora-cyan/30"
              transition={{
                scale: { duration: 1.5, repeat: Number.POSITIVE_INFINITY },
                rotate: { duration: 8, repeat: Number.POSITIVE_INFINITY, ease: "linear" },
              }}
            />

            {/* Core orb */}
            <motion.div
              animate={{
                scale: stage === "pulsing" ? [1, 1.1, 1] : [0.9, 1],
              }}
              className="relative h-20 w-20 overflow-hidden rounded-full"
              style={{
                background:
                  "radial-gradient(circle at 30% 30%, rgba(0,255,255,0.8), rgba(0,100,150,0.6))",
                boxShadow: "0 0 40px rgba(0,255,255,0.5), inset 0 0 20px rgba(255,255,255,0.2)",
              }}
              transition={{
                duration: stage === "pulsing" ? 1 : 0.5,
                repeat: stage === "pulsing" ? Number.POSITIVE_INFINITY : 0,
              }}
            >
              {/* Inner swirl effect */}
              <motion.div
                animate={{ rotate: 360 }}
                className="absolute inset-0"
                style={{
                  background:
                    "conic-gradient(from 0deg, transparent, rgba(255,255,255,0.3), transparent)",
                }}
                transition={{ duration: 3, repeat: Number.POSITIVE_INFINITY, ease: "linear" }}
              />

              {/* Progress indicator */}
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="font-bold text-white text-xs drop-shadow-lg">{progress}%</span>
              </div>
            </motion.div>

            {/* Particle effects */}
            {stage === "pulsing" && (
              <>
                {[...Array(6)].map((_, i) => (
                  <motion.div
                    animate={{
                      x: Math.cos((i * Math.PI) / 3) * 60,
                      y: Math.sin((i * Math.PI) / 3) * 60,
                      opacity: [0, 1, 0],
                    }}
                    className="absolute h-1 w-1 rounded-full bg-pandora-cyan"
                    initial={{
                      x: 0,
                      y: 0,
                      opacity: 0,
                    }}
                    key={i}
                    transition={{
                      duration: 2,
                      repeat: Number.POSITIVE_INFINITY,
                      delay: i * 0.3,
                    }}
                  />
                ))}
              </>
            )}
          </motion.div>
        )}

        {/* CRYSTALLIZING: Morphing to card */}
        {stage === "crystallizing" && (
          <motion.div
            animate={{ borderRadius: 12, width: 256, height: 160 }}
            className="h-40 w-64 overflow-hidden rounded-xl"
            initial={{ borderRadius: "50%", width: 80, height: 80 }}
            key="crystallizing"
            style={{
              background: "linear-gradient(135deg, rgba(0,255,255,0.2), rgba(0,50,80,0.8))",
              boxShadow: "0 0 30px rgba(0,255,255,0.3)",
            }}
            transition={{ duration: 0.6, ease: "easeOut" }}
          >
            {/* Shimmer effect */}
            <motion.div
              animate={{ x: ["-100%", "100%"] }}
              className="absolute inset-0"
              style={{
                background:
                  "linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent)",
              }}
              transition={{ duration: 1, repeat: 2 }}
            />
          </motion.div>
        )}

        {/* COMPLETE: Result card */}
        {stage === "complete" && showContent && (
          <motion.div
            animate={{ opacity: 1, scale: 1 }}
            className="w-64 overflow-hidden rounded-xl border border-pandora-cyan/30 bg-black/80"
            initial={{ opacity: 0, scale: 0.95 }}
            key="complete"
            transition={{ duration: 0.3 }}
          >
            {/* Media preview */}
            <div className="relative aspect-video bg-black">
              {type === "video" && resultUrl && (
                <video
                  className="h-full w-full object-cover"
                  loop
                  muted
                  onMouseEnter={(e) => e.currentTarget.play()}
                  onMouseLeave={(e) => {
                    e.currentTarget.pause();
                    e.currentTarget.currentTime = 0;
                  }}
                  playsInline
                  poster={thumbnailUrl || undefined}
                  src={resultUrl}
                />
              )}
              {type === "image" && resultUrl && (
                <img alt="Generated" className="h-full w-full object-cover" src={resultUrl} />
              )}
              {type === "audio" && (
                <div className="flex h-full w-full items-center justify-center bg-gradient-to-br from-purple-900/50 to-black">
                  <motion.div
                    animate="visible"
                    className="flex h-12 items-end gap-1"
                    initial="hidden"
                  >
                    {[...Array(5)].map((_, i) => (
                      <motion.div
                        animate={{
                          height: [12, 32, 12],
                        }}
                        className="w-2 rounded-full bg-pandora-cyan"
                        key={i}
                        transition={{
                          duration: 0.8,
                          repeat: Number.POSITIVE_INFINITY,
                          delay: i * 0.1,
                        }}
                      />
                    ))}
                  </motion.div>
                </div>
              )}

              {/* Play button overlay for video */}
              {type === "video" && (
                <div className="absolute inset-0 flex items-center justify-center bg-black/30 opacity-0 transition-opacity hover:opacity-100">
                  <div className="flex h-12 w-12 items-center justify-center rounded-full bg-white/20 backdrop-blur-sm">
                    <Play className="ml-1 text-white" size={24} />
                  </div>
                </div>
              )}
            </div>

            {/* Actions */}
            <div className="flex items-center justify-between p-3">
              <span className="text-gray-400 text-xs uppercase">{type}</span>
              <button
                className="rounded-lg p-2 transition-colors hover:bg-white/10"
                onClick={onDownload}
              >
                <Download className="text-pandora-cyan" size={16} />
              </button>
            </div>
          </motion.div>
        )}

        {/* FAILED: Error state */}
        {stage === "failed" && (
          <motion.div
            animate={{ opacity: 1, scale: 1 }}
            className="w-64 overflow-hidden rounded-xl border border-red-500/30 bg-red-950/30 p-4"
            initial={{ opacity: 0, scale: 0.95 }}
            key="failed"
          >
            <div className="flex items-start gap-3">
              <AlertCircle className="mt-0.5 flex-shrink-0 text-red-400" size={20} />
              <div className="flex-1">
                <div className="font-medium text-red-300 text-sm">Ошибка генерации</div>
                <div className="mt-1 text-red-400/70 text-xs">
                  {errorMessage || "Что-то пошло не так"}
                </div>
              </div>
            </div>

            {onRetry && (
              <button
                className="mt-3 flex w-full items-center justify-center gap-2 rounded-lg bg-red-500/20 py-2 text-red-300 text-sm transition-colors hover:bg-red-500/30"
                onClick={onRetry}
              >
                <RefreshCw size={14} />
                Попробовать снова
              </button>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

export default CrystallizationAnimation;
