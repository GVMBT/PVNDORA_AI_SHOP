import { useState, useEffect, useCallback, useMemo } from 'react';
import { useProducts, useOrders, usePromo, useCartApi } from './useApi';
import { useLocale } from './useLocale';
import { useTelegram } from './useTelegram';

interface Product {
  id: string;
  name: string;
  price: number;
  final_price?: number;
  currency?: string;
  [key: string]: unknown;
}

interface CartItem {
  product_id: string;
  quantity: number;
  product?: Product;
  [key: string]: unknown;
}

interface Cart {
  items: CartItem[];
  total?: number;
  subtotal?: number;
  promo_code?: string;
  promo_discount_percent?: number;
  currency?: string;
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
export function useCheckoutFlow({ productId, initialQuantity = 1, onBack, onSuccess }: UseCheckoutFlowProps) {
  const { getProduct, loading: productLoading } = useProducts();
  const { createOrderFromCart, getPaymentMethods } = useOrders();
  const { checkPromo, loading: promoLoading } = usePromo();
  const { getCart, addToCart, updateCartItem, removeCartItem, applyCartPromo, removeCartPromo, loading: cartLoading } = useCartApi();
  const { t, formatPrice } = useLocale();
  const { setBackButton, hapticFeedback, showAlert } = useTelegram();

  const [product, setProduct] = useState<Product | null>(null);
  const [cart, setCart] = useState<Cart | null>(null);
  const [promoCode, setPromoCode] = useState('');
  const [promoResult, setPromoResult] = useState<PromoResult | null>(null);
  const [quantity, setQuantity] = useState(initialQuantity);
  const [error, setError] = useState<string | null>(null);
  const [availableMethods, setAvailableMethods] = useState<PaymentMethod[]>([]);
  const [selectedGateway, setSelectedGateway] = useState('crystalpay');
  const isCartMode = !productId;

  const loadProduct = useCallback(async () => {
    if (!productId) return;
    try {
      const data = await getProduct(productId);
      setProduct(data.product as Product);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    }
  }, [getProduct, productId]);

  const loadCart = useCallback(async () => {
    try {
      const data = await getCart();
      if (data && data.items && Array.isArray(data.items) && data.items.length > 0) {
        setCart(data as Cart);
        if (data.promo_code) {
          setPromoCode(data.promo_code);
        }
      } else {
        setError(t('checkout.cartEmpty') || 'Cart is empty');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    }
  }, [getCart, t]);

  const calculateTotal = useCallback(() => {
    if (isCartMode) {
      if (!cart || !cart.items || !Array.isArray(cart.items) || cart.items.length === 0) return 0;

      let total = cart.total || cart.subtotal || 0;

      if (promoResult?.is_valid && promoResult.discount_percent) {
        total = total * (1 - promoResult.discount_percent / 100);
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
  }, [isCartMode, cart, promoResult, product, quantity]);

  const handlePromoCheck = useCallback(async () => {
    if (!promoCode.trim()) return;

    try {
      if (isCartMode) {
        const updated = await applyCartPromo(promoCode);
        setCart(updated as Cart);
        setPromoResult({ is_valid: true, discount_percent: updated.promo_discount_percent || 0 });
        hapticFeedback('notification', 'success');
      } else {
        const result = await checkPromo(promoCode);
        setPromoResult(result);

        if (result.is_valid) {
          hapticFeedback('notification', 'success');
        } else {
          hapticFeedback('notification', 'error');
        }
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setPromoResult({ is_valid: false, error: errorMessage });
      hapticFeedback('notification', 'error');
      await showAlert(errorMessage);
    }
  }, [applyCartPromo, checkPromo, hapticFeedback, isCartMode, promoCode, showAlert]);

  const handleRemovePromo = useCallback(async () => {
    if (!isCartMode) {
      setPromoResult(null);
      setPromoCode('');
      return;
    }
    try {
      const updated = await removeCartPromo();
      setCart(updated as Cart);
      setPromoResult(null);
      setPromoCode('');
      hapticFeedback('notification', 'success');
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      await showAlert(errorMessage);
    }
  }, [hapticFeedback, isCartMode, removeCartPromo, showAlert]);

  const handleCartQuantity = useCallback(async (pid: string, newQuantity: number) => {
    try {
      hapticFeedback('selection');
      const updated = await updateCartItem(pid, newQuantity);
      setCart(updated as Cart);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      await showAlert(errorMessage);
    }
  }, [hapticFeedback, showAlert, updateCartItem]);

  const handleCartRemove = useCallback(async (pid: string) => {
    try {
      hapticFeedback('selection');
      const updated = await removeCartItem(pid);
      setCart(updated as Cart);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      await showAlert(errorMessage);
    }
  }, [hapticFeedback, removeCartItem, showAlert]);

  const handleCheckout = useCallback(async (selectedPaymentMethod = 'card') => {
    try {
      hapticFeedback('impact', 'medium');

      if (!isCartMode && productId) {
        await addToCart(productId, quantity);
      }

      if (promoResult?.is_valid && promoCode) {
        await applyCartPromo(promoCode);
      }

      const result = await createOrderFromCart(
        promoResult?.is_valid ? promoCode : null,
        selectedPaymentMethod || 'card',
        selectedGateway
      );

      hapticFeedback('notification', 'success');

      if (result.payment_url) {
        const isLocalForm = result.payment_url.includes('/payment/form');
        
        if (isLocalForm) {
          window.location.href = result.payment_url;
        } else {
          if ((window as any).Telegram?.WebApp?.openLink) {
            (window as any).Telegram.WebApp.openLink(result.payment_url);
          } else {
            window.open(result.payment_url, '_blank');
          }
          setTimeout(() => {
            if ((window as any).Telegram?.WebApp?.close) {
              (window as any).Telegram.WebApp.close();
            }
          }, 500);
        }
      } else {
        await showAlert(t('checkout.orderCreated'));
        onSuccess();
      }

    } catch (err) {
      hapticFeedback('notification', 'error');
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      await showAlert(errorMessage);
      throw err;
    }
  }, [
    addToCart,
    applyCartPromo,
    createOrderFromCart,
    hapticFeedback,
    isCartMode,
    onSuccess,
    productId,
    promoCode,
    promoResult,
    quantity,
    showAlert,
    selectedGateway,
    t
  ]);

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
            { system_group: 'card', name: 'Банковская карта', icon: '💳' },
            { system_group: 'sbp', name: 'СБП', icon: '🏦' },
            { system_group: 'crypto', name: 'Криптовалюта', icon: '₿' },
          ]);
        }
      })
      .catch(() => setAvailableMethods([
        { system_group: 'card', name: 'Банковская карта', icon: '💳' },
        { system_group: 'sbp', name: 'СБП', icon: '🏦' },
      ]));

    setBackButton({
      isVisible: true,
      onClick: onBack
    });

    return () => {
      setBackButton({ isVisible: false });
    };
  }, [productId, loadProduct, loadCart, onBack, setBackButton, getPaymentMethods, selectedGateway]);

  const total = calculateTotal();
  const currency = product?.currency || cart?.currency || 'USD';

  const priceMeta = useMemo(() => {
    let subtotal = 0;
    let discount = 0;

    if (isCartMode && cart) {
      subtotal = cart.subtotal || 0;
      discount = subtotal - total;
    } else if (!isCartMode && product) {
      const basePrice = (product.final_price || product.price) * quantity;
      subtotal = basePrice;
      discount = subtotal - total;
    }

    return { subtotal, discount };
  }, [isCartMode, cart, product, quantity, total]);

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
