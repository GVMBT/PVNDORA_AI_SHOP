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
      <div className="flex flex-col items-center justify-between gap-4 rounded-sm border border-white/10 bg-[#0e0e0e] p-4 md:flex-row">
        <div className="flex w-full flex-col gap-4 md:w-auto md:flex-row">
          <div className="relative w-full md:w-64">
            <Search className="absolute top-1/2 left-3 -translate-y-1/2 text-gray-500" size={14} />
            <input
              className="w-full border border-white/20 bg-black py-2 pr-4 pl-9 font-mono text-white text-xs outline-none focus:border-pandora-cyan"
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search SKU..."
              type="text"
              value={searchQuery}
            />
          </div>

          {/* Category Filter Button (Mobile Drawer Trigger) */}
          <div className="relative w-full md:hidden">
            <button
              className="flex w-full items-center justify-between gap-2 border border-white/20 bg-black px-4 py-2 font-mono text-white text-xs transition-colors hover:border-pandora-cyan"
              onClick={() => setIsCategoryDrawerOpen(true)}
              type="button"
            >
              <div className="flex items-center gap-2">
                <Filter size={14} />
                <span>Category: {PRODUCT_CATEGORY_LABELS[activeCategory] || activeCategory}</span>
              </div>
              <ChevronDown size={14} />
            </button>
          </div>

          {/* Category Filter Dropdown (Desktop) */}
          <div className="relative hidden md:block" ref={categoryDropdownRef}>
            <button
              className="flex min-w-[160px] items-center justify-between gap-2 border border-white/20 bg-black px-4 py-2 font-mono text-white text-xs transition-colors hover:border-pandora-cyan"
              onClick={() => setIsCategoryDrawerOpen(!isCategoryDrawerOpen)}
              type="button"
            >
              <div className="flex items-center gap-2">
                <Filter size={14} />
                <span>{PRODUCT_CATEGORY_LABELS[activeCategory] || activeCategory}</span>
              </div>
              <ChevronDown
                className={`transition-transform ${isCategoryDrawerOpen ? "rotate-180" : ""}`}
                size={14}
              />
            </button>

            <AnimatePresence>
              {isCategoryDrawerOpen && (
                <motion.div
                  animate={{ opacity: 1, y: 0 }}
                  className="absolute top-full right-0 left-0 z-50 mt-2 border border-white/20 bg-[#0a0a0a] shadow-xl"
                  exit={{ opacity: 0, y: -10 }}
                  initial={{ opacity: 0, y: -10 }}
                  onClick={(e) => e.stopPropagation()}
                >
                  {PRODUCT_CATEGORIES.map((cat) => (
                    <button
                      className="flex w-full items-center justify-between px-4 py-2 text-left font-mono text-xs hover:bg-white/10 hover:text-pandora-cyan"
                      key={cat}
                      onClick={() => {
                        setActiveCategory(cat);
                        setIsCategoryDrawerOpen(false);
                      }}
                      type="button"
                    >
                      <span>{PRODUCT_CATEGORY_LABELS[cat] || cat}</span>
                      {activeCategory === cat && <Check className="text-pandora-cyan" size={12} />}
                    </button>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>

        <button
          className="flex w-full items-center justify-center gap-2 bg-pandora-cyan px-4 py-2 font-bold text-black text-xs uppercase transition-colors hover:bg-white md:w-auto"
          onClick={onNewProduct}
          type="button"
        >
          <Plus size={14} /> Add Product
        </button>
      </div>

      {/* Mobile Category Drawer */}
      <AnimatePresence>
        {isCategoryDrawerOpen && (
          <>
            <motion.div
              animate={{ opacity: 1 }}
              className="fixed inset-0 z-50 bg-black/80 md:hidden"
              exit={{ opacity: 0 }}
              initial={{ opacity: 0 }}
              onClick={() => setIsCategoryDrawerOpen(false)}
            />
            <motion.div
              animate={{ x: 0 }}
              className="fixed top-0 right-0 bottom-0 z-50 w-80 border-white/20 border-l bg-[#0a0a0a] shadow-2xl md:hidden"
              exit={{ x: "100%" }}
              initial={{ x: "100%" }}
              transition={{ type: "spring", damping: 25, stiffness: 200 }}
            >
              <div className="flex items-center justify-between border-white/10 border-b p-4">
                <h3 className="font-bold text-sm text-white uppercase tracking-wider">
                  Filter by Category
                </h3>
                <button
                  className="text-gray-400 hover:text-white"
                  onClick={() => setIsCategoryDrawerOpen(false)}
                  type="button"
                >
                  <X size={20} />
                </button>
              </div>
              <div className="max-h-[calc(100vh-80px)] space-y-1 overflow-y-auto p-4">
                {PRODUCT_CATEGORIES.map((cat) => (
                  <button
                    className={`flex w-full items-center justify-between rounded-sm px-4 py-3 text-left font-mono text-sm transition-colors ${
                      activeCategory === cat
                        ? "border border-pandora-cyan/50 bg-pandora-cyan/20 text-pandora-cyan"
                        : "text-gray-300 hover:bg-white/10 hover:text-white"
                    }`}
                    key={cat}
                    onClick={() => {
                      setActiveCategory(cat);
                      setIsCategoryDrawerOpen(false);
                    }}
                    type="button"
                  >
                    <span>{PRODUCT_CATEGORY_LABELS[cat] || cat}</span>
                    {activeCategory === cat && <Check className="text-pandora-cyan" size={16} />}
                  </button>
                ))}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Desktop Table */}
      <div className="hidden overflow-hidden rounded-sm border border-white/10 bg-[#0e0e0e] md:block">
        <table className="w-full text-left font-mono text-xs">
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
                <td className="p-8 text-center text-gray-500" colSpan={5}>
                  No products found
                </td>
              </tr>
            ) : (
              filteredProducts.map((p) => (
                <tr className="transition-colors hover:bg-white/5" key={p.id}>
                  <td className="flex items-center gap-3 p-4 font-bold text-white">
                    <div className="h-8 w-8 overflow-hidden rounded-sm border border-white/10 bg-black">
                      <img alt="" className="h-full w-full object-cover" src={p.image} />
                    </div>
                    {p.name}
                  </td>
                  <td className="p-4">
                    <span className="rounded bg-white/5 px-2 py-1 text-[10px]">
                      {PRODUCT_CATEGORY_LABELS[p.category] || p.category}
                    </span>
                  </td>
                  <td className="p-4">
                    {/* All prices are in RUB after migration */}
                    <div className="text-white">{p.price} ₽</div>
                    {/* MSRP (strikethrough) */}
                    {p.msrp && p.msrp > p.price && (
                      <div className="text-[10px] text-gray-500 line-through">{p.msrp} ₽</div>
                    )}
                  </td>
                  <td className="p-4">
                    <StockIndicator stock={p.stock} />
                  </td>
                  <td className="p-4 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        className="p-1 hover:text-pandora-cyan"
                        onClick={() => onEditProduct(p)}
                        title="Edit"
                        type="button"
                      >
                        <Edit size={14} />
                      </button>
                      {onDeleteProduct && (
                        <button
                          className="p-1 text-gray-500 hover:text-red-400"
                          onClick={() => {
                            if (globalThis.confirm(`Delete "${p.name}"?`)) {
                              onDeleteProduct(String(p.id));
                            }
                          }}
                          title="Delete"
                          type="button"
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
      <div className="space-y-4 md:hidden">
        {filteredProducts.length === 0 ? (
          <div className="border border-white/10 bg-[#0e0e0e] p-8 text-center text-gray-500">
            No products found
          </div>
        ) : (
          filteredProducts.map((p) => (
            <div
              className="flex items-center justify-between border border-white/10 bg-[#0e0e0e] p-4"
              key={p.id}
            >
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 shrink-0 overflow-hidden rounded-sm border border-white/10 bg-black">
                  <img alt="" className="h-full w-full object-cover" src={p.image} />
                </div>
                <div>
                  <div className="mb-1 font-bold text-white">{p.name}</div>
                  <div className="mb-2 text-gray-500 text-xs">
                    {PRODUCT_CATEGORY_LABELS[p.category] || p.category} • {p.price} ₽
                  </div>
                  <StockIndicator stock={p.stock} />
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  className="rounded-full border border-white/10 p-2 text-gray-400 hover:border-pandora-cyan hover:text-white"
                  onClick={() => onEditProduct(p)}
                  title="Edit"
                  type="button"
                >
                  <Edit size={16} />
                </button>
                {onDeleteProduct && (
                  <button
                    className="rounded-full border border-white/10 p-2 text-gray-400 hover:border-red-400 hover:text-red-400"
                    onClick={() => {
                      if (globalThis.confirm(`Delete "${p.name}"?`)) {
                        onDeleteProduct(String(p.id));
                      }
                    }}
                    title="Delete"
                    type="button"
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
