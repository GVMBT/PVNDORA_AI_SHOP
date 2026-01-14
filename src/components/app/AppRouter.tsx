/**
 * AppRouter Component
 *
 * Handles navigation between different views/pages in the app.
 * Uses AnimatePresence for smooth transitions.
 * Heavy components are lazy-loaded for better initial bundle size.
 */

import { AnimatePresence, motion } from "framer-motion";
import { memo, Suspense } from "react";
import type { CatalogProduct } from "../../types/component";
import { lazyWithRetry } from "../../utils/lazyWithRetry";
import {
  CatalogConnected,
  Footer,
  Guarantees,
  Hero,
  PaymentResult,
  ProductDetailConnected,
  type RefundContext,
} from "../new";
import type { FeedbackType } from "./useFeedback";

// Lazy load heavy components with auto-retry on chunk errors
const AdminPanelConnected = lazyWithRetry(() => import("../new/AdminPanelConnected"));
const LeaderboardConnected = lazyWithRetry(() => import("../new/LeaderboardConnected"));
const OrdersConnected = lazyWithRetry(() => import("../new/OrdersConnected"));
const ProfileConnected = lazyWithRetry(() => import("../new/ProfileConnected"));
const Legal = lazyWithRetry(() => import("../new/Legal"));

export type ViewType =
  | "home"
  | "orders"
  | "profile"
  | "leaderboard"
  | "legal"
  | "admin"
  | "payment-result";

interface AppRouterProps {
  readonly currentView: ViewType;
  readonly selectedProduct: CatalogProduct | null;
  readonly legalDoc: string;
  readonly paymentResultOrderId: string | null;
  readonly onNavigate: (view: ViewType) => void;
  readonly onNavigateLegal: (doc: string) => void;
  readonly onProductSelect: (product: CatalogProduct) => void;
  readonly onBackToCatalog: () => void;
  readonly onAddToCart: (product: CatalogProduct, quantity?: number) => void;
  readonly onOpenSupport: (context?: RefundContext | null) => void;
  readonly onHaptic: (type?: FeedbackType) => void;
}

/**
 * Loading fallback component for lazy-loaded views
 */
function ViewLoader() {
  return (
    <div className="min-h-[60vh] flex items-center justify-center">
      <div className="flex flex-col items-center gap-4">
        <div className="w-8 h-8 border-2 border-pandora-cyan border-t-transparent rounded-full animate-spin" />
        <span className="text-xs font-mono text-gray-500 tracking-wider">LOADING_MODULE...</span>
      </div>
    </div>
  );
}

// Helper: Render payment result view
function renderPaymentResultView(orderId: string, onNavigate: (view: ViewType) => void) {
  return (
    <PaymentResult
      key="payment-result"
      orderId={orderId}
      onComplete={() => onNavigate("home")}
      onViewOrders={() => onNavigate("orders")}
    />
  );
}

// Helper: Render admin view
function renderAdminView(onNavigate: (view: ViewType) => void) {
  return (
    <Suspense fallback={<ViewLoader />}>
      <AdminPanelConnected key="admin" onExit={() => onNavigate("profile")} />
    </Suspense>
  );
}

// Helper: Render profile view
function renderProfileView(
  onNavigate: (view: ViewType) => void,
  onHaptic: (type?: FeedbackType) => void
) {
  return (
    <Suspense fallback={<ViewLoader />}>
      <ProfileConnected
        key="profile"
        onBack={() => onNavigate("home")}
        onHaptic={onHaptic}
        onAdminEnter={() => onNavigate("admin")}
      />
    </Suspense>
  );
}

// Helper: Render orders view
function renderOrdersView(
  onNavigate: (view: ViewType) => void,
  onOpenSupport: (context?: RefundContext | null) => void
) {
  return (
    <Suspense fallback={<ViewLoader />}>
      <OrdersConnected
        key="orders"
        onBack={() => onNavigate("home")}
        onOpenSupport={onOpenSupport}
      />
    </Suspense>
  );
}

// Helper: Render leaderboard view
function renderLeaderboardView(onNavigate: (view: ViewType) => void) {
  return (
    <Suspense fallback={<ViewLoader />}>
      <LeaderboardConnected key="leaderboard" onBack={() => onNavigate("home")} />
    </Suspense>
  );
}

// Helper: Render legal view
function renderLegalView(legalDoc: string, onNavigate: (view: ViewType) => void) {
  return (
    <Suspense fallback={<ViewLoader />}>
      <Legal key="legal" doc={legalDoc} onBack={() => onNavigate("home")} />
    </Suspense>
  );
}

// Helper: Render product detail view
function renderProductDetailView(
  selectedProduct: CatalogProduct,
  onBackToCatalog: () => void,
  onAddToCart: (product: CatalogProduct, quantity?: number) => void,
  onProductSelect: (product: CatalogProduct) => void,
  onHaptic: (type?: FeedbackType) => void
) {
  return (
    <ProductDetailConnected
      key="detail"
      productId={String(selectedProduct.id)}
      onBack={onBackToCatalog}
      onAddToCart={onAddToCart}
      onProductSelect={onProductSelect}
      onHaptic={onHaptic}
    />
  );
}

// Helper: Render home view (catalog)
function renderHomeView(
  onProductSelect: (product: CatalogProduct) => void,
  onAddToCart: (product: CatalogProduct, quantity?: number) => void,
  onHaptic: (type?: FeedbackType) => void,
  onNavigateLegal: (doc: string) => void,
  onOpenSupport: (context?: RefundContext | null) => void
) {
  return (
    <motion.div key="home" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
      <Hero />
      <CatalogConnected
        onSelectProduct={onProductSelect}
        onAddToCart={onAddToCart}
        onHaptic={onHaptic}
      />
      <Guarantees />
      <Footer onNavigate={onNavigateLegal} onOpenSupport={() => onOpenSupport()} />
    </motion.div>
  );
}

function AppRouterComponent({
  currentView,
  selectedProduct,
  legalDoc,
  paymentResultOrderId,
  onNavigate,
  onNavigateLegal,
  onProductSelect,
  onBackToCatalog,
  onAddToCart,
  onOpenSupport,
  onHaptic,
}: AppRouterProps) {
  // Determine which view to render based on currentView
  const renderCurrentView = () => {
    if (currentView === "payment-result" && paymentResultOrderId) {
      return renderPaymentResultView(paymentResultOrderId, onNavigate);
    }
    if (currentView === "admin") {
      return renderAdminView(onNavigate);
    }
    if (currentView === "profile") {
      return renderProfileView(onNavigate, onHaptic);
    }
    if (currentView === "orders") {
      return renderOrdersView(onNavigate, onOpenSupport);
    }
    if (currentView === "leaderboard") {
      return renderLeaderboardView(onNavigate);
    }
    if (currentView === "legal") {
      return renderLegalView(legalDoc, onNavigate);
    }
    if (selectedProduct) {
      return renderProductDetailView(
        selectedProduct,
        onBackToCatalog,
        onAddToCart,
        onProductSelect,
        onHaptic
      );
    }
    return renderHomeView(onProductSelect, onAddToCart, onHaptic, onNavigateLegal, onOpenSupport);
  };

  return (
    <main className="w-full relative z-10">
      <AnimatePresence mode="wait">{renderCurrentView()}</AnimatePresence>
    </main>
  );
}

export const AppRouter = memo(AppRouterComponent);
