/**
 * BackgroundMusic Component
 * 
 * Manages ambient background music for the PVNDORA app.
 * Preloads sound.ogg completely before playing to avoid stuttering.
 */

import React, { useEffect, useRef, useState, memo } from 'react';
import { Volume2, VolumeX } from 'lucide-react';

interface BackgroundMusicProps {
  src?: string;
  volume?: number; // 0-1
  autoPlay?: boolean;
  loop?: boolean;
  onLoadComplete?: () => void;
  onLoadError?: (error: Error) => void;
}

const BackgroundMusicComponent: React.FC<BackgroundMusicProps> = ({
  src = '/sound.ogg',
  volume = 0.20,
  autoPlay = true,
  loop = true,
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
    const startTime = Date.now();

    const loadAudio = async () => {
      try {
        // First: Prefetch the entire file via fetch to ensure it's fully downloaded
        const response = await fetch(src, { 
          cache: 'force-cache',
        });
        
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        // Convert to blob URL for better buffering
        const blob = await response.blob();
        const blobUrl = URL.createObjectURL(blob);
        
        if (cancelled) {
          URL.revokeObjectURL(blobUrl);
          return;
        }

        // Now create Audio element with blob URL
        const audio = new Audio(blobUrl);
        audio.loop = loop;
        audio.volume = volume;
        audio.preload = 'auto';
        
        // CRITICAL: Set crossOrigin to avoid CORS issues
        audio.crossOrigin = 'anonymous';
        
        audioRef.current = audio;

        // Wait for FULL buffering before playing
        const handleCanPlayThrough = () => {
          if (cancelled) return;
          
          setIsLoading(false);
          onLoadCompleteRef.current?.();
          
          if (autoPlay) {
            // Small delay to ensure everything is ready
            setTimeout(() => {
              if (!cancelled && audioRef.current) {
                audioRef.current.play().catch((err) => {
                  console.warn('[BackgroundMusic] Autoplay blocked:', err);
                });
              }
            }, 100);
          }
        };

        // Handle buffering issues
        const handleWaiting = () => {
          console.warn('[BackgroundMusic] Buffering...');
          // Audio is waiting for data - this shouldn't happen if fully preloaded
        };

        const handleStalled = () => {
          console.warn('[BackgroundMusic] Stalled - retrying...');
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
          const error = new Error(`Failed to load audio: ${errorMsg}`);
          
          console.error('[BackgroundMusic] Load error:', error);
          
          // Retry logic
          if (retryCountRef.current < maxRetries) {
            retryCountRef.current++;
            setTimeout(() => {
              if (!cancelled) {
                loadAudio();
              }
            }, 1000 * retryCountRef.current);
            return;
          }
          
          setLoadError(error);
          setIsLoading(false);
          onLoadErrorRef.current?.(error);
          URL.revokeObjectURL(blobUrl);
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
          URL.revokeObjectURL(blobUrl);
          audioRef.current = null;
        };
      } catch (error) {
        if (cancelled) return;
        
        console.error('[BackgroundMusic] Prefetch error:', error);
        
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
    // Only re-run if src, loop, volume, or autoPlay change - NOT callbacks
  }, [src, loop, volume, autoPlay]);

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
                  console.warn('[BackgroundMusic] Resume after visibility change failed:', err);
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
        console.warn('[BackgroundMusic] Play failed:', err);
      });
    }
  };

  const toggleMute = () => {
    if (!audioRef.current) return;
    setIsMuted(!isMuted);
  };

  // Auto-resume on user interaction (for autoplay policies)
  useEffect(() => {
    const handleUserInteraction = () => {
      if (audioRef.current && autoPlay && !isPlayingRef.current && !isLoading && !loadError) {
        audioRef.current.play().catch(() => {
          // Ignore autoplay errors
        });
      }
    };

    window.addEventListener('click', handleUserInteraction, { once: true });
    window.addEventListener('keydown', handleUserInteraction, { once: true });

    return () => {
      window.removeEventListener('click', handleUserInteraction);
      window.removeEventListener('keydown', handleUserInteraction);
    };
  }, [autoPlay, isLoading, loadError]);

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
