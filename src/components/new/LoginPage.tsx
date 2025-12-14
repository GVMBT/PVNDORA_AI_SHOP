/**
 * LoginPage - Web authentication via Telegram Login Widget
 * 
 * For desktop/browser users who don't have access to Telegram Mini App context.
 * Clean, modern design with Telegram OAuth.
 */

import React, { useEffect, useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Shield, Zap, ExternalLink, Loader2, Send } from 'lucide-react';
import { verifySessionToken, saveSessionToken, removeSessionToken, getSessionToken } from '../../utils/auth';
import { BOT } from '../../config';
import { logger } from '../../utils/logger';
import { apiPost } from '../../utils/apiClient';

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
}

const LoginPage: React.FC<LoginPageProps> = ({ 
  onLoginSuccess,
  botUsername = BOT.USERNAME,
  redirectPath = '/',
}) => {
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [widgetLoaded, setWidgetLoaded] = useState(false);

  // Handle Telegram Login callback
  const handleTelegramAuth = useCallback(async (user: TelegramLoginData) => {
    setLoading(true);
    setError(null);
    
    try {
      const data = await apiPost<{ session_token: string }>('/auth/telegram-login', user);
      saveSessionToken(data.session_token);
      onLoginSuccess();
      if (redirectPath) {
        window.location.replace(redirectPath);
      }
    } catch (err: unknown) {
      logger.error('Login error', err instanceof Error ? err : new Error(String(err)));
      const errorMessage = err instanceof Error ? err.message : 'Failed to authenticate';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  }, [onLoginSuccess, redirectPath]);

  // Check existing session and inject Telegram Widget
  useEffect(() => {
    const checkExistingSession = async () => {
      const existingSession = getSessionToken();
      if (existingSession) {
        const data = await verifySessionToken(existingSession);
        if (data?.valid) {
          onLoginSuccess();
          if (redirectPath) {
            window.location.replace(redirectPath);
          }
        } else {
          removeSessionToken();
        }
      }
    };
    
    checkExistingSession();

    // Setup global callback for Telegram Widget
    window.onTelegramAuth = handleTelegramAuth;

    // Load Telegram widget script
    const script = document.createElement('script');
    script.src = 'https://telegram.org/js/telegram-widget.js?22';
    script.setAttribute('data-telegram-login', botUsername);
    script.setAttribute('data-size', 'large');
    script.setAttribute('data-radius', '8');
    script.setAttribute('data-onauth', 'onTelegramAuth(user)');
    script.setAttribute('data-request-access', 'write');
    script.async = true;
    script.onload = () => setWidgetLoaded(true);

    const container = document.getElementById('telegram-login-container');
    if (container) {
      container.appendChild(script);
    }

    return () => {
      delete window.onTelegramAuth;
      if (container && script.parentNode === container) {
        container.removeChild(script);
      }
    };
  }, [botUsername, handleTelegramAuth, onLoginSuccess, redirectPath]);

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-4 relative overflow-hidden bg-black">
      {/* Background Effects */}
      <div className="fixed inset-0 z-0">
        <div className="absolute inset-0 bg-gradient-to-b from-pandora-cyan/5 via-transparent to-transparent" />
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-pandora-cyan/10 blur-[120px] rounded-full" />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="relative z-10 w-full max-w-sm"
      >
        {/* Logo */}
        <div className="text-center mb-8">
          <motion.div 
            initial={{ scale: 0.8 }}
            animate={{ scale: 1 }}
            className="inline-flex items-center justify-center w-16 h-16 bg-pandora-cyan/10 border border-pandora-cyan/30 rounded-xl mb-4"
          >
            <Shield size={32} className="text-pandora-cyan" />
          </motion.div>
          
          <h1 className="text-2xl font-display font-black text-white tracking-tight mb-1">
            PVNDORA
          </h1>
          <p className="text-xs text-gray-500 font-mono">
            AI Subscription Marketplace
          </p>
        </div>

        {/* Login Card */}
        <div className="bg-gray-900/50 backdrop-blur-xl border border-white/10 rounded-2xl p-6 space-y-6">
          {/* Header */}
          <div className="text-center">
            <h2 className="text-lg font-semibold text-white mb-1">
              Sign in with Telegram
            </h2>
            <p className="text-sm text-gray-400">
              Secure authentication via Telegram
            </p>
          </div>

          {/* Telegram Widget */}
          <div className="flex flex-col items-center gap-4">
            {loading ? (
              <div className="flex items-center gap-3 py-6 text-pandora-cyan">
                <Loader2 size={24} className="animate-spin" />
                <span className="text-sm">Connecting...</span>
              </div>
            ) : (
              <>
                {/* Telegram Login Widget Container */}
                <div 
                  id="telegram-login-container" 
                  className="flex justify-center min-h-[44px] py-2"
                >
                  {!widgetLoaded && (
                    <div className="flex items-center gap-2 text-gray-500 text-sm">
                      <Loader2 size={16} className="animate-spin" />
                      <span>Loading...</span>
                    </div>
                  )}
                </div>

                {/* Error Message */}
                {error && (
                  <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="w-full p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-center"
                  >
                    <p className="text-sm text-red-400">{error}</p>
                  </motion.div>
                )}
              </>
            )}
          </div>

          {/* Divider */}
          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-white/10" />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-gray-900/50 px-3 text-gray-500">or</span>
            </div>
          </div>

          {/* Mini App Link */}
          <a
            href={`https://t.me/${botUsername}?start=app`}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center justify-center gap-3 w-full py-3 px-4 bg-[#2AABEE] hover:bg-[#229ED9] text-white font-medium rounded-xl transition-colors"
          >
            <Send size={18} />
            <span>Open in Telegram</span>
            <ExternalLink size={14} className="opacity-60" />
          </a>

          <p className="text-center text-xs text-gray-500">
            For the best experience, use our{' '}
            <a 
              href={`https://t.me/${botUsername}`} 
              className="text-pandora-cyan hover:underline"
              target="_blank"
              rel="noopener noreferrer"
            >
              Telegram Mini App
            </a>
          </p>
        </div>

        {/* Features */}
        <div className="mt-6 grid grid-cols-2 gap-4">
          <div className="flex items-center gap-2 text-gray-400">
            <Zap size={14} className="text-pandora-cyan" />
            <span className="text-xs">Instant access</span>
          </div>
          <div className="flex items-center gap-2 text-gray-400">
            <Shield size={14} className="text-pandora-cyan" />
            <span className="text-xs">E2E encrypted</span>
          </div>
        </div>

        {/* Footer */}
        <div className="mt-8 text-center">
          <p className="text-[10px] text-gray-600">
            By signing in, you agree to our Terms of Service
          </p>
        </div>
      </motion.div>
    </div>
  );
};

export default LoginPage;
