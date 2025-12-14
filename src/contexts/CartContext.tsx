/**
 * CartContext
 * 
 * Provides global cart state management across all components.
 * Solves the issue of multiple useCartTyped() instances having separate state.
 */

import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import { useApi } from '../hooks/useApi';
import { adaptCart } from '../adapters/cartAdapter';
import { logger } from '../utils/logger';
import type { APICartResponse } from '../types/api';
import type { CartData } from '../types/component';

interface CartContextType {
  cart: CartData | null;
  loading: boolean;
  error: string | null;
  getCart: () => Promise<CartData | null>;
  addToCart: (productId: string, quantity?: number) => Promise<CartData>;
  updateCartItem: (productId: string, quantity: number) => Promise<CartData>;
  removeCartItem: (productId: string) => Promise<CartData>;
  applyPromo: (code: string) => Promise<CartData | null>;
  removePromo: () => Promise<CartData | null>;
  clearCartState: () => void;
}

const CartContext = createContext<CartContextType | null>(null);

export function CartProvider({ children }: { children: ReactNode }) {
  const { get, post, patch, del, loading, error } = useApi();
  const [cart, setCart] = useState<CartData | null>(null);

  const getCart = useCallback(async (): Promise<CartData | null> => {
    try {
      const response: APICartResponse = await get('/cart');
      const adapted = adaptCart(response);
      setCart(adapted);
      return adapted;
    } catch (err) {
      logger.error('Failed to get cart', err);
      return null;
    }
  }, [get]);

  const addToCart = useCallback(async (productId: string, quantity: number = 1): Promise<CartData> => {
    try {
      const response: APICartResponse = await post('/cart/add', { product_id: productId, quantity });
      const adapted = adaptCart(response);
      setCart(adapted);
      return adapted;
    } catch (err) {
      logger.error('Failed to add to cart', err);
      throw err;
    }
  }, [post]);

  const updateCartItem = useCallback(async (productId: string, quantity: number): Promise<CartData> => {
    try {
      const response: APICartResponse = await patch('/cart/item', { product_id: productId, quantity });
      const adapted = adaptCart(response);
      setCart(adapted);
      return adapted;
    } catch (err) {
      logger.error('Failed to update cart item', err);
      throw err;
    }
  }, [patch]);

  const removeCartItem = useCallback(async (productId: string): Promise<CartData> => {
    try {
      const response: APICartResponse = await del(`/cart/item?product_id=${encodeURIComponent(productId)}`);
      const adapted = adaptCart(response);
      setCart(adapted);
      return adapted;
    } catch (err) {
      logger.error('Failed to remove cart item', err);
      throw err;
    }
  }, [del]);

  const applyPromo = useCallback(async (code: string): Promise<CartData | null> => {
    try {
      await post('/cart/promo/apply', { code });
      return getCart();
    } catch (err) {
      logger.error('Failed to apply promo', err);
      throw err;
    }
  }, [post, getCart]);

  const removePromo = useCallback(async (): Promise<CartData | null> => {
    try {
      await post('/cart/promo/remove', {});
      return getCart();
    } catch (err) {
      logger.error('Failed to remove promo', err);
      throw err;
    }
  }, [post, getCart]);

  const clearCartState = useCallback(() => {
    setCart(null);
  }, []);

  return (
    <CartContext.Provider value={{
      cart,
      loading,
      error,
      getCart,
      addToCart,
      updateCartItem,
      removeCartItem,
      applyPromo,
      removePromo,
      clearCartState,
    }}>
      {children}
    </CartContext.Provider>
  );
}

export function useCart(): CartContextType {
  const context = useContext(CartContext);
  if (!context) {
    throw new Error('useCart must be used within a CartProvider');
  }
  return context;
}

