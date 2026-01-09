/**
 * CheckoutModalConnected
 * 
 * Connected version of CheckoutModal with real cart and payment API.
 * 
 * UNIFIED CURRENCY ARCHITECTURE:
 * - Uses USD values (_usd) for all balance vs total comparisons
 * - Uses display values for UI rendering
 * - Never mixes currencies in calculations
 */

import React, { useEffect, useState, useCallback } from 'react';
import CheckoutModal from './CheckoutModal';
import { useOrdersTyped, useProfileTyped } from '../../hooks/useApiTyped';
import { useCart } from '../../contexts/CartContext';
import { useLocaleContext } from '../../contexts/LocaleContext';
import { useLocale } from '../../hooks/useLocale';
import type { CartItem, PaymentMethod } from '../../types/component';
import type { APICreateOrderRequest } from '../../types/api';

interface CheckoutModalConnectedProps {
  onClose: () => void;
  onSuccess: () => void;
  onAwaitingPayment?: (orderId: string) => void;
}

const CheckoutModalConnected: React.FC<CheckoutModalConnectedProps> = ({
  onClose,
  onSuccess,
}) => {
  const { cart: contextCart, getCart, removeCartItem, updateCartItem, applyPromo, removePromo, loading: cartLoading, error: cartError } = useCart();
  const { createOrder, loading: orderLoading, error: orderError } = useOrdersTyped();
  const { profile: contextProfile, getProfile } = useProfileTyped();
  const { setExchangeRate } = useLocaleContext();
  const { t } = useLocale();
  const [isInitialized, setIsInitialized] = useState(false);
  
  // Store fresh data from API to avoid stale closure issues
  const [freshCart, setFreshCart] = useState<typeof contextCart>(null);
  const [freshProfile, setFreshProfile] = useState<typeof contextProfile>(null);

  useEffect(() => {
    let isMounted = true;
    const init = async () => {
      try {
        const [cartData, profileData] = await Promise.all([getCart(), getProfile()]);
        
        if (!isMounted) return;
        
        setFreshCart(cartData);
        setFreshProfile(profileData);
        
        // Update exchange rate in context for consistency
        if (cartData?.exchangeRate) {
          setExchangeRate(cartData.exchangeRate);
        }
        
        setIsInitialized(true);
      } catch {
        if (isMounted) setIsInitialized(true);
      }
    };
    init();
    
    return () => { isMounted = false; };
  }, [getCart, getProfile, setExchangeRate]);
  
  const cart = freshCart || contextCart;
  const profile = freshProfile || contextProfile;

  const handleRemoveItem = useCallback(async (productId: string) => {
    try {
      const updatedCart = await removeCartItem(productId);
      setFreshCart(updatedCart);
      if (!updatedCart || !updatedCart.items || updatedCart.items.length === 0) {
        onClose();
      }
    } catch {
      // Cart context will show error state
    }
  }, [removeCartItem, onClose]);

  const handleUpdateQuantity = useCallback(async (productId: string | number, quantity: number) => {
    if (quantity < 1) {
      // If quantity becomes 0 or less, remove item instead
      await handleRemoveItem(productId);
      return;
    }
    try {
      // Ensure productId is string for API call
      const updatedCart = await updateCartItem(String(productId), quantity);
      setFreshCart(updatedCart);
    } catch {
      // Cart context will show error state
    }
  }, [updateCartItem, handleRemoveItem]);
  
  const handleApplyPromo = useCallback(async (code: string): Promise<{ success: boolean; message?: string }> => {
    try {
      const updatedCart = await applyPromo(code);
      if (updatedCart) setFreshCart(updatedCart);
      return { success: true };
    } catch (err) {
      return { success: false, message: err instanceof Error ? err.message : 'Invalid promo code' };
    }
  }, [applyPromo]);
  
  const handleRemovePromo = useCallback(async () => {
    try {
      const updatedCart = await removePromo();
      if (updatedCart) setFreshCart(updatedCart);
    } catch {
      // Silently fail
    }
  }, [removePromo]);

  const handlePay = useCallback(async (method: PaymentMethod) => {
    const request: APICreateOrderRequest = {
      use_cart: true,
      ...(method === 'internal' 
        ? { payment_method: 'balance' }
        : { 
            payment_method: 'card',
            payment_gateway: method === 'crystalpay' ? 'crystalpay' : undefined
          }
      ),
    };
    
    const response = await createOrder(request);
    
    if (!response || !response.order_id) {
      throw new Error('Не удалось создать заказ. Попробуйте позже.');
    }
    
    if (response.payment_url && method !== 'internal') {
      window.location.href = response.payment_url;
      return null;
    }
    
    if (method === 'internal') {
      return response;
    }
    
    throw new Error('Payment URL not received');
  }, [createOrder]);

  // Close if cart becomes empty
  useEffect(() => {
    if (!isInitialized || cartLoading) return;
    
    const isEmpty = !cart || !cart.items || cart.items.length === 0;
    if (isEmpty) {
      const timeoutId = setTimeout(onClose, 0);
      return () => clearTimeout(timeoutId);
    }
  }, [isInitialized, cartLoading, cart, onClose]);

  // Loading state
  if (!isInitialized || cartLoading) {
    return (
      <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 backdrop-blur-sm">
        <div className="text-center">
          <div className="w-12 h-12 border-2 border-pandora-cyan border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <div className="font-mono text-xs text-gray-500 uppercase tracking-widest">
            {t('common.loadingCart')}
          </div>
        </div>
      </div>
    );
  }

  // Convert cart items
  const cartItems: CartItem[] = cart?.items?.map((item) => ({
    id: item.id,
    name: item.name,
    category: item.category,
    price: item.price,
    priceUsd: item.priceUsd,
    currency: item.currency || cart.currency || 'USD',
    quantity: item.quantity,
    image: item.image,
  })) || [];

  if (cartItems.length === 0) {
    return null;
  }

  // UNIFIED CURRENCY: Pass both USD and display values
  // CheckoutModal will use USD for comparisons, display for UI
  const modalProps = {
    cart: cartItems,
    // USD values (for calculations) - CRITICAL: always compare in same currency
    userBalanceUsd: profile?.balanceUsd || 0,
    totalUsd: cart?.totalUsd || 0,
    // Display values (for UI)
    userBalance: profile?.balance || 0,
    total: cart?.total || 0,
    originalTotal: cart?.originalTotal,
    // Currency info
    currency: cart?.currency || 'USD',
    exchangeRate: cart?.exchangeRate || 1.0,
    // Promo
    promoCode: cart?.promoCode,
    promoDiscountPercent: cart?.promoDiscountPercent,
    // Handlers
    onClose,
    onRemoveItem: handleRemoveItem,
    onUpdateQuantity: handleUpdateQuantity,
    onPay: handlePay,
    onSuccess,
    onApplyPromo: handleApplyPromo,
    onRemovePromo: handleRemovePromo,
    loading: orderLoading,
    error: cartError || orderError,
  };
  
  return <CheckoutModal {...modalProps} />;
};

export default CheckoutModalConnected;
