/**
 * LoginPage - Web authentication via Telegram Login Widget
 * 
 * For desktop/browser users who don't have access to Telegram Mini App context.
 * Uses Telegram Login Widget to authenticate.
 */

import React, { useEffect, useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Shield, Zap, LogIn, Terminal, AlertTriangle, Loader2 } from 'lucide-react';

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
}

const LoginPage: React.FC<LoginPageProps> = ({ 
  onLoginSuccess,
  botUsername = 'pvndora_ai_bot' // Default bot username (from env)
}) => {
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Handle Telegram Login callback
  const handleTelegramAuth = useCallback(async (user: TelegramLoginData) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch('/api/webapp/auth/telegram-login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(user),
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.detail || 'Authentication failed');
      }
      
      // Store session token
      localStorage.setItem('pvndora_session', data.session_token);
      
      // Notify parent of success
      onLoginSuccess();
    } catch (err: any) {
      console.error('Login error:', err);
      setError(err.message || 'Failed to authenticate');
    } finally {
      setLoading(false);
    }
  }, [onLoginSuccess]);

  // Inject Telegram Login Widget script
  useEffect(() => {
    // Check if already logged in
    const existingSession = localStorage.getItem('pvndora_session');
    if (existingSession) {
      // Verify session is still valid
      fetch('/api/webapp/auth/verify-session', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_token: existingSession }),
      })
        .then(r => r.json())
        .then(data => {
          if (data.valid) {
            onLoginSuccess();
          } else {
            localStorage.removeItem('pvndora_session');
          }
        })
        .catch(() => {
          localStorage.removeItem('pvndora_session');
        });
    }

    // Setup global callback for Telegram Widget
    (window as any).onTelegramAuth = handleTelegramAuth;

    // Load Telegram widget script
    const script = document.createElement('script');
    script.src = 'https://telegram.org/js/telegram-widget.js?22';
    script.setAttribute('data-telegram-login', botUsername);
    script.setAttribute('data-size', 'large');
    script.setAttribute('data-radius', '4');
    script.setAttribute('data-onauth', 'onTelegramAuth(user)');
    script.setAttribute('data-request-access', 'write');
    script.async = true;

    const container = document.getElementById('telegram-login-container');
    if (container) {
      container.appendChild(script);
    }

    return () => {
      delete (window as any).onTelegramAuth;
      if (container && script.parentNode === container) {
        container.removeChild(script);
      }
    };
  }, [botUsername, handleTelegramAuth, onLoginSuccess]);

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-4 relative overflow-hidden">
      {/* Background */}
      <div className="fixed inset-0 z-[-2] bg-[radial-gradient(circle_at_50%_0%,_#0e3a3a_0%,_#050505_90%)]" />
      
      {/* Grid */}
      <div 
        className="fixed inset-0 pointer-events-none opacity-[0.03] z-[-1]" 
        style={{ 
          backgroundImage: 'linear-gradient(#00FFFF 1px, transparent 1px), linear-gradient(90deg, #00FFFF 1px, transparent 1px)', 
          backgroundSize: '40px 40px',
        }} 
      />

      {/* Ambient Glow */}
      <div className="fixed top-1/4 left-1/2 -translate-x-1/2 w-[500px] h-[500px] bg-pandora-cyan/10 blur-[150px] pointer-events-none" />

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="relative z-10 w-full max-w-md"
      >
        {/* Logo/Header */}
        <div className="text-center mb-10">
          <motion.div 
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ delay: 0.2 }}
            className="inline-flex items-center justify-center w-20 h-20 bg-[#0a0a0a] border border-pandora-cyan/50 rounded-lg mb-6 relative"
          >
            <div className="absolute inset-0 bg-pandora-cyan/10 rounded-lg animate-pulse" />
            <Shield size={40} className="text-pandora-cyan relative z-10" />
          </motion.div>
          
          <h1 className="text-3xl md:text-4xl font-display font-black text-white uppercase tracking-tighter mb-2">
            PVNDORA
          </h1>
          <p className="font-mono text-xs text-gray-500 uppercase tracking-widest">
            UPLINK_TERMINAL v2.0
          </p>
        </div>

        {/* Login Card */}
        <div className="bg-[#0a0a0a]/80 backdrop-blur-xl border border-white/10 p-8 relative overflow-hidden">
          {/* Corner Decorations */}
          <div className="absolute top-0 left-0 w-4 h-4 border-t border-l border-pandora-cyan/50" />
          <div className="absolute top-0 right-0 w-4 h-4 border-t border-r border-pandora-cyan/50" />
          <div className="absolute bottom-0 left-0 w-4 h-4 border-b border-l border-pandora-cyan/50" />
          <div className="absolute bottom-0 right-0 w-4 h-4 border-b border-r border-pandora-cyan/50" />

          <div className="text-center mb-8">
            <div className="flex items-center justify-center gap-2 text-pandora-cyan font-mono text-xs mb-4">
              <Terminal size={14} />
              <span className="uppercase tracking-wider">ACCESS_REQUIRED</span>
            </div>
            <h2 className="text-xl font-bold text-white mb-2">Initialize Uplink</h2>
            <p className="text-sm text-gray-500">
              Authenticate via Telegram to access the Neural Catalog
            </p>
          </div>

          {/* Telegram Login Widget Container */}
          <div className="flex flex-col items-center gap-6">
            {loading ? (
              <div className="flex items-center gap-3 py-4 text-pandora-cyan">
                <Loader2 size={20} className="animate-spin" />
                <span className="font-mono text-sm uppercase">Establishing secure connection...</span>
              </div>
            ) : (
              <>
                <div id="telegram-login-container" className="flex justify-center min-h-[50px]">
                  {/* Telegram widget will be injected here */}
                </div>
                <button
                  onClick={() => {
                    // fallback: reopen widget / open bot page if widget blocked
                    const script = document.createElement('script');
                    script.src = 'https://telegram.org/js/telegram-widget.js?22';
                    script.setAttribute('data-telegram-login', botUsername);
                    script.setAttribute('data-size', 'large');
                    script.setAttribute('data-radius', '4');
                    script.setAttribute('data-onauth', 'onTelegramAuth(user)');
                    script.setAttribute('data-request-access', 'write');
                    script.async = true;
                    const container = document.getElementById('telegram-login-container');
                    if (container) {
                      container.innerHTML = '';
                      container.appendChild(script);
                    }
                    window.open(`https://t.me/${botUsername}`, '_blank');
                  }}
                  className="px-5 py-2 border border-pandora-cyan/60 text-pandora-cyan font-mono text-xs uppercase tracking-widest hover:bg-pandora-cyan hover:text-black transition-colors"
                >
                  Авторизоваться через Telegram
                </button>
              </>
            )}

            {error && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex items-center gap-2 text-red-400 text-sm font-mono bg-red-500/10 border border-red-500/30 px-4 py-2 rounded-sm"
              >
                <AlertTriangle size={14} />
                <span>{error}</span>
              </motion.div>
            )}
          </div>

          {/* Features */}
          <div className="mt-10 pt-8 border-t border-white/10 grid grid-cols-2 gap-4">
            <div className="flex items-start gap-3">
              <Zap size={16} className="text-pandora-cyan mt-1 shrink-0" />
              <div>
                <div className="text-xs font-bold text-white uppercase">Instant Access</div>
                <div className="text-[10px] text-gray-500">No registration required</div>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <Shield size={16} className="text-pandora-cyan mt-1 shrink-0" />
              <div>
                <div className="text-xs font-bold text-white uppercase">Encrypted</div>
                <div className="text-[10px] text-gray-500">E2E secure channel</div>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="text-center mt-8">
          <p className="font-mono text-[10px] text-gray-600 uppercase tracking-wider">
            For best experience, use <span className="text-pandora-cyan">Telegram Mini App</span>
          </p>
        </div>
      </motion.div>

      {/* Scanlines */}
      <div className="fixed inset-0 pointer-events-none z-[100] opacity-[0.02] bg-[url('https://grainy-gradients.vercel.app/noise.svg')]" />
    </div>
  );
};

export default LoginPage;

