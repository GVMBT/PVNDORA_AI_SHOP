/**
 * BackgroundMusic Component
 * 
 * Manages ambient background music for the PVNDORA app.
 * Loads sound.flac and plays it in a loop with volume control.
 */

import React, { useEffect, useRef, useState } from 'react';
import { Volume2, VolumeX } from 'lucide-react';

interface BackgroundMusicProps {
  src?: string;
  volume?: number; // 0-1
  autoPlay?: boolean;
  loop?: boolean;
  onLoadComplete?: () => void;
  onLoadError?: (error: Error) => void;
}

export const BackgroundMusic: React.FC<BackgroundMusicProps> = ({
  src = '/sound.flac',
  volume = 0.15, // Low volume for ambient music
  autoPlay = true,
  loop = true,
  onLoadComplete,
  onLoadError,
}) => {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<Error | null>(null);
  const [loadStartTime] = useState(Date.now());

  // Initialize audio element
  useEffect(() => {
    const audio = new Audio(src);
    audio.loop = loop;
    audio.volume = volume;
    audio.preload = 'auto';
    
    audioRef.current = audio;

    // Handle loading
    const handleCanPlay = () => {
      setIsLoading(false);
      const loadTime = Date.now() - loadStartTime;
      console.log(`[BackgroundMusic] Loaded in ${loadTime}ms`);
      onLoadComplete?.();
      
      if (autoPlay) {
        audio.play().catch((err) => {
          console.warn('[BackgroundMusic] Autoplay blocked:', err);
          // Autoplay might be blocked - user needs to interact first
        });
      }
    };

    const handleCanPlayThrough = () => {
      setIsLoading(false);
    };

    const handleError = (e: ErrorEvent) => {
      const error = new Error(`Failed to load audio: ${e.message || 'Unknown error'}`);
      setLoadError(error);
      setIsLoading(false);
      onLoadError?.(error);
      console.error('[BackgroundMusic] Load error:', error);
    };

    const handlePlay = () => setIsPlaying(true);
    const handlePause = () => setIsPlaying(false);
    const handleEnded = () => setIsPlaying(false);

    audio.addEventListener('canplay', handleCanPlay);
    audio.addEventListener('canplaythrough', handleCanPlayThrough);
    audio.addEventListener('error', handleError);
    audio.addEventListener('play', handlePlay);
    audio.addEventListener('pause', handlePause);
    audio.addEventListener('ended', handleEnded);

    // Start loading
    audio.load();

    return () => {
      audio.removeEventListener('canplay', handleCanPlay);
      audio.removeEventListener('canplaythrough', handleCanPlayThrough);
      audio.removeEventListener('error', handleError);
      audio.removeEventListener('play', handlePlay);
      audio.removeEventListener('pause', handlePause);
      audio.removeEventListener('ended', handleEnded);
      audio.pause();
      audio.src = '';
      audioRef.current = null;
    };
  }, [src, loop, volume, autoPlay, onLoadComplete, onLoadError, loadStartTime]);

  // Update volume when prop changes
  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.volume = isMuted ? 0 : volume;
    }
  }, [volume, isMuted]);

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
      if (audioRef.current && autoPlay && !isPlaying && !isLoading && !loadError) {
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
  }, [autoPlay, isPlaying, isLoading, loadError]);

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

export default BackgroundMusic;
