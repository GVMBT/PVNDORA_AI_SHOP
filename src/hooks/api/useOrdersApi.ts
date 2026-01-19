/**
 * Orders API Hook
 *
 * Type-safe hook for fetching and creating orders.
 */

import { useCallback, useState } from "react";
import { adaptOrders } from "../../adapters";
import type {
  APICreateOrderRequest,
  APICreateOrderResponse,
  APIOrdersResponse,
  APIPaymentMethodsResponse,
} from "../../types/api";
import type { Order } from "../../types/component";
import { logger } from "../../utils/logger";
import { useApi } from "../useApi";

export function useOrdersTyped() {
  const { get, post, loading, error } = useApi();
  const [orders, setOrders] = useState<Order[]>([]);

  const getOrders = useCallback(
    async (params?: { limit?: number; offset?: number }): Promise<Order[]> => {
      const searchParams = new URLSearchParams();
      if (params?.limit) {
        searchParams.append("limit", params.limit.toString());
      }
      if (params?.offset) {
        searchParams.append("offset", params.offset.toString());
      }
      const qs = searchParams.toString();

      try {
        const endpoint = qs ? `/orders?${qs}` : "/orders";
        const response: APIOrdersResponse = await get(endpoint);
        const adapted = adaptOrders(response);
        setOrders(adapted);
        return adapted;
      } catch (err) {
        logger.error("Failed to fetch orders", err);
        return [];
      }
    },
    [get]
  );

  const createOrder = useCallback(
    async (request: APICreateOrderRequest): Promise<APICreateOrderResponse | null> => {
      try {
        return await post("/orders", request);
      } catch (err) {
        logger.error("Failed to create order", err);
        // Re-throw error so caller can handle it properly
        throw err;
      }
    },
    [post]
  );

  const getPaymentMethods = useCallback(
    async (gateway?: string): Promise<APIPaymentMethodsResponse> => {
      try {
        const query = gateway ? `?gateway=${gateway}` : "";
        return await get<APIPaymentMethodsResponse>(`/payments/methods${query}`);
      } catch (err) {
        logger.error("Failed to fetch payment methods", err);
        // Return default methods on error
        return {
          systems: [
            {
              system_group: "card",
              name: "Банковская карта",
              icon: "💳",
              enabled: true,
              min_amount: 0,
            },
            { system_group: "sbp", name: "СБП", icon: "🏦", enabled: true, min_amount: 0 },
          ],
        };
      }
    },
    [get]
  );

  const createOrderFromCart = useCallback(
    async (
      promoCode: string | null = null,
      paymentMethod = "card",
      paymentGateway: string | null = null
    ): Promise<APICreateOrderResponse | null> => {
      try {
        return await post<APICreateOrderResponse>("/orders", {
          use_cart: true,
          promo_code: promoCode,
          payment_method: paymentMethod,
          payment_gateway: paymentGateway,
        });
      } catch (err) {
        logger.error("Failed to create order from cart", err);
        return null;
      }
    },
    [post]
  );

  const verifyPayment = useCallback(
    async (
      orderId: string
    ): Promise<{ status: string; message?: string; invoice_state?: string } | null> => {
      try {
        return await post(`/orders/${orderId}/verify-payment`, {});
      } catch (err) {
        logger.error("Failed to verify payment", err);
        return null;
      }
    },
    [post]
  );

  return {
    orders,
    getOrders,
    createOrder,
    createOrderFromCart,
    getPaymentMethods,
    verifyPayment,
    loading,
    error,
  };
}
