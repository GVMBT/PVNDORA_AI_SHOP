/**
 * ProductCard - Individual product card with optimized media and parallax
 */

import { motion, useMotionValue } from "framer-motion";
import { Activity, Crosshair, HardDrive, ShoppingCart, Zap } from "lucide-react";
import type React from "react";
import { useLocale } from "../../hooks/useLocale";
import { formatPrice } from "../../utils/currency";
import ProductCardMedia from "./ProductCardMedia";

type ProductAvailability = "available" | "on_demand" | "discontinued" | "coming_soon";

interface ProductData {
  id: string | number;
  name: string;
  category: string;
  price: number;
  currency: string;
  description: string;
  warranty: number;
  sold: number;
  image: string;
  video?: string;
  popular: boolean;
  sku: string;
  status?: ProductAvailability;
}

interface ProductCardProps {
  product: ProductData;
  getProductAvailability: (product: ProductData) => ProductAvailability;
  onSelect: (product: ProductData) => void;
  onAddToCart: (product: ProductData, quantity: number) => void;
}

// Utility for fake hex stream
const HexStream = () => {
  // Static hex values for decorative display (not security-critical)
  const hexValues = ["A3F2", "B7E1", "C9D4", "D2A8", "E5B3", "F1C7", "A8D9", "B4E6"] as const;
  return (
    <div className="flex flex-col font-mono text-[8px] text-pandora-cyan/60 leading-tight opacity-50">
      {hexValues.map((hex) => (
        <span key={hex}>0x{hex}</span>
      ))}
    </div>
  );
};

