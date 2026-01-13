/**
 * ProductCard - Individual product card with optimized media and parallax
 */

import React from "react";
import { motion, useMotionValue, useTransform } from "framer-motion";
import { ShoppingCart, Zap, HardDrive, Activity, Crosshair } from "lucide-react";
import { formatPrice } from "../../utils/currency";
import { useLocale } from "../../hooks/useLocale";
import ProductCardMedia from "./ProductCardMedia";

interface ProductCardProps {
  product: {
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
    status?: "available" | "on_demand" | "discontinued" | "coming_soon";
  };
  getProductAvailability: (
    product: any
  ) => "available" | "on_demand" | "discontinued" | "coming_soon";
  onSelect: (product: any) => void;
  onAddToCart: (product: any, quantity: number) => void;
}

// Utility for fake hex stream
const HexStream = () => {
  return (
    <div className="flex flex-col text-[8px] font-mono text-pandora-cyan/60 leading-tight opacity-50">
      {Array.from({ length: 8 }).map((_, i) => (
        <span key={i}>0x{Math.random().toString(16).substr(2, 4).toUpperCase()}</span>
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
      layout
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={{ duration: 0.2 }}
      onClick={() => onSelect(product)}
      onMouseMove={handleCardMouseMove}
      onMouseLeave={handleCardMouseLeave}
      className="group relative bg-[#0a0a0a] border border-white/10 flex flex-col overflow-hidden hover:border-pandora-cyan/50 transition-all duration-300 cursor-pointer shadow-lg hover:shadow-[0_0_30px_rgba(0,255,255,0.1)]"
    >
      {/* Technical Header */}
      <div className="flex justify-between items-center px-4 py-2 border-b border-white/5 bg-white/[0.02] relative z-20">
        <span className="text-[9px] font-mono text-gray-500">{product.sku}</span>
        <div className="flex items-center gap-2">
          <div
            className={`w-1.5 h-1.5 rounded-full ${statusConfig.color} ${statusConfig.pulse ? "animate-pulse" : ""}`}
          />
          <span className={`text-[9px] font-mono uppercase ${statusConfig.textColor}`}>
            {statusConfig.label}
          </span>
        </div>
      </div>

      {/* Image & Holographic Grid Section */}
      <div className="h-40 w-full relative overflow-hidden bg-black/50">
        {/* Optimized Media Component (supports video/particles) */}
        <ProductCardMedia
          image={product.image}
          video={product.video}
          useParticles={product.popular} // Enable particles for popular items
          parallaxX={cardX}
          parallaxY={cardY}
          alt={product.name}
          className="group-hover:scale-105 transition-transform duration-700"
        />

        {/* --- HOLOGRAPHIC GRID PROJECTION --- */}
        <div className="absolute inset-0 z-20 pointer-events-none overflow-hidden opacity-0 group-hover:opacity-100 transition-opacity duration-300">
          {/* 1. Moving Grid (Waterflow Effect) */}
          <div
            className="absolute -top-[100%] left-0 w-full h-[300%] animate-[scan_6s_linear_infinite]"
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
            <div className="w-16 h-16 border border-pandora-cyan/30 rounded-full flex items-center justify-center animate-[spin_4s_linear_infinite]">
              <div className="w-12 h-12 border-t border-b border-pandora-cyan/60 rounded-full" />
            </div>
            <Crosshair size={24} className="text-pandora-cyan absolute" />
          </div>

          {/* 3. Data Stream (Right Side) */}
          <div className="absolute right-1 top-2 bottom-2 w-8 overflow-hidden flex flex-col justify-center items-end">
            <HexStream />
          </div>

          {/* 4. Scanning Bar (Visual Lead) */}
          <div className="absolute top-0 left-0 w-full h-full bg-gradient-to-b from-transparent via-pandora-cyan/10 to-transparent animate-[scan_2s_linear_infinite] opacity-50" />
        </div>

        {/* --- TACTICAL BRACKETS (Corner Snapping) --- */}
        <div className="absolute top-0 left-0 w-3 h-3 border-t-2 border-l-2 border-pandora-cyan z-30 transition-all duration-200 transform -translate-x-2 -translate-y-2 opacity-0 group-hover:translate-x-1 group-hover:translate-y-1 group-hover:opacity-100" />
        <div className="absolute top-0 right-0 w-3 h-3 border-t-2 border-r-2 border-pandora-cyan z-30 transition-all duration-200 transform translate-x-2 -translate-y-2 opacity-0 group-hover:-translate-x-1 group-hover:translate-y-1 group-hover:opacity-100" />
        <div className="absolute bottom-0 left-0 w-3 h-3 border-b-2 border-l-2 border-pandora-cyan z-30 transition-all duration-200 transform -translate-x-2 translate-y-2 opacity-0 group-hover:translate-x-1 group-hover:-translate-y-1 group-hover:opacity-100" />
        <div className="absolute bottom-0 right-0 w-3 h-3 border-b-2 border-r-2 border-pandora-cyan z-30 transition-all duration-200 transform translate-x-2 translate-y-2 opacity-0 group-hover:-translate-x-1 group-hover:-translate-y-1 group-hover:opacity-100" />

        {/* Trending Badge */}
        {product.popular && (
          <div className="absolute top-2 left-2 bg-pandora-cyan text-black text-[9px] font-bold px-2 py-0.5 uppercase tracking-wider flex items-center gap-1 z-30 shadow-[0_0_10px_#00FFFF]">
            <Zap size={8} fill="currentColor" /> {t("catalog.card.trending")}
          </div>
        )}
      </div>

      {/* Info Body */}
      <div className="p-4 flex flex-col flex-grow relative bg-[#0a0a0a]">
        <div className="mb-4">
          <div className="flex justify-between items-start">
            <h3 className="text-sm font-display font-bold text-white tracking-wide group-hover:text-pandora-cyan transition-colors line-clamp-1">
              {product.name}
            </h3>
            <span className="text-[9px] font-mono text-gray-500 border border-white/10 px-1.5 rounded bg-white/5">
              {product.category}
            </span>
          </div>
          <div className="w-full h-px bg-white/10 my-3 group-hover:bg-pandora-cyan/30 transition-colors" />

          {/* Mini Specs */}
          <div className="grid grid-cols-2 gap-2 text-[10px] font-mono text-gray-400">
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
            <span className="text-[9px] text-gray-600 font-mono uppercase">
              {t("catalog.creditsRequired")}
            </span>
            <div className="text-lg font-bold text-white group-hover:text-pandora-cyan transition-colors">
              {formatPrice(product.price, product.currency)}
            </div>
          </div>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onAddToCart(product, 1);
            }}
            className="bg-white/5 hover:bg-pandora-cyan text-white hover:text-black p-2 border border-white/10 hover:border-pandora-cyan transition-all group/btn shadow-none hover:shadow-[0_0_15px_#00FFFF]"
          >
            <ShoppingCart size={16} />
          </button>
        </div>
      </div>
    </motion.div>
  );
};

export default ProductCard;
