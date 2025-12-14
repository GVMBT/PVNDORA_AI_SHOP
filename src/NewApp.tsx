/**
 * PVNDORA New App - React 19 UI with Connected Components
 * 
 * Main application entry point. Uses modular components for:
 * - Boot Sequence (OS-style loading)
 * - Procedural Audio (Web Audio API)
 * - HUD Notifications (System Logs)
 */

import React, { useState, useEffect, useCallback } from 'react';
import { AnimatePresence } from 'framer-motion';

// App Components
import { AppLayout, AppRouter, useFeedback, useBootTasks, type ViewType } from './components/app';

// Connected Components
import {
  Navbar,
  SupportChatConnected,
  CommandPalette,
  CheckoutModalConnected,
  LoginPage,
  BootSequence,
  useHUD,
  BackgroundMusic,
  PaymentResult,
  CyberModalProvider,
  HUDProvider,
  type RefundContext,
} from './components/new';

// Types
import type { CatalogProduct } from './types/component';

// Hooks
import { useProductsTyped, useProfileTyped } from './hooks/useApiTyped';
import { useCart } from './contexts/CartContext';

// Audio Engine
import { AudioEngine } from './lib/AudioEngine';

// Config
const BOT_USERNAME = (import.meta as any)?.env?.VITE_BOT_USERNAME || (window as any).__BOT_USERNAME || 'pvndora_ai_bot';

/**
 * Check for payment redirect on initial load
 */
function usePaymentRedirect() {
  return useState<string | null>(() => {
    if (typeof window === 'undefined') return null;
    
    if (window.location.pathname === '/payment/result') {
      const urlParams = new URLSearchParams(window.location.search);
      const orderId = urlParams.get('order_id');
      const topupId = urlParams.get('topup_id');
      if (orderId) return orderId;
      if (topupId) return `topup_${topupId}`;
    }
    
    const tg = (window as any).Telegram?.WebApp;
    const startParam = tg?.initDataUnsafe?.start_param;
    const urlParams = new URLSearchParams(window.location.search);
    const urlStartapp = urlParams.get('tgWebAppStartParam') || urlParams.get('startapp');
    const hashParams = new URLSearchParams(window.location.hash.slice(1));
    const hashStartapp = hashParams.get('tgWebAppStartParam');
    
    const effectiveStartParam = startParam || urlStartapp || hashStartapp;
    
    if (effectiveStartParam?.startsWith('payresult_')) {
      return effectiveStartParam.replace('payresult_', '');
    }
    if (effectiveStartParam?.startsWith('topup_')) {
      return `topup_${effectiveStartParam.replace('topup_', '')}`;
    }
    
    return null;
  });
}

