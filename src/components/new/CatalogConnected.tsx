/**
 * CatalogConnected
 *
 * Connected version of Catalog component with real API data.
 * Replaces mock data with live backend integration.
 */

import type React from "react";
import { memo, useCallback, useEffect, useRef, useState } from "react";
import { useLocaleContext } from "../../contexts/LocaleContext";
import { useProductsTyped } from "../../hooks/useApiTyped";
import { useLocale } from "../../hooks/useLocale";
import type { CatalogProduct } from "../../types/component";
import Catalog from "./Catalog";

interface CatalogConnectedProps {
  onSelectProduct?: (product: CatalogProduct) => void;
  onAddToCart?: (product: CatalogProduct, quantity: number) => void;
  onHaptic?: (type?: "light" | "medium") => void;
}

const CatalogConnected: React.FC<CatalogConnectedProps> = ({
  onSelectProduct,
  onAddToCart,
  onHaptic,
}) => {
  const { products, getProducts, loading, error } = useProductsTyped();
  const { locale, currency } = useLocaleContext();
  const { t } = useLocale();
  const [isInitialized, setIsInitialized] = useState(false);

  // Track previous locale/currency to detect actual changes
  const prevLocaleRef = useRef(locale);
  const prevCurrencyRef = useRef(currency);

  // Initial load - only once
  useEffect(() => {
    const init = async () => {
      await getProducts();
      setIsInitialized(true);
    };
    init();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [getProducts]); // Empty deps - run only on mount

  // Reload products ONLY when currency or language actually changes (not on initial mount)
  useEffect(() => {
    const localeChanged = prevLocaleRef.current !== locale;
    const currencyChanged = prevCurrencyRef.current !== currency;

    if (isInitialized && (localeChanged || currencyChanged)) {
      getProducts();
    }

    // Update refs after check
    prevLocaleRef.current = locale;
    prevCurrencyRef.current = currency;
  }, [locale, currency, isInitialized, getProducts]);

  const handleSelectProduct = useCallback(
    (product: CatalogProduct) => {
      if (onHaptic) {
        onHaptic("light");
      }
      if (onSelectProduct) {
        onSelectProduct(product);
      }
    },
    [onSelectProduct, onHaptic]
  );

  const handleAddToCart = useCallback(
    (product: CatalogProduct, quantity: number) => {
      if (onHaptic) {
        onHaptic("medium");
      }
      if (onAddToCart) {
        onAddToCart(product, quantity);
      }
    },
    [onAddToCart, onHaptic]
  );

  // Loading state
  if (!isInitialized || loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <div className="mx-auto mb-4 h-12 w-12 animate-spin rounded-full border-2 border-pandora-cyan border-t-transparent" />
          <div className="font-mono text-gray-500 text-xs uppercase tracking-widest">
            {t("common.loadingModules")}
          </div>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="max-w-md text-center">
          <div className="mb-4 text-6xl text-red-500">⚠</div>
          <div className="mb-2 font-mono text-red-400 text-sm">CONNECTION_ERROR</div>
          <p className="text-gray-500 text-sm">{error}</p>
          <button
            className="mt-6 border border-white/20 bg-white/10 px-6 py-2 font-mono text-white text-xs uppercase transition-colors hover:bg-white/20"
            onClick={() => getProducts()}
            type="button"
          >
            Retry Connection
          </button>
        </div>
      </div>
    );
  }

  return (
    <Catalog
      onAddToCart={handleAddToCart}
      onHaptic={onHaptic}
      onSelectProduct={handleSelectProduct}
      products={products}
    />
  );
};

export default memo(CatalogConnected);
