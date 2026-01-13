import React, { useState, useEffect, useMemo } from "react";
import {
  ArrowLeft,
  ArrowRight,
  CheckCircle,
  Cpu,
  FileCode,
  HardDrive,
  Loader2,
  Lock,
  Minus,
  Plus,
  Radio,
  Server,
  Terminal,
  Video,
} from "lucide-react";
import { motion, AnimatePresence, useMotionValue, useTransform, useSpring } from "framer-motion";
import { formatPrice } from "../../utils/currency";
import { useTimeoutState } from "../../hooks/useTimeoutState";
import { useLocale } from "../../hooks/useLocale";
import { UI } from "../../config";
import { randomInt } from "../../utils/random";
import ProductSpecs from "./ProductSpecs";
import ProductFiles from "./ProductFiles";
import ProductManifest from "./ProductManifest";
import { logger } from "../../utils/logger";

import type {
  ProductDetailData,
  CatalogProduct,
} from "../../types/component";

// Helper functions for availability state (extracted to avoid nested ternaries)
type AvailabilityState = "available" | "preorder" | "disabled";

const getAvailabilityState = (hasStock: boolean, isPreorder: boolean): AvailabilityState => {
  if (hasStock) return "available";
  if (isPreorder) return "preorder";
  return "disabled";
};

const getAccessProtocol = (state: AvailabilityState): string => {
  if (state === "available") return "DIRECT_ACCESS";
  if (state === "preorder") return "ON_DEMAND";
  return "DISCONTINUED";
};

const getNodeStatus = (state: AvailabilityState): string => {
  if (state === "available") return "OPERATIONAL";
  if (state === "preorder") return "STANDBY";
  return "DISABLED";
};

const getNodeStatusColor = (state: AvailabilityState): string => {
  if (state === "available") return "text-green-500";
  if (state === "preorder") return "text-yellow-500";
  return "text-red-500";
};

const getStatusDotColor = (state: AvailabilityState): string => {
  if (state === "available") return "bg-green-500";
  if (state === "preorder") return "bg-yellow-500";
  return "bg-red-500";
};

const getStatusText = (state: AvailabilityState): string => {
  if (state === "available") return "GRID_ONLINE";
  if (state === "preorder") return "RESOURCE_QUEUE";
  return "OFFLINE";
};

const getTabLabel = (tab: string, t: (key: string) => string): string => {
  if (tab === "specs") return t("product.techSpecs");
  if (tab === "files") return t("product.packageContent");
  return t("product.systemManifest");
};

const getButtonClassName = (isDisabled: boolean, isSuccess: boolean): string => {
  if (isDisabled) return "bg-gray-800 text-gray-400 cursor-not-allowed";
  if (isSuccess) return "bg-green-500 text-black";
  return "bg-pandora-cyan hover:bg-white text-black";
};

interface ProductDetailProps {
  product: ProductDetailData;
  onBack: () => void;
  onAddToCart: (product: CatalogProduct, quantity: number) => void;
  onProductSelect?: (product: CatalogProduct) => void;
  isInCart: boolean;
  onHaptic?: (type?: "light" | "medium" | "success") => void;
}

