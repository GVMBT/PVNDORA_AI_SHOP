/**
 * AdminPanel Component
 * 
 * Main admin panel container that orchestrates all admin views.
 */

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  AdminDashboard,
  AdminCatalog,
  AdminSales,
  AdminUsers,
  AdminPartners,
  AdminSupport,
  AdminWithdrawals,
  AdminPromo,
  AdminMigration,
  AdminAccounting,
  AdminSidebar,
  AdminHeader,
  ProductModal,
  type AdminView,
  type ProductData,
  type OrderData,
  type UserData,
  type TicketData,
  type WithdrawalData,
  type AdminStats,
  type PromoCodeData,
  type AccountingData,
} from '../admin';
import { logger } from '../../utils/logger';

interface AdminPanelProps {
  onExit: () => void;
  // Optional data props - if not provided, will use empty arrays
  products?: ProductData[];
  orders?: OrderData[];
  users?: UserData[];
  tickets?: TicketData[];
  withdrawals?: WithdrawalData[];
  stats?: AdminStats;
  promoCodes?: PromoCodeData[];
  accountingData?: AccountingData;
  onCreatePromo?: (data: Omit<PromoCodeData, 'id' | 'usage_count' | 'created_at'>) => Promise<void>;
  onUpdatePromo?: (id: string, data: Partial<PromoCodeData>) => Promise<void>;
  onDeletePromo?: (id: string) => Promise<void>;
  onTogglePromoActive?: (id: string, isActive: boolean) => Promise<void>;
  onRefreshTickets?: () => void;
  onRefreshWithdrawals?: () => void;
  onRefreshAccounting?: () => void;
  onRefreshOrders?: () => void;
  isAccountingLoading?: boolean;
  // User actions
  onBanUser?: (userId: number, ban: boolean) => void;
  onUpdateBalance?: (userId: number, amount: number) => void;
  // Product actions
  onSaveProduct?: (product: Partial<ProductData>) => Promise<void>;
  onDeleteProduct?: (productId: string) => void;
}

const AdminPanel: React.FC<AdminPanelProps> = ({ 
  onExit,
  products: propsProducts = [],
  orders: propsOrders = [],
  users: propsUsers = [],
  tickets: propsTickets = [],
  withdrawals: propsWithdrawals = [],
  stats: propsStats,
  promoCodes: propsPromoCodes = [],
  accountingData,
  onCreatePromo,
  onUpdatePromo,
  onDeletePromo,
  onTogglePromoActive,
  onRefreshTickets,
  onRefreshWithdrawals,
  onRefreshAccounting,
  onRefreshOrders,
  isAccountingLoading,
  onBanUser,
  onUpdateBalance,
  onSaveProduct,
  onDeleteProduct,
}) => {
  const [currentView, setCurrentView] = useState<AdminView>('dashboard');
  const [isSidebarOpen, setSidebarOpen] = useState(false);
  const [isSidebarCollapsed, setSidebarCollapsed] = useState(false);
  
  // Modal states
  const [isProductModalOpen, setIsProductModalOpen] = useState(false);
  const [editingProduct, setEditingProduct] = useState<Partial<ProductData> | null>(null);

  // Handlers
  const handleEditProduct = (product: ProductData) => {
    setEditingProduct(product);
    setIsProductModalOpen(true);
  };

  const handleNewProduct = () => {
    setEditingProduct({ 
      name: '', 
      price: 0, 
      stock: 0, 
      category: 'Text', 
      image: 'https://images.unsplash.com/photo-1550751827-4bd374c3f58b?q=80&w=800&auto=format&fit=crop',
    });
    setIsProductModalOpen(true);
  };

  const handleSaveProduct = async (product: Partial<ProductData>) => {
    if (onSaveProduct) {
      await onSaveProduct(product);
    }
    setIsProductModalOpen(false);
    setEditingProduct(null);
  };

  const renderCurrentView = () => {
    switch (currentView) {
      case 'dashboard':
        return <AdminDashboard stats={propsStats} />;
      case 'catalog':
        return (
          <AdminCatalog
            products={propsProducts}
            onEditProduct={handleEditProduct}
            onNewProduct={handleNewProduct}
            onDeleteProduct={onDeleteProduct}
          />
        );
      case 'sales':
        return <AdminSales orders={propsOrders} onRefresh={onRefreshOrders} />;
      case 'partners':
        return (
          <AdminPartners
            partners={propsUsers.filter(u => u.role === 'VIP')}
            onEditPartner={(partner) => {
              // Handle partner edit - can reuse AdminUsers modal or create specific one
              handleEditProduct({} as ProductData); // Placeholder - will be replaced with partner edit
            }}
            onRefresh={onRefreshOrders}
          />
        );
      case 'support':
        return <AdminSupport tickets={propsTickets} onRefresh={onRefreshTickets} />;
      case 'withdrawals':
        return <AdminWithdrawals withdrawals={propsWithdrawals} onRefresh={onRefreshWithdrawals} />;
      case 'promo':
        return (
          <AdminPromo
            promoCodes={propsPromoCodes}
            products={propsProducts.map(p => ({ id: p.id, name: p.name }))}  // Pass products for selection
            onCreatePromo={onCreatePromo}
            onUpdatePromo={onUpdatePromo}
            onDeletePromo={onDeletePromo}
            onToggleActive={onTogglePromoActive}
          />
        );
      case 'migration':
        return <AdminMigration />;
      case 'accounting':
        return (
          <AdminAccounting 
            data={accountingData}
            onRefresh={onRefreshAccounting}
            isLoading={isAccountingLoading}
          />
        );
      default:
        return null;
    }
  };

  return (
    <motion.div 
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="min-h-screen bg-black text-white flex flex-col md:flex-row overflow-hidden"
    >
      <AdminSidebar
        currentView={currentView}
        isOpen={isSidebarOpen}
        isCollapsed={isSidebarCollapsed}
        onViewChange={setCurrentView}
        onToggleCollapse={() => setSidebarCollapsed(!isSidebarCollapsed)}
        onClose={() => setSidebarOpen(false)}
        onExit={onExit}
      />

      {/* Overlay for mobile sidebar */}
      {isSidebarOpen && (
        <div 
          className="fixed inset-0 bg-black/80 z-30 md:hidden" 
          onClick={() => setSidebarOpen(false)} 
        />
      )}

      {/* Main Content */}
      <div className="flex-1 min-w-0 bg-[#080808] h-[calc(100vh-64px)] md:h-screen overflow-y-auto">
        <AdminHeader currentView={currentView} />

        {/* View Content */}
        <div className="p-4 md:p-8 pb-24 md:pb-8">
          <AnimatePresence mode="wait">
            <motion.div 
              key={currentView}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.2 }}
            >
              {renderCurrentView()}
            </motion.div>
          </AnimatePresence>
        </div>
      </div>

      {/* Modals */}
      <ProductModal
        isOpen={isProductModalOpen}
        product={editingProduct}
        onClose={() => {
          setIsProductModalOpen(false);
          setEditingProduct(null);
        }}
        onSave={handleSaveProduct}
      />

    </motion.div>
  );
};

export default AdminPanel;
