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
  console.log('[CheckoutModal] ===== COMPONENT RENDER START =====');
  
  // Use global cart context - shared with NewApp
  const { cart, getCart, removeCartItem, loading: cartLoading, error: cartError } = useCart();
  const { createOrder, loading: orderLoading, error: orderError } = useOrdersTyped();
  const { profile, getProfile } = useProfileTyped();
  const [isInitialized, setIsInitialized] = useState(false);
  
  console.log('[CheckoutModal] Initial state:', {
    cart,
    cartLoading,
    cartError,
    orderLoading,
    orderError,
    profile,
    isInitialized,
  });

  useEffect(() => {
    console.log('[CheckoutModal] useEffect[init] triggered');
    let isMounted = true;
    const init = async () => {
      try {
        console.log('[CheckoutModal] Initializing, fetching cart and profile...');
        const results = await Promise.all([getCart(), getProfile()]);
        console.log('[CheckoutModal] Fetch results:', {
          cart: results[0],
          profile: results[1],
        });
        
        if (!isMounted) {
          console.log('[CheckoutModal] Component unmounted during init, aborting');
          return;
        }
        console.log('[CheckoutModal] Setting isInitialized = true');
        setIsInitialized(true);
      } catch (err) {
        console.error('[CheckoutModal] Initialization error:', err);
        if (isMounted) {
          console.log('[CheckoutModal] Setting isInitialized = true (after error)');
          setIsInitialized(true);
        }
      }
    };
    init();
    
    return () => {
      console.log('[CheckoutModal] useEffect[init] cleanup - unmounting');
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
  console.log('[CheckoutModal] Checking loading state:', {
    isInitialized,
    cartLoading,
    shouldShowLoading: !isInitialized || cartLoading,
  });
  
  if (!isInitialized || cartLoading) {
    console.log('[CheckoutModal] RENDERING LOADING STATE');
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
  
  console.log('[CheckoutModal] Past loading check, processing cart data');

  // Convert cart data to component format - simplified without useMemo
  console.log('[CheckoutModal] Converting cart data, cart:', cart);
  let cartItems: CartItem[] = [];
  
  if (!cart) {
    console.log('[CheckoutModal] Cart is null/undefined');
  } else if (!cart.items) {
    console.log('[CheckoutModal] Cart.items is null/undefined');
  } else if (!Array.isArray(cart.items)) {
    console.log('[CheckoutModal] Cart.items is not an array:', typeof cart.items, cart.items);
  } else {
    console.log('[CheckoutModal] Cart.items is valid array, length:', cart.items.length);
    try {
      cartItems = cart.items.map((item, index) => {
        console.log(`[CheckoutModal] Mapping item ${index}:`, item);
        return {
          id: item.id,
          name: item.name,
          category: item.category,
          price: item.price,
          quantity: item.quantity,
          image: item.image,
        };
      });
      console.log('[CheckoutModal] Mapped cartItems:', cartItems);
    } catch (err) {
      console.error('[CheckoutModal] Error mapping cart items:', err, cart);
      cartItems = [];
    }
  }
  
  console.log('[CheckoutModal] Final cartItems:', {
    length: cartItems.length,
    items: cartItems,
  });

  // Check if cart is empty and close modal if needed
  // Use cart.items directly instead of cartItems to avoid dependency on computed value
  useEffect(() => {
    console.log('[CheckoutModal] useEffect[empty-check] triggered', {
      isInitialized,
      cartLoading,
      cartItems: cart?.items?.length || 0,
    });
    
    if (!isInitialized || cartLoading) {
      console.log('[CheckoutModal] Skipping empty check - not initialized or loading');
      return;
    }
    
    const isEmpty = !cart || !cart.items || !Array.isArray(cart.items) || cart.items.length === 0;
    if (isEmpty) {
      console.log('[CheckoutModal] Cart is empty, scheduling close');
      const timeoutId = setTimeout(() => {
        console.log('[CheckoutModal] Executing onClose()');
        onClose();
      }, 0);
      
      return () => {
        console.log('[CheckoutModal] useEffect[empty-check] cleanup - clearing timeout');
        clearTimeout(timeoutId);
      };
    } else {
      console.log('[CheckoutModal] Cart is not empty, length:', cart.items.length);
    }
  }, [isInitialized, cartLoading, cart, onClose]);

  // Don't render modal if cart is empty
  console.log('[CheckoutModal] Final render check:', {
    cartItemsLength: cartItems.length,
    willRender: cartItems.length > 0,
  });
  
  if (cartItems.length === 0) {
    console.log('[CheckoutModal] RENDERING NULL - cart is empty');
    return null;
  }

  console.log('[CheckoutModal] RENDERING MODAL with props:', {
    cartItemsCount: cartItems.length,
    userBalance: profile?.balance || 0,
    orderLoading,
    hasError: !!(cartError || orderError),
  });
  
  const modalProps = {
    cart: cartItems,
    userBalance: profile?.balance || 0,
    onClose,
    onRemoveItem: handleRemoveItem,
    onPay: handlePay,
    onSuccess,
    loading: orderLoading,
    error: cartError || orderError,
  };
  
  console.log('[CheckoutModal] ===== COMPONENT RENDER END - RETURNING MODAL =====');
  
  return (
    <CheckoutModal {...modalProps} />
  );
};

export default CheckoutModalConnected;


