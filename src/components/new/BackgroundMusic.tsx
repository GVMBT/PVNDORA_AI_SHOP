/**
 * BackgroundMusic Component
 *
 * Manages ambient background music for the PVNDORA app.
 * Preloads sound.ogg completely before playing to avoid stuttering.
 */

import { Volume2, VolumeX } from "lucide-react";
import type React from "react";
import { memo, useEffect, useRef, useState } from "react";
import { logger } from "../../utils/logger";

// Helper: Determine if running inside Telegram WebApp
const isTelegramEnvironment = (): boolean =>
  globalThis.window !== undefined &&
  !!(globalThis as unknown as { Telegram?: { WebApp?: unknown } }).Telegram?.WebApp;

interface BackgroundMusicProps {
  src?: string;
  volume?: number; // 0-1
  autoPlay?: boolean;
  loop?: boolean;
  /** If provided, skip fetch and use this preloaded blob URL directly */
  preloadedBlobUrl?: string;
  onLoadComplete?: () => void;
  onLoadError?: (error: Error) => void;
}

// =============================================================================
// Helper Functions (reduce nesting depth)
// =============================================================================

const fetchAudioBlob = async (src: string): Promise<string> => {
  const response = await fetch(src, { cache: "force-cache" });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }
  const blob = await response.blob();
  return URL.createObjectURL(blob);
};

const waitForAudioReady = (audio: HTMLAudioElement): Promise<void> => {
  return new Promise((resolve) => {
    if (audio.readyState >= 3) {
      resolve();
      return;
    }

    const onReady = () => {
      audio.removeEventListener("canplay", onReady);
      resolve();
    };
    audio.addEventListener("canplay", onReady);

    // Timeout after 3 seconds
    setTimeout(() => {
      audio.removeEventListener("canplay", onReady);
      resolve();
    }, 3000);
  });
};

const tryAutoplay = async (
  audio: HTMLAudioElement,
  volume: number,
  isPlayingRef: React.RefObject<boolean>,
  setIsPlaying: (playing: boolean) => void,
  cancelled: () => boolean
): Promise<void> => {
  if (cancelled()) {
    return;
  }

  try {
    audio.volume = volume;
    audio.muted = true;

    await waitForAudioReady(audio);
    if (cancelled()) {
      return;
    }

    await audio.play();

    if (!audio.paused) {
      audio.muted = false;
      (isPlayingRef as React.MutableRefObject<boolean>).current = true;
      setIsPlaying(true);
      logger.debug("[BackgroundMusic] Autoplay succeeded");
    }
  } catch (err) {
    logger.warn("[BackgroundMusic] Autoplay blocked", err);
  }
};

interface AudioLoadErrorContext {
  retryCountRef: React.RefObject<number>;
  maxRetries: number;
  loadAudio: () => void;
  cancelled: () => boolean;
  setLoadError: (error: Error) => void;
  setIsLoading: (loading: boolean) => void;
  onLoadErrorRef: React.RefObject<((error: Error) => void) | undefined>;
  ownedBlobUrl: string | null;
}

const handleAudioLoadError = (
  audioError: MediaError | null,
  context: AudioLoadErrorContext
): void => {
  const {
    retryCountRef,
    maxRetries,
    loadAudio,
    cancelled,
    setLoadError,
    setIsLoading,
    onLoadErrorRef,
    ownedBlobUrl,
  } = context;
  const errorMsg = audioError ? `Code ${audioError.code}: ${audioError.message}` : "Unknown error";

  // CRITICAL: Stop retrying if format is not supported (Code 4)
  if (audioError?.code === 4) {
    logger.error("[BackgroundMusic] Audio format not supported. Stopping retries.");
    setLoadError(new Error("Audio format not supported"));
    setIsLoading(false);
    return;
  }

  const error = new Error(`Failed to load audio: ${errorMsg}`);
  logger.error("[BackgroundMusic] Load error", error);

  // Retry logic
  const currentRetry = retryCountRef.current ?? 0;
  if (currentRetry < maxRetries) {
    (retryCountRef as React.MutableRefObject<number>).current = currentRetry + 1;
    const delay = Math.min(2000 * 2 ** (currentRetry + 1), 10_000);

    setTimeout(() => {
      if (!cancelled()) {
        loadAudio();
      }
    }, delay);
    return;
  }

  setLoadError(error);
  setIsLoading(false);
  onLoadErrorRef.current?.(error);

  if (ownedBlobUrl) {
    URL.revokeObjectURL(ownedBlobUrl);
  }
};

