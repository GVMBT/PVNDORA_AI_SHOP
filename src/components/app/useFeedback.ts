/**
 * Unified Feedback Hook
 * 
 * Handles haptic feedback (Telegram/vibration) and audio feedback.
 */

import { useCallback } from 'react';
import { AudioEngine } from '../../lib/AudioEngine';

export type FeedbackType = 'light' | 'medium' | 'heavy' | 'success' | 'error';

export function useFeedback() {
  const handleFeedback = useCallback((type: FeedbackType = 'light') => {
    // 1. Haptic (Telegram)
    const tg = (window as any).Telegram?.WebApp;
    if (tg?.HapticFeedback) {
      switch (type) {
        case 'light': tg.HapticFeedback.impactOccurred('light'); break;
        case 'medium': tg.HapticFeedback.impactOccurred('medium'); break;
        case 'heavy': tg.HapticFeedback.impactOccurred('heavy'); break;
        case 'success': tg.HapticFeedback.notificationOccurred('success'); break;
        case 'error': tg.HapticFeedback.notificationOccurred('error'); break;
      }
    } else if (typeof navigator !== 'undefined' && navigator.vibrate) {
      // Fallback vibrate
      switch (type) {
        case 'light': navigator.vibrate(5); break;
        case 'medium': navigator.vibrate(15); break;
        case 'heavy': navigator.vibrate(30); break;
        case 'success': navigator.vibrate([10, 30, 10]); break;
        case 'error': navigator.vibrate([30, 50, 30, 50, 30]); break;
      }
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
  }, []);

  return handleFeedback;
}
