import { useState, useEffect, useCallback } from "react";
import type {
  WebAppUser,
  WebApp,
  HapticStyle as TelegramHapticStyle,
  HapticNotificationType,
} from "../types/telegram";

// Re-export types for convenience
export type TelegramUser = WebAppUser;

type HapticType = "impact" | "notification" | "selection";
type HapticStyle = TelegramHapticStyle | "success" | "warning" | "error";
type ColorScheme = "light" | "dark";

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
  const [initData, setInitData] = useState("");
  const [user, setUser] = useState<TelegramUser | null>(null);
  const [colorScheme, setColorScheme] = useState<ColorScheme>("dark");

  useEffect(() => {
    const tg: WebApp | undefined = window.Telegram?.WebApp;

    if (tg) {
      // Mark as ready
      tg.ready();
      tg.expand();

      // Get init data
      setInitData(tg.initData);
      setUser(tg.initDataUnsafe?.user || null);
      setColorScheme(tg.colorScheme || "dark");

      // Theme changed listener
      tg.onEvent("themeChanged", () => {
        setColorScheme(tg.colorScheme);
      });

      setIsReady(true);
    } else {
      // Development mode without Telegram
      setInitData("");
      setUser({
        id: 123456789,
        is_bot: false,
        first_name: "Test",
        last_name: "User",
        username: "testuser",
        language_code: "en",
      });
      setIsReady(true);
    }
  }, []);

  const showConfirm = useCallback((message: string): Promise<boolean> => {
    const tg: WebApp | undefined = window.Telegram?.WebApp;
    if (tg?.showConfirm) {
      return new Promise((resolve) => {
        tg.showConfirm(message, resolve);
      });
    }
    return Promise.resolve(window.confirm(message));
  }, []);

  const showAlert = useCallback((message: string): Promise<void> => {
    const tg: WebApp | undefined = window.Telegram?.WebApp;
    if (tg?.showAlert) {
      return new Promise((resolve) => {
        tg.showAlert(message, resolve);
      });
    }
    window.alert(message);
    return Promise.resolve();
  }, []);

  const hapticFeedback = useCallback(
    (type: HapticType = "impact", style: HapticStyle = "medium"): void => {
      const haptic = window.Telegram?.WebApp?.HapticFeedback;
      if (haptic) {
        if (type === "impact") {
          // Map custom styles to Telegram styles
          const telegramStyle: TelegramHapticStyle =
            style === "success" || style === "warning" || style === "error" ? "medium" : style;
          haptic.impactOccurred(telegramStyle);
        } else if (type === "notification") {
          // Map custom styles to Telegram notification types
          const notificationType: HapticNotificationType =
            style === "success"
              ? "success"
              : style === "warning"
                ? "warning"
                : style === "error"
                  ? "error"
                  : "error";
          haptic.notificationOccurred(notificationType);
        } else if (type === "selection") {
          haptic.selectionChanged();
        }
      }
    },
    []
  );

  const close = useCallback((): void => {
    window.Telegram?.WebApp?.close();
  }, []);

  const openLink = useCallback((url: string): void => {
    window.Telegram?.WebApp?.openLink(url);
  }, []);

  const openTelegramLink = useCallback((url: string): void => {
    window.Telegram?.WebApp?.openTelegramLink(url);
  }, []);

  const sendData = useCallback((data: unknown): void => {
    window.Telegram?.WebApp?.sendData(JSON.stringify(data));
  }, []);

  const setMainButton = useCallback((config: MainButtonConfig): void => {
    const btn = window.Telegram?.WebApp?.MainButton;
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
    const btn = window.Telegram?.WebApp?.BackButton;
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
    setBackButton,
  };
}

export default useTelegram;
