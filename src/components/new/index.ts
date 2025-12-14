/**
 * PVNDORA New Components
 * 
 * Barrel file for all new frontend components.
 * Use Connected versions for production (real API data).
 * Use base versions for development/testing (mock data).
 */

// === STATIC COMPONENTS (No Data Required) ===
export { default as Hero } from './Hero';
export { default as Navbar } from './Navbar';
export { default as Footer } from './Footer';
export { default as Guarantees } from './Guarantees';
export { default as PandoraBox } from './PandoraBox';
export { default as SupportChat } from './SupportChat';
// CommandPalette - lazy loaded in NewApp.tsx (removed from barrel to avoid duplicate import)
// Legal - lazy loaded in AppRouter.tsx (removed from barrel to avoid duplicate import)

// === SYSTEM COMPONENTS ===
export { default as BootSequence, type BootTask } from './BootSequence';
export { HUDProvider, useHUD, HUDIcons } from './HUDNotifications';
export { CyberModalProvider, useCyberModal } from './CyberModal';
export { default as BackgroundMusic } from './BackgroundMusic';
export { default as PaymentResult } from './PaymentResult';

// === DATA COMPONENTS (With Mock Data - For Development) ===
export { default as Catalog } from './Catalog';
export { default as ProductDetail } from './ProductDetail';
export { default as Orders, type RefundContext } from './Orders';
export { default as Profile } from './Profile';
export { default as Leaderboard } from './Leaderboard';
export { default as CheckoutModal } from './CheckoutModal';
export { default as AdminPanel } from './AdminPanel';

// === CONNECTED COMPONENTS (Real API Data - For Production) ===
export { default as CatalogConnected } from './CatalogConnected';
export { default as ProductDetailConnected } from './ProductDetailConnected';
export { default as LoginPage } from './LoginPage';
export { default as SupportChatConnected } from './SupportChatConnected';
// Lazy-loaded components (use direct imports in lazy() to avoid duplicate import warnings):
// - OrdersConnected (lazy loaded in AppRouter.tsx)
// - ProfileConnected (lazy loaded in AppRouter.tsx)
// - LeaderboardConnected (lazy loaded in AppRouter.tsx)
// - CheckoutModalConnected (lazy loaded in NewApp.tsx)
// - AdminPanelConnected (lazy loaded in AppRouter.tsx)