function NewAppInner() {
  // UI State
  const [selectedProduct, setSelectedProduct] = useState<CatalogProduct | null>(null);
  const [isCheckoutOpen, setIsCheckoutOpen] = useState(false);
  const [isSupportWidgetOpen, setIsSupportWidgetOpen] = useState(false);
  const [supportContext, setSupportContext] = useState<RefundContext | null>(null);
  const [isCmdOpen, setIsCmdOpen] = useState(false);
  
  // Navigation State
  const [currentView, setCurrentView] = useState<ViewType>('home');
  const [legalDoc, setLegalDoc] = useState('terms');
  const [paymentResultOrderId, setPaymentResultOrderId] = useState<string | null>(null);
  
  // Auth State
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null);
  
  // Boot State
  const [isBooted, setIsBooted] = useState(() => {
    if (typeof window !== 'undefined') {
      return sessionStorage.getItem('pvndora_booted') === 'true';
    }
    return false;
  });
  const [musicBlobUrl, setMusicBlobUrl] = useState<string | undefined>(undefined);
  
  // Payment redirect check
  const [isPaymentRedirect, setIsPaymentRedirect] = usePaymentRedirect();
  
  // Hooks
  const hud = useHUD();
  const handleFeedback = useFeedback();
  const { products: allProducts, getProducts } = useProductsTyped();
  const { getProfile } = useProfileTyped();
  const { cart, getCart, addToCart, removeCartItem } = useCart();
  
  // Boot tasks
  const bootTasks = useBootTasks({ getProducts, getCart, getProfile });

  // Initialize Audio and CMD+K
  useEffect(() => {
    const initAudio = () => {
      AudioEngine.init();
      AudioEngine.resume();
      window.removeEventListener('click', initAudio);
      window.removeEventListener('keydown', initAudio);
    };
    window.addEventListener('click', initAudio);
    window.addEventListener('keydown', initAudio);
    
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

  // Navigation handlers
  const navigate = useCallback((view: ViewType) => {
    handleFeedback('light');
    setSelectedProduct(null);
    setIsCheckoutOpen(false);
    setCurrentView(view);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, [handleFeedback]);

  const handleNavigateLegal = useCallback((doc: string) => {
    handleFeedback('light');
    setLegalDoc(doc);
    setCurrentView('legal');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, [handleFeedback]);

  const handleProductSelect = useCallback((product: CatalogProduct) => {
    handleFeedback('medium');
    setSelectedProduct(product);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, [handleFeedback]);

  const handleBackToCatalog = useCallback(() => {
    handleFeedback('light');
    setSelectedProduct(null);
  }, [handleFeedback]);

  // Cart handlers
  const handleAddToCart = useCallback(async (product: CatalogProduct, quantity: number = 1) => {
    try {
      await addToCart(String(product.id), quantity);
      AudioEngine.addToCart();
      hud.success('MODULE MOUNTED', `${product.name} added to payload`);
    } catch (err) {
      console.error('Failed to add to cart:', err);
      hud.error('MOUNT FAILED', 'Unable to add module to payload');
    }
  }, [addToCart, hud]);

  const handleOpenCart = useCallback(() => {
    handleFeedback('medium');
    setIsCheckoutOpen(true);
  }, [handleFeedback]);

  const handleCloseCheckout = useCallback(() => {
    handleFeedback('light');
    setIsCheckoutOpen(false);
  }, [handleFeedback]);

  const handleCheckoutSuccess = useCallback(() => {
    getCart();
    setIsCheckoutOpen(false);
    setCurrentView('orders');
    window.scrollTo({ top: 0, behavior: 'smooth' });
    AudioEngine.transaction();
    hud.success('TRANSACTION COMPLETE', 'Assets transferred to your account');
  }, [getCart, hud]);

  // Command palette navigation
  const handleUniversalNavigate = useCallback((target: any) => {
    handleFeedback('medium');
    if (typeof target === 'string') {
      navigate(target as ViewType);
    } else if (target.type === 'product') {
      setCurrentView('home');
      setSelectedProduct(target.product);
    }
  }, [handleFeedback, navigate]);

  // Support handler
  const handleOpenSupport = useCallback((context?: RefundContext | null) => {
    setSupportContext(context || null);
    setIsSupportWidgetOpen(true);
  }, []);

  // Boot completion handler
  const handleBootComplete = useCallback((results: Record<string, any>) => {
    const authResult = results.auth;
    setIsAuthenticated(authResult?.authenticated || false);
    
    const musicResult = results.music;
    if (musicResult?.loaded && musicResult.blobUrl) {
      setMusicBlobUrl(musicResult.blobUrl);
    }
    
    setIsBooted(true);
    sessionStorage.setItem('pvndora_booted', 'true');
    AudioEngine.connect();
    
    const productCount = results.catalog?.productCount || 0;
    const cartCount = results.cart?.itemCount || 0;
    
    setTimeout(() => {
      hud.system('UPLINK ESTABLISHED', `${productCount} modules available • ${cartCount} in payload`);
    }, 500);
  }, [hud]);

  // Payment redirect URL cleanup
  useEffect(() => {
    if (isPaymentRedirect && window.location.pathname === '/payment/result') {
      window.history.replaceState({}, '', '/');
    }
  }, [isPaymentRedirect]);

  // Mark as booted on payment redirect
  useEffect(() => {
    if (isPaymentRedirect && !isBooted) {
      setIsBooted(true);
      sessionStorage.setItem('pvndora_booted', 'true');
    }
  }, [isPaymentRedirect, isBooted]);

  // Computed values
  const getActiveTab = () => {
    if (currentView === 'profile') return 'profile';
    if (currentView === 'orders') return 'orders';
    if (currentView === 'leaderboard') return 'leaderboard';
    return 'catalog';
  };

  // Payment redirect flow
  if (isPaymentRedirect) {
    const isTopUp = isPaymentRedirect.startsWith('topup_');
    const actualId = isTopUp ? isPaymentRedirect.replace('topup_', '') : isPaymentRedirect;
    
    return (
      <div className="min-h-screen bg-black">
        <PaymentResult 
          orderId={actualId}
          isTopUp={isTopUp}
          onComplete={() => {
            setIsPaymentRedirect(null);
            setCurrentView(isTopUp ? 'profile' : 'home');
          }}
          onViewOrders={() => {
            setIsPaymentRedirect(null);
            setCurrentView(isTopUp ? 'profile' : 'orders');
          }}
        />
      </div>
    );
  }

  // Boot sequence
  if (!isBooted) {
    return <BootSequence tasks={bootTasks} onComplete={handleBootComplete} minDuration={2500} />;
  }

  // Login page
  if (!isAuthenticated) {
    return <LoginPage onLoginSuccess={() => setIsAuthenticated(true)} botUsername={BOT_USERNAME} redirectPath="/" />;
  }

  // Main app
  return (
    <AppLayout>
      {currentView !== 'admin' && currentView !== 'payment-result' && (
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
      
      <AppRouter
        currentView={currentView}
        selectedProduct={selectedProduct}
        legalDoc={legalDoc}
        paymentResultOrderId={paymentResultOrderId}
        onNavigate={navigate}
        onNavigateLegal={handleNavigateLegal}
        onProductSelect={handleProductSelect}
        onBackToCatalog={handleBackToCatalog}
        onAddToCart={handleAddToCart}
        onOpenSupport={handleOpenSupport}
        onHaptic={handleFeedback}
      />

      <CommandPalette 
        isOpen={isCmdOpen} 
        onClose={() => setIsCmdOpen(false)} 
        onNavigate={handleUniversalNavigate}
        products={allProducts} 
      />

      <AnimatePresence>
        {isCheckoutOpen && (
          <CheckoutModalConnected onClose={handleCloseCheckout} onSuccess={handleCheckoutSuccess} />
        )}
      </AnimatePresence>

      <SupportChatConnected 
        isOpen={isSupportWidgetOpen} 
        onToggle={(val) => {
          setIsSupportWidgetOpen(val);
          if (!val) setSupportContext(null);
        }} 
        onHaptic={() => handleFeedback('light')} 
        raiseOnMobile={currentView === 'leaderboard'}
        initialContext={supportContext}
      />

      {isBooted && (
        <BackgroundMusic 
          key="background-music-persistent"
          src="/sound.ogg"
          volume={0.20}
          autoPlay={true}
          loop={true}
          preloadedBlobUrl={musicBlobUrl}
        />
      )}
    </AppLayout>
  );
}

// Main App with providers
function NewApp() {
  return (
    <HUDProvider position="top-right" maxNotifications={5} defaultDuration={4000}>
      <CyberModalProvider>
        <NewAppInner />
      </CyberModalProvider>
    </HUDProvider>
  );
}

export default NewApp;
