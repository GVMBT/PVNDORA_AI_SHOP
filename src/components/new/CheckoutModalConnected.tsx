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
          console.log('[Checkout] Redirecting to CrystalPay:', response.payment_url);
          // In Telegram WebApp, use openLink
          const tg = (window as any).Telegram?.WebApp;
          if (tg?.openLink) {
            // Close modal before redirect
            onClose();
            // Small delay to let modal close animation start
            setTimeout(() => {
              tg.openLink(response.payment_url);
            }, 100);
            // Return null to prevent success screen
            return null;
          } else {
            // Fallback: redirect directly (this will close modal automatically)
            window.location.href = response.payment_url;
            return null;
          }
        }
        
        // For internal (balance) payment, return response to show success
        console.log('[Checkout] Balance payment completed, showing success');
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


