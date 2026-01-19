import { AnimatePresence, motion } from "framer-motion";
import { Check, ChevronDown, Cpu, Grid, List, Search } from "lucide-react";
import type React from "react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { type AvailabilityFilter, PRODUCT_CATEGORIES } from "../../constants";
import { useLocale } from "../../hooks/useLocale";
import { formatPrice } from "../../utils/currency";
import ProductCard from "./ProductCard";

type SortOption = "popular" | "price_asc" | "price_desc";
type ViewMode = "grid" | "list";

// Product availability status (derived from API)
type ProductAvailability = "available" | "on_demand" | "discontinued" | "coming_soon";

// Type for product data (matches CatalogProduct from types/component)
interface ProductData {
  id: string | number;
  name: string;
  category: string;
  categories?: string[];
  price: number;
  msrp?: number;
  currency: string;
  description: string;
  warranty: number;
  duration?: number;
  instructions?: string;
  image: string;
  popular: boolean;
  stock: number;
  fulfillment: number;
  sold: number;
  video?: string;
  sku: string;
  version?: string;
  status?: ProductAvailability;
  can_fulfill_on_demand?: boolean;
}

interface CatalogProps {
  products?: ProductData[];
  onSelectProduct?: (product: ProductData) => void;
  onAddToCart?: (product: ProductData, quantity: number) => void;
  onHaptic?: (type?: "light" | "medium") => void;
}

// Utility for fake hex stream
// Decorative hex codes - static IDs used since items never reorder
const HEX_IDS = ["h0", "h1", "h2", "h3", "h4", "h5", "h6", "h7"] as const;
// Static hex values for decorative display (not security-critical)
const STATIC_HEX_VALUES = ["A3F2", "B7E1", "C9D4", "D2A8", "E5B3", "F1C7", "A8D9", "B4E6"] as const;

const _HexStream = () => {
  return (
    <div className="flex flex-col font-mono text-[8px] text-pandora-cyan/60 leading-tight opacity-50">
      {HEX_IDS.map((id, index) => (
        <span key={id}>0x{STATIC_HEX_VALUES[index]}</span>
      ))}
    </div>
  );
};

