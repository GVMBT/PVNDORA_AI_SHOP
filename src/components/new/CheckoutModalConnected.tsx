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
  const { cart, getCart, removeCartItem, loading: cartLoading, error: cartError } = useCart();
  const { createOrder, loading: orderLoading, error: orderError } = useOrdersTyped();
  const { profile, getProfile } = useProfileTyped();
  const [isInitialized, setIsInitialized] = useState(false);

  useEffect(() => {
    let isMounted = true;
    const init = async () => {
      try {
        await Promise.all([getCart(), getProfile()]);
        
        if (!isMounted) {
          return;
        }
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

  const handleRemoveItem = useCallback(async (productId: string) => {
    try {
      const updatedCart = await removeCartItem(productId);
      // Cart state will trigger useEffect to close if empty
      // But also close immediately for faster UX
      if (!updatedCart || !updatedCart.items || updatedCart.items.length === 0) {
        onClose();
      }
    } catch (err) {
      // Silently handle error - cart context will show error state
    }
  }, [removeCartItem, onClose]);

  const handlePay = useCallback(async (method: PaymentMethod) => {
    try {
      // Map component payment method to API format
      // Note: 'balance' is not in API types, but backend accepts it for internal payments
      // For external payments, use 'card' with gateway
      const paymentMethod: 'card' | 'sbp' | 'crypto' = method === 'internal' ? 'card' : 'card';
      const paymentGateway: 'rukassa' | 'crystalpay' | '1plat' | 'freekassa' | undefined = 
        method === 'crystalpay' ? 'crystalpay' : undefined;
      
      // For internal balance, backend expects payment_method='card' without gateway
      // The backend logic checks user balance when gateway is not provided
      const request: APICreateOrderRequest = {
        use_cart: true,
        ...(method === 'internal' 
          ? { payment_method: 'card' } // Backend handles balance deduction
          : { 
              payment_method: paymentMethod,
              payment_gateway: paymentGateway 
            }
        ),
      };
      
      const response = await createOrder(request);
      
      if (response) {
        // For external payment (CrystalPay), open in browser and show polling screen
        if (response.payment_url && method !== 'internal') {
          const tgWebApp = window.Telegram?.WebApp;
          
          // Open payment URL in external browser
          if (tgWebApp?.openLink) {
            try {
              tgWebApp.openLink(response.payment_url);
            } catch (err) {
              // Fallback: open in new tab
              window.open(response.payment_url, '_blank');
            }
          } else {
            // Fallback for non-Telegram environment
            window.open(response.payment_url, '_blank');
          }
          
          // Close modal and show PaymentResult with polling
          // This keeps Mini App open while user pays in external browser
          if (response.order_id && onAwaitingPayment) {
            onClose();  // Close checkout modal
            onAwaitingPayment(response.order_id);  // Show PaymentResult
          }
          
          return null;
        }
        
        // For internal (balance) payment, return response to show success
        if (method === 'internal') {
          return response;
        }
        
        // If no payment_url and not internal, something went wrong
        throw new Error('Payment URL not received');
      }
      
      throw new Error('No response from server');
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

  const modalProps = {
    cart: cartItems,
    userBalance: profile?.balance || 0,
    currency: cart?.currency || profile?.currency || 'USD',
    onClose,
    onRemoveItem: handleRemoveItem,
    onPay: handlePay,
    onSuccess,
    loading: orderLoading,
    error: cartError || orderError,
  };
  
  return (
    <CheckoutModal {...modalProps} />
  );
};

export default CheckoutModalConnected;
