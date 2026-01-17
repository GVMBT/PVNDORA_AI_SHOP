/**
 * PVNDORA New App - React 19 UI with Connected Components
 *
 * Main application entry point. Uses modular components for:
 * - Boot Sequence (OS-style loading)
 * - Procedural Audio (Web Audio API)
 * - HUD Notifications (System Logs)
 */

import { AnimatePresence } from "framer-motion";
import React, { Suspense, useCallback, useEffect, useState } from "react";

// App Components
import { AppLayout, AppRouter, useBootTasks, useFeedback, type ViewType } from "./components/app";

// Connected Components (lazy load heavy ones)
import {
  BackgroundMusic,
  BootSequence,
  CyberModalProvider,
  HUDProvider,
  LoginPage,
  Navbar,
  PaymentResult,
  type RefundContext,
  SupportChatConnected,
  useHUD,
} from "./components/new";

// Lazy load with auto-retry on chunk errors
import { clearReloadCounter, lazyWithRetry } from "./utils/lazyWithRetry";

const CommandPalette = lazyWithRetry(() => import("./components/new/CommandPalette"));
const CheckoutModalConnected = lazyWithRetry(
  () => import("./components/new/CheckoutModalConnected")
);

import { BOT, CACHE, UI } from "./config";
import { useCart } from "./contexts/CartContext";
import { LocaleProvider } from "./contexts/LocaleContext";

// Hooks
import { useProductsTyped, useProfileTyped } from "./hooks/useApiTyped";
import { useLocale } from "./hooks/useLocale";
// Audio Engine
import { AudioEngine } from "./lib/AudioEngine";
// Types
import type { CatalogProduct, NavigationTarget } from "./types/component";
import { getSessionToken, removeSessionToken, verifySessionToken } from "./utils/auth";
import { logger } from "./utils/logger";
import { sessionStorage } from "./utils/storage";
import {
  expandWebApp,
  getStartParam,
  getTelegramInitData,
  requestFullscreen,
} from "./utils/telegram";

/**
 * Check for payment redirect on initial load
 */
