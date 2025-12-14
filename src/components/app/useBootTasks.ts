/**
 * Boot Tasks Hook
 * 
 * Defines the boot sequence tasks for the application.
 * These run real operations: auth check, data loading, etc.
 */

import { useMemo } from 'react';
import { AudioEngine } from '../../lib/AudioEngine';
import { logger } from '../../utils/logger';
import { getTelegramInitData } from '../../utils/telegram';
import type { BootTask } from '../new';

interface UseBootTasksProps {
  getProducts: () => Promise<any>;
  getCart: () => Promise<any>;
  getProfile: () => Promise<any>;
}

export function useBootTasks({ getProducts, getCart, getProfile }: UseBootTasksProps): BootTask[] {
  return useMemo(() => [
    {
      id: 'audio',
      label: 'Initializing audio subsystem...',
      successLabel: 'Audio engine: ONLINE',
      execute: async () => {
        AudioEngine.init();
        await AudioEngine.resume();
        AudioEngine.boot();
        return true;
      },
    },
    {
      id: 'auth',
      label: 'Verifying operator credentials...',
      successLabel: 'Operator authenticated',
      errorLabel: 'Authentication required',
      critical: false,
      execute: async () => {
        const { persistSessionTokenFromQuery } = await import('../../utils/auth');
        persistSessionTokenFromQuery();

        const initData = getTelegramInitData();
        if (initData) {
          return { authenticated: true, source: 'telegram' };
        }
        
        const { getSessionToken, verifySessionToken, removeSessionToken } = await import('../../utils/auth');
        const sessionToken = getSessionToken();
        if (sessionToken) {
          const result = await verifySessionToken(sessionToken);
          if (result?.valid) {
            return { authenticated: true, source: 'session' };
          }
          removeSessionToken();
        }
        
        return { authenticated: false };
      },
    },
    {
      id: 'catalog',
      label: 'Syncing inventory database...',
      successLabel: 'Product catalog loaded',
      execute: async () => {
        const products = await getProducts();
        return { productCount: products?.length || 0 };
      },
    },
    {
      id: 'cart',
      label: 'Loading operator payload...',
      successLabel: 'Cart data synchronized',
      execute: async () => {
        const cart = await getCart();
        return { itemCount: cart?.items?.length || 0 };
      },
    },
    {
      id: 'profile',
      label: 'Fetching operator profile...',
      successLabel: 'Profile data cached',
      errorLabel: 'Profile unavailable',
      critical: false,
      execute: async () => {
        try {
          const profileData = await getProfile();
          return { 
            loaded: !!profileData,
            username: profileData?.handle || null,
            balance: profileData?.balance || 0,
          };
        } catch (e) {
          logger.warn('[Boot] Profile fetch failed', e);
          return { loaded: false };
        }
      },
    },
    {
      id: 'music',
      label: 'Loading ambient audio stream...',
      successLabel: 'Ambient audio: READY',
      errorLabel: 'Audio stream unavailable',
      critical: false,
      execute: async () => {
        const musicUrl = '/sound.ogg';
        const startTime = Date.now();
        
        try {
          const response = await fetch(musicUrl, { cache: 'force-cache' });
          
          if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
          }

          const blob = await response.blob();
          const blobUrl = URL.createObjectURL(blob);
          const fetchTime = Date.now() - startTime;

          return new Promise((resolve) => {
            const audio = new Audio(blobUrl);
            audio.preload = 'auto';
            audio.volume = 0;
            audio.crossOrigin = 'anonymous';
            
            const timeout = setTimeout(() => {
              logger.warn('[Boot] Music buffering timeout, continuing...');
              audio.pause();
              audio.src = '';
              resolve({ loaded: true, blobUrl, loadTime: Date.now() - startTime, fetchTime });
            }, 10000);
            
            audio.addEventListener('canplaythrough', () => {
              clearTimeout(timeout);
              const totalTime = Date.now() - startTime;
              audio.pause();
              audio.src = '';
              resolve({ loaded: true, blobUrl, loadTime: totalTime, fetchTime });
            }, { once: true });
            
            audio.addEventListener('error', (e) => {
              clearTimeout(timeout);
              const error = (e.target as HTMLAudioElement).error;
              const errorMsg = error ? `Code ${error.code}: ${error.message}` : 'Unknown';
              logger.warn('[Boot] Music load error', errorMsg);
              audio.pause();
              audio.src = '';
              URL.revokeObjectURL(blobUrl);
              resolve({ loaded: false, error: errorMsg, loadTime: Date.now() - startTime, fetchTime });
            }, { once: true });
            
            audio.load();
          });
        } catch (error) {
          const errorMsg = error instanceof Error ? error.message : 'Unknown prefetch error';
          logger.warn('[Boot] Music prefetch error', errorMsg);
          return { 
            loaded: false, 
            error: errorMsg, 
            loadTime: Date.now() - startTime,
            fetchTime: 0
          };
        }
      },
    },
    {
      id: 'prefetch',
      label: 'Caching static resources...',
      successLabel: 'Resources cached',
      execute: async () => {
        const prefetchUrls = ['https://grainy-gradients.vercel.app/noise.svg'];
        await Promise.allSettled(prefetchUrls.map(url => fetch(url).catch(() => null)));
        return true;
      },
    },
  ], [getProducts, getCart, getProfile]);
}
