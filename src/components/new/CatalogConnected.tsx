/**
 * CatalogConnected
 * 
 * Connected version of Catalog component with real API data.
 * Replaces mock data with live backend integration.
 */

import React, { useEffect, useState, useCallback, memo } from 'react';
import Catalog from './Catalog';
import { useProductsTyped } from '../../hooks/useApiTyped';
import type { CatalogProduct } from '../../types/component';

interface CatalogConnectedProps {
  onSelectProduct?: (product: CatalogProduct) => void;
  onAddToCart?: (product: CatalogProduct, quantity: number) => void;
  onHaptic?: (type?: 'light' | 'medium') => void;
}

const CatalogConnected: React.FC<CatalogConnectedProps> = ({
  onSelectProduct,
  onAddToCart,
  onHaptic,
}) => {
  const { products, getProducts, loading, error } = useProductsTyped();
  const [isInitialized, setIsInitialized] = useState(false);

  useEffect(() => {
    const init = async () => {
      await getProducts();
      setIsInitialized(true);
    };
    init();
  }, [getProducts]);

  const handleSelectProduct = useCallback((product: CatalogProduct) => {
    if (onHaptic) onHaptic('light');
    if (onSelectProduct) onSelectProduct(product);
  }, [onSelectProduct, onHaptic]);

  const handleAddToCart = useCallback((product: CatalogProduct, quantity: number) => {
    if (onHaptic) onHaptic('medium');
    if (onAddToCart) onAddToCart(product, quantity);
  }, [onAddToCart, onHaptic]);

  // Loading state
  if (!isInitialized || loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-2 border-pandora-cyan border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <div className="font-mono text-xs text-gray-500 uppercase tracking-widest">
            Loading Modules...
          </div>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center max-w-md">
          <div className="text-red-500 text-6xl mb-4">⚠</div>
          <div className="font-mono text-sm text-red-400 mb-2">CONNECTION_ERROR</div>
          <p className="text-gray-500 text-sm">{error}</p>
          <button
            onClick={() => getProducts()}
            className="mt-6 px-6 py-2 bg-white/10 border border-white/20 text-white text-xs font-mono uppercase hover:bg-white/20 transition-colors"
          >
            Retry Connection
          </button>
        </div>
      </div>
    );
  }

  return (
    <Catalog
      products={products}
      onSelectProduct={handleSelectProduct}
      onAddToCart={handleAddToCart}
      onHaptic={onHaptic}
    />
  );
};

export default memo(CatalogConnected);
