/**
 * Products API Hook
 * 
 * Type-safe hook for fetching products with automatic data transformation.
 */

import { useState, useCallback } from 'react';
import { useApi } from '../useApi';
import type { APIProductsResponse, APIProductResponse } from '../../types/api';
import type { CatalogProduct, ProductDetailData } from '../../types/component';
import { adaptProductList, adaptProductDetail } from '../../adapters';

function getLanguageCode(): string {
  const tgLang = (window as any).Telegram?.WebApp?.initDataUnsafe?.user?.language_code;
  const browserLang = navigator.language?.split('-')[0];
  return tgLang || browserLang || 'en';
}

export function useProductsTyped() {
  const { get, loading, error } = useApi();
  const [products, setProducts] = useState<CatalogProduct[]>([]);

  const getProducts = useCallback(async (category?: string): Promise<CatalogProduct[]> => {
    const lang = getLanguageCode();
    const params = new URLSearchParams();
    if (category) params.append('category', category);
    params.append('language_code', lang);
    
    try {
      const response: APIProductsResponse = await get(`/products?${params.toString()}`);
      const currency = response.currency || 'USD';
      const adapted = adaptProductList(response.products, currency);
      setProducts(adapted);
      return adapted;
    } catch (err) {
      console.error('Failed to fetch products:', err);
      return [];
    }
  }, [get]);

  const getProduct = useCallback(async (id: string): Promise<ProductDetailData | null> => {
    const lang = getLanguageCode();
    try {
      const response: APIProductResponse = await get(`/products/${id}?language_code=${lang}`);
      const currency = response.product?.currency || 'USD';
      return adaptProductDetail(response, currency);
    } catch (err) {
      console.error(`Failed to fetch product ${id}:`, err);
      return null;
    }
  }, [get]);

  return { products, getProducts, getProduct, loading, error };
}
