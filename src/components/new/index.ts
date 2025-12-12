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
export { default as CommandPalette } from './CommandPalette';
export { default as Legal } from './Legal';

// === DATA COMPONENTS (With Mock Data - For Development) ===
export { default as Catalog } from './Catalog';
export { default as ProductDetail } from './ProductDetail';
export { default as Orders } from './Orders';
export { default as Profile } from './Profile';
export { default as Leaderboard } from './Leaderboard';
export { default as CheckoutModal } from './CheckoutModal';
export { default as AdminPanel } from './AdminPanel';

// === CONNECTED COMPONENTS (Real API Data - For Production) ===
export { default as CatalogConnected } from './CatalogConnected';
export { default as ProductDetailConnected } from './ProductDetailConnected';
export { default as OrdersConnected } from './OrdersConnected';
export { default as ProfileConnected } from './ProfileConnected';
export { default as LeaderboardConnected } from './LeaderboardConnected';
export { default as CheckoutModalConnected } from './CheckoutModalConnected';
