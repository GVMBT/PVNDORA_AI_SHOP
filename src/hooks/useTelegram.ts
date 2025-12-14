import { useState, useEffect, useCallback } from 'react';

interface TelegramUser {
  id: number;
  first_name: string;
  last_name?: string;
  username?: string;
  language_code?: string;
  photo_url?: string;
}

type HapticType = 'impact' | 'notification' | 'selection';
type HapticStyle = 'light' | 'medium' | 'heavy' | 'rigid' | 'soft' | 'success' | 'warning' | 'error';
type ColorScheme = 'light' | 'dark';

interface MainButtonConfig {
  text?: string;
  color?: string;
  textColor?: string;
  onClick?: () => void;
  isVisible?: boolean;
  isLoading?: boolean;
}

interface BackButtonConfig {
  onClick?: () => void;
  isVisible?: boolean;
}

interface UseTelegramReturn {
  isReady: boolean;
  initData: string;
  user: TelegramUser | null;
  colorScheme: ColorScheme;
  showConfirm: (message: string) => Promise<boolean>;
  showAlert: (message: string) => Promise<void>;
  hapticFeedback: (type?: HapticType, style?: HapticStyle) => void;
  close: () => void;
  openLink: (url: string) => void;
  openTelegramLink: (url: string) => void;
  sendData: (data: unknown) => void;
  setMainButton: (config: MainButtonConfig) => void;
  setBackButton: (config: BackButtonConfig) => void;
}

/**
 * Hook for Telegram WebApp SDK integration
 */
export function useTelegram(): UseTelegramReturn {
  const [isReady, setIsReady] = useState(false);
  const [initData, setInitData] = useState('');
  const [user, setUser] = useState<TelegramUser | null>(null);
  const [colorScheme, setColorScheme] = useState<ColorScheme>('dark');
  
  useEffect(() => {
    const tg = (window as any).Telegram?.WebApp;
    
    if (tg) {
      // Mark as ready
      tg.ready();
      tg.expand();
      
      // Get init data
      setInitData(tg.initData);
      setUser(tg.initDataUnsafe?.user || null);
      setColorScheme(tg.colorScheme || 'dark');
      
      // Theme changed listener
      tg.onEvent('themeChanged', () => {
        setColorScheme(tg.colorScheme);
      });
      
      setIsReady(true);
    } else {
      // Development mode without Telegram
      setInitData('');
      setUser({
        id: 123456789,
        first_name: 'Test',
        last_name: 'User',
        username: 'testuser',
        language_code: 'en'
      });
      setIsReady(true);
    }
  }, []);
  
  const showConfirm = useCallback((message: string): Promise<boolean> => {
    const tg = (window as any).Telegram?.WebApp;
    if (tg?.showConfirm) {
      return new Promise((resolve) => {
        tg.showConfirm(message, resolve);
      });
    }
    return Promise.resolve(window.confirm(message));
  }, []);
  
  const showAlert = useCallback((message: string): Promise<void> => {
    const tg = (window as any).Telegram?.WebApp;
    if (tg?.showAlert) {
      return new Promise((resolve) => {
        tg.showAlert(message, resolve);
      });
    }
    window.alert(message);
    return Promise.resolve();
  }, []);
  
  const hapticFeedback = useCallback((type: HapticType = 'impact', style: HapticStyle = 'medium'): void => {
    const tg = (window as any).Telegram?.WebApp?.HapticFeedback;
    if (tg) {
      if (type === 'impact') {
        tg.impactOccurred(style);
      } else if (type === 'notification') {
        tg.notificationOccurred(style);
      } else if (type === 'selection') {
        tg.selectionChanged();
      }
    }
  }, []);
  
  const close = useCallback((): void => {
    (window as any).Telegram?.WebApp?.close();
  }, []);
  
  const openLink = useCallback((url: string): void => {
    (window as any).Telegram?.WebApp?.openLink(url);
  }, []);
  
  const openTelegramLink = useCallback((url: string): void => {
    (window as any).Telegram?.WebApp?.openTelegramLink(url);
  }, []);
  
  const sendData = useCallback((data: unknown): void => {
    (window as any).Telegram?.WebApp?.sendData(JSON.stringify(data));
  }, []);
  
  const setMainButton = useCallback((config: MainButtonConfig): void => {
    const btn = (window as any).Telegram?.WebApp?.MainButton;
    if (btn) {
      if (config.text) btn.setText(config.text);
      if (config.color) btn.setParams({ color: config.color });
      if (config.textColor) btn.setParams({ text_color: config.textColor });
      if (config.onClick) btn.onClick(config.onClick);
      if (config.isVisible !== undefined) {
        config.isVisible ? btn.show() : btn.hide();
      }
      if (config.isLoading !== undefined) {
        config.isLoading ? btn.showProgress() : btn.hideProgress();
      }
    }
  }, []);
  
  const setBackButton = useCallback((config: BackButtonConfig): void => {
    const btn = (window as any).Telegram?.WebApp?.BackButton;
    if (btn) {
      if (config.onClick) btn.onClick(config.onClick);
      if (config.isVisible !== undefined) {
        config.isVisible ? btn.show() : btn.hide();
      }
    }
  }, []);
  
  return {
    isReady,
    initData,
    user,
    colorScheme,
    showConfirm,
    showAlert,
    hapticFeedback,
    close,
    openLink,
    openTelegramLink,
    sendData,
    setMainButton,
    setBackButton
  };
}

export default useTelegram;
