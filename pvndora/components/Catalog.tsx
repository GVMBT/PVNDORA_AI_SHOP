
import React, { useState, useMemo } from 'react';
import { Search, ShoppingCart, ArrowUpRight, Zap, List, Grid, ChevronDown, Check, Cpu, HardDrive, Disc, Activity, Lock, ScanLine, Crosshair, Binary, Box, Database, Server } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

// --- MOCK DATA ---
const PRODUCTS = [
  { 
    id: 1, 
    name: 'Nano Banana Pro', 
    category: 'Text', 
    price: 299,
    msrp: 500,
    description: 'Get full access to GPT-4 Turbo via decentralized nodes. Includes priority queue handling, zero-logging policy, and direct API access.',
    warranty: 720, // Hours
    duration: 30, // Days
    instructions: "1. Download the portable client.\n2. Use the provided session token.\n3. Connect via USA VPN node.",
    image: 'https://images.unsplash.com/photo-1677442136019-21780ecad995?q=80&w=800&auto=format&fit=crop', 
    popular: true, 
    stock: 12,
    fulfillment: 0,
    sold: 1542,
    vpn: true,
    video: "https://youtube.com/watch?v=dQw4w9WgXcQ",
    sku: "NANO-BP-01",
    version: "v4.2.1"
  },
  { 
    id: 2, 
    name: 'Veo 3.1', 
    category: 'Video', 
    price: 450, 
    msrp: 800,
    description: 'High-fidelity video generation model. Supports 1080p rendering and prompt-to-video capabilities.',
    warranty: 168,
    duration: 30,
    instructions: "1. Access the web portal.\n2. Login with email:pass.\n3. Do not change profile settings.",
    image: 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?q=80&w=800&auto=format&fit=crop', 
    popular: true, 
    stock: 0,
    fulfillment: 0,
    sold: 890,
    vpn: false,
    sku: "VEO-VID-X",
    version: "v3.1.0"
  },
  { 
    id: 3, 
    name: 'Claude Max', 
    category: 'Text', 
    price: 350, 
    msrp: 600,
    description: 'Large context window model (200k tokens). Ideal for code analysis and book summarization.',
    warranty: 720,
    duration: 30,
    instructions: "Wait for email invite (approx 24h). Click the link to activate your workspace.",
    image: 'https://images.unsplash.com/photo-1620712943543-bcc4688e7485?q=80&w=800&auto=format&fit=crop', 
    popular: false, 
    stock: 5,
    fulfillment: 24,
    sold: 430,
    vpn: true,
    sku: "CLD-MX-200",
    version: "v2.1"
  },
  { 
    id: 4, 
    name: 'GitHub Copilot', 
    category: 'Code', 
    price: 190, 
    msrp: 1000,
    description: 'AI pair programmer. Autocomplete-style suggestions for code.',
    warranty: 720,
    duration: 30,
    instructions: "Login with the provided GitHub credentials.",
    image: 'https://images.unsplash.com/photo-1555066931-4365d14bab8c?q=80&w=800&auto=format&fit=crop', 
    popular: false, 
    stock: 8,
    fulfillment: 0,
    sold: 1200,
    vpn: false,
    sku: "GIT-CP-V2",
    version: "ENT-Edition"
  },
  { 
    id: 5, 
    name: 'Runway Gen-2', 
    category: 'Video', 
    price: 600, 
    msrp: 1200,
    description: 'Text-to-video synthesis. Create realistic videos from text descriptions.',
    warranty: 168,
    duration: 30,
    instructions: "Redeem the promo code in your account settings.",
    image: 'https://images.unsplash.com/photo-1550751827-4bd374c3f58b?q=80&w=800&auto=format&fit=crop', 
    popular: false, 
    stock: 0,
    fulfillment: 0,
    sold: 210,
    vpn: true,
    sku: "RW-G2-GEN",
    version: "v2.0"
  },
  { 
    id: 6, 
    name: 'Jasper AI', 
    category: 'Text', 
    price: 250, 
    msrp: 400,
    description: 'AI copywriter for marketing, blog posts, and social media.',
    warranty: 720,
    duration: 30,
    instructions: "Login to the shared team account.",
    image: 'https://images.unsplash.com/photo-1516110833967-0b5716ca1387?q=80&w=800&auto=format&fit=crop', 
    popular: false, 
    stock: 20,
    fulfillment: 0,
    sold: 650,
    vpn: false,
    sku: "JSP-CP-BIZ",
    version: "Pro"
  },
  { 
    id: 7, 
    name: 'Leonardo AI', 
    category: 'Image', 
    price: 320, 
    msrp: 500,
    description: 'Create production-quality visual assets for your projects.',
    warranty: 720,
    duration: 30,
    instructions: "Use the cookie method to access the pro features.",
    image: 'https://images.unsplash.com/photo-1633167606204-071160196276?q=80&w=800&auto=format&fit=crop', 
    popular: false, 
    stock: 3,
    fulfillment: 0,
    sold: 45,
    vpn: true,
    sku: "LEO-ART-01",
    version: "v.XL"
  },
  { 
    id: 8, 
    name: 'ElevenLabs', 
    category: 'Audio', 
    price: 210, 
    msrp: 400,
    description: 'The most realistic AI text-to-speech and voice cloning software.',
    warranty: 720,
    duration: 30,
    instructions: "API key will be sent to your dashboard.",
    image: 'https://images.unsplash.com/photo-1558486012-81714731dca7?q=80&w=800&auto=format&fit=crop', 
    popular: true, 
    stock: 0,
    fulfillment: 0,
    sold: 890,
    vpn: false,
    sku: "EL-VOC-SYN",
    version: "Voice-Gen-1"
  },
];

