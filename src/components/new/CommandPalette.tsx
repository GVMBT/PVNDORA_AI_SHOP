
import React, { useState, useEffect, useRef, memo, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, ChevronRight, Command, Package, User, Terminal, LogOut, ShoppingCart, Shield } from 'lucide-react';
import type { CatalogProduct, NavigationTarget } from '../../types/component';
import type { ViewType } from '../app';

// Command palette item types
interface CommandItem {
  id: string;
  label: string;
  icon: React.ReactNode;
  type: 'nav';
  view: ViewType;
}

interface ProductItem {
  id: string;
  label: string;
  icon: React.ReactNode;
  type: 'product';
  product: CatalogProduct;
}

type PaletteItem = CommandItem | ProductItem;

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  onNavigate: (view: NavigationTarget) => void;
  products: CatalogProduct[];
}

const CommandPalette: React.FC<CommandPaletteProps> = ({ isOpen, onClose, onNavigate, products }) => {
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  // Focus input on open
  useEffect(() => {
    if (isOpen) {
        setTimeout(() => inputRef.current?.focus(), 100);
        setQuery('');
        setSelectedIndex(0);
    }
  }, [isOpen]);

  // Filtering Logic - memoized for performance
  const commands = useMemo(() => [
      { id: 'home', label: 'Go to Catalog', icon: <Package size={14} />, type: 'nav', view: 'home' },
      { id: 'orders', label: 'My Orders / Logs', icon: <Terminal size={14} />, type: 'nav', view: 'orders' },
      { id: 'profile', label: 'Operative Profile', icon: <User size={14} />, type: 'nav', view: 'profile' },
      { id: 'leaderboard', label: 'Global Leaderboard', icon: <Shield size={14} />, type: 'nav', view: 'leaderboard' },
  ], []);

  const filteredItems = useMemo(() => {
    if (!query) return commands;
    
    const queryLower = query.toLowerCase();
    const filteredCommands = commands.filter(c => c.label.toLowerCase().includes(queryLower));
    const productResults = products
      .filter(p => p.name.toLowerCase().includes(queryLower))
      .map(p => ({ 
          id: `prod-${p.id}`, 
          label: p.name, 
          icon: <ShoppingCart size={14} />, 
          type: 'product', 
          product: p 
      }));
    
    return [...filteredCommands, ...productResults];
  }, [query, products, commands]);

  // Keyboard Navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
      if (e.key === 'ArrowDown') {
          e.preventDefault();
          setSelectedIndex(prev => (prev + 1) % filteredItems.length);
      } else if (e.key === 'ArrowUp') {
          e.preventDefault();
          setSelectedIndex(prev => (prev - 1 + filteredItems.length) % filteredItems.length);
      } else if (e.key === 'Enter') {
          e.preventDefault();
          executeCommand(filteredItems[selectedIndex]);
      } else if (e.key === 'Escape') {
          onClose();
      }
  };

  const executeCommand = (item: PaletteItem | undefined) => {
      if (!item) return;
      if (item.type === 'nav') {
          onNavigate(item.view);
      } else if (item.type === 'product') {
          onNavigate({ type: 'product', product: item.product });
      }
      onClose();
  };

  return (
    <AnimatePresence>
        {isOpen && (
            <div className="fixed inset-0 z-[200] flex items-start justify-center pt-[15vh] px-4">
                {/* Backdrop */}
                <motion.div 
                    initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                    onClick={onClose}
                    className="absolute inset-0 bg-black/80 backdrop-blur-sm"
                />

                {/* Modal */}
                <motion.div 
                    initial={{ scale: 0.95, opacity: 0, y: -20 }}
                    animate={{ scale: 1, opacity: 1, y: 0 }}
                    exit={{ scale: 0.95, opacity: 0, y: -20 }}
                    transition={{ type: "spring", stiffness: 300, damping: 25 }}
                    className="relative w-full max-w-2xl bg-[#0a0a0a] border border-white/20 shadow-[0_0_50px_rgba(0,0,0,0.8)] rounded-sm overflow-hidden flex flex-col max-h-[60vh]"
                >
                    {/* Header / Input */}
                    <div className="flex items-center gap-4 p-4 border-b border-white/10 bg-white/5 relative z-10">
                        <Search className="text-gray-500" size={20} />
                        <input 
                            ref={inputRef}
                            type="text" 
                            value={query}
                            onChange={(e) => { setQuery(e.target.value); setSelectedIndex(0); }}
                            onKeyDown={handleKeyDown}
                            placeholder="Type a command or search assets..."
                            className="flex-1 bg-transparent border-none outline-none text-lg text-white font-mono placeholder:text-gray-600"
                        />
                        <div className="hidden md:flex items-center gap-1 text-[10px] font-mono text-gray-500 border border-white/10 px-2 py-1 rounded-sm">
                            <span className="text-xs">ESC</span> TO CLOSE
                        </div>
                    </div>

                    {/* Results */}
                    <div className="overflow-y-auto p-2 scrollbar-hide">
                        {filteredItems.length === 0 ? (
                            <div className="py-12 text-center text-gray-600 font-mono text-xs">
                                NO_RESULTS_FOUND_IN_DATABASE
                            </div>
                        ) : (
                            <div className="space-y-1">
                                {filteredItems.map((item, index) => (
                                    <button
                                        key={item.id}
                                        onClick={() => executeCommand(item)}
                                        onMouseEnter={() => setSelectedIndex(index)}
                                        className={`w-full flex items-center justify-between p-3 rounded-sm transition-all group ${
                                            index === selectedIndex ? 'bg-pandora-cyan text-black shadow-[0_0_15px_rgba(0,255,255,0.4)]' : 'text-gray-400 hover:bg-white/5'
                                        }`}
                                    >
                                        <div className="flex items-center gap-3">
                                            <div className={`p-1.5 rounded-sm ${index === selectedIndex ? 'bg-black/20 text-black' : 'bg-white/5 text-gray-500'}`}>
                                                {item.icon}
                                            </div>
                                            <span className={`font-mono text-sm ${index === selectedIndex ? 'font-bold' : ''}`}>
                                                {item.label}
                                            </span>
                                        </div>
                                        {index === selectedIndex && (
                                            <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-wider animate-pulse">
                                                <ChevronRight size={12} />
                                                Execute
                                            </div>
                                        )}
                                    </button>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Footer */}
                    <div className="p-2 border-t border-white/10 bg-[#050505] text-[9px] font-mono text-gray-600 flex justify-between px-4">
                        <span>PANDORA_OS // V.2.4.0</span>
                        <div className="flex gap-4">
                            <span><span className="text-pandora-cyan">↑↓</span> NAVIGATE</span>
                            <span><span className="text-pandora-cyan">↵</span> SELECT</span>
                        </div>
                    </div>
                    
                    {/* Scanline */}
                    <div className="absolute inset-0 pointer-events-none opacity-[0.03] bg-[url('https://grainy-gradients.vercel.app/noise.svg')]" />
                </motion.div>
            </div>
        )}
    </AnimatePresence>
  );
};

export default memo(CommandPalette);
