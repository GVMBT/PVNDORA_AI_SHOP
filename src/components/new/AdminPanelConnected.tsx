/**
 * AdminPanelConnected
 *
 * Connected version of AdminPanel with real API data.
 * All data transformations are memoized to prevent infinite re-renders.
 */

import type React from "react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { type PromoCodeData, useAdminPromoTyped } from "../../hooks/api/useAdminPromoApi";
import { useAdmin } from "../../hooks/useAdmin";
import {
  useAdminAnalyticsTyped,
  useAdminOrdersTyped,
  useAdminProductsTyped,
  useAdminUsersTyped,
} from "../../hooks/useApiTyped";
import { formatDate, formatRelativeTime } from "../../utils/date";
import { logger } from "../../utils/logger";
import type { AccountingData, ProductData } from "../admin";
import type { TicketData } from "../admin/types";
import AdminPanel from "./AdminPanel";

interface AdminPanelConnectedProps {
  onExit: () => void;
}

// Raw API response types (before transformation)
interface RawTicketResponse {
  id: string;
  user_id?: string;
  first_name?: string;
  username?: string;
  status?: string;
  created_at?: string;
  description?: string;
  issue_type?: string;
  item_id?: string;
  order_id?: string;
  telegram_id?: number;
  admin_comment?: string;
  credentials?: string;
  product_name?: string;
}

interface RawWithdrawalResponse {
  id: string;
  user_id: string;
  telegram_id?: number;
  username?: string;
  first_name?: string;
  amount?: number;
  payment_method?: string;
  payment_details?: Record<string, unknown>;
  status?: string;
  admin_comment?: string;
  created_at?: string;
  processed_at?: string;
  user_balance?: number;
}

interface RawAnalyticsResponse {
  total_revenue?: number;
  orders_today?: number;
  orders_this_week?: number;
  orders_this_month?: number;
  total_users?: number;
  pending_orders?: number;
  open_tickets?: number;
  revenue_by_day?: Array<{ date: string; amount: number }>;
  total_user_balances?: number;
  pending_withdrawals?: number;
}

