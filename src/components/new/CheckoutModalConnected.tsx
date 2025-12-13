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

  // Track if we should auto-close (cart became empty after user action)
  const wasInitializedWithItems = React.useRef(false);

  useEffect(() => {
    const init = async () => {
      await Promise.all([getCart(), getProfile()]);
      setIsInitialized(true);
    };
    init();
  }, [getCart, getProfile]);

  // Track if cart had items on init
  useEffect(() => {
    if (isInitialized && cart?.items && cart.items.length > 0) {
      wasInitializedWithItems.current = true;
    }
  }, [isInitialized, cart]);

  // Close modal if cart becomes empty AFTER having items (user removed last item)
  // Don't close if cart was already empty on mount (just show empty state)
  useEffect(() => {
    if (isInitialized && wasInitializedWithItems.current && (!cart || !cart.items || cart.items.length === 0)) {
      // Small delay to allow animation and prevent jarring close
      const timer = setTimeout(() => {
        onClose();
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [isInitialized, cart, onClose]);

  const handleRemoveItem = useCallback(async (productId: string) => {
    try {
      const updatedCart = await removeCartItem(productId);
      // If cart becomes empty after removing item, close the modal
      if (!updatedCart || !updatedCart.items || updatedCart.items.length === 0) {
        onClose();
      }
    } catch (err) {
      console.error('Failed to remove item:', err);
      // Even on error, re-fetch cart to check actual state
      const freshCart = await getCart();
      if (!freshCart || !freshCart.items || freshCart.items.length === 0) {
        onClose();
      }
    }
  }, [removeCartItem, onClose, getCart]);

  const handlePay = useCallback(async (method: PaymentMethod) => {
    try {
      // Map component payment method to API format
      const paymentMethod = method === 'internal' ? 'balance' : 'card';
      const paymentGateway = method === 'crystalpay' ? 'crystalpay' : (method === 'rukassa' ? 'rukassa' : undefined);
      
      const response = await createOrder({
        use_cart: true,
        payment_method: paymentMethod as any,
        payment_gateway: paymentGateway as any,
      });
      
      if (response) {
        // For external payment, redirect to payment URL
        if (response.payment_url && method !== 'internal') {
          // In Telegram WebApp, use openLink
          const tg = (window as any).Telegram?.WebApp;
          if (tg?.openLink) {
            tg.openLink(response.payment_url);
          } else {
            window.open(response.payment_url, '_blank');
          }
        }
        
        return response;
      }
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
  const cartItems: CartItem[] = cart?.items.map(item => ({
    id: item.id,
    name: item.name,
    category: item.category,
    price: item.price,
    quantity: item.quantity,
    image: item.image,
  })) || [];

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