function usePaymentRedirect() {
  return useState<string | null>(() => {
    if (globalThis.window === undefined) return null;

    // Check sessionStorage first (preserved after URL cleanup)
    const storedId = sessionStorage.getItem("payment_redirect_id");
    if (storedId) {
      return storedId;
    }

    if (globalThis.location.pathname === "/payment/result") {
      const urlParams = new URLSearchParams(globalThis.location.search);
      const orderId = urlParams.get("order_id");
      const topupId = urlParams.get("topup_id");
      if (orderId) return orderId;
      if (topupId) return `topup_${topupId}`;
    }

    // Try to get start_param from Telegram WebApp
    const startParam = getStartParam();
    const urlParams = new URLSearchParams(globalThis.location.search);
    const urlStartapp = urlParams.get("tgWebAppStartParam") || urlParams.get("startapp");
    const hashParams = new URLSearchParams(globalThis.location.hash.slice(1));
    const hashStartapp = hashParams.get("tgWebAppStartParam");

    const effectiveStartParam = startParam || urlStartapp || hashStartapp;

    if (effectiveStartParam?.startsWith("payresult_")) {
      return effectiveStartParam.replace("payresult_", "");
    }
    if (effectiveStartParam?.startsWith("topup_")) {
      return `topup_${effectiveStartParam.replace("topup_", "")}`;
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
  const [currentView, setCurrentView] = useState<ViewType>("home");
  const [legalDoc, setLegalDoc] = useState("terms");
  const [paymentResultOrderId, setPaymentResultOrderId] = useState<string | null>(null);

  // Auth State - also check storage for already-booted case
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(() => {
    // Always return null initially to trigger auth re-check
    // This prevents the flicker when returning from payment redirect
    // and ensures auth state is verified on every mount
    return null;
  });
  const [isAuthChecking, setIsAuthChecking] = useState(false);

  // Boot State
  const [isBooted, setIsBooted] = useState(() => {
    return sessionStorage.get(CACHE.BOOT_STATE_KEY) === "true";
  });

  // Payment redirect check
  const [isPaymentRedirect, setIsPaymentRedirect] = usePaymentRedirect();

  // Hooks
  const hud = useHUD();
  const handleFeedback = useFeedback();
  const { products: allProducts, getProducts } = useProductsTyped();
  const { getProfile } = useProfileTyped();
  const { cart, getCart, addToCart } = useCart();
  const { t } = useLocale();

  // Boot tasks
  const bootTasks = useBootTasks({ getProducts, getCart, getProfile });

  // Re-check auth when already booted but auth state unknown
  // This handles the case when user returns from payment redirect
  useEffect(() => {
    // Only run if: booted + auth unknown + not already checking
    if (!isBooted || isAuthenticated !== null || isAuthChecking) return;

    const checkAuth = async () => {
      setIsAuthChecking(true);
      try {
        const initData = getTelegramInitData();

        if (initData) {
          setIsAuthenticated(true);
          setIsAuthChecking(false);
          return;
        }

        const sessionToken = getSessionToken();

        if (sessionToken) {
          const result = await verifySessionToken(sessionToken);
          if (result?.valid) {
            setIsAuthenticated(true);
            setIsAuthChecking(false);
            return;
          }
          removeSessionToken();
        }

        // No valid auth found
        setIsAuthenticated(false);
      } catch (err) {
        logger.error("[Auth] Re-check failed:", err);
        setIsAuthenticated(false);
      } finally {
        setIsAuthChecking(false);
      }
    };

    checkAuth();
  }, [isBooted, isAuthenticated, isAuthChecking]);

  // Initialize Telegram Mini App fullscreen mode
  useEffect(() => {
    // Request fullscreen for better UX in Telegram Mini App
    // Uses modern @telegram-apps/sdk with automatic fallback
    requestFullscreen().catch(() => {
      // Silently ignore if not available
    });
    // Also expand to full height as fallback for older clients
    expandWebApp().catch(() => {
      // Silently ignore if not available
    });
  }, []);

  // Initialize Audio and CMD+K
  useEffect(() => {
    // Initialize immediately (Telegram Mini App typically allows this right after opening).
    // No "unlock" UX needed.
    AudioEngine.init();
    AudioEngine.resume();

    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setIsCmdOpen((prev) => !prev);
        AudioEngine.open();
      }
    };
    globalThis.addEventListener("keydown", handleKeyDown);
    return () => {
      globalThis.removeEventListener("keydown", handleKeyDown);
    };
  }, []);

  // Navigation handlers
  const navigate = useCallback(
    (view: ViewType) => {
      handleFeedback("light");
      setSelectedProduct(null);
      setIsCheckoutOpen(false);
      setCurrentView(view);
      globalThis.scrollTo({ top: 0, behavior: "smooth" });
    },
    [handleFeedback]
  );

  const handleNavigateLegal = useCallback(
    (doc: string) => {
      handleFeedback("light");
      setLegalDoc(doc);
      setCurrentView("legal");
      globalThis.scrollTo({ top: 0, behavior: "smooth" });
    },
    [handleFeedback]
  );

  const handleLogout = useCallback(() => {
    handleFeedback("medium");
    removeSessionToken();
    setIsAuthenticated(false);
    setCurrentView("home");
    globalThis.scrollTo({ top: 0, behavior: "smooth" });
  }, [handleFeedback]);

  const handleProductSelect = useCallback(
    (product: CatalogProduct) => {
      handleFeedback("medium");
      setSelectedProduct(product);
      globalThis.scrollTo({ top: 0, behavior: "smooth" });
    },
    [handleFeedback]
  );

  const handleBackToCatalog = useCallback(() => {
    handleFeedback("light");
    setSelectedProduct(null);
  }, [handleFeedback]);

  // Cart handlers
  const handleAddToCart = useCallback(
    async (product: CatalogProduct, quantity: number = 1) => {
      try {
        await addToCart(String(product.id), quantity);
        AudioEngine.addToCart();
        hud.success("MODULE MOUNTED", `${product.name} added to payload`);
      } catch (err) {
        logger.error("Failed to add to cart:", err);
        hud.error("MOUNT FAILED", "Unable to add module to payload");
      }
    },
    [addToCart, hud]
  );

  const handleOpenCart = useCallback(() => {
    handleFeedback("medium");
    setIsCheckoutOpen(true);
  }, [handleFeedback]);

  const handleCloseCheckout = useCallback(() => {
    handleFeedback("light");
    setIsCheckoutOpen(false);
  }, [handleFeedback]);

  const handleCheckoutSuccess = useCallback(() => {
    getCart();
    setIsCheckoutOpen(false);
    setCurrentView("orders");
    globalThis.scrollTo({ top: 0, behavior: "smooth" });
    AudioEngine.transaction();
    hud.success(t("checkout.success.title"), t("checkout.success.description1"));
  }, [getCart, hud, t]);

  // Handle external payment - show PaymentResult with polling in Mini App
  const handleAwaitingPayment = useCallback((orderId: string) => {
    setPaymentResultOrderId(orderId);
    setCurrentView("payment-result");
  }, []);

  // Command palette navigation
  const handleUniversalNavigate = useCallback(
    (target: NavigationTarget) => {
      handleFeedback("medium");
      if (typeof target === "string") {
        navigate(target as ViewType);
      } else if (target.type === "product") {
        setCurrentView("home");
        setSelectedProduct(target.product);
      }
    },
    [handleFeedback, navigate]
  );

  // Support handler
  const handleOpenSupport = useCallback((context?: RefundContext | null) => {
    setSupportContext(context || null);
    setIsSupportWidgetOpen(true);
  }, []);

  // Boot completion handler
  const handleBootComplete = useCallback(
    (results: Record<string, unknown>) => {
      const authResult = results.auth as { authenticated?: boolean } | undefined;
      setIsAuthenticated(authResult?.authenticated || false);

      setIsBooted(true);
      sessionStorage.set(CACHE.BOOT_STATE_KEY, "true");

      // Clear chunk reload counter on successful boot
      clearReloadCounter();
      AudioEngine.connect();

      const catalogResult = results.catalog as { productCount?: number } | undefined;
      const cartResult = results.cart as { itemCount?: number } | undefined;
      const productCount = catalogResult?.productCount || 0;
      const cartCount = cartResult?.itemCount || 0;

      setTimeout(() => {
        hud.system(
          "UPLINK ESTABLISHED",
          `${productCount} modules available • ${cartCount} in payload`
        );
      }, 500);
    },
    [hud]
  );

  // Payment redirect URL cleanup - preserve order_id before clearing URL
  useEffect(() => {
    if (isPaymentRedirect && globalThis.location.pathname === "/payment/result") {
      // Save order_id to sessionStorage before clearing URL to prevent reload loop
      const urlParams = new URLSearchParams(globalThis.location.search);
      const orderId = urlParams.get("order_id");
      const topupId = urlParams.get("topup_id");
      if (orderId || topupId) {
        sessionStorage.setItem("payment_redirect_id", topupId ? `topup_${topupId}` : orderId || "");
      }
      // Clear URL to prevent infinite redirects
      globalThis.history.replaceState({}, "", "/");
    }
  }, [isPaymentRedirect]);

  // Mark as booted on payment redirect
  useEffect(() => {
    if (isPaymentRedirect && !isBooted) {
      setIsBooted(true);
      sessionStorage.set(CACHE.BOOT_STATE_KEY, "true");
    }
  }, [isPaymentRedirect, isBooted]);

  // Handle startapp parameters (checkout, pay_product_id, etc.)
  useEffect(() => {
    if (!isBooted || !isAuthenticated) return;

    // Get startapp from various sources
    const urlParams = new URLSearchParams(globalThis.location.search);
    const hashParams = new URLSearchParams(globalThis.location.hash.slice(1));
    const startParam = getStartParam();
    const startapp =
      startParam ||
      urlParams.get("startapp") ||
      urlParams.get("tgWebAppStartParam") ||
      hashParams.get("tgWebAppStartParam");

    if (!startapp) return;

    // Handle checkout
    if (startapp === "checkout" || startapp === "cart") {
      setIsCheckoutOpen(true);
      // Clean up URL
      globalThis.history.replaceState({}, "", globalThis.location.pathname);
      return;
    }

    // Handle pay_productId_qty_N
    if (startapp.startsWith("pay_")) {
      const parts = startapp.split("_");
      // pay_productId or pay_productId_qty_N
      if (parts.length >= 2) {
        const productId = parts[1];
        const product = allProducts.find((p) => p.id === productId);
        if (product) {
          setSelectedProduct(product);
        }
      }
      globalThis.history.replaceState({}, "", globalThis.location.pathname);
      return;
    }

    // Handle product_productId
    if (startapp.startsWith("product_")) {
      const productId = startapp.replace("product_", "");
      const product = allProducts.find((p) => p.id === productId);
      if (product) {
        setSelectedProduct(product);
      }
      globalThis.history.replaceState({}, "", globalThis.location.pathname);
    }
  }, [isBooted, isAuthenticated, allProducts]);

  // Computed values
  const getActiveTab = () => {
    if (currentView === "profile") return "profile";
    if (currentView === "orders") return "orders";
    if (currentView === "leaderboard") return "leaderboard";
    return "catalog";
  };

  // Payment redirect flow
  if (isPaymentRedirect) {
    const isTopUp = isPaymentRedirect.startsWith("topup_");
    const actualId = isTopUp ? isPaymentRedirect.replace("topup_", "") : isPaymentRedirect;

    return (
      <div className="min-h-screen bg-black">
        <PaymentResult
          orderId={actualId}
          isTopUp={isTopUp}
          onComplete={() => {
            // Clear payment redirect state to prevent reload loop
            setIsPaymentRedirect(null);
            sessionStorage.removeItem("payment_redirect_id");
            setCurrentView(isTopUp ? "profile" : "home");
          }}
          onViewOrders={() => {
            // Clear payment redirect state to prevent reload loop
            setIsPaymentRedirect(null);
            sessionStorage.removeItem("payment_redirect_id");
            setCurrentView(isTopUp ? "profile" : "orders");
          }}
        />
      </div>
    );
  }

  // Boot sequence
  if (!isBooted) {
    return (
      <BootSequence
        tasks={bootTasks}
        onComplete={handleBootComplete}
        minDuration={UI.BOOT_MIN_DURATION}
      />
    );
  }

  // Auth checking state - show loading instead of flashing LoginPage
  // This prevents the redirect loop when returning from payment
  if (isAuthenticated === null || isAuthChecking) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-pandora-cyan/30 border-t-pandora-cyan rounded-full animate-spin mx-auto mb-4" />
          <div className="text-xs text-gray-500 font-mono">VERIFYING_SESSION</div>
        </div>
      </div>
    );
  }

  // Login page - only show when we're SURE user is not authenticated
  // But allow viewing Legal documents before auth
  if (isAuthenticated === false) {
    // If user wants to view legal docs, show them (even without auth)
    if (currentView === "legal") {
      const Legal = React.lazy(() => import("./components/new/Legal"));
      return (
        <React.Suspense
          fallback={
            <div className="min-h-screen bg-black flex items-center justify-center">
              <div className="w-8 h-8 border-2 border-pandora-cyan/30 border-t-pandora-cyan rounded-full animate-spin" />
            </div>
          }
        >
          <Legal doc={legalDoc} onBack={() => setCurrentView("home")} />
        </React.Suspense>
      );
    }

    return (
      <LoginPage
        onLoginSuccess={() => setIsAuthenticated(true)}
        botUsername={BOT.USERNAME}
        redirectPath="/"
        onNavigateLegal={handleNavigateLegal}
      />
    );
  }

  // Main app
  return (
    <AppLayout>
      {currentView !== "admin" && currentView !== "payment-result" && (
        <Navbar
          showMobile={!selectedProduct}
          cartCount={cart?.items?.length || 0}
          onOpenCart={handleOpenCart}
          onNavigateHome={() => navigate("home")}
          onNavigateOrders={() => navigate("orders")}
          onNavigateProfile={() => navigate("profile")}
          onNavigateLeaderboard={() => navigate("leaderboard")}
          activeTab={getActiveTab()}
          onHaptic={() => handleFeedback("light")}
          onLogout={handleLogout}
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

      <Suspense fallback={null}>
        {isCmdOpen && (
          <CommandPalette
            isOpen={isCmdOpen}
            onClose={() => setIsCmdOpen(false)}
            onNavigate={handleUniversalNavigate}
            products={allProducts}
          />
        )}
      </Suspense>

      <AnimatePresence>
        {isCheckoutOpen && (
          <Suspense fallback={null}>
            <CheckoutModalConnected
              onClose={handleCloseCheckout}
              onSuccess={handleCheckoutSuccess}
              onAwaitingPayment={handleAwaitingPayment}
            />
          </Suspense>
        )}
      </AnimatePresence>

      <SupportChatConnected
        isOpen={isSupportWidgetOpen}
        onToggle={(val) => {
          setIsSupportWidgetOpen(val);
          if (!val) setSupportContext(null);
        }}
        onHaptic={() => handleFeedback("light")}
        raiseOnMobile={currentView === "leaderboard"}
        initialContext={supportContext}
      />

      {isBooted && (
        <BackgroundMusic
          key="background-music-persistent"
          src="/sound.ogg"
          volume={0.2}
          autoPlay={true}
          loop={true}
        />
      )}
    </AppLayout>
  );
}

// Main App with providers
function NewApp() {
  // Initialize LocaleProvider first (without profile, will use defaults)
  // Profile will be loaded inside NewAppInner and context will be updated
  return (
    <LocaleProvider>
      <HUDProvider
        position="top-right"
        maxNotifications={UI.HUD_MAX_NOTIFICATIONS}
        defaultDuration={UI.HUD_DURATION}
      >
        <CyberModalProvider>
          <NewAppInner />
        </CyberModalProvider>
      </HUDProvider>
    </LocaleProvider>
  );
}

export default NewApp;
