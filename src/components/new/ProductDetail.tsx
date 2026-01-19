import { AnimatePresence, motion, useMotionValue, useSpring, useTransform } from "framer-motion";
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
import type React from "react";
import { useEffect, useMemo, useState } from "react";
import { UI } from "../../config";
import { useLocale } from "../../hooks/useLocale";
import { useTimeoutState } from "../../hooks/useTimeoutState";
import type { CatalogProduct, ProductDetailData } from "../../types/component";
import { formatPrice } from "../../utils/currency";
import { logger } from "../../utils/logger";
import { randomInt } from "../../utils/random";
import ProductFiles from "./ProductFiles";
import ProductManifest from "./ProductManifest";
import ProductSpecs from "./ProductSpecs";

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

type TabType = "specs" | "files" | "manifest";

const ProductDetail: React.FC<ProductDetailProps> = ({
  product,
  onBack,
  onAddToCart,
  isInCart: _isInCart,
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
    const isDisabled = !(hasStock || isPreorder);
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
    // hasStock is computed internally, not used directly in JSX
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
  const handleMountModule = () => {
    if (isAllocating || isSuccess) return;
    if (onHaptic) onHaptic("medium");

    setIsAllocating(true);

    try {
      // Add to cart (synchronous operation)
      onAddToCart(product, quantity);
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
        <motion.div
          key="loading"
          {...motionProps}
          className="flex w-full items-center justify-center gap-3"
        >
          <Loader2 className="animate-spin" size={20} />
          <span>
            {isPreorder ? t("product.allocatingQueue") : t("product.allocatingResources")}
          </span>
        </motion.div>
      );
    }

    if (isSuccess) {
      return (
        <motion.div
          key="success"
          {...motionProps}
          className="flex w-full items-center justify-center gap-3"
        >
          <CheckCircle size={20} />
          <span>{t("product.accessGranted")}</span>
        </motion.div>
      );
    }

    return (
      <motion.div key="idle" {...motionProps} className="flex w-full items-center justify-between">
        <span className="flex items-center gap-3 text-sm transition-transform group-hover:translate-x-1 md:text-base">
          <Plus className="hidden sm:block" size={20} />
          {isPreorder ? t("product.queueAllocation") : t("product.mountModule")}
        </span>
        <span className="ml-4 border-black/20 border-l pl-4 font-bold font-mono text-lg md:text-xl">
          {formatPrice(product.price * quantity, product.currency)}
        </span>
      </motion.div>
    );
  };

  return (
    <motion.div
      animate={{ opacity: 1 }}
      className="relative z-40 min-h-screen bg-transparent px-4 pt-20 pb-48 text-white md:px-8 md:pt-24 md:pb-32 md:pl-28"
      exit={{ opacity: 0 }}
      initial={{ opacity: 0 }}
    >
      <div className="relative z-10 mx-auto max-w-7xl">
        {/* === UNIFIED HEADER (Leaderboard Style) === */}
        <div className="mb-8 md:mb-16">
          <button
            className="mb-4 flex items-center gap-2 font-mono text-[10px] text-gray-500 transition-colors hover:text-pandora-cyan"
            onClick={onBack}
            type="button"
          >
            <ArrowLeft size={12} /> {t("product.returnToCatalog")}
          </button>
          <h1 className="mb-4 break-words font-black font-display text-3xl text-white uppercase leading-[0.9] tracking-tighter sm:text-4xl md:text-6xl">
            {product.name}
          </h1>
          <div className="flex items-center gap-2 font-mono text-[10px] text-pandora-cyan uppercase tracking-widest">
            <DatabaseIcon category={product.category} />
            <span>
              {t("product.database")} {" // "} {product.category.toUpperCase()} {" // "}{" "}
              {product.sku}
            </span>
          </div>
        </div>

        <div className="mb-12 grid grid-cols-1 gap-8 md:mb-16 md:gap-12 lg:grid-cols-12">
          {/* === LEFT COLUMN: VISUALIZER === */}
          <div className="perspective-1000 lg:col-span-5">
            <motion.div
              className="group relative aspect-square w-full cursor-crosshair overflow-hidden rounded-sm border border-white/10 bg-[#0a0a0a] shadow-2xl shadow-black/50"
              onMouseLeave={handleMouseLeave}
              onMouseMove={handleMouseMove}
              style={{ rotateX, rotateY, transformStyle: "preserve-3d" }}
            >
              {/* Visual Layer - Video Loop or Image */}
              <div className="transform-style-3d absolute inset-0">
                {product.video ? (
                  // Video Loop for visual simulation
                  <video
                    autoPlay
                    className="h-full w-full object-cover opacity-80 transition-opacity group-hover:opacity-100"
                    loop
                    muted
                    playsInline
                    src={product.video}
                  />
                ) : (
                  // Standard image for products without video
                  <img
                    alt={product.name}
                    className="h-full w-full object-cover opacity-60 grayscale transition-all duration-700 group-hover:scale-105 group-hover:opacity-100 group-hover:grayscale-0"
                    src={product.image}
                  />
                )}
              </div>

              {/* Holographic Overlays */}
              <div
                className="pointer-events-none absolute inset-0 opacity-20 mix-blend-overlay"
                style={{
                  backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")`,
                }}
              />
              <div className="absolute inset-0 bg-[linear-gradient(0deg,rgba(0,0,0,0.8)_0%,transparent_50%)]" />
              <motion.div
                className="pointer-events-none absolute inset-0 z-20 hidden mix-blend-screen md:block"
                style={{ background: sheenGradient }}
              />

              {/* OVERLAY: Title & Version (Corner) */}
              <div className="absolute right-0 bottom-0 left-0 z-30 bg-gradient-to-t from-black/90 to-transparent p-4">
                <div className="mb-1 font-bold font-display text-3xl text-white">
                  {product.name}
                </div>
                <div className="inline-block border border-pandora-cyan/20 bg-pandora-cyan/10 px-2 py-0.5 font-mono text-[10px] text-pandora-cyan">
                  {t("product.sysVer")}: {product.version || "1.0.0"}
                </div>
              </div>

              <div className="absolute top-4 right-4 z-30 flex flex-col items-end gap-2">
                {product.popular && (
                  <div className="bg-pandora-cyan px-2 py-0.5 font-bold text-[10px] text-black uppercase shadow-[0_0_10px_#00FFFF]">
                    {t("product.trending")}
                  </div>
                )}
                <div className="h-2 w-2 animate-pulse rounded-full bg-red-500" />
              </div>
            </motion.div>

            {/* System Check Visual */}
            <div className="mt-4 hidden border border-white/10 bg-[#0a0a0a] p-3 md:block">
              <div className="mb-2 flex items-center justify-between font-mono text-[10px] text-gray-500">
                <span className="flex items-center gap-2">
                  <Cpu size={12} /> {t("product.compatibilityCheck")}
                </span>
                <span className="text-pandora-cyan">{systemCheck}%</span>
              </div>
              <div className="relative h-1 w-full overflow-hidden bg-gray-800">
                <div
                  className="h-full bg-pandora-cyan shadow-[0_0_10px_#00FFFF]"
                  style={{ width: `${systemCheck}%`, transition: "width 0.2s ease" }}
                />
              </div>
              {systemCheck === 100 && (
                <div className="mt-2 flex items-center gap-1 font-mono text-[10px] text-green-500">
                  <CheckCircle size={10} /> {t("product.systemOptimized")}
                </div>
              )}
            </div>
          </div>

          {/* === RIGHT COLUMN: DATA MATRIX & SPECS === */}
          <div className="flex flex-col gap-8 lg:col-span-7">
            {/* 1. DATA MATRIX (Price & ID) - REWORKED LAYOUT */}
            <div className="rounded-sm border border-white/10 bg-[#0c0c0c] p-1">
              <div className="grid grid-cols-2 divide-x divide-white/10">
                {/* Block 1: SKU & Status */}
                <div className="flex h-24 flex-col justify-between p-4">
                  <div className="mb-1 font-mono text-[9px] text-gray-500 uppercase tracking-widest">
                    {t("product.moduleIdentifier")}
                  </div>
                  <div className="font-bold font-mono text-lg text-white">{product.sku}</div>
                  <div className="mt-auto flex items-center gap-2">
                    <div className={`h-1.5 w-1.5 rounded-full ${statusDotColor}`} />
                    <span className={`font-mono text-[9px] uppercase ${nodeStatusColor}`}>
                      {statusText}
                    </span>
                  </div>
                </div>
                {/* Block 2: Price */}
                <div className="flex h-24 flex-col justify-between bg-white/[0.02] p-4">
                  <div className="mb-1 text-right font-mono text-[9px] text-gray-500 uppercase tracking-widest">
                    {t("product.allocationCost")}
                  </div>
                  <div className="text-right">
                    {product.msrp && (
                      <div className="mb-1 text-gray-600 text-xs line-through decoration-red-500/50">
                        {formatPrice(product.msrp, product.currency)}
                      </div>
                    )}
                    <div className="flex justify-end gap-1 font-bold font-display text-3xl text-shadow-glow text-white">
                      {formatPrice(product.price, product.currency)}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* 2. TABS & CONTENT */}
            <div className="flex-1">
              <div className="scrollbar-hide mb-6 flex gap-6 overflow-x-auto border-white/10 border-b md:gap-8">
                {(["specs", "files", "manifest"] as const).map((tab) => (
                  <button
                    className={`group relative whitespace-nowrap border-b-2 pb-3 font-bold font-mono text-[10px] uppercase tracking-widest transition-all ${
                      activeTab === tab
                        ? "border-pandora-cyan text-pandora-cyan"
                        : "border-transparent text-gray-600 hover:text-white"
                    }`}
                    key={tab}
                    onClick={() => handleTabChange(tab as TabType)}
                    type="button"
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
                      deliveryLabel={deliveryLabel}
                      durationLabel={durationLabel}
                      nodeStatus={nodeStatus}
                      nodeStatusColor={nodeStatusColor}
                      warrantyLabel={warrantyLabel}
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
        <div className="mt-4 border-white/10 border-t pt-8 md:mt-8">
          <div className="mb-6 flex items-center gap-4 md:mb-8">
            <div className="flex h-10 w-10 items-center justify-center rounded-sm border border-white/10 bg-white/5">
              <Radio className="animate-pulse text-pandora-cyan" size={20} />
            </div>
            <div>
              <h3 className="font-bold font-display text-lg text-white uppercase tracking-wider">
                {t("product.incomingTransmissions")}
              </h3>
              <div className="flex items-center gap-3 font-mono text-[10px] text-gray-500 uppercase">
                <span>{t("product.userLogs")}</span>
                <span className="text-pandora-cyan">● {t("product.liveFeed")}</span>
                <span>
                  {t("product.signalsDetected", { count: (product.reviews || []).length })}
                </span>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {(product.reviews || []).map((review, i) => (
              <div
                className="group relative overflow-hidden border border-white/10 bg-black/40 p-5 transition-all hover:border-white/30"
                key={review.id || i}
              >
                {/* Scanline for log effect */}
                <div className="absolute top-0 left-0 h-[1px] w-full bg-pandora-cyan/30 opacity-0 transition-opacity group-hover:opacity-100" />

                <div className="mb-3 flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className="max-w-[150px] truncate border border-pandora-cyan/20 bg-pandora-cyan/10 px-2 py-0.5 font-bold font-mono text-pandora-cyan text-xs">
                      {review.user || "ANON"}
                    </div>
                    {review.verified && (
                      <span className="flex items-center gap-1 rounded-sm border border-green-900 bg-green-900/10 px-1.5 py-0.5 font-mono text-[9px] text-green-500">
                        <CheckCircle size={8} /> {t("product.verified")}
                      </span>
                    )}
                  </div>
                  <div className="font-mono text-[10px] text-gray-600">{review.date}</div>
                </div>

                <div className="mb-4 border-white/10 border-l pl-4 font-mono text-gray-300 text-sm leading-relaxed">
                  "{review.text}"
                </div>

                <div className="flex items-center justify-between border-white/5 border-t pt-3">
                  <div className="flex gap-1">
                    {Array.from({ length: 5 }).map((_, starIndex) => (
                      <div
                        className={`h-1.5 w-1.5 rounded-full ${starIndex < review.rating ? "bg-pandora-cyan" : "bg-gray-800"}`}
                        key={`star-${review.id}-${starIndex}`}
                      />
                    ))}
                  </div>
                  <div className="font-mono text-[9px] text-gray-600 uppercase">
                    {t("product.signalStrength")}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* === CROSS SELL SECTION: COMPATIBLE MODULES === */}
        <div className="mt-16 border-white/10 border-t pt-8">
          <div className="mb-6 flex items-center justify-between">
            <h3 className="flex items-center gap-2 font-bold font-mono text-gray-400 text-xs uppercase">
              <Server size={14} /> {t("product.compatibleModules")}
            </h3>
            <div className="font-mono text-[9px] text-pandora-cyan">
              {t("product.aiRecommendation")}
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            {relatedProducts.map((rel) => (
              <button
                className="group flex cursor-pointer gap-3 border border-white/10 bg-[#0a0a0a] p-3 text-left transition-all hover:border-pandora-cyan/50 hover:bg-white/[0.02]"
                key={rel.id}
                onClick={() => onProductSelect?.(rel)}
                type="button"
              >
                <div className="relative h-12 w-12 shrink-0 overflow-hidden border border-white/10 bg-black">
                  <img
                    alt={rel.name}
                    className="h-full w-full object-cover opacity-60 grayscale transition-all group-hover:opacity-100 group-hover:grayscale-0"
                    src={rel.image}
                  />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="truncate font-bold text-white text-xs transition-colors group-hover:text-pandora-cyan">
                    {rel.name}
                  </div>
                  <div className="mb-1 font-mono text-[9px] text-gray-500">
                    {rel.category} {" // "} {rel.stock > 0 ? "ONLINE" : "OFFLINE"}
                  </div>
                  <div className="font-bold font-mono text-white text-xs">
                    {formatPrice(rel.price, rel.currency)}
                  </div>
                </div>
                <div className="flex items-center text-gray-600 transition-all group-hover:translate-x-1 group-hover:text-pandora-cyan">
                  <ArrowRight size={14} />
                </div>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* --- STICKY FOOTER (CLEAN TACTICAL STYLE) --- */}
      <div className="fixed right-0 bottom-0 left-0 z-[60] border-white/10 border-t bg-[#050505]/95 p-4 backdrop-blur-md md:left-20">
        <div className="mx-auto flex h-14 max-w-7xl gap-4 md:h-16">
          {/* QUANTITY CONTROL (Left) */}
          <div className="flex w-36 shrink-0 items-center overflow-hidden rounded-sm border border-white/20 bg-black/50">
            <button
              className="flex h-full w-12 items-center justify-center border-white/10 border-r text-gray-400 transition-colors hover:bg-white/5 hover:text-white active:bg-white/10"
              onClick={() => adjustQuantity(-1)}
              type="button"
            >
              <Minus size={18} />
            </button>
            <div className="flex flex-1 items-center justify-center font-bold font-mono text-white text-xl">
              {quantity.toString().padStart(2, "0")}
            </div>
            <button
              className="flex h-full w-12 items-center justify-center border-white/10 border-l text-gray-400 transition-colors hover:bg-white/5 hover:text-white active:bg-white/10"
              onClick={() => adjustQuantity(1)}
              type="button"
            >
              <Plus size={18} />
            </button>
          </div>

          {/* BUY BUTTON (Right) - WITH MICRO-INTERACTION */}
          <button
            className={`group relative flex flex-1 items-center justify-between overflow-hidden rounded-sm px-6 font-bold font-display uppercase tracking-widest transition-all ${getButtonClassName(isDisabled, isSuccess)}
                    `}
            disabled={isDisabled || isAllocating || isSuccess}
            onClick={handleMountModule}
            type="button"
          >
            {/* Animated Background for Loading */}
            {isAllocating && (
              <div className="absolute inset-0 bg-white/20">
                <div className="h-full w-full animate-[scan_1s_infinite] bg-[linear-gradient(90deg,transparent_0%,rgba(255,255,255,0.5)_50%,transparent_100%)]" />
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
              <AnimatePresence mode="wait">{renderButtonContent()}</AnimatePresence>
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
