/**
 * CheckoutModalConnected
 * 
 * Connected version of CheckoutModal with real cart and payment API.
 */

import React, { useEffect, useState, useCallback, useMemo } from 'react';
import CheckoutModal from './CheckoutModal';
import { useOrdersTyped, useProfileTyped } from '../../hooks/useApiTyped';
import { useCart } from '../../contexts/CartContext';
import type { CartItem, PaymentMethod } from '../../types/component';

interface CheckoutModalConnectedProps {
  onClose: () => void;
  onSuccess: () => void;
}

const CheckoutModalConnected: React.FC<CheckoutModalConnectedProps> = ({
  onClose,
  onSuccess,
}) => {
  // Use global cart context - shared with NewApp
  const { cart, getCart, removeCartItem, loading: cartLoading, error: cartError } = useCart();
  const { createOrder, loading: orderLoading, error: orderError } = useOrdersTyped();
  const { profile, getProfile } = useProfileTyped();
  const [isInitialized, setIsInitialized] = useState(false);

  useEffect(() => {
    const init = async () => {
      const [freshCart] = await Promise.all([getCart(), getProfile()]);
      setIsInitialized(true);
      
      // CRITICAL: If cart is empty after fetch, close immediately
      if (!freshCart || !freshCart.items || freshCart.items.length === 0) {
        onClose();
      }
    };
    init();
  }, [getCart, getProfile, onClose]);

  // ALWAYS close if cart becomes empty - no exceptions
  useEffect(() => {
    if (isInitialized && (!cart || !cart.items || cart.items.length === 0)) {
      onClose();
    }
  }, [isInitialized, cart, onClose]);

  const handleRemoveItem = useCallback(async (productId: string) => {
    try {
      const updatedCart = await removeCartItem(productId);
      // Cart state will trigger useEffect to close if empty
      // But also close immediately for faster UX
      if (!updatedCart || !updatedCart.items || updatedCart.items.length === 0) {
        onClose();
      }
    } catch (err) {
      console.error('Failed to remove item:', err);
    }
  }, [removeCartItem, onClose]);

  const handlePay = useCallback(async (method: PaymentMethod) => {
    try {
      // Map component payment method to API format
      const paymentMethod = method === 'internal' ? 'balance' : 'card';
      const paymentGateway = method === 'crystalpay' ? 'crystalpay' : undefined;
      
      const response = await createOrder({
        use_cart: true,
        payment_method: paymentMethod as any,
        payment_gateway: paymentGateway as any,
      });
      
      if (response) {
        // For external payment (CrystalPay), redirect IMMEDIATELY
        if (response.payment_url && method !== 'internal') {
          console.log('[Checkout] Payment URL received:', response.payment_url);
          console.log('[Checkout] Method:', method);
          
          // In Telegram WebApp, use openLink
          const tg = (window as any).Telegram?.WebApp;
          if (tg?.openLink) {
            console.log('[Checkout] Using tg.openLink');
            try {
              // Call openLink directly - it opens external browser
              tg.openLink(response.payment_url);
              // Don't close modal immediately - let user see the redirect
              // Modal will be closed when user returns or by parent component
              return null;
            } catch (err) {
              console.error('[Checkout] tg.openLink failed:', err);
              // Fallback to window.location if openLink fails
              window.location.href = response.payment_url;
              return null;
            }
          } else {
            // Fallback: redirect directly if Telegram WebApp not available
            console.log('[Checkout] Telegram WebApp not available, using window.location');
            window.location.href = response.payment_url;
            return null;
          }
        }
        
        // For internal (balance) payment, return response to show success
        if (method === 'internal') {
          console.log('[Checkout] Balance payment completed, showing success');
          return response;
        }
        
        // If no payment_url and not internal, something went wrong
        console.warn('[Checkout] No payment_url and not internal payment:', response);
        throw new Error('Payment URL not received');
      }
      
      console.warn('[Checkout] No response from createOrder');
      throw new Error('No response from server');
      return null;
    } catch (err) {
      console.error('Payment failed:', err);
      throw err;
    }
  }, [createOrder]);

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
  const cartItems: CartItem[] = cart?.items?.map(item => ({
    id: item.id,
    name: item.name,
    category: item.category,
    price: item.price,
    quantity: item.quantity,
    image: item.image,
  })) || [];

  // CRITICAL: Close modal immediately if cart is empty (check after mapping)
  useEffect(() => {
    if (isInitialized && (!cart || !cart.items || cartItems.length === 0)) {
      onClose();
    }
  }, [isInitialized, cart, cartItems.length, onClose]);

  // Don't render modal if cart is empty (but allow rendering during loading)
  if (!cart || !cart.items || cartItems.length === 0) {
    return null;
  }

  return (
    <CheckoutModal
      cart={cartItems}
      userBalance={profile?.balance || 0}
      onClose={onClose}
      onRemoveItem={handleRemoveItem}
      onPay={handlePay}
      onSuccess={onSuccess}
      loading={orderLoading}
      error={cartError || orderError}
    />
  );
};

export default CheckoutModalConnected;


