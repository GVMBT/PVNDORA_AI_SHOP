/**
 * CheckoutModalConnected
 * 
 * Connected version of CheckoutModal with real cart and payment API.
 */

import React, { useEffect, useState, useCallback } from 'react';
import CheckoutModal from './CheckoutModal';
import { useOrdersTyped, useProfileTyped } from '../../hooks/useApiTyped';
import { useCart } from '../../contexts/CartContext';
import type { CartItem, PaymentMethod } from '../../types/component';
import type { APICreateOrderRequest } from '../../types/api';

interface CheckoutModalConnectedProps {
  onClose: () => void;
  onSuccess: () => void;
  onAwaitingPayment?: (orderId: string) => void;  // Called when external payment opened
}

const CheckoutModalConnected: React.FC<CheckoutModalConnectedProps> = ({
  onClose,
  onSuccess,
  onAwaitingPayment,
}) => {
  // Use global cart context - shared with NewApp
  const { cart: contextCart, getCart, removeCartItem, applyPromo, removePromo, loading: cartLoading, error: cartError } = useCart();
  const { createOrder, loading: orderLoading, error: orderError } = useOrdersTyped();
  const { profile: contextProfile, getProfile } = useProfileTyped();
  const [isInitialized, setIsInitialized] = useState(false);
  
  // Store fresh data from API to avoid stale closure issues
  const [freshCart, setFreshCart] = useState<typeof contextCart>(null);
  const [freshProfile, setFreshProfile] = useState<typeof contextProfile>(null);

  useEffect(() => {
    let isMounted = true;
    const init = async () => {
      try {
        // Get FRESH data from API and store it locally to avoid stale closures
        const [cartData, profileData] = await Promise.all([getCart(), getProfile()]);
        
        if (!isMounted) {
          return;
        }
        
        // Store fresh data in local state
        setFreshCart(cartData);
        setFreshProfile(profileData);
        setIsInitialized(true);
      } catch (err) {
        if (isMounted) {
          setIsInitialized(true);
        }
      }
    };
    init();
    
    return () => {
      isMounted = false;
    };
  }, [getCart, getProfile]);
  
  // Use fresh data if available, fallback to context
  const cart = freshCart || contextCart;
  const profile = freshProfile || contextProfile;

  const handleRemoveItem = useCallback(async (productId: string) => {
    try {
      const updatedCart = await removeCartItem(productId);
      // Update fresh cart with new data
      setFreshCart(updatedCart);
      // Cart state will trigger useEffect to close if empty
      // But also close immediately for faster UX
      if (!updatedCart || !updatedCart.items || updatedCart.items.length === 0) {
        onClose();
      }
    } catch (err) {
      // Silently handle error - cart context will show error state
    }
  }, [removeCartItem, onClose]);
  
  const handleApplyPromo = useCallback(async (code: string): Promise<{ success: boolean; message?: string }> => {
    try {
      const updatedCart = await applyPromo(code);
      if (updatedCart) setFreshCart(updatedCart);
      return { success: true };
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Invalid promo code';
      return { success: false, message };
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
    try {
      // Map component payment method to API format
      // For internal balance: payment_method='balance' (no gateway needed)
      // For external payments: payment_method='card' with gateway
      const request: APICreateOrderRequest = {
        use_cart: true,
        ...(method === 'internal' 
          ? { payment_method: 'balance' } // Backend deducts from user balance
          : { 
              payment_method: 'card',
              payment_gateway: method === 'crystalpay' ? 'crystalpay' : undefined
            }
        ),
      };
      
      const response = await createOrder(request);
      
      // Check if response is valid
      if (!response || !response.order_id) {
        throw new Error('Не удалось создать заказ. Попробуйте позже.');
      }
      
      // For external payment (CrystalPay), redirect to payment page
      // After payment, CrystalPay will redirect back to /payment/result
      if (response.payment_url && method !== 'internal') {
        // Replace current window with payment URL
        // This closes Mini App and opens payment in browser
        // After payment, user will be redirected to /payment/result for polling
        window.location.href = response.payment_url;
        return null;
      }
      
      // For internal (balance) payment, return response to show success
      if (method === 'internal') {
        return response;
      }
      
      // If no payment_url and not internal, something went wrong
      throw new Error('Payment URL not received');
    } catch (err) {
      throw err;
    }
  }, [createOrder]);

  // Check if cart is empty and close modal if needed
  useEffect(() => {
    if (!isInitialized || cartLoading) {
      return;
    }
    
    const isEmpty = !cart || !cart.items || !Array.isArray(cart.items) || cart.items.length === 0;
    if (isEmpty) {
      const timeoutId = setTimeout(() => {
        onClose();
      }, 0);
      
      return () => {
        clearTimeout(timeoutId);
      };
    }
  }, [isInitialized, cartLoading, cart, onClose]);

  // Loading state
  if (!isInitialized || cartLoading) {
    return (
      <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 backdrop-blur-sm">
        <div className="text-center">
          <div className="w-12 h-12 border-2 border-pandora-cyan border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <div className="font-mono text-xs text-gray-500 uppercase tracking-widest">
            Loading Cart...
          </div>
        </div>
      </div>
    );
  }

  // Convert cart data to component format
  let cartItems: CartItem[] = [];
  
  if (cart?.items && Array.isArray(cart.items)) {
    try {
      const cartCurrency = cart.currency || 'USD';
      cartItems = cart.items.map((item) => ({
        id: item.id,
        name: item.name,
        category: item.category,
        price: item.price,
        currency: item.currency || cartCurrency,
        quantity: item.quantity,
        image: item.image,
      }));
    } catch (err) {
      cartItems = [];
    }
  }

  // Don't render modal if cart is empty
  if (cartItems.length === 0) {
    return null;
  }

  // CRITICAL FIX: Always compare balance vs cart total in the SAME currency
  // Problem: Cart may have prices in one currency (e.g., RUB), profile balance in another (e.g., USD)
  // Solution: Pass both USD balance and exchange rate for proper comparison
  const cartCurrency = cart?.currency || 'USD';
  const exchangeRate = cart?.exchangeRate || profile?.exchangeRate || 1.0;
  // Always compare against cart totals in the same currency
  const userBalanceUsd = profile?.balanceUsd || 0;
  const userBalanceInCartCurrency = cartCurrency === 'USD'
    ? userBalanceUsd
    : userBalanceUsd * exchangeRate;

  const modalProps = {
    cart: cartItems,
    userBalance: userBalanceInCartCurrency,
    currency: cartCurrency,
    originalTotal: cart?.originalTotal,
    promoCode: cart?.promoCode,
    promoDiscountPercent: cart?.promoDiscountPercent,
    onClose,
    onRemoveItem: handleRemoveItem,
    onPay: handlePay,
    onSuccess,
    onApplyPromo: handleApplyPromo,
    onRemovePromo: handleRemovePromo,
    loading: orderLoading,
    error: cartError || orderError,
  };
  
  return (
    <CheckoutModal {...modalProps} />
  );
};

export default CheckoutModalConnected;
