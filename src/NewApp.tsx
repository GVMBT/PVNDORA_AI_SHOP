/**
 * PVNDORA New App - React 19 UI with Connected Components
 * 
 * This is the new frontend that uses the redesigned components with real API data.
 * Features:
 * - Boot Sequence (OS-style loading)
 * - Procedural Audio (Web Audio API)
 * - HUD Notifications (System Logs)
 */

import React, { useState, useEffect, useCallback } from 'react';
import { AnimatePresence, motion, useMotionValue, useMotionTemplate } from 'framer-motion';

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
  BootSequence,
  useHUD,
} from './components/new';

// Types
import type { CatalogProduct } from './types/component';

// Hooks for data fetching
import { useProductsTyped } from './hooks/useApiTyped';
import { useCart } from './contexts/CartContext';

// Audio Engine (procedural sound generation)
import { AudioEngine } from './lib/AudioEngine';

type ViewType = 'home' | 'orders' | 'profile' | 'leaderboard' | 'legal' | 'admin';

function NewAppInner() {
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
  
  // Boot Sequence State
  const [isBooted, setIsBooted] = useState(false);
  
  // HUD Notifications (replaces old toast system)
  const hud = useHUD();

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
          AudioEngine.init();
          AudioEngine.resume();
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
              AudioEngine.open();
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

      // 2. Audio (using new AudioEngine)
      AudioEngine.resume();
      switch (type) {
          case 'light': AudioEngine.hover(); break;
          case 'medium': AudioEngine.click(); break;
          case 'heavy': AudioEngine.open(); break;
          case 'success': AudioEngine.success(); break;
          case 'error': AudioEngine.error(); break;
      }
  }, []);

  // --- ACTIONS --- (HUD notifications replace old toast system)

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
      AudioEngine.addToCart();
      hud.success('MODULE MOUNTED', `${product.name} added to payload`);
    } catch (err) {
      console.error('Failed to add to cart:', err);
      hud.error('MOUNT FAILED', 'Unable to add module to payload');
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
    console.log('[NewApp] ========================================');
    console.log('[NewApp] handleOpenCart CALLED');
    console.log('[NewApp] Current isCheckoutOpen:', isCheckoutOpen);
    console.log('[NewApp] Current cart:', cart);
    console.log('[NewApp] Cart items count:', cart?.items?.length || 0);
    try {
      handleFeedback('medium');
    } catch (err) {
      console.error('[NewApp] Error in handleFeedback:', err);
    }
    console.log('[NewApp] Setting isCheckoutOpen = true');
    setIsCheckoutOpen(true);
    console.log('[NewApp] ========================================');
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
    AudioEngine.transaction();
    hud.success('TRANSACTION COMPLETE', 'Assets transferred to your account');
  }, [getCart, hud]);

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
  
  // Handle boot sequence completion
  const handleBootComplete = useCallback(() => {
    setIsBooted(true);
    AudioEngine.connect();
    hud.system('UPLINK ESTABLISHED', 'Welcome back, Operator');
  }, [hud]);

  // Show Boot Sequence first (only once per session)
  if (!isBooted && isAuthenticated !== false) {
    return (
      <BootSequence 
        onComplete={handleBootComplete}
        minDuration={3500}
      />
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
          console.log('[NewApp] ===== CHECKOUT MODAL RENDER CHECK =====');
          console.log('[NewApp] isCheckoutOpen:', isCheckoutOpen);
          console.log('[NewApp] willRender:', !!isCheckoutOpen);
          if (!isCheckoutOpen) {
            console.log('[NewApp] Checkout modal NOT rendering - isCheckoutOpen is false');
            return null;
          }
          console.log('[NewApp] ===== RENDERING CheckoutModalConnected =====');
          try {
            return (
              <CheckoutModalConnected 
                onClose={handleCloseCheckout} 
                onSuccess={handleCheckoutSuccess}
              />
            );
          } catch (err) {
            console.error('[NewApp] ERROR rendering CheckoutModalConnected:', err);
            return null;
          }
        })()}
      </AnimatePresence>

      {/* --- PERSISTENT SUPPORT WIDGET --- */}
      <SupportChatConnected 
        isOpen={isSupportWidgetOpen} 
        onToggle={(val) => setIsSupportWidgetOpen(val)} 
        onHaptic={() => handleFeedback('light')} 
        raiseOnMobile={shouldRaiseSupport}
      />

      {/* HUD Notifications are rendered by HUDProvider */}
      
      {/* Subtle Grain/Scanline Effect */}
      <div className="fixed inset-0 pointer-events-none z-[100] opacity-[0.02] bg-[url('https://grainy-gradients.vercel.app/noise.svg')] brightness-100 contrast-150" />
    </div>
  );
}

// Import HUDProvider for wrapping
import { HUDProvider } from './components/new';

// Main App with HUD Provider wrapper
function NewApp() {
  return (
    <HUDProvider position="top-right" maxNotifications={5} defaultDuration={4000}>
      <NewAppInner />
    </HUDProvider>
  );
}

export default NewApp;