const ProductDetail: React.FC<ProductDetailProps> = ({
  product,
  onBack,
  onAddToCart,
  isInCart,
  onHaptic,
  onProductSelect,
}) => {
  const { t } = useLocale();
  const [activeTab, setActiveTab] = useState<"specs" | "files" | "manifest">("specs");
  const [systemCheck, setSystemCheck] = useState(0);
  const [quantity, setQuantity] = useState(1);
  const files = product.files || [];

  // Micro-interaction states
  const [isAllocating, setIsAllocating] = useState(false);
  const [isSuccess, setIsSuccess] = useTimeoutState(false, {
    timeout: UI.SUCCESS_MESSAGE_DURATION,
  });

  // Simulated System Check Animation - optimized with useMemo for cleanup
  useEffect(() => {
    let interval: ReturnType<typeof setInterval> | null = null;

    const updateSystemCheck = () => {
      setSystemCheck((prev) => {
        if (prev >= 100) {
          if (interval) clearInterval(interval);
          return 100;
        }
        return prev + randomInt(1, 15);
      });
    };

    interval = setInterval(updateSystemCheck, 150);

    return () => {
      if (interval) clearInterval(interval);
    };
  }, []);

  // --- 3D TILT LOGIC (Desktop Only) ---
  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const mouseX = useSpring(x, { stiffness: 150, damping: 20 });
  const mouseY = useSpring(y, { stiffness: 150, damping: 20 });

  function handleMouseMove({ currentTarget, clientX, clientY }: React.MouseEvent) {
    if (globalThis.innerWidth < 768) return;
    const { left, top, width, height } = currentTarget.getBoundingClientRect();
    const xPct = (clientX - left) / width - 0.5;
    const yPct = (clientY - top) / height - 0.5;
    x.set(xPct);
    y.set(yPct);
  }

  function handleMouseLeave() {
    x.set(0);
    y.set(0);
  }

  const handleTabChange = (tab: "specs" | "files" | "manifest") => {
    if (onHaptic) onHaptic("light");
    setActiveTab(tab);
  };

  const adjustQuantity = (delta: number) => {
    const newQty = Math.max(1, quantity + delta);
    setQuantity(newQty);
    if (onHaptic) onHaptic("light");
  };

  // --- DERIVED AVAILABILITY STATES --- (memoized for performance)
  const availabilityData = useMemo(() => {
    const hasStock = product.stock > 0;
    const isPreorder = !hasStock && product.fulfillment > 0;
    const isDisabled = !hasStock && !isPreorder;
    const state = getAvailabilityState(hasStock, isPreorder);

    const accessProtocol = getAccessProtocol(state);
    // Helper for delivery label (avoid nested ternary)
    const getDeliveryLabel = (): string => {
      if (hasStock) return "INSTANT_DEPLOY";
      if (isPreorder) return `ALLOCATION_QUEUE ~${product.fulfillment}H`;
      return "UNAVAILABLE";
    };
    const deliveryLabel = getDeliveryLabel();

    const nodeStatus = getNodeStatus(state);
    const nodeStatusColor = getNodeStatusColor(state);
    const statusDotColor = getStatusDotColor(state);
    const statusText = getStatusText(state);

    // Warranty label helper
    const getWarrantyLabel = (): string => {
      if (product.warranty <= 0) return "UNSPECIFIED";
      if (product.warranty % 24 === 0) return `${product.warranty / 24} DAYS`;
      return `${product.warranty} HOURS`;
    };
    const warrantyLabel = getWarrantyLabel();

    const durationLabel =
      product.duration && product.duration > 0 ? `${product.duration} DAYS` : "UNBOUNDED";

    return {
      hasStock,
      isPreorder,
      isDisabled,
      accessProtocol,
      deliveryLabel,
      nodeStatus,
      nodeStatusColor,
      statusDotColor,
      statusText,
      warrantyLabel,
      durationLabel,
    };
  }, [product.stock, product.fulfillment, product.warranty, product.duration]);

  const {
    hasStock,
    isPreorder,
    isDisabled,
    accessProtocol,
    deliveryLabel,
    nodeStatus,
    nodeStatusColor,
    statusDotColor,
    statusText,
    warrantyLabel,
    durationLabel,
  } = availabilityData;

  // --- MICRO-INTERACTION: ADD TO CART ---
  const handleMountModule = async () => {
    if (isAllocating || isSuccess) return;
    if (onHaptic) onHaptic("medium");

    setIsAllocating(true);

    try {
      // Actually add to cart (await the async operation)
      await onAddToCart(product, quantity);
      setIsSuccess(true);
      if (onHaptic) onHaptic("success");
    } catch (err) {
      logger.error("Failed to add to cart", err);
    } finally {
      setIsAllocating(false);
    }
  };

  // --- CROSS-SELL LOGIC (memoized) ---
  const relatedProducts = useMemo(() => {
    return (product.relatedProducts || []).filter((p) => p.id !== product.id).slice(0, 3);
  }, [product.relatedProducts, product.id]);

  // 3D tilt transforms (memoized)
  const rotateX = useTransform(mouseY, [-0.5, 0.5], [10, -10]);
  const rotateY = useTransform(mouseX, [-0.5, 0.5], [-10, 10]);
  const sheenGradient = useTransform(
    mouseX,
    [-0.5, 0.5],
    [
      "linear-gradient(115deg, transparent 0%, rgba(255,255,255,0) 40%, rgba(255,255,255,0) 60%, transparent 100%)",
      "linear-gradient(115deg, transparent 0%, rgba(255,255,255,0.1) 40%, rgba(0,255,255,0.2) 60%, transparent 100%)",
    ]
  );

  // Helper to render button content based on state (avoids nested ternaries)
  const renderButtonContent = () => {
    const motionProps = {
      initial: { opacity: 0, y: 10 },
      animate: { opacity: 1, y: 0 },
      exit: { opacity: 0, y: -10 },
    };

    if (isAllocating) {
      return (
        <motion.div key="loading" {...motionProps} className="flex items-center gap-3 w-full justify-center">
          <Loader2 size={20} className="animate-spin" />
          <span>{isPreorder ? t("product.allocatingQueue") : t("product.allocatingResources")}</span>
        </motion.div>
      );
    }

    if (isSuccess) {
      return (
        <motion.div key="success" {...motionProps} className="flex items-center gap-3 w-full justify-center">
          <CheckCircle size={20} />
          <span>{t("product.accessGranted")}</span>
        </motion.div>
      );
    }

    return (
      <motion.div key="idle" {...motionProps} className="w-full flex items-center justify-between">
        <span className="flex items-center gap-3 text-sm md:text-base group-hover:translate-x-1 transition-transform">
          <Plus size={20} className="hidden sm:block" />
          {isPreorder ? t("product.queueAllocation") : t("product.mountModule")}
        </span>
        <span className="font-mono text-lg md:text-xl font-bold border-l border-black/20 pl-4 ml-4">
          {formatPrice(product.price * quantity, product.currency)}
        </span>
      </motion.div>
    );
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="min-h-screen text-white pt-20 md:pt-24 pb-48 md:pb-32 px-4 md:px-8 md:pl-28 relative z-40 bg-transparent"
    >
      <div className="max-w-7xl mx-auto relative z-10">
        {/* === UNIFIED HEADER (Leaderboard Style) === */}
        <div className="mb-8 md:mb-16">
          <button
            onClick={onBack}
            className="flex items-center gap-2 text-[10px] font-mono text-gray-500 hover:text-pandora-cyan mb-4 transition-colors"
          >
            <ArrowLeft size={12} /> {t("product.returnToCatalog")}
          </button>
          <h1 className="text-3xl sm:text-4xl md:text-6xl font-display font-black text-white uppercase tracking-tighter leading-[0.9] mb-4 break-words">
            {product.name}
          </h1>
          <div className="flex items-center gap-2 text-[10px] font-mono text-pandora-cyan tracking-widest uppercase">
            <DatabaseIcon category={product.category} />
            <span>
              {t("product.database")} {" // "} {product.category.toUpperCase()} {" // "} {product.sku}
            </span>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 md:gap-12 mb-12 md:mb-16">
          {/* === LEFT COLUMN: VISUALIZER === */}
          <div className="lg:col-span-5 perspective-1000">
            <motion.div
              style={{ rotateX, rotateY, transformStyle: "preserve-3d" }}
              onMouseMove={handleMouseMove}
              onMouseLeave={handleMouseLeave}
              className="relative aspect-square w-full bg-[#0a0a0a] border border-white/10 group cursor-crosshair shadow-2xl shadow-black/50 rounded-sm overflow-hidden"
            >
              {/* Visual Layer - Video Loop or Image */}
              <div className="absolute inset-0 transform-style-3d">
                {product.video ? (
                  // Video Loop for visual simulation
                  <video
                    src={product.video}
                    autoPlay
                    loop
                    muted
                    playsInline
                    className="w-full h-full object-cover opacity-80 group-hover:opacity-100 transition-opacity"
                  />
                ) : (
                  // Standard image for products without video
                  <img
                    src={product.image}
                    alt={product.name}
                    className="w-full h-full object-cover opacity-60 group-hover:opacity-100 group-hover:scale-105 transition-all duration-700 grayscale group-hover:grayscale-0"
                  />
                )}
              </div>

              {/* Holographic Overlays */}
              <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-20 mix-blend-overlay pointer-events-none" />
              <div className="absolute inset-0 bg-[linear-gradient(0deg,rgba(0,0,0,0.8)_0%,transparent_50%)]" />
              <motion.div
                style={{ background: sheenGradient }}
                className="absolute inset-0 pointer-events-none z-20 mix-blend-screen hidden md:block"
              />

              {/* OVERLAY: Title & Version (Corner) */}
              <div className="absolute bottom-0 left-0 right-0 p-4 z-30 bg-gradient-to-t from-black/90 to-transparent">
                <div className="text-3xl font-display font-bold text-white mb-1">
                  {product.name}
                </div>
                <div className="text-[10px] font-mono text-pandora-cyan bg-pandora-cyan/10 px-2 py-0.5 inline-block border border-pandora-cyan/20">
                  {t("product.sysVer")}: {product.version || "1.0.0"}
                </div>
              </div>

              <div className="absolute top-4 right-4 z-30 flex flex-col items-end gap-2">
                {product.popular && (
                  <div className="text-[10px] bg-pandora-cyan text-black px-2 py-0.5 font-bold uppercase shadow-[0_0_10px_#00FFFF]">
                    {t("product.trending")}
                  </div>
                )}
                <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
              </div>
            </motion.div>

            {/* System Check Visual */}
            <div className="mt-4 bg-[#0a0a0a] border border-white/10 p-3 hidden md:block">
              <div className="flex justify-between items-center text-[10px] font-mono text-gray-500 mb-2">
                <span className="flex items-center gap-2">
                  <Cpu size={12} /> {t("product.compatibilityCheck")}
                </span>
                <span className="text-pandora-cyan">{systemCheck}%</span>
              </div>
              <div className="w-full h-1 bg-gray-800 relative overflow-hidden">
                <div
                  className="h-full bg-pandora-cyan shadow-[0_0_10px_#00FFFF]"
                  style={{ width: `${systemCheck}%`, transition: "width 0.2s ease" }}
                />
              </div>
              {systemCheck === 100 && (
                <div className="mt-2 text-[10px] text-green-500 font-mono flex items-center gap-1">
                  <CheckCircle size={10} /> {t("product.systemOptimized")}
                </div>
              )}
            </div>
          </div>

          {/* === RIGHT COLUMN: DATA MATRIX & SPECS === */}
          <div className="lg:col-span-7 flex flex-col gap-8">
            {/* 1. DATA MATRIX (Price & ID) - REWORKED LAYOUT */}
            <div className="bg-[#0c0c0c] border border-white/10 p-1 rounded-sm">
              <div className="grid grid-cols-2 divide-x divide-white/10">
                {/* Block 1: SKU & Status */}
                <div className="p-4 flex flex-col justify-between h-24">
                  <div className="text-[9px] font-mono text-gray-500 uppercase tracking-widest mb-1">
                    {t("product.moduleIdentifier")}
                  </div>
                  <div className="text-lg font-mono text-white font-bold">{product.sku}</div>
                  <div className="mt-auto flex items-center gap-2">
                    <div className={`w-1.5 h-1.5 rounded-full ${statusDotColor}`} />
                    <span className={`text-[9px] font-mono uppercase ${nodeStatusColor}`}>
                      {statusText}
                    </span>
                  </div>
                </div>
                {/* Block 2: Price */}
                <div className="p-4 flex flex-col justify-between h-24 bg-white/[0.02]">
                  <div className="text-[9px] font-mono text-gray-500 uppercase tracking-widest mb-1 text-right">
                    {t("product.allocationCost")}
                  </div>
                  <div className="text-right">
                    {product.msrp && (
                      <div className="text-xs text-gray-600 line-through decoration-red-500/50 mb-1">
                        {formatPrice(product.msrp, product.currency)}
                      </div>
                    )}
                    <div className="text-3xl font-display font-bold text-white text-shadow-glow flex justify-end gap-1">
                      {formatPrice(product.price, product.currency)}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* 2. TABS & CONTENT */}
            <div className="flex-1">
              <div className="flex border-b border-white/10 mb-6 gap-6 md:gap-8 overflow-x-auto scrollbar-hide">
                {["specs", "files", "manifest"].map((tab) => (
                  <button
                    key={tab}
                    onClick={() => handleTabChange(tab as any)}
                    className={`pb-3 text-[10px] font-mono font-bold uppercase tracking-widest border-b-2 transition-all relative group whitespace-nowrap ${
                      activeTab === tab
                        ? "border-pandora-cyan text-pandora-cyan"
                        : "border-transparent text-gray-600 hover:text-white"
                    }`}
                  >
                    {getTabLabel(tab, t)}
                  </button>
                ))}
              </div>

              <div className="min-h-[200px]">
                <AnimatePresence mode="wait">
                  {/* === TECH SPECS === */}
                  {activeTab === "specs" && (
                    <ProductSpecs
                      accessProtocol={accessProtocol}
                      warrantyLabel={warrantyLabel}
                      durationLabel={durationLabel}
                      deliveryLabel={deliveryLabel}
                      nodeStatus={nodeStatus}
                      nodeStatusColor={nodeStatusColor}
                    />
                  )}

                  {/* === FILES === */}
                  {activeTab === "files" && <ProductFiles files={files} />}

                  {/* === MANIFEST === */}
                  {activeTab === "manifest" && (
                    <ProductManifest
                      description={product.description}
                      instructions={product.instructions}
                    />
                  )}
                </AnimatePresence>
              </div>
            </div>
          </div>
        </div>

        {/* === INCOMING TRANSMISSIONS (Rubber Spacing) === */}
        <div className="border-t border-white/10 pt-8 mt-4 md:mt-8">
          <div className="flex items-center gap-4 mb-6 md:mb-8">
            <div className="w-10 h-10 bg-white/5 border border-white/10 flex items-center justify-center rounded-sm">
              <Radio className="text-pandora-cyan animate-pulse" size={20} />
            </div>
            <div>
              <h3 className="text-lg font-display font-bold text-white uppercase tracking-wider">
                {t("product.incomingTransmissions")}
              </h3>
              <div className="text-[10px] font-mono text-gray-500 uppercase flex items-center gap-3">
                <span>{t("product.userLogs")}</span>
                <span className="text-pandora-cyan">● {t("product.liveFeed")}</span>
                <span>
                  {t("product.signalsDetected", { count: (product.reviews || []).length })}
                </span>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {(product.reviews || []).map((review, i) => (
              <div
                key={review.id || i}
                className="bg-black/40 border border-white/10 p-5 relative group overflow-hidden hover:border-white/30 transition-all"
              >
                {/* Scanline for log effect */}
                <div className="absolute top-0 left-0 w-full h-[1px] bg-pandora-cyan/30 opacity-0 group-hover:opacity-100 transition-opacity" />

                <div className="flex justify-between items-start mb-3">
                  <div className="flex items-center gap-3">
                    <div className="font-mono text-xs font-bold text-pandora-cyan bg-pandora-cyan/10 px-2 py-0.5 border border-pandora-cyan/20 truncate max-w-[150px]">
                      {review.user || "ANON"}
                    </div>
                    {review.verified && (
                      <span className="flex items-center gap-1 text-[9px] text-green-500 font-mono border border-green-900 bg-green-900/10 px-1.5 py-0.5 rounded-sm">
                        <CheckCircle size={8} /> {t("product.verified")}
                      </span>
                    )}
                  </div>
                  <div className="text-[10px] font-mono text-gray-600">{review.date}</div>
                </div>

                <div className="font-mono text-sm text-gray-300 leading-relaxed mb-4 pl-4 border-l border-white/10">
                  "{review.text}"
                </div>

                <div className="flex items-center justify-between border-t border-white/5 pt-3">
                  <div className="flex gap-1">
                    {[...Array(5)].map((_, starIndex) => (
                      <div
                        key={`star-${review.id}-${starIndex}`}
                        className={`w-1.5 h-1.5 rounded-full ${starIndex < review.rating ? "bg-pandora-cyan" : "bg-gray-800"}`}
                      />
                    ))}
                  </div>
                  <div className="text-[9px] font-mono text-gray-600 uppercase">
                    {t("product.signalStrength")}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* === CROSS SELL SECTION: COMPATIBLE MODULES === */}
        <div className="mt-16 pt-8 border-t border-white/10">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-xs font-mono font-bold text-gray-400 uppercase flex items-center gap-2">
              <Server size={14} /> {t("product.compatibleModules")}
            </h3>
            <div className="text-[9px] font-mono text-pandora-cyan">
              {t("product.aiRecommendation")}
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {(product.relatedProducts || []).map((rel) => (
              <div
                key={rel.id}
                onClick={() => onProductSelect && onProductSelect(rel)}
                className="bg-[#0a0a0a] border border-white/10 p-3 flex gap-3 cursor-pointer hover:border-pandora-cyan/50 hover:bg-white/[0.02] transition-all group"
              >
                <div className="w-12 h-12 bg-black shrink-0 border border-white/10 relative overflow-hidden">
                  <img
                    src={rel.image}
                    alt={rel.name}
                    className="w-full h-full object-cover opacity-60 grayscale group-hover:grayscale-0 group-hover:opacity-100 transition-all"
                  />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-xs font-bold text-white truncate group-hover:text-pandora-cyan transition-colors">
                    {rel.name}
                  </div>
                  <div className="text-[9px] font-mono text-gray-500 mb-1">
                    {rel.category} {" // "} {rel.stock > 0 ? "ONLINE" : "OFFLINE"}
                  </div>
                  <div className="text-xs font-mono text-white font-bold">
                    {formatPrice(rel.price, rel.currency)}
                  </div>
                </div>
                <div className="flex items-center text-gray-600 group-hover:text-pandora-cyan group-hover:translate-x-1 transition-all">
                  <ArrowRight size={14} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* --- STICKY FOOTER (CLEAN TACTICAL STYLE) --- */}
      <div className="fixed bottom-0 left-0 md:left-20 right-0 bg-[#050505]/95 backdrop-blur-md border-t border-white/10 p-4 z-[60]">
        <div className="max-w-7xl mx-auto flex gap-4 h-14 md:h-16">
          {/* QUANTITY CONTROL (Left) */}
          <div className="flex items-center bg-black/50 border border-white/20 w-36 shrink-0 rounded-sm overflow-hidden">
            <button
              onClick={() => adjustQuantity(-1)}
              className="h-full w-12 flex items-center justify-center text-gray-400 hover:text-white hover:bg-white/5 active:bg-white/10 transition-colors border-r border-white/10"
            >
              <Minus size={18} />
            </button>
            <div className="flex-1 flex items-center justify-center font-mono font-bold text-white text-xl">
              {quantity.toString().padStart(2, "0")}
            </div>
            <button
              onClick={() => adjustQuantity(1)}
              className="h-full w-12 flex items-center justify-center text-gray-400 hover:text-white hover:bg-white/5 active:bg-white/10 transition-colors border-l border-white/10"
            >
              <Plus size={18} />
            </button>
          </div>

          {/* BUY BUTTON (Right) - WITH MICRO-INTERACTION */}
          <button
            onClick={handleMountModule}
            disabled={isDisabled || isAllocating || isSuccess}
            className={`
                        flex-1 font-display font-bold uppercase tracking-widest transition-all flex items-center justify-between px-6 rounded-sm group relative overflow-hidden
                        ${getButtonClassName(isDisabled, isSuccess)}
                    `}
          >
            {/* Animated Background for Loading */}
            {isAllocating && (
              <div className="absolute inset-0 bg-white/20">
                <div className="h-full w-full bg-[linear-gradient(90deg,transparent_0%,rgba(255,255,255,0.5)_50%,transparent_100%)] animate-[scan_1s_infinite]" />
              </div>
            )}

            {isDisabled ? (
              <>
                <span className="flex items-center gap-2">
                  <Lock size={18} /> {t("product.disabled")}
                </span>
                <span>--</span>
              </>
            ) : (
              <AnimatePresence mode="wait">
                {renderButtonContent()}
              </AnimatePresence>
            )}
          </button>
        </div>
      </div>
    </motion.div>
  );
};

// --- HELPER FOR HEADER ICON ---
const DatabaseIcon: React.FC<{ category: string }> = ({ category }) => {
  switch (category) {
    case "Text":
      return <Terminal size={12} />;
    case "Video":
      return <Video size={12} />;
    case "Code":
      return <FileCode size={12} />;
    default:
      return <HardDrive size={12} />;
  }
};

export default ProductDetail;
