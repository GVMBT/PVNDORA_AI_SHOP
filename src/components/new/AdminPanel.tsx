/**
 * AdminPanel Component
 *
 * Main admin panel container that orchestrates all admin views.
 */

import { AnimatePresence, motion } from "framer-motion";
import type React from "react";
import { useState } from "react";
import { logger } from "../../utils/logger";
import {
  type AccountingData,
  AdminAccounting,
  AdminCatalog,
  AdminDashboard,
  AdminHeader,
  AdminMigration,
  AdminPartners,
  AdminPromo,
  AdminSales,
  AdminSidebar,
  type AdminStats,
  AdminSupport,
  AdminUsers,
  type AdminView,
  AdminWithdrawals,
  type ExpenseData,
  ExpenseModal,
  type OrderData,
  PartnerModal,
  type ProductData,
  ProductModal,
  type PromoCodeData,
  type TicketData,
  type UserData,
  type WithdrawalData,
} from "../admin";

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
  onCreatePromo?: (data: Omit<PromoCodeData, "id" | "usage_count" | "created_at">) => Promise<void>;
  onUpdatePromo?: (id: string, data: Partial<PromoCodeData>) => Promise<void>;
  onDeletePromo?: (id: string) => Promise<void>;
  onTogglePromoActive?: (id: string, isActive: boolean) => Promise<void>;
  onRefreshTickets?: () => void;
  onRefreshWithdrawals?: () => void;
  onRefreshAccounting?: (
    period?: "today" | "month" | "all" | "custom",
    customFrom?: string,
    customTo?: string,
    displayCurrency?: "USD" | "RUB"
  ) => void;
  onRefreshOrders?: () => void;
  isAccountingLoading?: boolean;
  onAddExpense?: (expense: ExpenseData) => Promise<void>;
  // User actions
  onBanUser?: (userId: number, ban: boolean) => void;
  onUpdateBalance?: (userId: number, amount: number) => void;
  onToggleVIP?: (userId: string, isVIP: boolean) => Promise<void>;
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
  onToggleVIP,
  onSaveProduct,
  onDeleteProduct,
  onAddExpense,
}) => {
  const [currentView, setCurrentView] = useState<AdminView>("dashboard");
  const [isSidebarOpen, setSidebarOpen] = useState(false);
  const [isSidebarCollapsed, setSidebarCollapsed] = useState(false);

  // Modal states
  const [isProductModalOpen, setIsProductModalOpen] = useState(false);
  const [editingProduct, setEditingProduct] = useState<Partial<ProductData> | null>(null);
  const [selectedPartner, setSelectedPartner] = useState<UserData | null>(null);
  const [isExpenseModalOpen, setIsExpenseModalOpen] = useState(false);

  // Handlers
  const handleEditProduct = (product: ProductData) => {
    setEditingProduct(product);
    setIsProductModalOpen(true);
  };

  const handleNewProduct = () => {
    setEditingProduct({
      name: "",
      price: 0,
      stock: 0,
      category: "Text",
      image:
        "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?q=80&w=800&auto=format&fit=crop",
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

  const handleSavePartner = (partner: UserData) => {
    // TODO: Implement partner update API call
    // For now, just close modal and refresh
    logger.info("Partner update requested", partner);
    setSelectedPartner(null);
    if (onRefreshOrders) {
      onRefreshOrders();
    }
  };

  const handleSaveExpense = async (expense: ExpenseData) => {
    if (onAddExpense) {
      await onAddExpense(expense);
    }
    setIsExpenseModalOpen(false);
  };

  const renderCurrentView = () => {
    switch (currentView) {
      case "dashboard":
        return <AdminDashboard stats={propsStats} />;
      case "catalog":
        return (
          <AdminCatalog
            onDeleteProduct={onDeleteProduct}
            onEditProduct={handleEditProduct}
            onNewProduct={handleNewProduct}
            products={propsProducts}
          />
        );
      case "sales":
        return <AdminSales onRefresh={onRefreshOrders} orders={propsOrders} />;
      case "users":
        return (
          <AdminUsers
            onBanUser={onBanUser}
            onRefresh={onRefreshOrders}
            onUpdateBalance={onUpdateBalance}
            users={propsUsers}
          />
        );
      case "partners":
        return (
          <AdminPartners
            onEditPartner={(partner) => {
              // Open partner management modal
              setSelectedPartner(partner);
            }}
            onRefresh={onRefreshOrders}
            onRevokeVIP={async (partner) => {
              if (onToggleVIP) {
                await onToggleVIP(partner.dbId, false);
                if (onRefreshOrders) {
                  onRefreshOrders();
                }
              }
            }}
            partners={propsUsers.filter((u) => u.role === "VIP")}
          />
        );
      case "support":
        return <AdminSupport onRefresh={onRefreshTickets} tickets={propsTickets} />;
      case "withdrawals":
        return <AdminWithdrawals onRefresh={onRefreshWithdrawals} withdrawals={propsWithdrawals} />;
      case "promo":
        return (
          <AdminPromo
            onCreatePromo={onCreatePromo}
            onDeletePromo={onDeletePromo} // Pass products for selection
            onToggleActive={onTogglePromoActive}
            onUpdatePromo={onUpdatePromo}
            products={propsProducts.map((p) => ({ id: String(p.id), name: p.name }))}
            promoCodes={propsPromoCodes}
          />
        );
      case "migration":
        return <AdminMigration />;
      case "accounting":
        return (
          <AdminAccounting
            data={accountingData}
            isLoading={isAccountingLoading}
            onAddExpense={onAddExpense ? () => setIsExpenseModalOpen(true) : undefined}
            onRefresh={onRefreshAccounting}
          />
        );
      default:
        return null;
    }
  };

  return (
    <motion.div
      animate={{ opacity: 1 }}
      className="flex min-h-screen flex-col overflow-hidden bg-black text-white md:flex-row"
      exit={{ opacity: 0 }}
      initial={{ opacity: 0 }}
    >
      <AdminSidebar
        currentView={currentView}
        isCollapsed={isSidebarCollapsed}
        isOpen={isSidebarOpen}
        onClose={() => setSidebarOpen(false)}
        onExit={onExit}
        onToggleCollapse={() => setSidebarCollapsed(!isSidebarCollapsed)}
        onViewChange={setCurrentView}
      />

      {/* Overlay for mobile sidebar */}
      {isSidebarOpen && (
        <button
          aria-label="Close sidebar"
          className="fixed inset-0 z-30 cursor-default bg-black/80 md:hidden"
          onClick={() => setSidebarOpen(false)}
          type="button"
        />
      )}

      {/* Main Content */}
      <div className="h-[calc(100vh-64px)] min-w-0 flex-1 overflow-y-auto bg-[#080808] md:h-screen">
        <AdminHeader currentView={currentView} />

        {/* View Content */}
        <div className="p-4 pb-24 md:p-8 md:pb-8">
          <AnimatePresence mode="wait">
            <motion.div
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              initial={{ opacity: 0, y: 10 }}
              key={currentView}
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
        onClose={() => {
          setIsProductModalOpen(false);
          setEditingProduct(null);
        }}
        onSave={handleSaveProduct}
        product={editingProduct}
      />

      <PartnerModal
        onClose={() => setSelectedPartner(null)}
        onSave={handleSavePartner}
        partner={selectedPartner}
      />

      {onAddExpense && (
        <ExpenseModal
          expense={null}
          isOpen={isExpenseModalOpen}
          onClose={() => setIsExpenseModalOpen(false)}
          onSave={handleSaveExpense}
        />
      )}
    </motion.div>
  );
};

export default AdminPanel;