const CATEGORIES = ['All', 'Text', 'Image', 'Video', 'Code', 'Audio'];

type SortOption = 'popular' | 'price_asc' | 'price_desc';
type ViewMode = 'grid' | 'list';

interface CatalogProps {
  onSelectProduct?: (product: any) => void;
  onHaptic?: (type?: 'light' | 'medium') => void;
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

const Catalog: React.FC<CatalogProps> = ({ onSelectProduct, onHaptic }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [activeCategory, setActiveCategory] = useState('All');
  const [viewMode, setViewMode] = useState<ViewMode>('grid');
  const [sortBy, setSortBy] = useState<SortOption>('popular');
  const [isSortOpen, setIsSortOpen] = useState(false);

  const filteredProducts = useMemo(() => {
    let result = PRODUCTS.filter(product => {
      const matchesSearch = product.name.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesCategory = activeCategory === 'All' || product.category === activeCategory;
      return matchesSearch && matchesCategory;
    });

    // Sorting Logic
    result = result.sort((a, b) => {
      if (sortBy === 'price_asc') return a.price - b.price;
      if (sortBy === 'price_desc') return b.price - a.price;
      // Default: Popular (Items with popular:true come first)
      return (a.popular === b.popular) ? 0 : a.popular ? -1 : 1;
    });

    return result;
  }, [searchQuery, activeCategory, sortBy]);

  const handleCategoryChange = (cat: string) => {
      if (onHaptic) onHaptic('light');
      setActiveCategory(cat);
  };

  const handleProductClick = (product: any) => {
      if (onHaptic) onHaptic('medium');
      if (onSelectProduct) onSelectProduct(product);
  };

  return (
    <section id="catalog" className="relative w-full bg-transparent text-white pt-24 pb-24 px-6 md:pl-28 md:pt-32 md:-mt-24 min-h-screen z-30">
      
      {/* === VISUAL CONNECTOR (DATA STREAM) FROM HERO === */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 h-20 w-px bg-gradient-to-b from-transparent via-pandora-cyan/30 to-transparent z-0 opacity-50" />
      
      {/* --- HEADER ROW --- */}
      <div className="max-w-7xl mx-auto mb-10 flex flex-col xl:flex-row gap-6 items-start xl:items-end justify-between relative z-10 pt-8">
        
        {/* Title Area: NARRATIVE UPDATE (Techno/Module) */}
        <div>
          <h2 className="text-3xl font-display font-bold text-white mb-2 flex items-center gap-3">
            <span className="w-2 h-8 bg-pandora-cyan block rounded-sm shadow-[0_0_10px_#00FFFF]"></span>
            NEURAL_MODULES
          </h2>
          <p className="text-gray-500 font-mono text-xs tracking-widest uppercase flex items-center gap-2">
              <Cpu size={12} className="text-pandora-cyan" />
              <span>SOURCE: COMPUTE_NODES</span>
              <span className="text-gray-700">|</span>
              <span className="text-pandora-cyan">STATUS: OPERATIONAL</span>
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
                    placeholder="SEARCH_MODULES..."
                    className="w-full bg-[#0a0a0a] border border-white/10 text-white text-sm rounded-sm py-3 pl-10 pr-4 focus:outline-none focus:border-pandora-cyan/50 focus:bg-[#0f0f0f] transition-all placeholder:text-gray-600 font-mono uppercase tracking-wider"
                />
            </div>

            <div className="flex gap-4">
                {/* Sort Dropdown */}
                <div className="relative">
                    <button 
                        onClick={() => { if(onHaptic) onHaptic('light'); setIsSortOpen(!isSortOpen); }}
                        className="h-full px-4 flex items-center gap-2 bg-[#0a0a0a] border border-white/10 hover:border-pandora-cyan/50 text-sm font-mono text-gray-300 transition-all rounded-sm min-w-[160px] justify-between"
                    >
                        <span className="uppercase text-[10px] tracking-wider">
                            {sortBy === 'popular' && 'FILTER: POPULAR'}
                            {sortBy === 'price_asc' && 'FILTER: COST ASC'}
                            {sortBy === 'price_desc' && 'FILTER: COST DESC'}
                        </span>
                        <ChevronDown size={14} className={`transition-transform ${isSortOpen ? 'rotate-180' : ''}`} />
                    </button>
                    
                    <AnimatePresence>
                        {isSortOpen && (
                            <motion.div 
                                initial={{ opacity: 0, y: -10 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0, y: -10 }}
                                className="absolute top-full left-0 right-0 mt-2 bg-[#0a0a0a] border border-white/20 z-50 shadow-xl shadow-black/80"
                            >
                                {[
                                    { label: 'POPULARITY_RANK', value: 'popular' },
                                    { label: 'COST: LOW > HIGH', value: 'price_asc' },
                                    { label: 'COST: HIGH > LOW', value: 'price_desc' }
                                ].map((option) => (
                                    <button
                                        key={option.value}
                                        onClick={() => { if(onHaptic) onHaptic('light'); setSortBy(option.value as SortOption); setIsSortOpen(false); }}
                                        className="w-full text-left px-4 py-2 text-[10px] uppercase font-mono hover:bg-white/10 hover:text-pandora-cyan flex items-center justify-between"
                                    >
                                        {option.label}
                                        {sortBy === option.value && <Check size={12} className="text-pandora-cyan" />}
                                    </button>
                                ))}
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>

                {/* View Toggle */}
                <div className="flex bg-[#0a0a0a] border border-white/10 p-1 rounded-sm gap-1">
                    <button 
                        onClick={() => { if(onHaptic) onHaptic('light'); setViewMode('grid'); }}
                        className={`p-2 rounded-sm transition-all ${viewMode === 'grid' ? 'bg-white/10 text-pandora-cyan' : 'text-gray-600 hover:text-white'}`}
                    >
                        <Grid size={16} />
                    </button>
                    <button 
                        onClick={() => { if(onHaptic) onHaptic('light'); setViewMode('list'); }}
                        className={`p-2 rounded-sm transition-all ${viewMode === 'list' ? 'bg-white/10 text-pandora-cyan' : 'text-gray-600 hover:text-white'}`}
                    >
                        <List size={16} />
                    </button>
                </div>
            </div>
        </div>
      </div>

      {/* --- CATEGORY TABS --- */}
      <div className="max-w-7xl mx-auto mb-8 border-b border-white/5 pb-1">
         <div className="flex gap-6 overflow-x-auto pb-2 scrollbar-hide">
            {CATEGORIES.map((cat) => (
                <button
                key={cat}
                onClick={() => handleCategoryChange(cat)}
                className={`
                    relative pb-2 text-sm font-display font-medium tracking-wide transition-all duration-300 whitespace-nowrap uppercase
                    ${activeCategory === cat 
                    ? 'text-pandora-cyan drop-shadow-[0_0_8px_rgba(0,255,255,0.5)]' 
                    : 'text-gray-500 hover:text-gray-300'}
                `}
                >
                <span className="mr-1 opacity-50 text-[10px] font-mono">0{CATEGORIES.indexOf(cat) + 1}.</span>
                {cat}
                {activeCategory === cat && (
                    <motion.div layoutId="activeTab" className="absolute bottom-0 left-0 right-0 h-0.5 bg-pandora-cyan shadow-[0_0_10px_#00FFFF]" />
                )}
                </button>
            ))}
         </div>
      </div>

      {/* --- CONTENT AREA --- */}
      <div className="max-w-7xl mx-auto min-h-[400px]">
        <AnimatePresence mode="wait">
            
            {/* === GRID VIEW (IMPROVED SCAN EFFECT) === */}
            {viewMode === 'grid' ? (
                <motion.div 
                    key="grid"
                    initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                    className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6"
                >
                    {filteredProducts.map((product) => (
                        <motion.div
                        layout
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.95 }}
                        transition={{ duration: 0.2 }}
                        key={product.id}
                        onClick={() => handleProductClick(product)}
                        className="group relative bg-[#0a0a0a] border border-white/10 flex flex-col overflow-hidden hover:border-pandora-cyan/50 transition-all duration-300 cursor-pointer shadow-lg hover:shadow-[0_0_30px_rgba(0,255,255,0.1)]"
                        >
                            {/* Technical Header */}
                            <div className="flex justify-between items-center px-4 py-2 border-b border-white/5 bg-white/[0.02] relative z-20">
                                <span className="text-[9px] font-mono text-gray-500">{product.sku}</span>
                                <div className="flex items-center gap-2">
                                    <div className={`w-1.5 h-1.5 rounded-full ${product.stock > 0 ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
                                    <span className={`text-[9px] font-mono uppercase ${product.stock > 0 ? 'text-green-500' : 'text-red-500'}`}>{product.stock > 0 ? 'AVAILABLE' : 'DEPLETED'}</span>
                                </div>
                            </div>

                            {/* Image & Holographic Grid Section */}
                            <div className="h-40 w-full relative overflow-hidden bg-black/50">
                                {/* Base Image */}
                                <img 
                                    src={product.image} 
                                    alt={product.name} 
                                    className="absolute inset-0 w-full h-full object-cover opacity-60 grayscale group-hover:opacity-100 group-hover:grayscale-0 transition-all duration-700 group-hover:scale-105" 
                                />
                                
                                {/* --- HOLOGRAPHIC GRID PROJECTION --- */}
                                <div className="absolute inset-0 z-20 pointer-events-none overflow-hidden opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                                    
                                    {/* 1. Moving Grid (Waterflow Effect) */}
                                    <div 
                                        className="absolute -top-[100%] left-0 w-full h-[300%] animate-[scan_6s_linear_infinite]"
                                        style={{
                                            backgroundImage: 'linear-gradient(to right, rgba(0, 255, 255, 0.15) 1px, transparent 1px), linear-gradient(to bottom, rgba(0, 255, 255, 0.15) 1px, transparent 1px)',
                                            backgroundSize: '24px 24px',
                                            maskImage: 'linear-gradient(to bottom, transparent, black 15%, black 85%, transparent)'
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
                                {/* Top Left */}
                                <div className="absolute top-0 left-0 w-3 h-3 border-t-2 border-l-2 border-pandora-cyan z-30 transition-all duration-200 transform -translate-x-2 -translate-y-2 opacity-0 group-hover:translate-x-1 group-hover:translate-y-1 group-hover:opacity-100" />
                                {/* Top Right */}
                                <div className="absolute top-0 right-0 w-3 h-3 border-t-2 border-r-2 border-pandora-cyan z-30 transition-all duration-200 transform translate-x-2 -translate-y-2 opacity-0 group-hover:-translate-x-1 group-hover:translate-y-1 group-hover:opacity-100" />
                                {/* Bottom Left */}
                                <div className="absolute bottom-0 left-0 w-3 h-3 border-b-2 border-l-2 border-pandora-cyan z-30 transition-all duration-200 transform -translate-x-2 translate-y-2 opacity-0 group-hover:translate-x-1 group-hover:-translate-y-1 group-hover:opacity-100" />
                                {/* Bottom Right */}
                                <div className="absolute bottom-0 right-0 w-3 h-3 border-b-2 border-r-2 border-pandora-cyan z-30 transition-all duration-200 transform translate-x-2 translate-y-2 opacity-0 group-hover:-translate-x-1 group-hover:-translate-y-1 group-hover:opacity-100" />

                                {/* Trending Badge */}
                                {product.popular && (
                                    <div className="absolute top-2 left-2 bg-pandora-cyan text-black text-[9px] font-bold px-2 py-0.5 uppercase tracking-wider flex items-center gap-1 z-30 shadow-[0_0_10px_#00FFFF]">
                                        <Zap size={8} fill="currentColor" /> Trending
                                    </div>
                                )}
                            </div>
                            
                            {/* Info Body */}
                            <div className="p-4 flex flex-col flex-grow relative bg-[#0a0a0a]">
                                <div className="mb-4">
                                    <div className="flex justify-between items-start">
                                        <h3 className="text-sm font-display font-bold text-white tracking-wide group-hover:text-pandora-cyan transition-colors line-clamp-1">{product.name}</h3>
                                        <span className="text-[9px] font-mono text-gray-500 border border-white/10 px-1.5 rounded bg-white/5">{product.category}</span>
                                    </div>
                                    <div className="w-full h-px bg-white/10 my-3 group-hover:bg-pandora-cyan/30 transition-colors" />
                                    
                                    {/* Mini Specs */}
                                    <div className="grid grid-cols-2 gap-2 text-[10px] font-mono text-gray-400">
                                        <div className="flex items-center gap-1"><HardDrive size={10} /> {product.warranty}H WAR</div>
                                        <div className="flex items-center gap-1"><Activity size={10} /> {product.sold}+ SOLD</div>
                                    </div>
                                </div>

                                <div className="mt-auto flex items-center justify-between">
                                    <div className="flex flex-col">
                                        <span className="text-[9px] text-gray-600 font-mono uppercase">Credits Required</span>
                                        <div className="text-lg font-bold text-white group-hover:text-pandora-cyan transition-colors">{product.price} ₽</div>
                                    </div>
                                    <button className="bg-white/5 hover:bg-pandora-cyan text-white hover:text-black p-2 border border-white/10 hover:border-pandora-cyan transition-all group/btn shadow-none hover:shadow-[0_0_15px_#00FFFF]">
                                        <ShoppingCart size={16} />
                                    </button>
                                </div>
                            </div>
                        </motion.div>
                    ))}
                </motion.div>
            ) : (
                
                /* === LIST VIEW (TERMINAL STYLE) === */
                <motion.div 
                    key="list"
                    initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
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
                                    <img src={product.image} className="absolute inset-0 w-full h-full object-cover opacity-50 grayscale group-hover:opacity-100 group-hover:grayscale-0 transition-all" />
                                    <div className="relative z-10 font-mono text-[9px] text-white bg-black/50 px-1">{product.category.substring(0,3).toUpperCase()}</div>
                                </div>
                                <div>
                                    <div className="flex items-center gap-3">
                                        <h3 className="text-sm font-bold text-white font-mono uppercase tracking-wider group-hover:text-pandora-cyan">{product.name}</h3>
                                        {product.popular && <span className="text-[9px] text-pandora-cyan bg-pandora-cyan/10 px-1">HOT</span>}
                                    </div>
                                    <div className="text-[10px] font-mono text-gray-500">SKU: {product.sku} // VER: {product.version}</div>
                                </div>
                            </div>

                            <div className="flex items-center gap-8 md:gap-12 pr-4">
                                <div className="hidden md:flex flex-col items-end">
                                    <div className="flex items-center gap-2">
                                        <div className={`w-1.5 h-1.5 rounded-full ${product.stock > 0 ? 'bg-green-500' : 'bg-red-500'}`} />
                                        <span className="text-[10px] font-mono text-gray-400">{product.stock > 0 ? `QTY: ${product.stock}` : 'OUT_OF_STOCK'}</span>
                                    </div>
                                </div>

                                <div className="flex items-center gap-4 min-w-[100px] justify-end">
                                    <span className="block text-lg font-bold text-white font-mono">{product.price} ₽</span>
                                    <ChevronDown className="-rotate-90 text-gray-600 group-hover:text-pandora-cyan transition-colors" size={16} />
                                </div>
                            </div>
                        </motion.div>
                     ))}
                </motion.div>
            )}

        </AnimatePresence>

        {filteredProducts.length === 0 && (
            <div className="text-center py-20 opacity-50 border border-dashed border-white/10 mt-10">
                <p className="font-mono text-pandora-cyan text-lg">SYSTEM_ERROR: NO_DATA_FOUND</p>
                <p className="text-sm text-gray-500 mt-2">Adjust filter parameters and retry sequence.</p>
            </div>
        )}
      </div>

    </section>
  );
};

export default Catalog;