const ProductCard: React.FC<ProductCardProps> = ({
  product,
  getProductAvailability,
  onSelect,
  onAddToCart,
}) => {
  const { t } = useLocale();

  // Parallax for product card (desktop only)
  const cardX = useMotionValue(0);
  const cardY = useMotionValue(0);

  const handleCardMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (globalThis.innerWidth < 768) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width - 0.5;
    const y = (e.clientY - rect.top) / rect.height - 0.5;
    cardX.set(x);
    cardY.set(y);
  };

  const handleCardMouseLeave = () => {
    cardX.set(0);
    cardY.set(0);
  };

  const avail = getProductAvailability(product);
  const statusConfig = {
    available: {
      color: "bg-green-500",
      textColor: "text-green-500",
      label: t("catalog.availability.available"),
      pulse: true,
    },
    on_demand: {
      color: "bg-yellow-500",
      textColor: "text-yellow-500",
      label: t("catalog.availability.onDemand"),
      pulse: true,
    },
    discontinued: {
      color: "bg-red-500",
      textColor: "text-red-500",
      label: t("catalog.availability.discontinued"),
      pulse: false,
    },
    coming_soon: {
      color: "bg-blue-500",
      textColor: "text-blue-500",
      label: t("catalog.availability.comingSoon"),
      pulse: true,
    },
  }[avail];

  return (
    <motion.div
      animate={{ opacity: 1, scale: 1 }}
      className="group relative flex cursor-pointer flex-col overflow-hidden border border-white/10 bg-[#0a0a0a] shadow-lg transition-all duration-300 hover:border-pandora-cyan/50 hover:shadow-[0_0_30px_rgba(0,255,255,0.1)]"
      exit={{ opacity: 0, scale: 0.95 }}
      initial={{ opacity: 0, scale: 0.95 }}
      layout
      onClick={() => onSelect(product)}
      onMouseLeave={handleCardMouseLeave}
      onMouseMove={handleCardMouseMove}
      transition={{ duration: 0.2 }}
    >
      {/* Technical Header */}
      <div className="relative z-20 flex items-center justify-between border-white/5 border-b bg-white/[0.02] px-4 py-2">
        <span className="font-mono text-[9px] text-gray-500">{product.sku}</span>
        <div className="flex items-center gap-2">
          <div
            className={`h-1.5 w-1.5 rounded-full ${statusConfig.color} ${statusConfig.pulse ? "animate-pulse" : ""}`}
          />
          <span className={`font-mono text-[9px] uppercase ${statusConfig.textColor}`}>
            {statusConfig.label}
          </span>
        </div>
      </div>

      {/* Image & Holographic Grid Section */}
      <div className="relative h-40 w-full overflow-hidden bg-black/50">
        {/* Optimized Media Component (supports video/particles) */}
        <ProductCardMedia
          alt={product.name}
          className="transition-transform duration-700 group-hover:scale-105"
          image={product.image} // Enable particles for popular items
          parallaxX={cardX}
          parallaxY={cardY}
          useParticles={product.popular}
          video={product.video}
        />

        {/* --- HOLOGRAPHIC GRID PROJECTION --- */}
        <div className="pointer-events-none absolute inset-0 z-20 overflow-hidden opacity-0 transition-opacity duration-300 group-hover:opacity-100">
          {/* 1. Moving Grid (Waterflow Effect) */}
          <div
            className="absolute -top-[100%] left-0 h-[300%] w-full animate-[scan_6s_linear_infinite]"
            style={{
              backgroundImage:
                "linear-gradient(to right, rgba(0, 255, 255, 0.15) 1px, transparent 1px), linear-gradient(to bottom, rgba(0, 255, 255, 0.15) 1px, transparent 1px)",
              backgroundSize: "24px 24px",
              maskImage:
                "linear-gradient(to bottom, transparent, black 15%, black 85%, transparent)",
            }}
          />

          {/* 2. Central Targeting Reticle (Rotating) */}
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="flex h-16 w-16 animate-[spin_4s_linear_infinite] items-center justify-center rounded-full border border-pandora-cyan/30">
              <div className="h-12 w-12 rounded-full border-pandora-cyan/60 border-t border-b" />
            </div>
            <Crosshair className="absolute text-pandora-cyan" size={24} />
          </div>

          {/* 3. Data Stream (Right Side) */}
          <div className="absolute top-2 right-1 bottom-2 flex w-8 flex-col items-end justify-center overflow-hidden">
            <HexStream />
          </div>

          {/* 4. Scanning Bar (Visual Lead) */}
          <div className="absolute top-0 left-0 h-full w-full animate-[scan_2s_linear_infinite] bg-gradient-to-b from-transparent via-pandora-cyan/10 to-transparent opacity-50" />
        </div>

        {/* --- TACTICAL BRACKETS (Corner Snapping) --- */}
        <div className="absolute top-0 left-0 z-30 h-3 w-3 -translate-x-2 -translate-y-2 transform border-pandora-cyan border-t-2 border-l-2 opacity-0 transition-all duration-200 group-hover:translate-x-1 group-hover:translate-y-1 group-hover:opacity-100" />
        <div className="absolute top-0 right-0 z-30 h-3 w-3 translate-x-2 -translate-y-2 transform border-pandora-cyan border-t-2 border-r-2 opacity-0 transition-all duration-200 group-hover:-translate-x-1 group-hover:translate-y-1 group-hover:opacity-100" />
        <div className="absolute bottom-0 left-0 z-30 h-3 w-3 -translate-x-2 translate-y-2 transform border-pandora-cyan border-b-2 border-l-2 opacity-0 transition-all duration-200 group-hover:translate-x-1 group-hover:-translate-y-1 group-hover:opacity-100" />
        <div className="absolute right-0 bottom-0 z-30 h-3 w-3 translate-x-2 translate-y-2 transform border-pandora-cyan border-r-2 border-b-2 opacity-0 transition-all duration-200 group-hover:-translate-x-1 group-hover:-translate-y-1 group-hover:opacity-100" />

        {/* Trending Badge */}
        {product.popular && (
          <div className="absolute top-2 left-2 z-30 flex items-center gap-1 bg-pandora-cyan px-2 py-0.5 font-bold text-[9px] text-black uppercase tracking-wider shadow-[0_0_10px_#00FFFF]">
            <Zap fill="currentColor" size={8} /> {t("catalog.card.trending")}
          </div>
        )}
      </div>

      {/* Info Body */}
      <div className="relative flex flex-grow flex-col bg-[#0a0a0a] p-4">
        <div className="mb-4">
          <div className="flex items-start justify-between">
            <h3 className="line-clamp-1 font-bold font-display text-sm text-white tracking-wide transition-colors group-hover:text-pandora-cyan">
              {product.name}
            </h3>
            <span className="rounded border border-white/10 bg-white/5 px-1.5 font-mono text-[9px] text-gray-500">
              {product.category}
            </span>
          </div>
          <div className="my-3 h-px w-full bg-white/10 transition-colors group-hover:bg-pandora-cyan/30" />

          {/* Mini Specs */}
          <div className="grid grid-cols-2 gap-2 font-mono text-[10px] text-gray-400">
            <div className="flex items-center gap-1">
              <HardDrive size={10} /> {t("catalog.card.warranty", { hours: product.warranty })}
            </div>
            <div className="flex items-center gap-1">
              <Activity size={10} /> {t("catalog.card.sold", { count: product.sold })}
            </div>
          </div>
        </div>

        <div className="mt-auto flex items-center justify-between">
          <div className="flex flex-col">
            <span className="font-mono text-[9px] text-gray-600 uppercase">
              {t("catalog.creditsRequired")}
            </span>
            <div className="font-bold text-lg text-white transition-colors group-hover:text-pandora-cyan">
              {formatPrice(product.price, product.currency)}
            </div>
          </div>
          <button
            className="group/btn border border-white/10 bg-white/5 p-2 text-white shadow-none transition-all hover:border-pandora-cyan hover:bg-pandora-cyan hover:text-black hover:shadow-[0_0_15px_#00FFFF]"
            onClick={(e) => {
              e.stopPropagation();
              onAddToCart(product, 1);
            }}
            type="button"
          >
            <ShoppingCart size={16} />
          </button>
        </div>
      </div>
    </motion.div>
  );
};

export default ProductCard;
