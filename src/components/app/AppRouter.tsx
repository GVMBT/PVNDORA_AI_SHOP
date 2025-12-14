/**
 * AppRouter Component
 * 
 * Handles navigation between different views/pages in the app.
 * Uses AnimatePresence for smooth transitions.
 * Heavy components are lazy-loaded for better initial bundle size.
 */

import React, { memo, Suspense } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import {
  Hero,
  Guarantees,
  Footer,
  CatalogConnected,
  ProductDetailConnected,
  PaymentResult,
  type RefundContext,
} from '../new';
import type { CatalogProduct } from '../../types/component';
import type { FeedbackType } from './useFeedback';
import { lazyWithRetry } from '../../utils/lazyWithRetry';

// Lazy load heavy components with auto-retry on chunk errors
const AdminPanelConnected = lazyWithRetry(() => import('../new/AdminPanelConnected'));
const LeaderboardConnected = lazyWithRetry(() => import('../new/LeaderboardConnected'));
const OrdersConnected = lazyWithRetry(() => import('../new/OrdersConnected'));
const ProfileConnected = lazyWithRetry(() => import('../new/ProfileConnected'));
const Legal = lazyWithRetry(() => import('../new/Legal'));

export type ViewType = 'home' | 'orders' | 'profile' | 'leaderboard' | 'legal' | 'admin' | 'payment-result';

interface AppRouterProps {
  currentView: ViewType;
  selectedProduct: CatalogProduct | null;
  legalDoc: string;
  paymentResultOrderId: string | null;
  onNavigate: (view: ViewType) => void;
  onNavigateLegal: (doc: string) => void;
  onProductSelect: (product: CatalogProduct) => void;
  onBackToCatalog: () => void;
  onAddToCart: (product: CatalogProduct, quantity?: number) => void;
  onOpenSupport: (context?: RefundContext | null) => void;
  onHaptic: (type?: FeedbackType) => void;
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
  return (
    <main className="w-full relative z-10">
      <AnimatePresence mode="wait">
        {currentView === 'payment-result' && paymentResultOrderId ? (
          <PaymentResult 
            key="payment-result"
            orderId={paymentResultOrderId}
            onComplete={() => onNavigate('home')}
            onViewOrders={() => onNavigate('orders')}
          />
        ) : currentView === 'admin' ? (
          <Suspense fallback={<ViewLoader />}>
            <AdminPanelConnected 
              key="admin" 
              onExit={() => onNavigate('profile')} 
            />
          </Suspense>
        ) : currentView === 'profile' ? (
          <Suspense fallback={<ViewLoader />}>
            <ProfileConnected 
              key="profile" 
              onBack={() => onNavigate('home')} 
              onHaptic={onHaptic} 
              onAdminEnter={() => onNavigate('admin')} 
            />
          </Suspense>
        ) : currentView === 'orders' ? (
          <Suspense fallback={<ViewLoader />}>
            <OrdersConnected 
              key="orders" 
              onBack={() => onNavigate('home')} 
              onOpenSupport={onOpenSupport}
            />
          </Suspense>
        ) : currentView === 'leaderboard' ? (
          <Suspense fallback={<ViewLoader />}>
            <LeaderboardConnected 
              key="leaderboard" 
              onBack={() => onNavigate('home')} 
            />
          </Suspense>
        ) : currentView === 'legal' ? (
          <Suspense fallback={<ViewLoader />}>
            <Legal 
              key="legal" 
              doc={legalDoc} 
              onBack={() => onNavigate('home')} 
            />
          </Suspense>
        ) : selectedProduct ? (
          <ProductDetailConnected 
            key="detail" 
            productId={String(selectedProduct.id)}
            onBack={onBackToCatalog} 
            onAddToCart={onAddToCart}
            onProductSelect={onProductSelect}
            onHaptic={onHaptic}
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
              onSelectProduct={onProductSelect} 
              onAddToCart={onAddToCart}
              onHaptic={onHaptic} 
            />
            <Guarantees />
            <Footer 
              onNavigate={onNavigateLegal} 
              onOpenSupport={() => onOpenSupport()} 
            />
          </motion.div>
        )}
      </AnimatePresence>
    </main>
  );
}

export const AppRouter = memo(AppRouterComponent);