const AdminPanelConnected: React.FC<AdminPanelConnectedProps> = ({ onExit }) => {
  // API hooks
  const { products, getProducts, createProduct, updateProduct, deleteProduct } =
    useAdminProductsTyped();
  const { orders, getOrders } = useAdminOrdersTyped();
  const { users, getUsers, banUser, updateBalance } = useAdminUsersTyped();
  const { analytics, getAnalytics } = useAdminAnalyticsTyped();
  const {
    promoCodes,
    getPromoCodes,
    createPromoCode,
    updatePromoCode,
    deletePromoCode,
    togglePromoActive,
  } = useAdminPromoTyped();
  const { getTickets, getWithdrawals } = useAdmin();

  // Local state
  const [isInitialized, setIsInitialized] = useState(false);
  const [tickets, setTickets] = useState<RawTicketResponse[]>([]);
  const [withdrawals, setWithdrawals] = useState<RawWithdrawalResponse[]>([]);
  const [accountingData, setAccountingData] = useState<AccountingData | undefined>();
  const [isAccountingLoading, setIsAccountingLoading] = useState(false);

  // Ref to store user ID mapping (telegram_id -> UUID)
  const userIdMapRef = useRef<Map<number, string>>(new Map());

  // Fetch tickets - stable callback
  const fetchTickets = useCallback(async () => {
    try {
      const response = await getTickets("all");
      if (response?.tickets) {
        setTickets(response.tickets);
      }
    } catch (err) {
      logger.error("Failed to fetch tickets", err);
      setTickets([]);
    }
  }, [getTickets]);

  // Fetch withdrawals - stable callback
  const fetchWithdrawals = useCallback(async () => {
    try {
      const response = await getWithdrawals("all");
      if (response?.withdrawals) {
        setWithdrawals(response.withdrawals);
      }
    } catch (err) {
      logger.error("Failed to fetch withdrawals", err);
      setWithdrawals([]);
    }
  }, [getWithdrawals]);

  // Fetch accounting data with optional period filter and currency
  const fetchAccounting = useCallback(
    async (
      period?: "today" | "month" | "all" | "custom",
      customFrom?: string,
      customTo?: string,
      displayCurrency: "USD" | "RUB" = "RUB"
    ) => {
      setIsAccountingLoading(true);
      try {
        const { apiRequest } = await import("../../utils/apiClient");
        const { API } = await import("../../config");

        // Build URL with period and currency params
        let url = `${API.ADMIN_URL}/accounting/overview`;
        const params = new URLSearchParams();
        params.append("display_currency", displayCurrency);
        if (period && period !== "all") {
          params.append("period", period);
        }
        if (period === "custom" && customFrom) {
          params.append("from", customFrom);
        }
        if (period === "custom" && customTo) {
          params.append("to", customTo);
        }
        if (params.toString()) {
          url += `?${params.toString()}`;
        }

        const data = await apiRequest<AccountingData>(url);

        // Log for debugging
        logger.info("Accounting data loaded", data);

        setAccountingData({
          // Filter info
          period: data.period,
          startDate: data.start_date,
          endDate: data.end_date,

          // Orders
          totalOrders: Number.parseInt(data.total_orders, 10) || 0,

          // Revenue by currency (NEW - real amounts!)
          revenueByCurrency: data.revenue_by_currency || {},

          // Legacy totals in USD
          totalRevenue: Number.parseFloat(data.total_revenue) || 0,
          revenueGross: Number.parseFloat(data.total_revenue_gross) || 0,
          totalDiscountsGiven: Number.parseFloat(data.total_discounts_given) || 0,

          // Expenses (always in USD)
          totalCogs: Number.parseFloat(data.total_cogs) || 0,
          totalAcquiringFees: Number.parseFloat(data.total_acquiring_fees) || 0,
          totalReferralPayouts: Number.parseFloat(data.total_referral_payouts) || 0,
          totalReserves: Number.parseFloat(data.total_reserves) || 0,
          totalReviewCashbacks: Number.parseFloat(data.total_review_cashbacks) || 0,
          totalReplacementCosts: Number.parseFloat(data.total_replacement_costs) || 0,
          totalOtherExpenses: Number.parseFloat(data.total_other_expenses) || 0,
          totalInsuranceRevenue: Number.parseFloat(data.total_insurance_revenue) || 0,

          // Liabilities by currency (NEW - real amounts!)
          liabilitiesByCurrency: data.liabilities_by_currency || {},

          // Legacy liabilities
          totalUserBalances: Number.parseFloat(data.total_user_balances) || 0,
          pendingWithdrawals: Number.parseFloat(data.pending_withdrawals) || 0,

          // Profit (USD)
          netProfit: Number.parseFloat(data.net_profit) || 0,
          grossProfit: Number.parseFloat(data.profit_usd?.gross_profit) || undefined,
          operatingProfit: Number.parseFloat(data.profit_usd?.operating_profit) || undefined,
          grossMarginPct: Number.parseFloat(data.profit_usd?.gross_margin_pct) || undefined,
          netMarginPct: Number.parseFloat(data.profit_usd?.net_margin_pct) || undefined,

          // Reserves
          reservesAccumulated: Number.parseFloat(data.reserves_accumulated) || 0,
          reservesUsed: Number.parseFloat(data.reserves_used) || 0,
          reservesAvailable: Number.parseFloat(data.reserves_available) || 0,

          // Deprecated (kept for backward compatibility)
          currencyBreakdown: data.currency_breakdown || data.revenue_by_currency || {},
        });
      } catch (err) {
        logger.error("Failed to fetch accounting data", err);
      } finally {
        setIsAccountingLoading(false);
      }
    },
    []
  );

  // Initial data fetch - only run once on mount
  useEffect(() => {
    let isMounted = true;

    const init = async () => {
      try {
        await Promise.allSettled([
          getProducts(),
          getOrders(undefined, 50),
          getUsers(50),
          getAnalytics(),
          getPromoCodes(),
          fetchTickets(),
          fetchWithdrawals(),
          fetchAccounting("all", undefined, undefined, "RUB"),
        ]);

        if (isMounted) {
          setIsInitialized(true);
        }
      } catch (err) {
        logger.error("Failed to initialize admin panel", err);
        if (isMounted) {
          setIsInitialized(true);
        }
      }
    };

    init();

    return () => {
      isMounted = false;
    };
  }, [
    fetchAccounting,
    fetchTickets,
    fetchWithdrawals,
    getAnalytics,
    getOrders,
    getProducts,
    getPromoCodes,
    getUsers,
  ]); // eslint-disable-line react-hooks/exhaustive-deps

  // ALL useMemo hooks MUST be before any conditional returns (Rules of Hooks)

  // Memoized transformations
  const transformedProducts = useMemo(
    () =>
      products.map((p) => ({
        id: p.id,
        name: p.name,
        category: p.category || "ai",
        description: p.description || "",
        price: p.price,
        prices: p.prices || {}, // Anchor prices: {RUB: 990}
        msrp: p.msrp || p.price * 1.5,
        // msrp_prices removed - use msrp (always in RUB)
        discountPrice: p.discountPrice || 0,
        costPrice: p.costPrice || 0,
        fulfillmentType: p.fulfillmentType || "auto",
        stock: p.stock || 0,
        fulfillment: p.fulfillment || 0,
        warranty: p.warranty || 168,
        duration: p.duration || 30,
        sold: p.sold || 0,
        image:
          p.image ||
          "https://images.unsplash.com/photo-1677442136019-21780ecad995?q=80&w=800&auto=format&fit=crop",
        video: p.video,
        instructions: p.instructions || "",
        status: p.status || "active",
      })),
    [products]
  );

  const transformedOrders = useMemo(
    () =>
      orders.map((o) => ({
        id: o.id,
        user: o.user_handle || `@user_${o.user_id?.slice(0, 6)}`,
        product: o.product_name || "Unknown Product",
        amount: o.amount,
        status: o.status?.toUpperCase() || "PENDING",
        date: formatRelativeTime(o.created_at),
        method: o.payment_method?.toUpperCase() || "UNKNOWN",
      })),
    [orders]
  );

  const transformedUsers = useMemo(() => {
    // Update ref with fresh mapping
    const newMap = new Map<number, string>();
    const result = users.map((u) => {
      const telegramId = Number.parseInt(u.telegram_id, 10) || 0;
      newMap.set(telegramId, u.id);
      return {
        id: telegramId,
        dbId: u.id, // Database UUID for API calls
        username: u.username || `user_${u.id?.slice(0, 6)}`,
        role: (u.role?.toUpperCase() || "USER") as "USER" | "VIP" | "ADMIN",
        joinedAt: formatDate(u.created_at),
        purchases: u.orders_count || 0,
        spent: u.total_spent || 0,
        balance: u.balance || 0,
        balanceCurrency: u.balance_currency || "USD",
        isBanned: u.is_banned || false,
        invites: 0,
        earned: u.total_referral_earnings || 0, // Referral earnings
        savings: 0,
        // Partner-specific fields
        rewardType: u.partner_mode === "discount" ? "discount" : "commission",
      };
    });
    userIdMapRef.current = newMap;
    return result;
  }, [users]);

  const transformedTickets = useMemo(
    (): TicketData[] =>
      tickets.map((t) => ({
        id: t.id,
        user: t.first_name || t.username || `user_${t.user_id?.slice(0, 6)}`,
        subject: t.description?.slice(0, 50) || "No subject",
        status: (t.status?.toUpperCase() || "OPEN") as TicketData["status"],
        createdAt: t.created_at,
        lastMessage: t.description || "",
        priority: "MEDIUM" as const,
        date: formatRelativeTime(t.created_at),
        issue_type: t.issue_type,
        item_id: t.item_id,
        order_id: t.order_id,
        telegram_id: t.telegram_id,
        admin_comment: t.admin_comment,
        description: t.description,
        // Credentials for admin verification
        credentials: t.credentials,
        product_name: t.product_name,
      })),
    [tickets]
  );

  // Transform withdrawals for admin panel - MUST be before conditional return
  const transformedWithdrawals = useMemo(
    () =>
      withdrawals.map((w) => ({
        id: w.id,
        user_id: w.user_id,
        telegram_id: w.telegram_id,
        username: w.username,
        first_name: w.first_name,
        amount: w.amount || 0,
        payment_method: w.payment_method,
        payment_details: w.payment_details,
        status: w.status || "pending",
        admin_comment: w.admin_comment,
        created_at: w.created_at,
        processed_at: w.processed_at,
        user_balance: w.user_balance,
      })),
    [withdrawals]
  );

  const transformedStats = useMemo(() => {
    if (!analytics) return undefined;
    return {
      totalRevenue: analytics.total_revenue || 0,
      ordersToday: analytics.orders_today || 0,
      ordersWeek: analytics.orders_this_week || 0,
      ordersMonth: analytics.orders_this_month || 0,
      totalUsers: (analytics as RawAnalyticsResponse).total_users || 0,
      pendingOrders: (analytics as RawAnalyticsResponse).pending_orders || 0,
      openTickets: (analytics as RawAnalyticsResponse).open_tickets || 0,
      revenueByDay: analytics.revenue_by_day || [],
      totalUserBalances: (analytics as RawAnalyticsResponse).total_user_balances || 0,
      pendingWithdrawals: (analytics as RawAnalyticsResponse).pending_withdrawals || 0,
    };
  }, [analytics]);

  // Stable action handlers - use ref for userIdMap to avoid dependency issues
  const handleBanUser = useCallback(
    (telegramId: number, ban: boolean) => {
      const userId = userIdMapRef.current.get(telegramId);
      if (userId) {
        banUser(userId, ban);
      }
    },
    [banUser]
  );

  const handleUpdateBalance = useCallback(
    (telegramId: number, _amount: number) => {
      const userId = userIdMapRef.current.get(telegramId);
      if (userId) {
        const amount = globalThis.prompt("Enter amount to add (negative to subtract):", "0");
        if (amount !== null) {
          const parsed = Number.parseFloat(amount);
          if (!Number.isNaN(parsed)) {
            updateBalance(userId, parsed);
          }
        }
      }
    },
    [updateBalance]
  );

  // Promo handlers
  const handleCreatePromo = useCallback(
    async (data: Omit<PromoCodeData, "id" | "usage_count" | "created_at">) => {
      await createPromoCode(data);
    },
    [createPromoCode]
  );

  const handleUpdatePromo = useCallback(
    async (id: string, data: Partial<PromoCodeData>) => {
      await updatePromoCode(id, data);
    },
    [updatePromoCode]
  );

  const handleDeletePromo = useCallback(
    async (id: string) => {
      await deletePromoCode(id);
    },
    [deletePromoCode]
  );

  const handleTogglePromoActive = useCallback(
    async (id: string, isActive: boolean) => {
      await togglePromoActive(id, isActive);
    },
    [togglePromoActive]
  );

  // Product handlers
  const handleSaveProduct = useCallback(
    async (product: Partial<ProductData>) => {
      if (product.id) {
        // Update existing product
        await updateProduct(product.id, product);
      } else {
        // Create new product
        await createProduct(product);
      }
    },
    [createProduct, updateProduct]
  );

  const handleDeleteProduct = useCallback(
    async (productId: string) => {
      await deleteProduct(productId);
    },
    [deleteProduct]
  );

  // Toggle VIP status handler
  const handleToggleVIP = useCallback(
    async (userId: string, isVIP: boolean) => {
      const { apiRequest: makeRequest } = await import("../../utils/apiClient");
      const { API: apiConfig } = await import("../../config");

      try {
        await makeRequest(`${apiConfig.ADMIN_URL}/users/${userId}/vip`, {
          method: "POST",
          body: JSON.stringify({
            is_partner: isVIP,
            partner_level_override: isVIP ? 3 : null,
          }),
        });
        // Refresh users list
        await getUsers(50);
      } catch (err) {
        logger.error("Failed to toggle VIP status", err);
        throw err;
      }
    },
    [getUsers]
  );

  // Add expense handler
  const handleAddExpense = useCallback(
    async (expense: {
      description: string;
      amount: number;
      currency: "USD" | "RUB";
      category: string;
      date?: string;
      supplier_id?: string;
    }) => {
      const { apiRequest } = await import("../../utils/apiClient");
      const { API } = await import("../../config");

      try {
        await apiRequest(`${API.ADMIN_URL}/accounting/expenses`, {
          method: "POST",
          body: JSON.stringify(expense),
        });
        // Refresh accounting data
        await fetchAccounting("all");
        logger.info("Expense created successfully");
      } catch (err) {
        logger.error("Failed to create expense", err);
        throw err;
      }
    },
    [fetchAccounting]
  );

  // Loading state - AFTER all hooks
  if (!isInitialized) {
    return (
      <div className="fixed inset-0 z-[100] bg-[#050505] flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-2 border-pandora-cyan border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <div className="font-mono text-xs text-gray-500 uppercase tracking-widest">
            Загрузка админ-панели...
          </div>
        </div>
      </div>
    );
  }

  return (
    <AdminPanel
      onExit={onExit}
      products={transformedProducts}
      orders={transformedOrders}
      users={transformedUsers}
      tickets={transformedTickets}
      withdrawals={transformedWithdrawals}
      stats={transformedStats}
      promoCodes={promoCodes}
      accountingData={accountingData}
      onCreatePromo={handleCreatePromo}
      onUpdatePromo={handleUpdatePromo}
      onDeletePromo={handleDeletePromo}
      onTogglePromoActive={handleTogglePromoActive}
      onRefreshTickets={fetchTickets}
      onRefreshWithdrawals={fetchWithdrawals}
      onRefreshAccounting={fetchAccounting}
      onRefreshOrders={getOrders}
      isAccountingLoading={isAccountingLoading}
      onBanUser={handleBanUser}
      onUpdateBalance={handleUpdateBalance}
      onToggleVIP={handleToggleVIP}
      onSaveProduct={handleSaveProduct}
      onDeleteProduct={handleDeleteProduct}
      onAddExpense={handleAddExpense}
    />
  );
};

export default AdminPanelConnected;