const setupAudioEventListeners = (
  audio: HTMLAudioElement,
  cancelled: () => boolean,
  isPlayingRef: React.RefObject<boolean>,
  setIsPlaying: (playing: boolean) => void,
  setIsLoading: (loading: boolean) => void,
  onLoadCompleteRef: React.RefObject<(() => void) | undefined>
): (() => void) => {
  const handleCanPlayThrough = () => {
    if (cancelled()) {
      return;
    }
    setIsLoading(false);
    onLoadCompleteRef.current?.();
  };

  const handleWaiting = () => {
    logger.warn("[BackgroundMusic] Buffering...");
  };

  const handleStalled = () => {
    logger.warn("[BackgroundMusic] Stalled - retrying...");
    const isCurrentlyPlaying = isPlayingRef.current;
    if (!cancelled() && isCurrentlyPlaying) {
      setTimeout(() => {
        const stillPlaying = isPlayingRef.current;
        if (!cancelled() && stillPlaying && audio) {
          audio.play().catch(() => {});
        }
      }, 500);
    }
  };

  const handlePlay = () => {
    if (!cancelled()) {
      (isPlayingRef as React.MutableRefObject<boolean>).current = true;
      setIsPlaying(true);
    }
  };

  const handlePause = () => {
    if (!(cancelled() || document.hidden)) {
      (isPlayingRef as React.MutableRefObject<boolean>).current = false;
      setIsPlaying(false);
    }
  };

  const handleEnded = () => {
    if (!cancelled()) {
      (isPlayingRef as React.MutableRefObject<boolean>).current = false;
      setIsPlaying(false);
    }
  };

  const handleProgress = () => {
    // Buffering tracked internally
  };

  audio.addEventListener("canplaythrough", handleCanPlayThrough, { once: true });
  audio.addEventListener("waiting", handleWaiting);
  audio.addEventListener("stalled", handleStalled);
  audio.addEventListener("play", handlePlay);
  audio.addEventListener("pause", handlePause);
  audio.addEventListener("ended", handleEnded);
  audio.addEventListener("progress", handleProgress);

  return () => {
    audio.removeEventListener("canplaythrough", handleCanPlayThrough);
    audio.removeEventListener("waiting", handleWaiting);
    audio.removeEventListener("stalled", handleStalled);
    audio.removeEventListener("play", handlePlay);
    audio.removeEventListener("pause", handlePause);
    audio.removeEventListener("ended", handleEnded);
    audio.removeEventListener("progress", handleProgress);
  };
};

// =============================================================================
// Main Component
// =============================================================================

