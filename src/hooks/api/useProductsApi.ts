/**
 * Products API Hook
 * 
 * Type-safe hook for fetching products with automatic data transformation.
 */

import { useState, useCallback } from 'react';
import { useApi } from '../useApi';
import { useLocaleContext } from '../../contexts/LocaleContext';
import { logger } from '../../utils/logger';
import type { APIProductsResponse, APIProductResponse } from '../../types/api';
import type { CatalogProduct, ProductDetailData } from '../../types/component';
import { adaptProductList, adaptProductDetail } from '../../adapters';

export function useProductsTyped() {
  const { get, loading, error } = useApi();
  const { locale, currency } = useLocaleContext();
  const [products, setProducts] = useState<CatalogProduct[]>([]);

  const getProducts = useCallback(async (category?: string): Promise<CatalogProduct[]> => {
    const params = new URLSearchParams();
    if (category) params.append('category', category);
    params.append('language_code', locale);
    params.append('currency', currency); // Pass currency explicitly
    
    try {
      const response: APIProductsResponse = await get(`/products?${params.toString()}`);
      const responseCurrency = response.currency || currency;
      const adapted = adaptProductList(response.products, responseCurrency);
      setProducts(adapted);
      return adapted;
    } catch (err) {
      logger.error('Failed to fetch products', err);
      return [];
    }
  }, [get, locale, currency]);

  const getProduct = useCallback(async (id: string): Promise<ProductDetailData | null> => {
    try {
      const response: APIProductResponse = await get(`/products/${id}?language_code=${locale}&currency=${currency}`); // Pass currency explicitly
      const responseCurrency = response.product?.currency || currency;
      return adaptProductDetail(response, responseCurrency);
    } catch (err) {
      logger.error(`Failed to fetch product ${id}`, err);
      return null;
    }
  }, [get, locale, currency]);

  return { products, getProducts, getProduct, loading, error };
}
