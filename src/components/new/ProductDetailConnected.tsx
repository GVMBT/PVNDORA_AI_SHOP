/**
 * ProductDetailConnected
 * 
 * Connected version of ProductDetail with real API data.
 * Fetches detailed product info and related products.
 */

import React, { useEffect, useState, useCallback, useRef } from 'react';
import ProductDetail from './ProductDetail';
import { useProductsTyped } from '../../hooks/useApiTyped';
import { useCart } from '../../contexts/CartContext';
import { useLocaleContext } from '../../contexts/LocaleContext';
import { useLocale } from '../../hooks/useLocale';
import { AudioEngine } from '../../lib/AudioEngine';
import { logger } from '../../utils/logger';
import type { CatalogProduct, ProductDetailData, ProductReview, ProductFile } from '../../types/component';

interface ProductDetailConnectedProps {
  productId: string;
  initialProduct?: CatalogProduct;
  onBack: () => void;
  onAddToCart?: (product: CatalogProduct, quantity: number) => void;
  onProductSelect?: (product: CatalogProduct) => void;
  isInCart?: boolean;
  onHaptic?: (type?: 'light' | 'medium' | 'success') => void;
}

const ProductDetailConnected: React.FC<ProductDetailConnectedProps> = ({
  productId,
  initialProduct,
  onBack,
  onAddToCart: onAddToCartProp,
  onProductSelect,
  isInCart = false,
  onHaptic,
}) => {
  const { getProduct, getProducts, loading, error } = useProductsTyped();
  const { addToCart } = useCart();
  const { locale, currency } = useLocaleContext();
  const { t } = useLocale();
  const [productData, setProductData] = useState<ProductDetailData | null>(null);
  const [relatedProducts, setRelatedProducts] = useState<CatalogProduct[]>([]);
  const [isInitialized, setIsInitialized] = useState(false);
  
  // Track previous locale/currency to detect actual changes
  const prevLocaleRef = useRef(locale);
  const prevCurrencyRef = useRef(currency);

  // Play product open sound when component mounts
  useEffect(() => {
    AudioEngine.resume();
    AudioEngine.productOpen();
  }, [productId]);

  const loadProductData = useCallback(async () => {
    // Fetch detailed product
    const detail = await getProduct(productId);
    if (detail) {
      setProductData(detail);
    }
    
    // Fetch related products
    const allProducts = await getProducts();
    const related = allProducts
      .filter(p => p.id !== productId)
      .sort(() => 0.5 - Math.random())
      .slice(0, 3);
    setRelatedProducts(related);
    
    setIsInitialized(true);
  }, [productId, getProduct, getProducts]);

  // Initial load and reload on productId change
  useEffect(() => {
    loadProductData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [productId]); // Only re-fetch when productId changes

  // Reload product ONLY when currency or language actually changes
  useEffect(() => {
    const localeChanged = prevLocaleRef.current !== locale;
    const currencyChanged = prevCurrencyRef.current !== currency;
    
    if (isInitialized && (localeChanged || currencyChanged)) {
      loadProductData();
    }
    
    // Update refs after check
    prevLocaleRef.current = locale;
    prevCurrencyRef.current = currency;
  }, [locale, currency, isInitialized, loadProductData]);

  const handleAddToCart = useCallback(async (product: CatalogProduct, quantity: number) => {
    if (onHaptic) onHaptic('medium');
    
    // If parent provides onAddToCart, use that (for local cart state)
    if (onAddToCartProp) {
      onAddToCartProp(product, quantity);
      return;
    }
    
    // Otherwise use cart API
    try {
      await addToCart(String(product.id), quantity);
      if (onHaptic) onHaptic('success');
    } catch (err) {
      logger.error('Failed to add to cart', err);
    }
  }, [addToCart, onHaptic, onAddToCartProp]);

  // Loading state - show skeleton or initial product
  if (!isInitialized) {
    // If we have initial product data, use it while loading detailed data
    if (initialProduct) {
      const tempProduct: ProductDetailData = {
        ...initialProduct,
        reviews: [] as ProductReview[],
        files: [] as ProductFile[],
        relatedProducts: [] as CatalogProduct[],
      };
      return (
        <ProductDetail
          product={tempProduct}
          onBack={onBack}
          onAddToCart={handleAddToCart}
          onProductSelect={onProductSelect}
          isInCart={isInCart}
          onHaptic={onHaptic}
        />
      );
    }
    
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-2 border-pandora-cyan border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <div className="font-mono text-xs text-gray-500 uppercase tracking-widest">
            {t('common.loadingModule')}
          </div>
        </div>
      </div>
    );
  }

  // Error state
  if (error || !productData) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center max-w-md">
          <div className="text-red-500 text-6xl mb-4">⚠</div>
          <div className="font-mono text-sm text-red-400 mb-2">{t('common.moduleNotFound')}</div>
          <p className="text-gray-500 text-sm">{t('common.failedToLoad')}</p>
          <button
            onClick={onBack}
            className="mt-6 px-6 py-2 bg-white/10 border border-white/20 text-white text-xs font-mono uppercase hover:bg-white/20 transition-colors"
          >
            {t('common.returnToCatalog')}
          </button>
        </div>
      </div>
    );
  }

  // Merge related products
  const fullProductData = {
    ...productData,
    relatedProducts,
  };

  return (
    <ProductDetail
      product={fullProductData}
      onBack={onBack}
      onAddToCart={handleAddToCart}
      onProductSelect={onProductSelect}
      isInCart={isInCart}
      onHaptic={onHaptic}
    />
  );
};

export default ProductDetailConnected;


