/**
 * Unified Feedback Hook
 * 
 * Handles haptic feedback (Telegram/vibration) and audio feedback.
 */

import { useCallback } from 'react';
import { AudioEngine } from '../../lib/AudioEngine';
import { useTelegram } from '../../hooks/useTelegram';

export type FeedbackType = 'light' | 'medium' | 'heavy' | 'success' | 'error';

export function useFeedback() {
  const { hapticFeedback } = useTelegram();
  
  const handleFeedback = useCallback((type: FeedbackType = 'light') => {
    // 1. Haptic (Telegram) - uses useTelegram hook
    switch (type) {
      case 'light': hapticFeedback('impact', 'light'); break;
      case 'medium': hapticFeedback('impact', 'medium'); break;
      case 'heavy': hapticFeedback('impact', 'heavy'); break;
      case 'success': hapticFeedback('notification', 'success'); break;
      case 'error': hapticFeedback('notification', 'error'); break;
    }

    // 2. Audio (using AudioEngine)
    AudioEngine.resume();
    switch (type) {
      case 'light': AudioEngine.hover(); break;
      case 'medium': AudioEngine.click(); break;
      case 'heavy': AudioEngine.open(); break;
      case 'success': AudioEngine.success(); break;
      case 'error': AudioEngine.error(); break;
    }
  }, [hapticFeedback]);

  return handleFeedback;
}