const BackgroundMusicComponent: React.FC<BackgroundMusicProps> = ({
  src = "/sound.ogg",
  volume = 0.2,
  autoPlay = true,
  loop = true,
  preloadedBlobUrl,
  onLoadComplete,
  onLoadError,
}) => {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const isPlayingRef = useRef(false);
  const wasPlayingBeforeHiddenRef = useRef(false);
  const [, setIsPlaying] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<Error | null>(null);
  const retryCountRef = useRef(0);
  const maxRetries = 3;

  const onLoadCompleteRef = useRef(onLoadComplete);
  const onLoadErrorRef = useRef(onLoadError);

  useEffect(() => {
    onLoadCompleteRef.current = onLoadComplete;
    onLoadErrorRef.current = onLoadError;
  }, [onLoadComplete, onLoadError]);

  // Preload audio file
  useEffect(() => {
    let cancelled = false;
    let ownedBlobUrl: string | null = null;
    let cleanupListeners: (() => void) | null = null;

    const isCancelled = () => cancelled;

    const loadAudio = async () => {
      try {
        let audioSrc: string;

        if (isTelegramEnvironment()) {
          audioSrc = src;
        } else if (preloadedBlobUrl) {
          audioSrc = preloadedBlobUrl;
        } else {
          const blobUrl = await fetchAudioBlob(src);
          ownedBlobUrl = blobUrl;
          audioSrc = blobUrl;

          if (cancelled) {
            URL.revokeObjectURL(blobUrl);
            return;
          }
        }

        const audio = new Audio(audioSrc);
        audio.loop = loop;
        audio.volume = volume;
        audio.preload = "auto";
        audio.crossOrigin = "anonymous";

        audioRef.current = audio;

        if (autoPlay) {
          void tryAutoplay(audio, volume, isPlayingRef, setIsPlaying, isCancelled);
        }

        const retryLoadAudio = () => {
          void loadAudio();
        };

        const handleError = (e: Event) => {
          if (cancelled) {
            return;
          }
          const audioError = (e.target as HTMLAudioElement).error;
          handleAudioLoadError(audioError, {
            retryCountRef,
            maxRetries,
            loadAudio: retryLoadAudio,
            cancelled: isCancelled,
            setLoadError,
            setIsLoading,
            onLoadErrorRef,
            ownedBlobUrl,
          });
        };

        audio.addEventListener("error", handleError);

        cleanupListeners = setupAudioEventListeners(
          audio,
          isCancelled,
          isPlayingRef,
          setIsPlaying,
          setIsLoading,
          onLoadCompleteRef
        );

        audio.load();

        return () => {
          audio.removeEventListener("error", handleError);
          cleanupListeners?.();
          audio.pause();
          audio.src = "";
          if (ownedBlobUrl) {
            URL.revokeObjectURL(ownedBlobUrl);
          }
          audioRef.current = null;
        };
      } catch (error) {
        if (cancelled) {
          return;
        }

        logger.error("[BackgroundMusic] Prefetch error", error);

        if (retryCountRef.current < maxRetries) {
          retryCountRef.current++;
          setTimeout(() => {
            if (!cancelled) {
              loadAudio();
            }
          }, 1000 * retryCountRef.current);
          return;
        }

        const err = error instanceof Error ? error : new Error("Unknown prefetch error");
        setLoadError(err);
        setIsLoading(false);
        onLoadErrorRef.current?.(err);
      }
    };

    loadAudio();

    return () => {
      cancelled = true;
      cleanupListeners?.();
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.src = "";
        audioRef.current = null;
      }
    };
  }, [src, loop, volume, autoPlay, preloadedBlobUrl]);

  // Update volume when prop changes
  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.volume = isMuted ? 0 : volume;
    }
  }, [volume, isMuted]);

  // Handle page visibility
  useEffect(() => {
    const resumePlayback = async () => {
      const audio = audioRef.current;
      if (!audio || document.hidden) {
        return;
      }

      try {
        await audio.play();
        isPlayingRef.current = true;
        setIsPlaying(true);
      } catch (err) {
        logger.warn("[BackgroundMusic] Resume after visibility change failed", err);
        isPlayingRef.current = false;
        setIsPlaying(false);
        wasPlayingBeforeHiddenRef.current = false;
      }
    };

    const handleVisibilityChange = () => {
      const audio = audioRef.current;
      if (!audio) {
        return;
      }

      if (document.hidden) {
        wasPlayingBeforeHiddenRef.current = isPlayingRef.current;
        if (isPlayingRef.current) {
          audio.pause();
        }
        return;
      }

      const shouldResume = wasPlayingBeforeHiddenRef.current && autoPlay && !isMuted;
      if (shouldResume) {
        const handleResumeError = () => {
          // Ignore: autoplay policies vary
        };
        setTimeout(() => {
          resumePlayback().catch(handleResumeError);
        }, 100);
      }
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => {
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [autoPlay, isMuted]);

  const toggleMute = () => {
    if (!audioRef.current) {
      return;
    }
    setIsMuted(!isMuted);
  };

  // Auto-resume on user interaction
  useEffect(() => {
    const tryPlay = () => {
      const audio = audioRef.current;
      if (!(audio && autoPlay) || isMuted || loadError || isLoading || isPlayingRef.current) {
        return;
      }

      audio
        .play()
        .then(() => {
          isPlayingRef.current = true;
          setIsPlaying(true);
        })
        .catch(() => {
          // Ignore: autoplay policies vary
        });
    };

    globalThis.addEventListener("pointerdown", tryPlay, { passive: true });
    globalThis.addEventListener("touchstart", tryPlay, { passive: true });
    globalThis.addEventListener("click", tryPlay);
    globalThis.addEventListener("keydown", tryPlay);

    return () => {
      globalThis.removeEventListener("pointerdown", tryPlay);
      globalThis.removeEventListener("touchstart", tryPlay);
      globalThis.removeEventListener("click", tryPlay);
      globalThis.removeEventListener("keydown", tryPlay);
    };
  }, [autoPlay, isLoading, loadError, isMuted]);

  if (loadError) {
    return null;
  }

  return (
    <div className="group pointer-events-none fixed right-4 bottom-24 z-[90] opacity-0 transition-opacity hover:opacity-100">
      <button
        className="pointer-events-auto flex h-10 w-10 items-center justify-center rounded-full border border-white/10 bg-black/50 transition-all hover:border-pandora-cyan/30 hover:bg-black/70"
        onClick={toggleMute}
        title={isMuted ? "Unmute ambient music" : "Mute ambient music"}
        type="button"
      >
        {isMuted ? (
          <VolumeX className="text-gray-400" size={16} />
        ) : (
          <Volume2 className="text-pandora-cyan" size={16} />
        )}
      </button>
      {isLoading && (
        <div className="absolute -top-6 left-1/2 -translate-x-1/2 whitespace-nowrap font-mono text-[9px] text-gray-500">
          Loading...
        </div>
      )}
    </div>
  );
};

export const BackgroundMusic = memo(BackgroundMusicComponent);

export default BackgroundMusic;
