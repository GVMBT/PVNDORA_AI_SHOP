/**
 * AdminCatalog Component
 *
 * Catalog management view for products.
 */

import { AnimatePresence, motion } from "framer-motion";
import { Check, ChevronDown, Edit, Filter, Plus, Search, Trash2, X } from "lucide-react";
import type React from "react";
import { memo, useEffect, useMemo, useRef, useState } from "react";
import { PRODUCT_CATEGORIES, PRODUCT_CATEGORY_LABELS } from "../../constants";
import StockIndicator from "./StockIndicator";
import type { ProductData } from "./types";

interface AdminCatalogProps {
  products: ProductData[];
  onEditProduct: (product: ProductData) => void;
  onNewProduct: () => void;
  onDeleteProduct?: (productId: string) => void;
}

const AdminCatalog: React.FC<AdminCatalogProps> = ({
  products,
  onEditProduct,
  onNewProduct,
  onDeleteProduct,
}) => {
  const [searchQuery, setSearchQuery] = useState("");
  const [activeCategory, setActiveCategory] = useState<string>("All");
  const [isCategoryDrawerOpen, setIsCategoryDrawerOpen] = useState(false);
  const categoryDropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside (desktop only)
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        categoryDropdownRef.current &&
        !categoryDropdownRef.current.contains(event.target as Node) &&
        globalThis.innerWidth >= 768 // Only for desktop
      ) {
        setIsCategoryDrawerOpen(false);
      }
    };

    if (isCategoryDrawerOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isCategoryDrawerOpen]);

  // Filter products by search and category
  const filteredProducts = useMemo(() => {
    let result = products;

    // Search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      result = result.filter(
        (p) =>
          p.name.toLowerCase().includes(query) ||
          p.category.toLowerCase().includes(query) ||
          p.id.toString().includes(query)
      );
    }

    // Category filter
    if (activeCategory !== "All") {
      result = result.filter((p) => p.category.toLowerCase() === activeCategory.toLowerCase());
    }

    return result;
  }, [products, searchQuery, activeCategory]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row justify-between items-center gap-4 bg-[#0e0e0e] border border-white/10 p-4 rounded-sm">
        <div className="flex flex-col md:flex-row gap-4 w-full md:w-auto">
          <div className="relative w-full md:w-64">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" size={14} />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search SKU..."
              className="w-full bg-black border border-white/20 pl-9 pr-4 py-2 text-xs font-mono text-white focus:border-pandora-cyan outline-none"
            />
          </div>

          {/* Category Filter Button (Mobile Drawer Trigger) */}
          <div className="relative md:hidden w-full">
            <button
              onClick={() => setIsCategoryDrawerOpen(true)}
              className="w-full flex items-center justify-between gap-2 bg-black border border-white/20 px-4 py-2 text-xs font-mono text-white hover:border-pandora-cyan transition-colors"
            >
              <div className="flex items-center gap-2">
                <Filter size={14} />
                <span>Category: {PRODUCT_CATEGORY_LABELS[activeCategory] || activeCategory}</span>
              </div>
              <ChevronDown size={14} />
            </button>
          </div>

          {/* Category Filter Dropdown (Desktop) */}
          <div ref={categoryDropdownRef} className="hidden md:block relative">
            <button
              onClick={() => setIsCategoryDrawerOpen(!isCategoryDrawerOpen)}
              className="flex items-center justify-between gap-2 bg-black border border-white/20 px-4 py-2 text-xs font-mono text-white hover:border-pandora-cyan transition-colors min-w-[160px]"
            >
              <div className="flex items-center gap-2">
                <Filter size={14} />
                <span>{PRODUCT_CATEGORY_LABELS[activeCategory] || activeCategory}</span>
              </div>
              <ChevronDown
                size={14}
                className={`transition-transform ${isCategoryDrawerOpen ? "rotate-180" : ""}`}
              />
            </button>

            <AnimatePresence>
              {isCategoryDrawerOpen && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className="absolute top-full left-0 right-0 mt-2 bg-[#0a0a0a] border border-white/20 z-50 shadow-xl"
                  onClick={(e) => e.stopPropagation()}
                >
                  {PRODUCT_CATEGORIES.map((cat) => (
                    <button
                      key={cat}
                      onClick={() => {
                        setActiveCategory(cat);
                        setIsCategoryDrawerOpen(false);
                      }}
                      className="w-full text-left px-4 py-2 text-xs font-mono hover:bg-white/10 hover:text-pandora-cyan flex items-center justify-between"
                    >
                      <span>{PRODUCT_CATEGORY_LABELS[cat] || cat}</span>
                      {activeCategory === cat && <Check size={12} className="text-pandora-cyan" />}
                    </button>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>

        <button
          onClick={onNewProduct}
          className="w-full md:w-auto flex items-center justify-center gap-2 bg-pandora-cyan text-black px-4 py-2 text-xs font-bold uppercase hover:bg-white transition-colors"
        >
          <Plus size={14} /> Add Product
        </button>
      </div>

      {/* Mobile Category Drawer */}
      <AnimatePresence>
        {isCategoryDrawerOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/80 z-50 md:hidden"
              onClick={() => setIsCategoryDrawerOpen(false)}
            />
            <motion.div
              initial={{ x: "100%" }}
              animate={{ x: 0 }}
              exit={{ x: "100%" }}
              transition={{ type: "spring", damping: 25, stiffness: 200 }}
              className="fixed right-0 top-0 bottom-0 w-80 bg-[#0a0a0a] border-l border-white/20 z-50 md:hidden shadow-2xl"
            >
              <div className="p-4 border-b border-white/10 flex items-center justify-between">
                <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                  Filter by Category
                </h3>
                <button
                  onClick={() => setIsCategoryDrawerOpen(false)}
                  className="text-gray-400 hover:text-white"
                >
                  <X size={20} />
                </button>
              </div>
              <div className="p-4 space-y-1 overflow-y-auto max-h-[calc(100vh-80px)]">
                {PRODUCT_CATEGORIES.map((cat) => (
                  <button
                    key={cat}
                    onClick={() => {
                      setActiveCategory(cat);
                      setIsCategoryDrawerOpen(false);
                    }}
                    className={`w-full text-left px-4 py-3 text-sm font-mono rounded-sm transition-colors flex items-center justify-between ${
                      activeCategory === cat
                        ? "bg-pandora-cyan/20 text-pandora-cyan border border-pandora-cyan/50"
                        : "text-gray-300 hover:bg-white/10 hover:text-white"
                    }`}
                  >
                    <span>{PRODUCT_CATEGORY_LABELS[cat] || cat}</span>
                    {activeCategory === cat && <Check size={16} className="text-pandora-cyan" />}
                  </button>
                ))}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Desktop Table */}
      <div className="hidden md:block bg-[#0e0e0e] border border-white/10 rounded-sm overflow-hidden">
        <table className="w-full text-left text-xs font-mono">
          <thead className="bg-white/5 text-gray-400 uppercase">
            <tr>
              <th className="p-4">Name</th>
              <th className="p-4">Category</th>
              <th className="p-4">Price / MSRP</th>
              <th className="p-4">Stock</th>
              <th className="p-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5 text-gray-300">
            {filteredProducts.length === 0 ? (
              <tr>
                <td colSpan={5} className="p-8 text-center text-gray-500">
                  No products found
                </td>
              </tr>
            ) : (
              filteredProducts.map((p) => (
                <tr key={p.id} className="hover:bg-white/5 transition-colors">
                  <td className="p-4 font-bold text-white flex items-center gap-3">
                    <div className="w-8 h-8 rounded-sm overflow-hidden bg-black border border-white/10">
                      <img src={p.image} alt="" className="w-full h-full object-cover" />
                    </div>
                    {p.name}
                  </td>
                  <td className="p-4">
                    <span className="text-[10px] bg-white/5 px-2 py-1 rounded">
                      {PRODUCT_CATEGORY_LABELS[p.category] || p.category}
                    </span>
                  </td>
                  <td className="p-4">
                    {/* Display price: use anchor price for RUB if available, otherwise show USD base price */}
                    {(() => {
                      // Check if anchor price for RUB exists
                      const hasAnchorPrice =
                        p.prices && typeof p.prices === "object" && "RUB" in p.prices;
                      const displayPrice = hasAnchorPrice ? p.prices.RUB : p.price;
                      const displayCurrency = hasAnchorPrice ? "₽" : "$";
                      const isAnchor = hasAnchorPrice;

                      return (
                        <div className={isAnchor ? "text-blue-400" : "text-white"}>
                          {displayPrice} {displayCurrency}
                          {!isAnchor && (
                            <span className="text-[9px] text-gray-600 ml-1">(USD)</span>
                          )}
                        </div>
                      );
                    })()}
                    {/* Display MSRP: use anchor MSRP for RUB if available, otherwise show USD base MSRP */}
                    {(() => {
                      const hasAnchorMsrp =
                        p.msrp_prices &&
                        typeof p.msrp_prices === "object" &&
                        "RUB" in p.msrp_prices;
                      const displayMsrp = hasAnchorMsrp ? p.msrp_prices.RUB : p.msrp;
                      const currentPrice =
                        p.prices && typeof p.prices === "object" && "RUB" in p.prices
                          ? p.prices.RUB
                          : p.price;

                      // Only show MSRP if it's greater than current price
                      if (!displayMsrp || displayMsrp <= currentPrice) return null;

                      const displayCurrency = hasAnchorMsrp ? "₽" : "$";
                      return (
                        <div className="text-[10px] text-gray-500 line-through">
                          {displayMsrp} {displayCurrency}
                        </div>
                      );
                    })()}
                  </td>
                  <td className="p-4">
                    <StockIndicator stock={p.stock} />
                  </td>
                  <td className="p-4 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => onEditProduct(p)}
                        className="hover:text-pandora-cyan p-1"
                        title="Edit"
                      >
                        <Edit size={14} />
                      </button>
                      {onDeleteProduct && (
                        <button
                          onClick={() => {
                            if (globalThis.confirm(`Delete "${p.name}"?`)) {
                              onDeleteProduct(String(p.id));
                            }
                          }}
                          className="hover:text-red-400 p-1 text-gray-500"
                          title="Delete"
                        >
                          <Trash2 size={14} />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Mobile Cards */}
      <div className="md:hidden space-y-4">
        {filteredProducts.length === 0 ? (
          <div className="bg-[#0e0e0e] border border-white/10 p-8 text-center text-gray-500">
            No products found
          </div>
        ) : (
          filteredProducts.map((p) => (
            <div
              key={p.id}
              className="bg-[#0e0e0e] border border-white/10 p-4 flex justify-between items-center"
            >
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-sm overflow-hidden bg-black border border-white/10 shrink-0">
                  <img src={p.image} alt="" className="w-full h-full object-cover" />
                </div>
                <div>
                  <div className="font-bold text-white mb-1">{p.name}</div>
                  <div className="text-xs text-gray-500 mb-2">
                    {PRODUCT_CATEGORY_LABELS[p.category] || p.category} • {(() => {
                      const hasAnchorPrice =
                        p.prices && typeof p.prices === "object" && "RUB" in p.prices;
                      const displayPrice = hasAnchorPrice ? p.prices.RUB : p.price;
                      const displayCurrency = hasAnchorPrice ? "₽" : "$";
                      return `${displayPrice} ${displayCurrency}`;
                    })()}
                  </div>
                  <StockIndicator stock={p.stock} />
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => onEditProduct(p)}
                  className="p-2 border border-white/10 rounded-full text-gray-400 hover:text-white hover:border-pandora-cyan"
                  title="Edit"
                >
                  <Edit size={16} />
                </button>
                {onDeleteProduct && (
                  <button
                    onClick={() => {
                      if (globalThis.confirm(`Delete "${p.name}"?`)) {
                        onDeleteProduct(String(p.id));
                      }
                    }}
                    className="p-2 border border-white/10 rounded-full text-gray-400 hover:text-red-400 hover:border-red-400"
                    title="Delete"
                  >
                    <Trash2 size={16} />
                  </button>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default memo(AdminCatalog);