const Catalog: React.FC<CatalogProps> = ({
  products: propProducts,
  onSelectProduct,
  onAddToCart,
  onHaptic,
}) => {
  const { t, tEn } = useLocale();
  const [searchQuery, setSearchQuery] = useState("");
  const [activeCategory, setActiveCategory] = useState("All");
  const [activeAvailability, setActiveAvailability] = useState<AvailabilityFilter>("All");
  const [viewMode, setViewMode] = useState<ViewMode>("grid");
  const [sortBy, setSortBy] = useState<SortOption>("popular");
  const [isSortOpen, setIsSortOpen] = useState(false);
  const [isAvailabilityOpen, setIsAvailabilityOpen] = useState(false);

  // Refs for dropdown containers
  const availabilityRef = useRef<HTMLDivElement>(null);
  const sortRef = useRef<HTMLDivElement>(null);

  // Flag to prevent immediate close after toggle
  const justToggledRef = useRef(false);

  // Close dropdowns on outside click
  // Using 'click' event (fires after pointerdown) to avoid race conditions with toggle buttons
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent | TouchEvent) => {
      // Skip if we just toggled
      if (justToggledRef.current) {
        justToggledRef.current = false;
        return;
      }

      const target = event.target as HTMLElement;

      // Skip if target is within either dropdown
      if (availabilityRef.current?.contains(target) || sortRef.current?.contains(target)) {
        return;
      }

      // Close both dropdowns
      setIsAvailabilityOpen(false);
      setIsSortOpen(false);
    };

    // Use both click and touchend for comprehensive coverage
    document.addEventListener("click", handleClickOutside, true);
    document.addEventListener("touchend", handleClickOutside, true);
    return () => {
      document.removeEventListener("click", handleClickOutside, true);
      document.removeEventListener("touchend", handleClickOutside, true);
    };
  }, []);

  // Use provided products or empty array (no mock data fallback)
  const productsData = propProducts || [];

  // Helper to derive availability from product data - wrapped in useCallback for stable reference
  const getProductAvailability = useCallback((product: ProductData): ProductAvailability => {
    if (product.status) return product.status;
    // Fallback logic for products without status
    if (product.stock > 0) return "available";
    if (product.can_fulfill_on_demand || product.fulfillment > 0) return "on_demand";
    return "discontinued";
  }, []);

  const filteredProducts = useMemo(() => {
    let result = productsData.filter((product) => {
      // Search filter
      const matchesSearch = product.name.toLowerCase().includes(searchQuery.toLowerCase());

      // Category filter
      const categories = product.categories || [product.category].filter(Boolean);
      const matchesCategory =
        activeCategory === "All" ||
        categories.some((c) => c.toLowerCase() === activeCategory.toLowerCase());

      // Availability filter
      const availability = getProductAvailability(product);
      let matchesAvailability = activeAvailability === "All";
      if (activeAvailability === "Available") matchesAvailability = availability === "available";
      if (activeAvailability === "On Demand") matchesAvailability = availability === "on_demand";
      if (activeAvailability === "Discontinued")
        matchesAvailability = availability === "discontinued" || availability === "coming_soon";

      return matchesSearch && matchesCategory && matchesAvailability;
    });

    // Sorting Logic
    result = result.sort((a, b) => {
      if (sortBy === "price_asc") return a.price - b.price;
      if (sortBy === "price_desc") return b.price - a.price;
      // Default: Popular (Items with popular:true come first)
      if (a.popular === b.popular) return 0;
      return a.popular ? -1 : 1;
    });

    return result;
  }, [
    productsData,
    searchQuery,
    activeCategory,
    activeAvailability,
    sortBy,
    getProductAvailability,
  ]);

  const handleCategoryChange = (cat: string) => {
    if (onHaptic) onHaptic("light");
    setActiveCategory(cat);
  };

  const handleProductClick = (product: ProductData) => {
    if (onHaptic) onHaptic("medium");
    if (onSelectProduct) onSelectProduct(product);
  };

  const handleAddToCart = (product: ProductData, quantity = 1) => {
    if (onHaptic) onHaptic("medium");
    if (onAddToCart) onAddToCart(product, quantity);
  };

  return (
    <section
      className="relative z-30 min-h-screen w-full bg-transparent px-6 pt-24 pb-24 text-white md:-mt-24 md:pt-32 md:pl-28"
      id="catalog"
    >
      {/* === VISUAL CONNECTOR (DATA STREAM) FROM HERO === */}
      <div className="absolute top-0 left-1/2 z-0 h-20 w-px -translate-x-1/2 bg-gradient-to-b from-transparent via-pandora-cyan/30 to-transparent opacity-50" />

      {/* --- HEADER ROW --- */}
      <div className="relative z-10 mx-auto mb-10 flex max-w-7xl flex-col items-start justify-between gap-6 pt-8 xl:flex-row xl:items-end">
        {/* Title Area: NARRATIVE UPDATE (Techno/Module) */}
        <div>
          <h2 className="mb-2 flex items-center gap-3 font-bold font-display text-3xl text-white">
            <span className="block h-8 w-2 rounded-sm bg-pandora-cyan shadow-[0_0_10px_#00FFFF]" />
            {tEn("catalog.pageTitle")}
          </h2>
          <p className="flex items-center gap-2 font-mono text-gray-500 text-xs uppercase tracking-widest">
            <Cpu className="text-pandora-cyan" size={12} />
            <span>{t("catalog.header.source")}</span>
            <span className="text-gray-700">|</span>
            <span className="text-pandora-cyan">{t("catalog.header.status")}</span>
          </p>
        </div>

        {/* Controls Area */}
        <div className="flex w-full flex-col gap-4 md:flex-row xl:w-auto">
          {/* Search Input */}
          <div className="group relative flex-grow md:w-80">
            <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-4">
              <Search className="h-4 w-4 text-gray-500 transition-colors group-focus-within:text-pandora-cyan" />
            </div>
            <input
              className="w-full rounded-sm border border-white/10 bg-[#0a0a0a] py-3 pr-4 pl-10 font-mono text-sm text-white uppercase tracking-wider transition-all placeholder:text-gray-600 focus:border-pandora-cyan/50 focus:bg-[#0f0f0f] focus:outline-none"
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder={t("catalog.search")}
              type="text"
              value={searchQuery}
            />
          </div>

          <div className="scrollbar-hide -mb-2 flex gap-2 overflow-x-auto pb-2 sm:gap-4">
            {/* Availability Filter Dropdown */}
            <div className="relative z-50 flex-shrink-0" ref={availabilityRef}>
              <button
                className="flex h-full min-w-fit touch-manipulation select-none items-center gap-2 whitespace-nowrap rounded-sm border border-white/10 bg-[#0a0a0a] px-3 py-2 font-mono text-gray-300 text-sm transition-all hover:border-pandora-cyan/50 sm:px-4"
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  justToggledRef.current = true;
                  if (onHaptic) onHaptic("light");
                  setIsAvailabilityOpen((prev) => !prev);
                  setIsSortOpen(false);
                }}
                type="button"
              >
                <span className="overflow-visible text-[9px] uppercase tracking-wider sm:text-[10px]">
                  {activeAvailability === "All" &&
                    `${t("catalog.availability.label")}: ${t("catalog.availability.all")}`}
                  {activeAvailability === "Available" &&
                    `${t("catalog.availability.label")}: ${t("catalog.availability.available")}`}
                  {activeAvailability === "On Demand" &&
                    `${t("catalog.availability.label")}: ${t("catalog.availability.onDemand")}`}
                  {activeAvailability === "Discontinued" &&
                    `${t("catalog.availability.label")}: ${t("catalog.availability.discontinued")}`}
                </span>
                <ChevronDown
                  className={`flex-shrink-0 transition-transform ${isAvailabilityOpen ? "rotate-180" : ""}`}
                  size={14}
                />
              </button>

              <AnimatePresence>
                {isAvailabilityOpen && (
                  <motion.div
                    animate={{ opacity: 1, y: 0 }}
                    className="absolute top-full left-0 z-[100] mt-2 w-fit min-w-full border border-white/20 bg-[#0a0a0a] shadow-black/80 shadow-xl"
                    exit={{ opacity: 0, y: -10 }}
                    initial={{ opacity: 0, y: -10 }}
                    onClick={(e) => e.stopPropagation()}
                  >
                    {[
                      {
                        label: t("catalog.availability.all"),
                        value: "All",
                        color: "text-gray-400",
                      },
                      {
                        label: t("catalog.availability.available"),
                        value: "Available",
                        color: "text-green-400",
                      },
                      {
                        label: t("catalog.availability.onDemand"),
                        value: "On Demand",
                        color: "text-yellow-400",
                      },
                      {
                        label: t("catalog.availability.discontinued"),
                        value: "Discontinued",
                        color: "text-red-400",
                      },
                    ].map((option) => (
                      <button
                        className="flex w-full select-none items-center justify-between whitespace-nowrap px-4 py-3 text-left font-mono text-[10px] uppercase hover:bg-white/10 hover:text-pandora-cyan"
                        key={option.value}
                        onClick={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          justToggledRef.current = true;
                          if (onHaptic) onHaptic("light");
                          setActiveAvailability(option.value as AvailabilityFilter);
                          setIsAvailabilityOpen(false);
                        }}
                        type="button"
                      >
                        <span className={`${option.color} overflow-visible`}>{option.label}</span>
                        {activeAvailability === option.value && (
                          <Check className="text-pandora-cyan" size={12} />
                        )}
                      </button>
                    ))}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* Sort Dropdown */}
            <div className="relative z-50 flex-shrink-0" ref={sortRef}>
              <button
                className="flex h-full touch-manipulation select-none items-center gap-2 whitespace-nowrap rounded-sm border border-white/10 bg-[#0a0a0a] px-3 py-2 font-mono text-gray-300 text-sm transition-all hover:border-pandora-cyan/50 sm:px-4"
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  justToggledRef.current = true;
                  if (onHaptic) onHaptic("light");
                  setIsSortOpen((prev) => !prev);
                  setIsAvailabilityOpen(false);
                }}
                type="button"
              >
                <span className="text-[9px] uppercase tracking-wider sm:text-[10px]">
                  {sortBy === "popular" &&
                    `${t("catalog.sort.label")}: ${t("catalog.sort.popularity")}`}
                  {sortBy === "price_asc" &&
                    `${t("catalog.sort.label")}: ${t("catalog.sort.priceAsc")}`}
                  {sortBy === "price_desc" &&
                    `${t("catalog.sort.label")}: ${t("catalog.sort.priceDesc")}`}
                </span>
                <ChevronDown
                  className={`flex-shrink-0 transition-transform ${isSortOpen ? "rotate-180" : ""}`}
                  size={14}
                />
              </button>

              <AnimatePresence>
                {isSortOpen && (
                  <motion.div
                    animate={{ opacity: 1, y: 0 }}
                    className="absolute top-full left-0 z-[100] mt-2 w-fit min-w-full border border-white/20 bg-[#0a0a0a] shadow-black/80 shadow-xl"
                    exit={{ opacity: 0, y: -10 }}
                    initial={{ opacity: 0, y: -10 }}
                    onClick={(e) => e.stopPropagation()}
                  >
                    {[
                      { label: t("catalog.sort.popularity"), value: "popular" },
                      { label: t("catalog.sort.priceAsc"), value: "price_asc" },
                      { label: t("catalog.sort.priceDesc"), value: "price_desc" },
                    ].map((option) => (
                      <button
                        className="flex w-full select-none items-center justify-between whitespace-nowrap px-4 py-3 text-left font-mono text-[10px] uppercase hover:bg-white/10 hover:text-pandora-cyan"
                        key={option.value}
                        onClick={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          justToggledRef.current = true;
                          if (onHaptic) onHaptic("light");
                          setSortBy(option.value as SortOption);
                          setIsSortOpen(false);
                        }}
                        type="button"
                      >
                        <span className="overflow-visible">{option.label}</span>
                        {sortBy === option.value && (
                          <Check className="text-pandora-cyan" size={12} />
                        )}
                      </button>
                    ))}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* View Toggle */}
            <div className="flex flex-shrink-0 gap-1 rounded-sm border border-white/10 bg-[#0a0a0a] p-1">
              <button
                className={`rounded-sm p-1.5 transition-all sm:p-2 ${viewMode === "grid" ? "bg-white/10 text-pandora-cyan" : "text-gray-600 hover:text-white"}`}
                onClick={() => {
                  if (onHaptic) onHaptic("light");
                  setViewMode("grid");
                }}
                type="button"
              >
                <Grid className="sm:h-4 sm:w-4" size={14} />
              </button>
              <button
                className={`rounded-sm p-1.5 transition-all sm:p-2 ${viewMode === "list" ? "bg-white/10 text-pandora-cyan" : "text-gray-600 hover:text-white"}`}
                onClick={() => {
                  if (onHaptic) onHaptic("light");
                  setViewMode("list");
                }}
                type="button"
              >
                <List className="sm:h-4 sm:w-4" size={14} />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* --- CATEGORY TABS --- */}
      <div className="mx-auto mb-8 max-w-7xl border-white/5 border-b pb-1">
        <div className="scrollbar-hide flex gap-6 overflow-x-auto pb-2">
          {PRODUCT_CATEGORIES.map((cat) => {
            // Map categories to localization keys
            const categoryKeyMap: Record<string, string> = {
              All: "all",
              ai: "ai",
              dev: "dev",
              design: "design",
              music: "music",
            };

            const translationKey = categoryKeyMap[cat] || cat.toLowerCase();

            return (
              <button
                className={`relative whitespace-nowrap pb-2 font-display font-medium text-sm uppercase tracking-wide transition-all duration-300 ${
                  activeCategory === cat
                    ? "text-pandora-cyan drop-shadow-[0_0_8px_rgba(0,255,255,0.5)]"
                    : "text-gray-500 hover:text-gray-300"
                }
                `}
                key={cat}
                onClick={() => handleCategoryChange(cat)}
                type="button"
              >
                <span className="mr-1 font-mono text-[10px] opacity-50">
                  0{PRODUCT_CATEGORIES.indexOf(cat) + 1}.
                </span>
                {cat === "All" ? t("catalog.all") : t(`catalog.category.${translationKey}`)}
                {activeCategory === cat && (
                  <motion.div
                    className="absolute right-0 bottom-0 left-0 h-0.5 bg-pandora-cyan shadow-[0_0_10px_#00FFFF]"
                    layoutId="activeTab"
                  />
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* --- CONTENT AREA --- */}
      <div className="mx-auto min-h-[400px] max-w-7xl">
        <AnimatePresence mode="wait">
          {/* === GRID VIEW (IMPROVED SCAN EFFECT) === */}
          {viewMode === "grid" ? (
            <motion.div
              animate={{ opacity: 1 }}
              className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
              exit={{ opacity: 0 }}
              initial={{ opacity: 0 }}
              key="grid"
            >
              {filteredProducts.map((product) => (
                <ProductCard
                  getProductAvailability={getProductAvailability}
                  key={product.id}
                  onAddToCart={handleAddToCart}
                  onSelect={handleProductClick}
                  product={product}
                />
              ))}
            </motion.div>
          ) : (
            /* === LIST VIEW (TERMINAL STYLE) === */
            <motion.div
              animate={{ opacity: 1 }}
              className="flex flex-col gap-2"
              exit={{ opacity: 0 }}
              initial={{ opacity: 0 }}
              key="list"
            >
              {filteredProducts.map((product, i) => (
                <motion.div
                  animate={{ opacity: 1, x: 0 }}
                  className="group relative flex cursor-pointer items-center justify-between overflow-hidden border border-white/10 bg-[#0a0a0a] p-3 transition-all duration-200 hover:border-pandora-cyan hover:bg-white/[0.02]"
                  initial={{ opacity: 0, x: -20 }}
                  key={product.id}
                  onClick={() => handleProductClick(product)}
                  transition={{ delay: i * 0.05 }}
                >
                  {/* Hover Scanline for List View */}
                  <div className="absolute top-0 bottom-0 left-0 w-1 bg-pandora-cyan opacity-0 transition-opacity group-hover:opacity-100" />

                  <div className="flex items-center gap-4 pl-2">
                    <div className="relative flex h-12 w-12 shrink-0 items-center justify-center overflow-hidden border border-white/10 bg-black">
                      {/* Small image for list view */}
                      <img
                        alt={product.name}
                        className="absolute inset-0 h-full w-full object-cover opacity-50 grayscale transition-all group-hover:opacity-100 group-hover:grayscale-0"
                        src={product.image}
                      />
                      <div className="relative z-10 bg-black/50 px-1 font-mono text-[9px] text-white">
                        {product.category.substring(0, 3).toUpperCase()}
                      </div>
                    </div>
                    <div>
                      <div className="flex items-center gap-3">
                        <h3 className="font-bold font-mono text-sm text-white uppercase tracking-wider group-hover:text-pandora-cyan">
                          {product.name}
                        </h3>
                        {product.popular && (
                          <span className="bg-pandora-cyan/10 px-1 text-[9px] text-pandora-cyan">
                            HOT
                          </span>
                        )}
                      </div>
                      <div className="font-mono text-[10px] text-gray-500">
                        SKU: {product.sku} {" // "} VER: {product.version}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-8 pr-4 md:gap-12">
                    <div className="hidden flex-col items-end md:flex">
                      {(() => {
                        const avail = getProductAvailability(product);
                        const cfg = {
                          available: {
                            color: "bg-green-500",
                            text: t("catalog.availability.available"),
                            textColor: "text-gray-400",
                          },
                          on_demand: {
                            color: "bg-yellow-500",
                            text: t("catalog.availability.onDemand"),
                            textColor: "text-yellow-400",
                          },
                          discontinued: {
                            color: "bg-red-500",
                            text: t("catalog.availability.discontinued"),
                            textColor: "text-red-400",
                          },
                          coming_soon: {
                            color: "bg-blue-500",
                            text: t("catalog.availability.comingSoon"),
                            textColor: "text-blue-400",
                          },
                        }[avail];
                        return (
                          <div className="flex items-center gap-2">
                            <div className={`h-1.5 w-1.5 rounded-full ${cfg.color}`} />
                            <span className={`font-mono text-[10px] ${cfg.textColor}`}>
                              {cfg.text}
                            </span>
                          </div>
                        );
                      })()}
                    </div>

                    <div className="flex min-w-[100px] items-center justify-end gap-4">
                      <span className="block font-bold font-mono text-lg text-white">
                        {formatPrice(product.price, product.currency)}
                      </span>
                      <ChevronDown
                        className="-rotate-90 text-gray-600 transition-colors group-hover:text-pandora-cyan"
                        size={16}
                      />
                    </div>
                  </div>
                </motion.div>
              ))}
            </motion.div>
          )}
        </AnimatePresence>

        {filteredProducts.length === 0 && (
          <div className="mt-10 border border-white/10 border-dashed py-20 text-center opacity-50">
            <p className="font-mono text-lg text-pandora-cyan">{t("catalog.empty")}</p>
            <p className="mt-2 text-gray-500 text-sm">{t("catalog.emptyHint")}</p>
          </div>
        )}
      </div>
    </section>
  );
};

export default Catalog;
