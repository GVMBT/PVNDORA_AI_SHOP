/**
 * PVNDORA New App - React 19 UI with Connected Components
 * 
 * This is the new frontend that uses the redesigned components with real API data.
 * Can be enabled via NEW_UI feature flag.
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { AnimatePresence, motion, useMotionValue, useMotionTemplate } from 'framer-motion';
import { Terminal, CheckCircle, AlertTriangle, Command } from 'lucide-react';

// New Connected Components
import {
  Hero,
  Guarantees,
  Footer,
  Navbar,
  Legal,
  SupportChatConnected,
  CommandPalette,
  AdminPanel,
  CatalogConnected,
  ProductDetailConnected,
  OrdersConnected,
  ProfileConnected,
  LeaderboardConnected,
  CheckoutModalConnected,
  LoginPage,
} from './components/new';

// Types
import type { CatalogProduct } from './types/component';

// Hooks for data fetching
import { useProductsTyped } from './hooks/useApiTyped';
import { useCart } from './contexts/CartContext';

// --- AUDIO ENGINE (Web Audio API) ---
class AudioEngine {
    ctx: AudioContext | null = null;
    
    init() {
        if (!this.ctx && typeof window !== 'undefined') {
            const AudioContext = window.AudioContext || (window as any).webkitAudioContext;
            this.ctx = new AudioContext();
        }
    }

    resume() {
        if (this.ctx && this.ctx.state === 'suspended') {
            this.ctx.resume();
        }
    }

    playTone(freq: number, type: OscillatorType, duration: number, vol: number = 0.05) {
        if (!this.ctx) return;
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();
        
        osc.type = type;
        osc.frequency.setValueAtTime(freq, this.ctx.currentTime);
        
        gain.gain.setValueAtTime(vol, this.ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + duration);
        
        osc.connect(gain);
        gain.connect(this.ctx.destination);
        
        osc.start();
        osc.stop(this.ctx.currentTime + duration);
    }

    playNoise(duration: number) {
        if (!this.ctx) return;
        const bufferSize = this.ctx.sampleRate * duration;
        const buffer = this.ctx.createBuffer(1, bufferSize, this.ctx.sampleRate);
        const data = buffer.getChannelData(0);
        for (let i = 0; i < bufferSize; i++) {
            data[i] = Math.random() * 2 - 1;
        }

        const noise = this.ctx.createBufferSource();
        noise.buffer = buffer;
        const gain = this.ctx.createGain();
        gain.gain.setValueAtTime(0.02, this.ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + duration);
        
        noise.connect(gain);
        gain.connect(this.ctx.destination);
        noise.start();
    }

    // --- SFX PRESETS ---
    hover() { this.playTone(800, 'sine', 0.03, 0.01); }
    click() { 
        this.playTone(1200, 'square', 0.05, 0.02); 
        this.playNoise(0.05);
    }
    success() {
        if (!this.ctx) return;
        this.playTone(440, 'sine', 0.2);
        setTimeout(() => this.playTone(554, 'sine', 0.2), 100);
        setTimeout(() => this.playTone(659, 'sine', 0.4), 200);
    }
    error() {
        this.playTone(150, 'sawtooth', 0.3, 0.05);
    }
    open() {
        this.playTone(200, 'sine', 0.5, 0.02);
    }
}

const audio = new AudioEngine();

// --- TOAST TYPES ---
interface Toast {
  id: number;
  message: string;
  type: 'success' | 'error' | 'info';
}

type ViewType = 'home' | 'orders' | 'profile' | 'leaderboard' | 'legal' | 'admin';

function NewApp() {
  // Bot username for web login widget
  const BOT_USERNAME =
    (import.meta as any)?.env?.VITE_BOT_USERNAME ||
    (window as any).__BOT_USERNAME ||
    'pvndora_ai_bot';

  const [selectedProduct, setSelectedProduct] = useState<CatalogProduct | null>(null);
  const [isCheckoutOpen, setIsCheckoutOpen] = useState(false);
  const [isSupportWidgetOpen, setIsSupportWidgetOpen] = useState(false);
  const [isCmdOpen, setIsCmdOpen] = useState(false);
  
  // Navigation State
  const [currentView, setCurrentView] = useState<ViewType>('home');
  const [legalDoc, setLegalDoc] = useState('terms');
  
  // Authentication State (for web users)
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null); // null = checking

  // Toast State
  const [toasts, setToasts] = useState<Toast[]>([]);

  // Products for CommandPalette (fetched once)
  const { products: allProducts, getProducts } = useProductsTyped();
  
  // Cart from global context (shared across all components)
  const { cart, getCart, addToCart, removeCartItem } = useCart();

  // --- SPOTLIGHT LOGIC (must be before any early returns) ---
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);

  // Spotlight gradient (useMotionTemplate must be called unconditionally)
  const spotlightBackground = useMotionTemplate`
    radial-gradient(
      600px circle at ${mouseX}px ${mouseY}px,
      rgba(0, 255, 255, 0.07),
      transparent 80%
    )
  `;

  // Mouse tracking for spotlight effect
  useEffect(() => {
    const handleMouseMove = ({ clientX, clientY }: MouseEvent) => {
      mouseX.set(clientX);
      mouseY.set(clientY);
    };
    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, [mouseX, mouseY]);

  // Check authentication on mount
  useEffect(() => {
    const checkAuth = async () => {
      // Persist session_token from URL query if present (using shared utility)
      const { persistSessionTokenFromQuery } = await import('./utils/auth');
      persistSessionTokenFromQuery();

      // In Telegram WebApp context - always authenticated via initData
      const tg = (window as any).Telegram?.WebApp;
      if (tg?.initData) {
        setIsAuthenticated(true);
        return;
      }
      
      // In browser - check for session token
      const { getSessionToken, verifySessionToken, removeSessionToken } = await import('./utils/auth');
      const sessionToken = getSessionToken();
      if (sessionToken) {
        // Verify token is still valid using shared utility
        const result = await verifySessionToken(sessionToken);
        setIsAuthenticated(result?.valid === true);
        if (!result?.valid) {
          removeSessionToken();
        }
      } else {
        setIsAuthenticated(false);
      }
    };
    
    checkAuth();
  }, []);

  // Fetch products and cart on mount (only when authenticated)
  useEffect(() => {
    if (isAuthenticated) {
      getProducts();
      getCart();
    }
  }, [getProducts, getCart, isAuthenticated]);

  // Initialize Audio on first interaction
  useEffect(() => {
      const initAudio = () => {
          audio.init();
          audio.resume();
          window.removeEventListener('click', initAudio);
          window.removeEventListener('keydown', initAudio);
      };
      window.addEventListener('click', initAudio);
      window.addEventListener('keydown', initAudio);
      
      // CMD+K Listener
      const handleKeyDown = (e: KeyboardEvent) => {
          if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
              e.preventDefault();
              setIsCmdOpen(prev => !prev);
              audio.open();
          }
      };
      window.addEventListener('keydown', handleKeyDown);
      return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // --- UNIFIED FEEDBACK HANDLER ---
  const handleFeedback = useCallback((type: 'light' | 'medium' | 'heavy' | 'success' | 'error' = 'light') => {
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

      // 2. Audio
      audio.resume();
      switch (type) {
          case 'light': audio.hover(); break;
          case 'medium': audio.click(); break;
          case 'heavy': audio.open(); break;
          case 'success': audio.success(); break;
          case 'error': audio.error(); break;
      }
  }, []);

  // --- ACTIONS ---

  const showToast = useCallback((message: string, type: 'success' | 'error' | 'info' = 'info') => {
    const id = Date.now();
    setToasts(prev => [...prev, { id, message, type }]);
    
    if (type === 'success') handleFeedback('success');
    if (type === 'error') handleFeedback('error');
    if (type === 'info') handleFeedback('medium');

    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 3000);
  }, [handleFeedback]);

  const handleProductSelect = (product: CatalogProduct) => {
    handleFeedback('medium');
    setSelectedProduct(product);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleBackToCatalog = () => {
    handleFeedback('light');
    setSelectedProduct(null);
  };

  // Cart operations - using backend API
  const handleAddToCart = async (product: CatalogProduct, quantity: number = 1) => {
    try {
      await addToCart(String(product.id), quantity);
      showToast(`MODULE [${product.name}] MOUNTED`, 'success');
    } catch (err) {
      console.error('Failed to add to cart:', err);
      showToast('Failed to add item to cart', 'error');
    }
  };

  const handleRemoveFromCart = async (productId: string | number) => {
    handleFeedback('medium');
    try {
      await removeCartItem(String(productId));
    } catch (err) {
      console.error('Failed to remove from cart:', err);
    }
  };

  const handleOpenCart = () => {
    console.log('[NewApp] handleOpenCart called');
    handleFeedback('medium');
    console.log('[NewApp] Setting isCheckoutOpen = true');
    setIsCheckoutOpen(true);
  };

  const handleCloseCheckout = useCallback(() => {
    handleFeedback('light');
    setIsCheckoutOpen(false);
  }, [handleFeedback]);

  const handleCheckoutSuccess = useCallback(() => {
    // Refresh cart from backend (should be empty after successful order)
    getCart();
    setIsCheckoutOpen(false);
    setCurrentView('orders');
    window.scrollTo({ top: 0, behavior: 'smooth' });
    showToast('TRANSACTION COMPLETE. ASSETS TRANSFERRED.', 'success');
  }, [getCart, showToast]);

  // Navigation Handlers
  const navigate = (view: ViewType) => {
      handleFeedback('light');
      setSelectedProduct(null);
      setIsCheckoutOpen(false);
      setCurrentView(view);
      window.scrollTo({ top: 0, behavior: 'smooth' });
  };
  
  // For Command Palette
  const handleUniversalNavigate = (target: any) => {
      handleFeedback('medium');
      if (typeof target === 'string') {
          navigate(target as ViewType);
      } else if (target.type === 'product') {
          setCurrentView('home');
          setSelectedProduct(target.product);
      }
  };

  const handleNavigateLegal = (doc: string) => {
    handleFeedback('light');
    setLegalDoc(doc);
    setCurrentView('legal');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  const getActiveTab = () => {
    if (currentView === 'profile') return 'profile';
    if (currentView === 'orders') return 'orders';
    if (currentView === 'leaderboard') return 'leaderboard';
    return 'catalog';
  };

  const shouldRaiseSupport = currentView === 'leaderboard';

  // Authentication loading state
  if (isAuthenticated === null) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#050505]">
        <div className="text-center">
          <div className="w-16 h-16 border-2 border-pandora-cyan border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <div className="font-mono text-xs text-gray-500 uppercase tracking-widest">
            Initializing Uplink...
          </div>
        </div>
      </div>
    );
  }

  // Show login page for unauthenticated web users
  if (!isAuthenticated) {
    return (
      <LoginPage 
        onLoginSuccess={() => setIsAuthenticated(true)}
        botUsername={BOT_USERNAME}
        redirectPath="/"
      />
    );
  }

  return (
    <div className="min-h-screen text-white overflow-x-hidden relative selection:bg-pandora-cyan selection:text-black">
      
      {/* === UNIFIED FIXED BACKGROUND LAYER === */}
      <div className="fixed inset-0 z-[-2] bg-[radial-gradient(circle_at_50%_0%,_#0e3a3a_0%,_#050505_90%)]" />
      
      {/* === 1. GLOBAL BACKGROUND GRID (Fixed Layer) === */}
      <div 
        className="fixed inset-0 pointer-events-none opacity-[0.03] z-[-1]" 
        style={{ 
            backgroundImage: 'linear-gradient(#00FFFF 1px, transparent 1px), linear-gradient(90deg, #00FFFF 1px, transparent 1px)', 
            backgroundSize: '40px 40px',
            backgroundPosition: 'center top'
        }} 
      />

      {/* GLOBAL SPOTLIGHT EFFECT */}
      <motion.div
        className="pointer-events-none fixed inset-0 z-0 transition-opacity duration-300 mix-blend-plus-lighter"
        style={{
          background: spotlightBackground,
        }}
      />
      
      {currentView !== 'admin' && (
          <Navbar 
            showMobile={!selectedProduct} 
            cartCount={cart?.items?.length || 0} 
            onOpenCart={handleOpenCart}
            onNavigateHome={() => navigate('home')}
            onNavigateOrders={() => navigate('orders')}
            onNavigateProfile={() => navigate('profile')}
            onNavigateLeaderboard={() => navigate('leaderboard')}
            activeTab={getActiveTab()}
            onHaptic={() => handleFeedback('light')}
          />
      )}
      
      {/* Main Content */}
      <main className="w-full relative z-10">
        <AnimatePresence mode="wait">
          {currentView === 'admin' ? (
            <AdminPanel key="admin" onExit={() => navigate('profile')} />
          ) : currentView === 'profile' ? (
            <ProfileConnected 
              key="profile" 
              onBack={() => navigate('home')} 
              onHaptic={handleFeedback} 
              onAdminEnter={() => navigate('admin')} 
            />
          ) : currentView === 'orders' ? (
             <OrdersConnected 
               key="orders" 
               onBack={() => navigate('home')} 
               onOpenSupport={() => setIsSupportWidgetOpen(true)} 
             />
          ) : currentView === 'leaderboard' ? (
             <LeaderboardConnected 
               key="leaderboard" 
               onBack={() => navigate('home')} 
             />
          ) : currentView === 'legal' ? (
             <Legal key="legal" doc={legalDoc} onBack={() => navigate('home')} />
          ) : selectedProduct ? (
            <ProductDetailConnected 
              key="detail" 
              productId={String(selectedProduct.id)}
              onBack={handleBackToCatalog} 
              onAddToCart={handleAddToCart}
              onProductSelect={handleProductSelect}
              onHaptic={handleFeedback}
            />
          ) : (
            <motion.div 
              key="home"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <Hero />
              <CatalogConnected 
                onSelectProduct={handleProductSelect} 
                onAddToCart={handleAddToCart}
                onHaptic={handleFeedback} 
              />
              <Guarantees />
              <Footer 
                onNavigate={handleNavigateLegal} 
                onOpenSupport={() => setIsSupportWidgetOpen(true)} 
              />
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      {/* --- COMMAND PALETTE --- */}
      <CommandPalette 
        isOpen={isCmdOpen} 
        onClose={() => setIsCmdOpen(false)} 
        onNavigate={handleUniversalNavigate}
        products={allProducts} 
      />

      {/* --- CHECKOUT MODAL --- */}
      <AnimatePresence>
        {(() => {
          console.log('[NewApp] Checking checkout modal render:', {
            isCheckoutOpen,
            willRender: !!isCheckoutOpen,
          });
          if (!isCheckoutOpen) {
            console.log('[NewApp] Checkout modal NOT rendering - isCheckoutOpen is false');
            return null;
          }
          console.log('[NewApp] RENDERING CheckoutModalConnected');
          return (
            <CheckoutModalConnected 
              onClose={handleCloseCheckout} 
              onSuccess={handleCheckoutSuccess}
            />
          );
        })()}
      </AnimatePresence>

      {/* --- PERSISTENT SUPPORT WIDGET --- */}
      <SupportChatConnected 
        isOpen={isSupportWidgetOpen} 
        onToggle={(val) => setIsSupportWidgetOpen(val)} 
        onHaptic={() => handleFeedback('light')} 
        raiseOnMobile={shouldRaiseSupport}
      />

      {/* --- SYSTEM TOASTS --- */}
      <div className="fixed top-4 left-1/2 -translate-x-1/2 z-[100] flex flex-col gap-2 w-full max-w-sm px-4 pointer-events-none">
        <AnimatePresence>
            {toasts.map(toast => (
                <motion.div
                    key={toast.id}
                    initial={{ opacity: 0, y: -20, scale: 0.9 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: -20, scale: 0.9 }}
                    className={`
                        pointer-events-auto flex items-center gap-3 p-3 border font-mono text-xs shadow-[0_4px_20px_rgba(0,0,0,0.5)] backdrop-blur-md
                        ${toast.type === 'success' ? 'bg-[#0a0a0a] border-pandora-cyan text-pandora-cyan' : ''}
                        ${toast.type === 'error' ? 'bg-red-900/10 border-red-500 text-red-500' : ''}
                        ${toast.type === 'info' ? 'bg-blue-900/10 border-blue-500 text-blue-400' : ''}
                    `}
                >
                    {toast.type === 'success' && <CheckCircle size={16} />}
                    {toast.type === 'error' && <AlertTriangle size={16} />}
                    {toast.type === 'info' && <Terminal size={16} />}
                    <span className="uppercase tracking-wide font-bold">{toast.message}</span>
                </motion.div>
            ))}
        </AnimatePresence>
      </div>
      
      {/* Subtle Grain/Scanline Effect */}
      <div className="fixed inset-0 pointer-events-none z-[100] opacity-[0.02] bg-[url('https://grainy-gradients.vercel.app/noise.svg')] brightness-100 contrast-150" />
    </div>
  );
}

export default NewApp;

