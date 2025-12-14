/**
 * BackgroundMusic Component
 * 
 * Manages ambient background music for the PVNDORA app.
 * Preloads sound.ogg completely before playing to avoid stuttering.
 */

import React, { useEffect, useRef, useState, memo } from 'react';
import { Volume2, VolumeX } from 'lucide-react';
import { logger } from '../../utils/logger';

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

const BackgroundMusicComponent: React.FC<BackgroundMusicProps> = ({
  src = '/sound.ogg',
  volume = 0.20,
  autoPlay = true,
  loop = true,
  preloadedBlobUrl,
  onLoadComplete,
  onLoadError,
}) => {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const isPlayingRef = useRef(false);
  const wasPlayingBeforeHiddenRef = useRef(false); // Track if music was playing before tab was hidden
  const [isPlaying, setIsPlaying] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<Error | null>(null);
  const [loadStartTime] = useState(Date.now());
  const retryCountRef = useRef(0);
  const maxRetries = 3;
  
  // Store callbacks in refs to prevent effect re-runs
  const onLoadCompleteRef = useRef(onLoadComplete);
  const onLoadErrorRef = useRef(onLoadError);
  
  useEffect(() => {
    onLoadCompleteRef.current = onLoadComplete;
    onLoadErrorRef.current = onLoadError;
  }, [onLoadComplete, onLoadError]);

  // Preload audio file completely before creating Audio element
  useEffect(() => {
    let cancelled = false;
    let ownedBlobUrl: string | null = null; // Track if we created the blob URL ourselves

    const loadAudio = async () => {
      try {
        const isTelegramWebApp = typeof window !== 'undefined' && !!(window as any).Telegram?.WebApp;

        let audioSrc: string;

        // In Telegram Mini App we want the earliest possible autoplay attempt.
        // Using blob prefetch delays `play()` and increases the chance Telegram blocks it.
        if (isTelegramWebApp) {
          audioSrc = src;
        } else if (preloadedBlobUrl) {
          // If preloaded blob URL provided, skip fetch entirely
          audioSrc = preloadedBlobUrl;
          // Don't mark as owned - boot sequence manages this URL's lifecycle
        } else {
          // Prefetch for smoother playback in regular browsers
          const response = await fetch(src, { cache: 'force-cache' });
          if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
          }

          const blob = await response.blob();
          const blobUrl = URL.createObjectURL(blob);
          ownedBlobUrl = blobUrl; // Mark as owned so we revoke on cleanup
          audioSrc = blobUrl;

          if (cancelled) {
            URL.revokeObjectURL(blobUrl);
            return;
          }
        }

        // Create Audio element
        const audio = new Audio(audioSrc);
        audio.loop = loop;
        audio.volume = volume;
        audio.preload = 'auto';
        
        // CRITICAL: Set crossOrigin to avoid CORS issues
        audio.crossOrigin = 'anonymous';
        
        audioRef.current = audio;

        // Try to start automatically "like before":
        // Start muted (allowed by autoplay policies more often), then unmute.
        if (autoPlay) {
          const tryAutoStart = async () => {
            if (cancelled) return;
            try {
              // Set volume BEFORE starting (muted doesn't affect volume property)
              audio.volume = volume;
              
              // Silent start to satisfy autoplay restrictions
              audio.muted = true;
              
              // Wait for enough data to play
              if (audio.readyState < 3) {
                await new Promise<void>((resolve) => {
                  const onReady = () => {
                    audio.removeEventListener('canplay', onReady);
                    resolve();
                  };
                  audio.addEventListener('canplay', onReady);
                  // Timeout after 3 seconds
                  setTimeout(() => {
                    audio.removeEventListener('canplay', onReady);
                    resolve();
                  }, 3000);
                });
              }
              
              if (cancelled) return;
              
              await audio.play();
              
              // Only unmute if playback actually started
              if (!audio.paused) {
                audio.muted = false;
                isPlayingRef.current = true;
                setIsPlaying(true);
                logger.debug('[BackgroundMusic] Autoplay succeeded');
              }
            } catch (err) {
              // If autoplay is blocked, we keep going (UI can still trigger later).
              logger.warn('[BackgroundMusic] Autoplay blocked', err);
            }
          };
          // Fire immediately (don't wait for canplaythrough).
          void tryAutoStart();
        }

        // Wait for FULL buffering before playing
        const handleCanPlayThrough = () => {
          if (cancelled) return;
          
          setIsLoading(false);
          onLoadCompleteRef.current?.();
        };

        // Handle buffering issues
        const handleWaiting = () => {
          logger.warn('[BackgroundMusic] Buffering...');
          // Audio is waiting for data - this shouldn't happen if fully preloaded
        };

        const handleStalled = () => {
          logger.warn('[BackgroundMusic] Stalled - retrying...');
          if (audioRef.current && !cancelled && isPlayingRef.current) {
            // Try to resume playback
            setTimeout(() => {
              if (audioRef.current && !cancelled && isPlayingRef.current) {
                audioRef.current.play().catch(() => {});
              }
            }, 500);
          }
        };

        const handleError = (e: Event) => {
          if (cancelled) return;
          
          const audioError = (e.target as HTMLAudioElement).error;
          const errorMsg = audioError 
            ? `Code ${audioError.code}: ${audioError.message}`
            : 'Unknown error';
          
          // CRITICAL: Stop retrying if format is not supported (Code 4) to prevent CPU heating
          if (audioError?.code === 4) {
             logger.error('[BackgroundMusic] Audio format not supported (likely OGG on iOS). Stopping retries.');
             setLoadError(new Error('Audio format not supported'));
             setIsLoading(false);
             return;
          }

          const error = new Error(`Failed to load audio: ${errorMsg}`);
          
          logger.error('[BackgroundMusic] Load error', error);
          
          // Retry logic - exponential backoff with cap
          if (retryCountRef.current < maxRetries) {
            retryCountRef.current++;
            const delay = Math.min(2000 * Math.pow(2, retryCountRef.current), 10000); // Max 10s delay
            
            setTimeout(() => {
              if (!cancelled) {
                loadAudio();
              }
            }, delay);
            return;
          }
          
          setLoadError(error);
          setIsLoading(false);
          onLoadErrorRef.current?.(error);
          // Only revoke if we created the blob URL ourselves
          if (ownedBlobUrl) {
            URL.revokeObjectURL(ownedBlobUrl);
          }
        };

        const handlePlay = () => {
          if (!cancelled) {
            isPlayingRef.current = true;
            setIsPlaying(true);
          }
        };

        const handlePause = () => {
          if (!cancelled) {
            // Only update state if pause was NOT caused by visibility change
            // (we check this by seeing if document is hidden)
            if (!document.hidden) {
              isPlayingRef.current = false;
              setIsPlaying(false);
            }
            // If document is hidden, we keep isPlayingRef.current = true
            // so we can resume when tab becomes visible again
          }
        };

        const handleEnded = () => {
          if (!cancelled) {
            isPlayingRef.current = false;
            setIsPlaying(false);
          }
        };

        // Progress tracking (silent)
        const handleProgress = () => {
          // Buffering tracked internally
        };

        audio.addEventListener('canplaythrough', handleCanPlayThrough, { once: true });
        audio.addEventListener('waiting', handleWaiting);
        audio.addEventListener('stalled', handleStalled);
        audio.addEventListener('error', handleError);
        audio.addEventListener('play', handlePlay);
        audio.addEventListener('pause', handlePause);
        audio.addEventListener('ended', handleEnded);
        audio.addEventListener('progress', handleProgress);

        // Start loading
        audio.load();

        return () => {
          audio.removeEventListener('canplaythrough', handleCanPlayThrough);
          audio.removeEventListener('waiting', handleWaiting);
          audio.removeEventListener('stalled', handleStalled);
          audio.removeEventListener('error', handleError);
          audio.removeEventListener('play', handlePlay);
          audio.removeEventListener('pause', handlePause);
          audio.removeEventListener('ended', handleEnded);
          audio.removeEventListener('progress', handleProgress);
          audio.pause();
          audio.src = '';
          // Only revoke if we created the blob URL ourselves
          if (ownedBlobUrl) {
            URL.revokeObjectURL(ownedBlobUrl);
          }
          audioRef.current = null;
        };
      } catch (error) {
        if (cancelled) return;
        
        logger.error('[BackgroundMusic] Prefetch error', error);
        
        // Retry on fetch error
        if (retryCountRef.current < maxRetries) {
          retryCountRef.current++;
          setTimeout(() => {
            if (!cancelled) {
              loadAudio();
            }
          }, 1000 * retryCountRef.current);
          return;
        }
        
        const err = error instanceof Error ? error : new Error('Unknown prefetch error');
        setLoadError(err);
        setIsLoading(false);
        onLoadErrorRef.current?.(err);
      }
    };

    loadAudio();

    return () => {
      cancelled = true;
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.src = '';
        audioRef.current = null;
      }
    };
    // Only re-run if src, loop, volume, autoPlay, or preloadedBlobUrl change - NOT callbacks
  }, [src, loop, volume, autoPlay, preloadedBlobUrl]);

  // Update volume when prop changes
  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.volume = isMuted ? 0 : volume;
    }
  }, [volume, isMuted]);

  // Handle page visibility - pause when hidden, resume when visible
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (!audioRef.current) return;
      
      if (document.hidden) {
        // Page is hidden - save state and pause music
        wasPlayingBeforeHiddenRef.current = isPlayingRef.current;
        if (isPlayingRef.current) {
          audioRef.current.pause();
          // Don't update isPlayingRef here - we want to resume later
        }
      } else {
        // Page is visible - resume if was playing before
        if (wasPlayingBeforeHiddenRef.current && autoPlay && !isMuted) {
          // Small delay to ensure audio context is ready
          setTimeout(() => {
            if (audioRef.current && !document.hidden) {
              audioRef.current.play()
                .then(() => {
                  // Successfully resumed - update state
                  isPlayingRef.current = true;
                  setIsPlaying(true);
                })
                .catch((err) => {
                  logger.warn('[BackgroundMusic] Resume after visibility change failed', err);
                  // If resume fails, update state
                  isPlayingRef.current = false;
                  setIsPlaying(false);
                  wasPlayingBeforeHiddenRef.current = false;
                });
            }
          }, 100);
        }
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [autoPlay, isMuted]);

  const togglePlay = () => {
    if (!audioRef.current) return;
    
    if (isPlaying) {
      audioRef.current.pause();
    } else {
      audioRef.current.play().catch((err) => {
        logger.warn('[BackgroundMusic] Play failed', err);
      });
    }
  };

  const toggleMute = () => {
    if (!audioRef.current) return;
    setIsMuted(!isMuted);
  };

  // Auto-resume on user interaction (for autoplay policies)
  // IMPORTANT: do NOT use `{ once: true }` here.
  // In Telegram Mini App, the first interaction may happen while the audio is still loading,
  // and we must keep listening until playback actually succeeds.
  useEffect(() => {
    const tryPlay = () => {
      const audio = audioRef.current;
      if (!audio) return;
      if (!autoPlay) return;
      if (isMuted) return;
      if (loadError) return;
      if (isLoading) return; // Don't try if still loading
      if (isPlayingRef.current) return;

      audio.play()
        .then(() => {
          // Successful user-gesture play: mark playing and keep state consistent.
          isPlayingRef.current = true;
          setIsPlaying(true);
        })
        .catch(() => {
          // Ignore: autoplay/user-gesture policies vary; next interaction may succeed.
        });
    };

    // Telegram WebView frequently emits pointer/touch before click.
    window.addEventListener('pointerdown', tryPlay, { passive: true });
    window.addEventListener('touchstart', tryPlay, { passive: true });
    window.addEventListener('click', tryPlay);
    window.addEventListener('keydown', tryPlay);

    return () => {
      window.removeEventListener('pointerdown', tryPlay);
      window.removeEventListener('touchstart', tryPlay);
      window.removeEventListener('click', tryPlay);
      window.removeEventListener('keydown', tryPlay);
    };
  }, [autoPlay, isLoading, loadError, isMuted]);

  // Don't render UI if there's an error or if not needed
  if (loadError) {
    return null; // Fail silently
  }

  // Optional: Render a small control button (hidden by default, visible on hover)
  // Position it so it doesn't conflict with support chat widget
  return (
    <div className="fixed bottom-24 right-4 z-[90] opacity-0 hover:opacity-100 transition-opacity pointer-events-none group">
      <button
        onClick={toggleMute}
        className="pointer-events-auto w-10 h-10 bg-black/50 border border-white/10 rounded-full flex items-center justify-center hover:bg-black/70 hover:border-pandora-cyan/30 transition-all"
        title={isMuted ? 'Unmute ambient music' : 'Mute ambient music'}
      >
        {isMuted ? (
          <VolumeX size={16} className="text-gray-400" />
        ) : (
          <Volume2 size={16} className="text-pandora-cyan" />
        )}
      </button>
      {isLoading && (
        <div className="absolute -top-6 left-1/2 -translate-x-1/2 text-[9px] font-mono text-gray-500 whitespace-nowrap">
          Loading...
        </div>
      )}
    </div>
  );
};

// Memoize to prevent re-creation on navigation
export const BackgroundMusic = memo(BackgroundMusicComponent);

export default BackgroundMusic;
