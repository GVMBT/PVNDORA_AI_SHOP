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
    <div className="flex flex-col text-[8px] font-mono text-pandora-cyan/60 leading-tight opacity-50">
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

  const handleAddToCart = (product: ProductData, quantity: number = 1) => {
    if (onHaptic) onHaptic("medium");
    if (onAddToCart) onAddToCart(product, quantity);
  };

  return (
    <section
      id="catalog"
      className="relative w-full bg-transparent text-white pt-24 pb-24 px-6 md:pl-28 md:pt-32 md:-mt-24 min-h-screen z-30"
    >
      {/* === VISUAL CONNECTOR (DATA STREAM) FROM HERO === */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 h-20 w-px bg-gradient-to-b from-transparent via-pandora-cyan/30 to-transparent z-0 opacity-50" />

      {/* --- HEADER ROW --- */}
      <div className="max-w-7xl mx-auto mb-10 flex flex-col xl:flex-row gap-6 items-start xl:items-end justify-between relative z-10 pt-8">
        {/* Title Area: NARRATIVE UPDATE (Techno/Module) */}
        <div>
          <h2 className="text-3xl font-display font-bold text-white mb-2 flex items-center gap-3">
            <span className="w-2 h-8 bg-pandora-cyan block rounded-sm shadow-[0_0_10px_#00FFFF]"></span>
            {tEn("catalog.pageTitle")}
          </h2>
          <p className="text-gray-500 font-mono text-xs tracking-widest uppercase flex items-center gap-2">
            <Cpu size={12} className="text-pandora-cyan" />
            <span>{t("catalog.header.source")}</span>
            <span className="text-gray-700">|</span>
            <span className="text-pandora-cyan">{t("catalog.header.status")}</span>
          </p>
        </div>

        {/* Controls Area */}
        <div className="flex flex-col md:flex-row gap-4 w-full xl:w-auto">
          {/* Search Input */}
          <div className="relative flex-grow md:w-80 group">
            <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
              <Search className="h-4 w-4 text-gray-500 group-focus-within:text-pandora-cyan transition-colors" />
            </div>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder={t("catalog.search")}
              className="w-full bg-[#0a0a0a] border border-white/10 text-white text-sm rounded-sm py-3 pl-10 pr-4 focus:outline-none focus:border-pandora-cyan/50 focus:bg-[#0f0f0f] transition-all placeholder:text-gray-600 font-mono uppercase tracking-wider"
            />
          </div>

          <div className="flex gap-2 sm:gap-4 overflow-x-auto pb-2 -mb-2 scrollbar-hide">
            {/* Availability Filter Dropdown */}
            <div ref={availabilityRef} className="relative flex-shrink-0 z-50">
              <button
                type="button"
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  justToggledRef.current = true;
                  if (onHaptic) onHaptic("light");
                  setIsAvailabilityOpen((prev) => !prev);
                  setIsSortOpen(false);
                }}
                className="h-full px-3 sm:px-4 py-2 flex items-center gap-2 bg-[#0a0a0a] border border-white/10 hover:border-pandora-cyan/50 text-sm font-mono text-gray-300 transition-all rounded-sm whitespace-nowrap touch-manipulation select-none min-w-fit"
              >
                <span className="uppercase text-[9px] sm:text-[10px] tracking-wider overflow-visible">
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
                  size={14}
                  className={`transition-transform flex-shrink-0 ${isAvailabilityOpen ? "rotate-180" : ""}`}
                />
              </button>

              <AnimatePresence>
                {isAvailabilityOpen && (
                  <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    onClick={(e) => e.stopPropagation()}
                    className="absolute top-full left-0 w-fit min-w-full mt-2 bg-[#0a0a0a] border border-white/20 z-[100] shadow-xl shadow-black/80"
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
                        type="button"
                        key={option.value}
                        onClick={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          justToggledRef.current = true;
                          if (onHaptic) onHaptic("light");
                          setActiveAvailability(option.value as AvailabilityFilter);
                          setIsAvailabilityOpen(false);
                        }}
                        className="w-full text-left px-4 py-3 text-[10px] uppercase font-mono hover:bg-white/10 hover:text-pandora-cyan flex items-center justify-between select-none whitespace-nowrap"
                      >
                        <span className={`${option.color} overflow-visible`}>{option.label}</span>
                        {activeAvailability === option.value && (
                          <Check size={12} className="text-pandora-cyan" />
                        )}
                      </button>
                    ))}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* Sort Dropdown */}
            <div ref={sortRef} className="relative flex-shrink-0 z-50">
              <button
                type="button"
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  justToggledRef.current = true;
                  if (onHaptic) onHaptic("light");
                  setIsSortOpen((prev) => !prev);
                  setIsAvailabilityOpen(false);
                }}
                className="h-full px-3 sm:px-4 py-2 flex items-center gap-2 bg-[#0a0a0a] border border-white/10 hover:border-pandora-cyan/50 text-sm font-mono text-gray-300 transition-all rounded-sm whitespace-nowrap touch-manipulation select-none"
              >
                <span className="uppercase text-[9px] sm:text-[10px] tracking-wider">
                  {sortBy === "popular" &&
                    `${t("catalog.sort.label")}: ${t("catalog.sort.popularity")}`}
                  {sortBy === "price_asc" &&
                    `${t("catalog.sort.label")}: ${t("catalog.sort.priceAsc")}`}
                  {sortBy === "price_desc" &&
                    `${t("catalog.sort.label")}: ${t("catalog.sort.priceDesc")}`}
                </span>
                <ChevronDown
                  size={14}
                  className={`transition-transform flex-shrink-0 ${isSortOpen ? "rotate-180" : ""}`}
                />
              </button>

              <AnimatePresence>
                {isSortOpen && (
                  <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    onClick={(e) => e.stopPropagation()}
                    className="absolute top-full left-0 w-fit min-w-full mt-2 bg-[#0a0a0a] border border-white/20 z-[100] shadow-xl shadow-black/80"
                  >
                    {[
                      { label: t("catalog.sort.popularity"), value: "popular" },
                      { label: t("catalog.sort.priceAsc"), value: "price_asc" },
                      { label: t("catalog.sort.priceDesc"), value: "price_desc" },
                    ].map((option) => (
                      <button
                        type="button"
                        key={option.value}
                        onClick={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          justToggledRef.current = true;
                          if (onHaptic) onHaptic("light");
                          setSortBy(option.value as SortOption);
                          setIsSortOpen(false);
                        }}
                        className="w-full text-left px-4 py-3 text-[10px] uppercase font-mono hover:bg-white/10 hover:text-pandora-cyan flex items-center justify-between select-none whitespace-nowrap"
                      >
                        <span className="overflow-visible">{option.label}</span>
                        {sortBy === option.value && (
                          <Check size={12} className="text-pandora-cyan" />
                        )}
                      </button>
                    ))}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* View Toggle */}
            <div className="flex bg-[#0a0a0a] border border-white/10 p-1 rounded-sm gap-1 flex-shrink-0">
              <button
                type="button"
                onClick={() => {
                  if (onHaptic) onHaptic("light");
                  setViewMode("grid");
                }}
                className={`p-1.5 sm:p-2 rounded-sm transition-all ${viewMode === "grid" ? "bg-white/10 text-pandora-cyan" : "text-gray-600 hover:text-white"}`}
              >
                <Grid size={14} className="sm:w-4 sm:h-4" />
              </button>
              <button
                type="button"
                onClick={() => {
                  if (onHaptic) onHaptic("light");
                  setViewMode("list");
                }}
                className={`p-1.5 sm:p-2 rounded-sm transition-all ${viewMode === "list" ? "bg-white/10 text-pandora-cyan" : "text-gray-600 hover:text-white"}`}
              >
                <List size={14} className="sm:w-4 sm:h-4" />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* --- CATEGORY TABS --- */}
      <div className="max-w-7xl mx-auto mb-8 border-b border-white/5 pb-1">
        <div className="flex gap-6 overflow-x-auto pb-2 scrollbar-hide">
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
                type="button"
                key={cat}
                onClick={() => handleCategoryChange(cat)}
                className={`
                    relative pb-2 text-sm font-display font-medium tracking-wide transition-all duration-300 whitespace-nowrap uppercase
                    ${
                      activeCategory === cat
                        ? "text-pandora-cyan drop-shadow-[0_0_8px_rgba(0,255,255,0.5)]"
                        : "text-gray-500 hover:text-gray-300"
                    }
                `}
              >
                <span className="mr-1 opacity-50 text-[10px] font-mono">
                  0{PRODUCT_CATEGORIES.indexOf(cat) + 1}.
                </span>
                {cat === "All" ? t("catalog.all") : t(`catalog.category.${translationKey}`)}
                {activeCategory === cat && (
                  <motion.div
                    layoutId="activeTab"
                    className="absolute bottom-0 left-0 right-0 h-0.5 bg-pandora-cyan shadow-[0_0_10px_#00FFFF]"
                  />
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* --- CONTENT AREA --- */}
      <div className="max-w-7xl mx-auto min-h-[400px]">
        <AnimatePresence mode="wait">
          {/* === GRID VIEW (IMPROVED SCAN EFFECT) === */}
          {viewMode === "grid" ? (
            <motion.div
              key="grid"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6"
            >
              {filteredProducts.map((product) => (
                <ProductCard
                  key={product.id}
                  product={product}
                  getProductAvailability={getProductAvailability}
                  onSelect={handleProductClick}
                  onAddToCart={handleAddToCart}
                />
              ))}
            </motion.div>
          ) : (
            /* === LIST VIEW (TERMINAL STYLE) === */
            <motion.div
              key="list"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="flex flex-col gap-2"
            >
              {filteredProducts.map((product, i) => (
                <motion.div
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.05 }}
                  key={product.id}
                  onClick={() => handleProductClick(product)}
                  className="group flex items-center justify-between p-3 bg-[#0a0a0a] border border-white/10 hover:border-pandora-cyan hover:bg-white/[0.02] cursor-pointer transition-all duration-200 relative overflow-hidden"
                >
                  {/* Hover Scanline for List View */}
                  <div className="absolute left-0 top-0 bottom-0 w-1 bg-pandora-cyan opacity-0 group-hover:opacity-100 transition-opacity" />

                  <div className="flex items-center gap-4 pl-2">
                    <div className="w-12 h-12 bg-black border border-white/10 flex items-center justify-center shrink-0 relative overflow-hidden">
                      {/* Small image for list view */}
                      <img
                        src={product.image}
                        alt={product.name}
                        className="absolute inset-0 w-full h-full object-cover opacity-50 grayscale group-hover:opacity-100 group-hover:grayscale-0 transition-all"
                      />
                      <div className="relative z-10 font-mono text-[9px] text-white bg-black/50 px-1">
                        {product.category.substring(0, 3).toUpperCase()}
                      </div>
                    </div>
                    <div>
                      <div className="flex items-center gap-3">
                        <h3 className="text-sm font-bold text-white font-mono uppercase tracking-wider group-hover:text-pandora-cyan">
                          {product.name}
                        </h3>
                        {product.popular && (
                          <span className="text-[9px] text-pandora-cyan bg-pandora-cyan/10 px-1">
                            HOT
                          </span>
                        )}
                      </div>
                      <div className="text-[10px] font-mono text-gray-500">
                        SKU: {product.sku} {" // "} VER: {product.version}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-8 md:gap-12 pr-4">
                    <div className="hidden md:flex flex-col items-end">
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
                            <div className={`w-1.5 h-1.5 rounded-full ${cfg.color}`} />
                            <span className={`text-[10px] font-mono ${cfg.textColor}`}>
                              {cfg.text}
                            </span>
                          </div>
                        );
                      })()}
                    </div>

                    <div className="flex items-center gap-4 min-w-[100px] justify-end">
                      <span className="block text-lg font-bold text-white font-mono">
                        {formatPrice(product.price, product.currency)}
                      </span>
                      <ChevronDown
                        className="-rotate-90 text-gray-600 group-hover:text-pandora-cyan transition-colors"
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
          <div className="text-center py-20 opacity-50 border border-dashed border-white/10 mt-10">
            <p className="font-mono text-pandora-cyan text-lg">{t("catalog.empty")}</p>
            <p className="text-sm text-gray-500 mt-2">{t("catalog.emptyHint")}</p>
          </div>
        )}
      </div>
    </section>
  );
};

export default Catalog;
