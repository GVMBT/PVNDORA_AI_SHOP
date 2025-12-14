/**
 * PVNDORA New App - React 19 UI with Connected Components
 * 
 * This is the new frontend that uses the redesigned components with real API data.
 * Features:
 * - Boot Sequence (OS-style loading)
 * - Procedural Audio (Web Audio API)
 * - HUD Notifications (System Logs)
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';
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
  AdminPanelConnected,
  CatalogConnected,
  ProductDetailConnected,
  OrdersConnected,
  ProfileConnected,
  LeaderboardConnected,
  CheckoutModalConnected,
  LoginPage,
  BootSequence,
  useHUD,
  BackgroundMusic,
  PaymentResult,
  CyberModalProvider,
  type BootTask,
  type RefundContext,
} from './components/new';

// Types
import type { CatalogProduct } from './types/component';

// Hooks for data fetching
import { useProductsTyped, useProfileTyped } from './hooks/useApiTyped';
import { useCart } from './contexts/CartContext';

// Audio Engine (procedural sound generation)
import { AudioEngine } from './lib/AudioEngine';

// API base URL
const API_BASE = (import.meta as any)?.env?.VITE_API_URL || '/api';

type ViewType = 'home' | 'orders' | 'profile' | 'leaderboard' | 'legal' | 'admin' | 'payment-result';

function NewAppInner() {
  // Bot username for web login widget
  const BOT_USERNAME =
    (import.meta as any)?.env?.VITE_BOT_USERNAME ||
    (window as any).__BOT_USERNAME ||
    'pvndora_ai_bot';

  const [selectedProduct, setSelectedProduct] = useState<CatalogProduct | null>(null);
  const [isCheckoutOpen, setIsCheckoutOpen] = useState(false);
  const [isSupportWidgetOpen, setIsSupportWidgetOpen] = useState(false);
  const [supportContext, setSupportContext] = useState<RefundContext | null>(null);
  const [isCmdOpen, setIsCmdOpen] = useState(false);
  
  // Navigation State
  const [currentView, setCurrentView] = useState<ViewType>('home');
  const [legalDoc, setLegalDoc] = useState('terms');
  const [paymentResultOrderId, setPaymentResultOrderId] = useState<string | null>(null);
  
  // Authentication State (for web users)
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null); // null = checking
  
  // Boot Sequence State (cached in sessionStorage to avoid re-boot on navigation)
  const [isBooted, setIsBooted] = useState(() => {
    // Check sessionStorage for cached boot state
    if (typeof window !== 'undefined') {
      return sessionStorage.getItem('pvndora_booted') === 'true';
    }
    return false;
  });
  const [musicLoaded, setMusicLoaded] = useState(false);
  
  // Check for payment redirect EARLY - before boot sequence
  // This allows PaymentResult to show immediately without waiting for boot
  const [isPaymentRedirect, setIsPaymentRedirect] = useState<string | null>(() => {
    if (typeof window === 'undefined') return null;
    
    // Check URL path for /payment/result (browser flow)
    if (window.location.pathname === '/payment/result') {
      const urlParams = new URLSearchParams(window.location.search);
      const orderId = urlParams.get('order_id');
      const topupId = urlParams.get('topup_id');
      if (orderId) {
        return orderId;
      }
      if (topupId) {
        return `topup_${topupId}`;
      }
    }
    
    // Check Telegram startapp parameter (Mini App flow)
    const tg = (window as any).Telegram?.WebApp;
    const startParam = tg?.initDataUnsafe?.start_param;
    const urlParams = new URLSearchParams(window.location.search);
    const urlStartapp = urlParams.get('tgWebAppStartParam') || urlParams.get('startapp');
    const hashParams = new URLSearchParams(window.location.hash.slice(1));
    const hashStartapp = hashParams.get('tgWebAppStartParam');
    
    const effectiveStartParam = startParam || urlStartapp || hashStartapp;
    
    if (effectiveStartParam?.startsWith('payresult_')) {
      const orderId = effectiveStartParam.replace('payresult_', '');
      return orderId;
    }
    
    // Handle topup redirect - navigate to profile after success
    if (effectiveStartParam?.startsWith('topup_')) {
      const topupId = effectiveStartParam.replace('topup_', '');
      return `topup_${topupId}`;
    }
    
    return null;
  });
  
  // HUD Notifications (replaces old toast system)
  const hud = useHUD();

  // Products for CommandPalette (fetched once)
  const { products: allProducts, getProducts } = useProductsTyped();
  
  // Profile data (preloaded during boot for faster Profile page access)
  const { profile, getProfile } = useProfileTyped();
  
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

  // Note: Authentication and data loading is now handled by BootSequence tasks

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
    handleFeedback('medium');
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
  
  // Boot sequence tasks - these run REAL operations
  const bootTasks: BootTask[] = useMemo(() => [
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
      critical: false, // Not critical - will show login page
      execute: async () => {
        // Persist session_token from URL query if present
        const { persistSessionTokenFromQuery } = await import('./utils/auth');
        persistSessionTokenFromQuery();

        // In Telegram WebApp context - always authenticated via initData
        const tg = (window as any).Telegram?.WebApp;
        if (tg?.initData) {
          return { authenticated: true, source: 'telegram' };
        }
        
        // In browser - check for session token
        const { getSessionToken, verifySessionToken, removeSessionToken } = await import('./utils/auth');
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
      critical: false, // Not critical - profile page will load its own data
      execute: async () => {
        try {
          const profileData = await getProfile();
          return { 
            loaded: !!profileData,
            username: profileData?.handle || null,
            balance: profileData?.balance || 0,
          };
        } catch (e) {
          console.warn('[Boot] Profile fetch failed:', e);
          return { loaded: false };
        }
      },
    },
    {
      id: 'music',
      label: 'Loading ambient audio stream...',
      successLabel: 'Ambient audio: READY',
      errorLabel: 'Audio stream unavailable',
      critical: false, // Not critical - app works without music
      execute: async () => {
        // Preload background music - FULL download via fetch first
        const musicUrl = '/sound.ogg';
        const startTime = Date.now();
        
        try {
          // Step 1: Prefetch entire file via fetch (same as BackgroundMusic component)
          const response = await fetch(musicUrl, { 
            cache: 'force-cache',
          });
          
          if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
          }

          // Step 2: Convert to blob to ensure full download
          const blob = await response.blob();
          const blobUrl = URL.createObjectURL(blob);
          const fetchTime = Date.now() - startTime;

          // Step 3: Create Audio element and wait for canplaythrough
          // NOTE: This is ONLY for preloading check - do NOT play it!
          return new Promise((resolve) => {
            const audio = new Audio(blobUrl);
            audio.preload = 'auto';
            audio.volume = 0; // Mute to prevent any accidental playback
            audio.crossOrigin = 'anonymous';
            
            const timeout = setTimeout(() => {
              // If loading takes too long, resolve anyway (non-critical)
              console.warn('[Boot] Music buffering timeout, continuing...');
              // Clean up: pause and remove audio element
              audio.pause();
              audio.src = '';
              URL.revokeObjectURL(blobUrl);
              resolve({ loaded: false, loadTime: Date.now() - startTime, fetchTime });
            }, 10000); // 10 second timeout for buffering
            
            audio.addEventListener('canplaythrough', () => {
              clearTimeout(timeout);
              const totalTime = Date.now() - startTime;
              URL.revokeObjectURL(blobUrl);
              resolve({ loaded: true, loadTime: totalTime, fetchTime });
            }, { once: true });
            
            audio.addEventListener('error', (e) => {
              clearTimeout(timeout);
              const error = (e.target as HTMLAudioElement).error;
              const errorMsg = error ? `Code ${error.code}: ${error.message}` : 'Unknown';
              console.warn('[Boot] Music load error:', errorMsg);
              // Clean up: pause and remove audio element
              audio.pause();
              audio.src = '';
              URL.revokeObjectURL(blobUrl);
              // Don't reject - music is non-critical
              resolve({ loaded: false, error: errorMsg, loadTime: Date.now() - startTime, fetchTime });
            }, { once: true });
            
            // Start loading
            audio.load();
          });
        } catch (error) {
          const errorMsg = error instanceof Error ? error.message : 'Unknown prefetch error';
          console.warn('[Boot] Music prefetch error:', errorMsg);
          // Don't reject - music is non-critical
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
        // Prefetch critical images/fonts
        const prefetchUrls = [
          'https://grainy-gradients.vercel.app/noise.svg',
        ];
        await Promise.allSettled(
          prefetchUrls.map(url => fetch(url).catch(() => null))
        );
        return true;
      },
    },
  ], [getProducts, getCart, getProfile]);
  
  // Handle boot sequence completion with real data
  const handleBootComplete = useCallback((results: Record<string, any>) => {
    // Check authentication result
    const authResult = results.auth;
    if (authResult?.authenticated) {
      setIsAuthenticated(true);
    } else {
      setIsAuthenticated(false);
    }
    
    // Check music loading result
    const musicResult = results.music;
    if (musicResult?.loaded) {
      setMusicLoaded(true);
    }
    
    setIsBooted(true);
    // Cache boot state to avoid re-boot on page navigation
    sessionStorage.setItem('pvndora_booted', 'true');
    AudioEngine.connect();
    
    // Show welcome notification with stats
    const productCount = results.catalog?.productCount || 0;
    const cartCount = results.cart?.itemCount || 0;
    
    setTimeout(() => {
      hud.system('UPLINK ESTABLISHED', `${productCount} modules available • ${cartCount} in payload`);
    }, 500);
  }, [hud]);

  // Handle payment redirect completion (clean URL after showing PaymentResult)
  useEffect(() => {
    if (isPaymentRedirect && window.location.pathname === '/payment/result') {
      // Clean up URL to prevent duplicate handling on refresh
      window.history.replaceState({}, '', '/');
    }
  }, [isPaymentRedirect]);

  // PRIORITY: Show PaymentResult immediately if coming from payment redirect
  // This bypasses boot sequence entirely for better UX
  // When user returns from payment, mark as booted to avoid boot sequence loop
  useEffect(() => {
    if (isPaymentRedirect && !isBooted) {
      // Mark as booted since user already loaded the app (they came from payment redirect)
      setIsBooted(true);
      if (typeof window !== 'undefined') {
        sessionStorage.setItem('pvndora_booted', 'true');
      }
    }
  }, [isPaymentRedirect, isBooted]);

  if (isPaymentRedirect) {
    const isTopUp = isPaymentRedirect.startsWith('topup_');
    const actualId = isTopUp ? isPaymentRedirect.replace('topup_', '') : isPaymentRedirect;
    
    const handleComplete = () => {
      setIsPaymentRedirect(null);
      // Navigate directly without boot sequence (already booted)
      if (isTopUp) {
        setCurrentView('profile');
      } else {
        setCurrentView('catalog');
      }
    };
    
    const handleViewOrders = () => {
      setIsPaymentRedirect(null);
      // Navigate directly without boot sequence
      setCurrentView(isTopUp ? 'profile' : 'orders');
    };
    
    return (
      <div className="min-h-screen bg-black">
        <PaymentResult 
          orderId={actualId}
          isTopUp={isTopUp}
          onComplete={handleComplete}
          onViewOrders={handleViewOrders}
        />
      </div>
    );
  }

  // Show Boot Sequence first (only once per session)
  if (!isBooted) {
    return (
      <BootSequence 
        tasks={bootTasks}
        onComplete={handleBootComplete}
        minDuration={2500}
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
      
      {/* Main Content */}
      <main className="w-full relative z-10">
        <AnimatePresence mode="wait">
          {currentView === 'payment-result' && paymentResultOrderId ? (
            <PaymentResult 
              key="payment-result"
              orderId={paymentResultOrderId}
              onComplete={() => {
                setPaymentResultOrderId(null);
                navigate('home');
              }}
              onViewOrders={() => {
                setPaymentResultOrderId(null);
                navigate('orders');
              }}
            />
          ) : currentView === 'admin' ? (
            <AdminPanelConnected key="admin" onExit={() => navigate('profile')} />
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
               onOpenSupport={(context) => {
                 setSupportContext(context || null);
                 setIsSupportWidgetOpen(true);
               }} 
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
        {isCheckoutOpen && (
          <CheckoutModalConnected 
            onClose={handleCloseCheckout} 
            onSuccess={handleCheckoutSuccess}
          />
        )}
      </AnimatePresence>

      {/* --- PERSISTENT SUPPORT WIDGET --- */}
      <SupportChatConnected 
        isOpen={isSupportWidgetOpen} 
        onToggle={(val) => {
          setIsSupportWidgetOpen(val);
          if (!val) setSupportContext(null); // Clear context when closing
        }} 
        onHaptic={() => handleFeedback('light')} 
        raiseOnMobile={shouldRaiseSupport}
        initialContext={supportContext}
      />

      {/* HUD Notifications are rendered by HUDProvider */}
      
      {/* Background Music (only after boot completes, persistent across navigation) */}
      {isBooted && (
        <BackgroundMusic 
          key="background-music-persistent" // Stable key prevents remounting
          src="/sound.ogg"
          volume={0.20}
          autoPlay={true}
          loop={true}
        />
      )}
      
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
      <CyberModalProvider>
        <NewAppInner />
      </CyberModalProvider>
    </HUDProvider>
  );
}

export default NewApp;

