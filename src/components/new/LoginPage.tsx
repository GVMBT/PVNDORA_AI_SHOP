/**
 * LoginPage - Web authentication via Telegram Login Widget
 *
 * For desktop/browser users who don't have access to Telegram Mini App context.
 * Clean, modern design with Telegram OAuth.
 */

import { motion } from "framer-motion";
import { ExternalLink, Loader2, Send, Shield, Zap } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { BOT } from "../../config";
import { apiPost } from "../../utils/apiClient";
import {
  getSessionToken,
  removeSessionToken,
  saveSessionToken,
  verifySessionToken,
} from "../../utils/auth";
import { logger } from "../../utils/logger";

interface TelegramLoginData {
  id: number;
  first_name: string;
  last_name?: string;
  username?: string;
  photo_url?: string;
  auth_date: number;
  hash: string;
}

interface LoginPageProps {
  onLoginSuccess: () => void;
  botUsername?: string;
  redirectPath?: string;
  onNavigateLegal?: (doc: string) => void;
}

const LoginPage = ({
  onLoginSuccess,
  botUsername = BOT.USERNAME,
  redirectPath = "/",
  onNavigateLegal,
}: LoginPageProps) => {
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [widgetLoaded, setWidgetLoaded] = useState(false);

  // Handle Telegram Login callback
  const handleTelegramAuth = useCallback(
    async (user: TelegramLoginData) => {
      setLoading(true);
      setError(null);

      try {
        const data = await apiPost<{ session_token: string }>("/auth/telegram-login", user);
        saveSessionToken(data.session_token);
        onLoginSuccess();
        if (redirectPath) {
          globalThis.location.replace(redirectPath);
        }
      } catch (err: unknown) {
        let errorInstance: Error;
        let errorMessage: string;

        if (err instanceof Error) {
          errorInstance = err;
          errorMessage = err.message;
        } else if (err) {
          const errStr = typeof err === "string" ? err : String(err);
          errorInstance = new Error(errStr);
          errorMessage = errStr;
        } else {
          errorInstance = new Error("Unknown error");
          errorMessage = "Failed to authenticate";
        }

        logger.error("Login error", errorInstance);
        setError(errorMessage);
      } finally {
        setLoading(false);
      }
    },
    [onLoginSuccess, redirectPath]
  );

  // Check existing session and inject Telegram Widget
  useEffect(() => {
    const checkExistingSession = async () => {
      const existingSession = getSessionToken();
      if (existingSession) {
        const data = await verifySessionToken(existingSession);
        if (data?.valid) {
          onLoginSuccess();
          if (redirectPath) {
            globalThis.location.replace(redirectPath);
          }
        } else {
          removeSessionToken();
        }
      }
    };

    checkExistingSession();

    // Setup global callback for Telegram Widget
    (
      globalThis as typeof globalThis & { onTelegramAuth?: typeof handleTelegramAuth }
    ).onTelegramAuth = handleTelegramAuth;

    // Load Telegram widget script
    const script = document.createElement("script");
    script.src = "https://telegram.org/js/telegram-widget.js?22";
    script.dataset.telegramLogin = botUsername;
    script.dataset.size = "large";
    script.dataset.radius = "8";
    script.dataset.onauth = "onTelegramAuth(user)";
    script.dataset.requestAccess = "write";
    script.async = true;
    script.onload = () => setWidgetLoaded(true);

    const container = document.getElementById("telegram-login-container");
    if (container) {
      container.appendChild(script);
    }

    return () => {
      delete (globalThis as typeof globalThis & { onTelegramAuth?: typeof handleTelegramAuth })
        .onTelegramAuth;
      if (container && script.parentNode === container) {
        script.remove();
      }
    };
  }, [botUsername, handleTelegramAuth, onLoginSuccess, redirectPath]);

  return (
    <div className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden bg-black p-4">
      {/* Background Effects */}
      <div className="fixed inset-0 z-0">
        <div className="absolute inset-0 bg-gradient-to-b from-pandora-cyan/5 via-transparent to-transparent" />
        <div className="absolute top-0 left-1/2 h-[400px] w-[800px] -translate-x-1/2 rounded-full bg-pandora-cyan/10 blur-[120px]" />
      </div>

      <motion.div
        animate={{ opacity: 1, y: 0 }}
        className="relative z-10 w-full max-w-sm"
        initial={{ opacity: 0, y: 20 }}
        transition={{ duration: 0.5 }}
      >
        {/* Logo */}
        <div className="mb-8 text-center">
          <motion.div
            animate={{ scale: 1 }}
            className="mb-4 inline-flex h-16 w-16 items-center justify-center rounded-xl border border-pandora-cyan/30 bg-pandora-cyan/10"
            initial={{ scale: 0.8 }}
          >
            <Shield className="text-pandora-cyan" size={32} />
          </motion.div>

          <h1 className="mb-1 font-black font-display text-2xl text-white tracking-tight">
            PVNDORA
          </h1>
          <p className="font-mono text-gray-500 text-xs">AI Subscription Marketplace</p>
        </div>

        {/* Login Card */}
        <div className="space-y-6 rounded-2xl border border-white/10 bg-gray-900/50 p-6 backdrop-blur-xl">
          {/* Header */}
          <div className="text-center">
            <h2 className="mb-1 font-semibold text-lg text-white">Sign in with Telegram</h2>
            <p className="text-gray-400 text-sm">Secure authentication via Telegram</p>
          </div>

          {/* Telegram Widget */}
          <div className="flex flex-col items-center gap-4">
            {loading ? (
              <div className="flex items-center gap-3 py-6 text-pandora-cyan">
                <Loader2 className="animate-spin" size={24} />
                <span className="text-sm">Connecting...</span>
              </div>
            ) : (
              <>
                {/* Telegram Login Widget Container */}
                <div
                  className="flex min-h-[44px] justify-center py-2"
                  id="telegram-login-container"
                >
                  {!widgetLoaded && (
                    <div className="flex items-center gap-2 text-gray-500 text-sm">
                      <Loader2 className="animate-spin" size={16} />
                      <span>Loading...</span>
                    </div>
                  )}
                </div>

                {/* Error Message */}
                {error && (
                  <motion.div
                    animate={{ opacity: 1, scale: 1 }}
                    className="w-full rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-center"
                    initial={{ opacity: 0, scale: 0.95 }}
                  >
                    <p className="text-red-400 text-sm">{error}</p>
                  </motion.div>
                )}
              </>
            )}
          </div>

          {/* Divider */}
          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-white/10 border-t" />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-gray-900/50 px-3 text-gray-500">or</span>
            </div>
          </div>

          {/* Mini App Link */}
          <a
            className="flex w-full items-center justify-center gap-3 rounded-xl bg-[#2AABEE] px-4 py-3 font-medium text-white transition-colors hover:bg-[#229ED9]"
            href={`https://t.me/${botUsername}?start=app`}
            rel="noopener noreferrer"
            target="_blank"
          >
            <Send size={18} />
            <span>Open in Telegram</span>
            <ExternalLink className="opacity-60" size={14} />
          </a>

          <p className="text-center text-gray-500 text-xs">
            For the best experience, use our{" "}
            <a
              className="text-pandora-cyan hover:underline"
              href={`https://t.me/${botUsername}`}
              rel="noopener noreferrer"
              target="_blank"
            >
              Telegram Mini App
            </a>
          </p>
        </div>

        {/* Features */}
        <div className="mt-6 flex items-center justify-center gap-8">
          <div className="flex items-center gap-2 text-gray-400">
            <Zap className="shrink-0 text-pandora-cyan" size={14} />
            <span className="whitespace-nowrap text-xs">Instant access</span>
          </div>
          <div className="flex items-center gap-2 text-gray-400">
            <Shield className="shrink-0 text-pandora-cyan" size={14} />
            <span className="whitespace-nowrap text-xs">E2E encrypted</span>
          </div>
        </div>

        {/* Footer - Legal Links */}
        <div className="mt-8 space-y-2 text-center">
          <p className="text-[10px] text-gray-600">
            By signing in, you agree to our{" "}
            <button
              className="text-pandora-cyan hover:underline"
              onClick={() => onNavigateLegal?.("terms")}
              type="button"
            >
              Terms of Service
            </button>{" "}
            and{" "}
            <button
              className="text-pandora-cyan hover:underline"
              onClick={() => onNavigateLegal?.("privacy")}
              type="button"
            >
              Privacy Policy
            </button>
          </p>
        </div>
      </motion.div>
    </div>
  );
};

export default LoginPage;
