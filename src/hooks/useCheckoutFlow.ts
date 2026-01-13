import { useState, useEffect, useCallback, useMemo } from "react";
import { useProductsTyped, useOrdersTyped, usePromoTyped } from "./useApiTyped";
import { useCart } from "../contexts/CartContext";
import { useLocale } from "./useLocale";
import { useTelegram } from "./useTelegram";
import { convertCartDataToLegacyCart, type LegacyCart } from "../utils/cartConverter";

interface Product {
  id: string;
  name: string;
  price: number;
  final_price?: number;
  currency?: string;
  [key: string]: string | number | undefined;
}

interface PromoResult {
  is_valid: boolean;
  discount_percent?: number;
  discount_amount?: number;
  error?: string;
}

interface PaymentMethod {
  system_group: string;
  name: string;
  icon?: string;
}

interface UseCheckoutFlowProps {
  productId?: string;
  initialQuantity?: number;
  onBack: () => void;
  onSuccess: () => void;
}

/**
 * Инкапсулирует логику страницы Checkout: загрузка товара/корзины,
 * промокоды, пересчёт тоталов, оформление заказа и взаимодействие
 * с Telegram UI (back button, haptics, alerts).
 */
export function useCheckoutFlow({
  productId,
  initialQuantity = 1,
  onBack,
  onSuccess,
}: UseCheckoutFlowProps) {
  const { getProduct, loading: productLoading } = useProductsTyped();
  const { createOrderFromCart, getPaymentMethods } = useOrdersTyped();
  const { checkPromo, loading: promoLoading } = usePromoTyped();
  const {
    cart: cartData,
    getCart,
    addToCart,
    updateCartItem,
    removeCartItem,
    applyPromo,
    removePromo,
    loading: cartLoading,
  } = useCart();
  const { t, formatPrice } = useLocale();
  const { setBackButton, hapticFeedback, showAlert, openLink, close } = useTelegram();

  const [product, setProduct] = useState<Product | null>(null);
  const [promoCode, setPromoCode] = useState("");
  const [promoResult, setPromoResult] = useState<PromoResult | null>(null);
  const [quantity, setQuantity] = useState(initialQuantity);
  const [error, setError] = useState<string | null>(null);
  const [availableMethods, setAvailableMethods] = useState<PaymentMethod[]>([]);
  const [selectedGateway, setSelectedGateway] = useState("crystalpay");
  const isCartMode = !productId;

  // Convert CartData to legacy Cart format for backward compatibility
  const cart: LegacyCart | null = useMemo(() => {
    return convertCartDataToLegacyCart(cartData);
  }, [cartData]);

  const loadProduct = useCallback(async () => {
    if (!productId) return;
    try {
      const data = await getProduct(productId);
      if (data) {
        setProduct({
          id: data.id,
          name: data.name,
          price: data.price,
          final_price: data.final_price,
          currency: data.currency,
        } as Product);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    }
  }, [getProduct, productId]);

  const loadCart = useCallback(async () => {
    try {
      const data = await getCart();
      if (data && data.items && Array.isArray(data.items) && data.items.length > 0) {
        // Cart is automatically updated via CartContext, just sync promo code
        if (data.promoCode) {
          setPromoCode(data.promoCode);
        }
      } else {
        setError(t("checkout.cartEmpty") || "Cart is empty");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    }
  }, [getCart, t]);

  const calculateTotal = useCallback(() => {
    if (isCartMode) {
      if (!cartData || !cartData.items || cartData.items.length === 0) return 0;

      let total = cartData.total || 0;

      // If promo is applied but not yet reflected in cartData, apply it manually
      if (promoResult?.is_valid && promoResult.discount_percent && !cartData.promoCode) {
        const subtotal = cartData.originalTotal || cartData.total || 0;
        total = subtotal * (1 - promoResult.discount_percent / 100);
      }

      return total;
    }

    if (!product) return 0;

    const price = product.final_price || product.price;
    let total = price * quantity;

    if (promoResult?.is_valid) {
      if (promoResult.discount_percent) {
        total = total * (1 - promoResult.discount_percent / 100);
      } else if (promoResult.discount_amount) {
        total = Math.max(0, total - promoResult.discount_amount);
      }
    }

    return total;
  }, [isCartMode, cartData, promoResult, product, quantity]);

  const handlePromoCheck = useCallback(async () => {
    if (!promoCode.trim()) return;

    try {
      if (isCartMode) {
        const updated = await applyPromo(promoCode);
        if (updated) {
          // Cart is automatically updated via CartContext
          setPromoResult({ is_valid: true, discount_percent: updated.promoDiscountPercent || 0 });
        }
        hapticFeedback("notification", "success");
      } else {
        const result = await checkPromo(promoCode);
        setPromoResult(result);

        if (result.is_valid) {
          hapticFeedback("notification", "success");
        } else {
          hapticFeedback("notification", "error");
        }
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Unknown error";
      setPromoResult({ is_valid: false, error: errorMessage });
      hapticFeedback("notification", "error");
      await showAlert(errorMessage);
    }
  }, [applyPromo, checkPromo, hapticFeedback, isCartMode, promoCode, showAlert]);

  const handleRemovePromo = useCallback(async () => {
    if (!isCartMode) {
      setPromoResult(null);
      setPromoCode("");
      return;
    }
    try {
      await removePromo();
      // Cart is automatically updated via CartContext
      setPromoResult(null);
      setPromoCode("");
      hapticFeedback("notification", "success");
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Unknown error";
      await showAlert(errorMessage);
    }
  }, [hapticFeedback, isCartMode, removePromo, showAlert]);

  const handleCartQuantity = useCallback(
    async (pid: string, newQuantity: number) => {
      try {
        hapticFeedback("selection");
        await updateCartItem(pid, newQuantity);
        // Cart is automatically updated via CartContext
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : "Unknown error";
        await showAlert(errorMessage);
      }
    },
    [hapticFeedback, showAlert, updateCartItem]
  );

  const handleCartRemove = useCallback(
    async (pid: string) => {
      try {
        hapticFeedback("selection");
        await removeCartItem(pid);
        // Cart is automatically updated via CartContext
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : "Unknown error";
        await showAlert(errorMessage);
      }
    },
    [hapticFeedback, removeCartItem, showAlert]
  );

  const handleCheckout = useCallback(
    async (selectedPaymentMethod = "card"): Promise<void> => {
      try {
        hapticFeedback("impact", "medium");

        if (!isCartMode && productId) {
          await addToCart(productId, quantity);
        }

        if (promoResult?.is_valid && promoCode) {
          await applyPromo(promoCode);
        }

        const result = await createOrderFromCart(
          promoResult?.is_valid ? promoCode : null,
          selectedPaymentMethod || "card",
          selectedGateway
        );

        hapticFeedback("notification", "success");

        if (result.payment_url) {
          // Replace current window with payment URL
          // After payment, CrystalPay will redirect to /payment/result for polling
          globalThis.location.href = result.payment_url;
          return;
        } else {
          await showAlert(t("checkout.orderCreated"));
          onSuccess();
        }
      } catch (err) {
        hapticFeedback("notification", "error");
        const errorMessage = err instanceof Error ? err.message : "Unknown error";
        await showAlert(errorMessage);
        throw err;
      }
    },
    [
      addToCart,
      applyPromo,
      createOrderFromCart,
      hapticFeedback,
      isCartMode,
      onSuccess,
      openLink,
      close,
      productId,
      promoCode,
      promoResult,
      quantity,
      showAlert,
      selectedGateway,
      t,
    ]
  );

  useEffect(() => {
    if (productId) {
      loadProduct();
    } else {
      loadCart();
    }

    getPaymentMethods(selectedGateway)
      .then((data) => {
        if (data && Array.isArray(data.systems)) {
          setAvailableMethods(data.systems);
        } else {
          setAvailableMethods([
            { system_group: "card", name: "Банковская карта", icon: "💳" },
            { system_group: "sbp", name: "СБП", icon: "🏦" },
            { system_group: "crypto", name: "Криптовалюта", icon: "₿" },
          ]);
        }
      })
      .catch(() =>
        setAvailableMethods([
          { system_group: "card", name: "Банковская карта", icon: "💳" },
          { system_group: "sbp", name: "СБП", icon: "🏦" },
        ])
      );

    setBackButton({
      isVisible: true,
      onClick: onBack,
    });

    return () => {
      setBackButton({ isVisible: false });
    };
  }, [productId, loadProduct, loadCart, onBack, setBackButton, getPaymentMethods, selectedGateway]);

  const total = calculateTotal();
  const currency = product?.currency || cartData?.currency || "USD";

  const priceMeta = useMemo(() => {
    let subtotal = 0;
    let discount = 0;

    if (isCartMode && cartData) {
      subtotal = cartData.originalTotal || cartData.total || 0;
      discount = subtotal - total;
    } else if (!isCartMode && product) {
      const basePrice = (product.final_price || product.price) * quantity;
      subtotal = basePrice;
      discount = subtotal - total;
    }

    return { subtotal, discount };
  }, [isCartMode, cartData, product, quantity, total]);

  return {
    product,
    cart,
    promoCode,
    setPromoCode,
    promoResult,
    quantity,
    setQuantity,
    error,
    isCartMode,
    productLoading,
    promoLoading,
    cartLoading,
    currency,
    total,
    subtotal: priceMeta.subtotal,
    discount: priceMeta.discount,
    handlePromoCheck,
    handleRemovePromo,
    handleCartQuantity,
    handleCartRemove,
    handleCheckout,
    calculateTotal,
    formatPrice,
    t,
    availableMethods,
    selectedGateway,
    setSelectedGateway,
  };
}

export default useCheckoutFlow;
