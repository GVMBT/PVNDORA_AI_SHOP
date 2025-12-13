
import React, { useState, useEffect, useRef } from 'react';
import { ShoppingBag, Box, User, Trophy, ShoppingCart, Activity, Shield, LogOut, ChevronRight, Zap, LayoutGrid, Command } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { AudioEngine } from '../../lib/AudioEngine';

interface NavbarProps {
  showMobile?: boolean;
  cartCount?: number;
  onOpenCart?: () => void;
  onNavigateHome?: () => void;
  onNavigateOrders?: () => void;
  onNavigateProfile?: () => void;
  onNavigateLeaderboard?: () => void;
  activeTab?: 'catalog' | 'orders' | 'profile' | 'leaderboard';
  onHaptic?: () => void;
}

// --- UTILITY: TYPEWRITER EFFECT ---
const Typewriter: React.FC<{ text: string; delay?: number; speed?: number }> = ({ text, delay = 0, speed = 30 }) => {
  const [displayedText, setDisplayedText] = useState('');

  useEffect(() => {
    // Reset on mount/change
    setDisplayedText('');
    
    const startTimeout = setTimeout(() => {
        let index = 0;
        // Start with first character immediately
        if (text.length > 0) setDisplayedText(text[0]);
        
        const interval = setInterval(() => {
            index++;
            if (index < text.length) {
                setDisplayedText((prev) => text.slice(0, index + 1));
            } else {
                clearInterval(interval);
            }
        }, speed);
        
        return () => clearInterval(interval);
    }, delay);

    return () => clearTimeout(startTimeout);
  }, [text, delay, speed]);

  return <span>{displayedText}</span>;
};

const Navbar: React.FC<NavbarProps> = ({ 
    showMobile = true, 
    cartCount = 0, 
    onOpenCart, 
    onNavigateHome, 
    onNavigateOrders,
    onNavigateProfile, 
    onNavigateLeaderboard,
    activeTab = 'catalog',
    onHaptic
}) => {
  const [isHovered, setIsHovered] = useState(false);
  const wasHoveredRef = useRef(false);

  // Play typewriter sound when sidebar expands
  useEffect(() => {
    if (isHovered && !wasHoveredRef.current) {
      AudioEngine.panelOpen();
      AudioEngine.typewriter(6);
    } else if (!isHovered && wasHoveredRef.current) {
      AudioEngine.panelClose();
    }
    wasHoveredRef.current = isHovered;
  }, [isHovered]);

  const handleClick = (callback?: () => void) => {
      if (onHaptic) onHaptic();
      if (callback) callback();
  };

  return (
    <>
      {/* === DESKTOP SIDEBAR (Expandable) === */}
      <motion.nav 
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        initial={{ width: 80 }}
        animate={{ width: isHovered ? 288 : 80 }}
        transition={{ type: "spring", stiffness: 300, damping: 30 }}
        className="hidden md:flex fixed top-0 left-0 h-screen z-50 flex-col bg-[#050505] border-r border-white/10 overflow-hidden shadow-[10px_0_30px_rgba(0,0,0,0.5)]"
      >
        
        {/* Logo Section */}
        <div className="h-24 flex items-center shrink-0 relative px-5 cursor-pointer" onClick={() => handleClick(onNavigateHome)}>
             <div className="w-10 h-10 flex items-center justify-center relative z-10 group">
                {/* Logo Glow (Internal Core) */}
                <div className="absolute inset-0 bg-pandora-cyan blur-md opacity-40 group-hover:opacity-60 transition-opacity" />
                
                {/* Custom Split Cube Logo SVG */}
                <svg width="32" height="32" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" className="relative z-10 drop-shadow-[0_0_10px_rgba(0,255,255,0.3)]">
                    <path d="M16 4L26 9V23L16 28L6 23V9L16 4Z" fill="#00FFFF" className="opacity-0 group-hover:opacity-20 transition-opacity animate-pulse"/>
                    <path d="M16 4V28" stroke="#00FFFF" strokeWidth="2" strokeLinecap="round" className="blur-[1px] opacity-80" />
                    <path d="M14 6L6 10V22L14 26V6Z" fill="#050505" stroke="white" strokeWidth="1.5" strokeLinejoin="round"/>
                    <path d="M6 10L14 14" stroke="white" strokeWidth="0.5" strokeOpacity="0.5"/>
                    <path d="M18 6L26 10V22L18 26V6Z" fill="#050505" stroke="white" strokeWidth="1.5" strokeLinejoin="round"/>
                    <path d="M18 14L26 10" stroke="white" strokeWidth="0.5" strokeOpacity="0.5"/>
                    <path d="M6 10L14 6" stroke="white" strokeWidth="0.5" strokeOpacity="0.2"/>
                    <path d="M26 10L18 6" stroke="white" strokeWidth="0.5" strokeOpacity="0.2"/>
                </svg>
             </div>
             
             {/* Text Logo (Visible on Expand) */}
             <AnimatePresence>
                {isHovered && (
                    <motion.div 
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: -10 }}
                        transition={{ delay: 0.1 }}
                        className="absolute left-20 pl-2 whitespace-nowrap overflow-hidden"
                    >
                        <h1 className="font-display font-bold text-xl text-white tracking-widest h-6 flex items-center">
                            <Typewriter text="PVNDORA" speed={40} />
                        </h1>
                        <div className="text-[9px] font-mono text-gray-500 tracking-widest h-4 flex items-center">
                            <span className="text-pandora-cyan mr-1 opacity-50">&gt;</span>
                            <Typewriter text="MARKET_PROTOCOL_V2" delay={300} speed={20} />
                        </div>
                    </motion.div>
                )}
             </AnimatePresence>
        </div>

        {/* Navigation Items */}
        <div className="flex-1 flex flex-col gap-4 py-6 px-3 w-full">
            <NavItem 
                icon={<LayoutGrid size={18} />} 
                label="Neural Catalog" 
                subLabel="Browse Modules"
                onClick={() => handleClick(onNavigateHome)} 
                active={activeTab === 'catalog'} 
                isExpanded={isHovered}
                delay={0.1}
            />
            <NavItem 
                icon={<Box size={18} />} 
                label="My Orders" 
                subLabel="Access Keys"
                onClick={() => handleClick(onNavigateOrders)} 
                active={activeTab === 'orders'} 
                isExpanded={isHovered}
                delay={0.2}
            />
            <NavItem 
                icon={<Trophy size={18} />} 
                label="Leaderboard" 
                subLabel="Global Rank"
                onClick={() => handleClick(onNavigateLeaderboard)} 
                active={activeTab === 'leaderboard'} 
                isExpanded={isHovered}
                delay={0.3}
            />
            <NavItem 
                icon={<User size={18} />} 
                label="Operative Profile" 
                subLabel="Settings & Stats"
                onClick={() => handleClick(onNavigateProfile)} 
                active={activeTab === 'profile'} 
                isExpanded={isHovered}
                delay={0.4}
            />
        </div>

        {/* Footer Info (Visible on Expand) */}
        <div className="mt-auto p-4 border-t border-white/5 bg-white/[0.02] relative overflow-hidden min-h-[80px]">
             {/* Collapsed View: Hint for CMD+K */}
             <div className={`absolute left-0 top-0 w-full h-full flex flex-col items-center justify-center pt-2 transition-opacity duration-200 ${isHovered ? 'opacity-0' : 'opacity-100'}`}>
                <Command size={16} className="text-gray-600 mb-1" />
                <span className="text-[9px] text-gray-700 font-mono">CMD+K</span>
             </div>

             {/* Expanded View */}
             <AnimatePresence>
                 {isHovered && (
                     <motion.div 
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        transition={{ delay: 0.2 }}
                        className="flex flex-col gap-3"
                     >
                         <div className="flex items-center justify-between text-[10px] font-mono text-gray-400">
                             <span className="flex items-center gap-2"><Shield size={10} /> <Typewriter text="ENCRYPTED" delay={200} /></span>
                             <span className="text-pandora-cyan"><Typewriter text="V.2.4.0" delay={400} /></span>
                         </div>
                         <div className="flex items-center gap-3">
                             <div className="w-8 h-8 rounded bg-gray-800 border border-white/10 flex items-center justify-center">
                                 <Activity size={14} className="text-green-500" />
                             </div>
                             <div className="flex-1">
                                 <div className="text-[10px] text-gray-500 font-mono uppercase"><Typewriter text="System Status" delay={500} /></div>
                                 <div className="text-xs text-white font-bold"><Typewriter text="ONLINE" delay={700} /></div>
                             </div>
                         </div>
                         <button className="flex items-center gap-2 mt-2 text-xs text-red-400 hover:text-red-300 transition-colors font-mono uppercase">
                             <LogOut size={12} /> <Typewriter text="DISCONNECT" delay={900} speed={50} />
                         </button>
                     </motion.div>
                 )}
             </AnimatePresence>
        </div>
      </motion.nav>

      {/* === FLOATING CART BUTTON === Only show when cart has items */}
      {/* Mobile: Bottom-left above navbar (avoid support widget on right). Desktop: Top-right */}
      <AnimatePresence>
        {cartCount > 0 && (
          <motion.button
              initial={{ scale: 0, rotate: 180 }}
              animate={{ scale: 1, rotate: 0 }}
              exit={{ scale: 0, rotate: -180 }}
              onClick={onOpenCart}
              className="fixed z-[110] group bottom-20 left-4 md:bottom-auto md:left-auto md:top-6 md:right-6"
          >
              <div className="relative bg-pandora-cyan text-black p-3 md:p-4 rounded-full shadow-[0_0_20px_rgba(0,255,255,0.4)] hover:bg-white hover:shadow-[0_0_30px_#FFFFFF] transition-all duration-300">
                  <ShoppingCart size={22} className="group-hover:scale-110 transition-transform" />
                  
                  {/* Count Badge */}
                  <div className="absolute -top-1 -right-1 bg-red-500 text-white text-[10px] font-bold w-5 h-5 flex items-center justify-center rounded-full shadow-[0_0_10px_red] animate-pulse">
                      {cartCount}
                  </div>
              </div>
          </motion.button>
        )}
      </AnimatePresence>

      {/* === MOBILE BOTTOM BAR === */}
      <nav 
        className={`
            md:hidden fixed bottom-0 left-0 w-full bg-[#050505]/95 backdrop-blur-xl border-t border-white/10 z-50 pb-safe 
            transition-transform duration-500 ease-in-out
            ${showMobile ? 'translate-y-0' : 'translate-y-[120%]'}
        `}
      >
        <div className="grid grid-cols-4 h-16 items-center relative">
            {/* Active Indicator Line */}
            <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-pandora-cyan/50 to-transparent opacity-50" />

            <MobileNavItem icon={<LayoutGrid size={20} />} label="Catalog" onClick={() => handleClick(onNavigateHome)} active={activeTab === 'catalog'} />
            <MobileNavItem icon={<Box size={20} />} label="Orders" onClick={() => handleClick(onNavigateOrders)} active={activeTab === 'orders'} />
            <MobileNavItem icon={<Trophy size={20} />} label="Rating" onClick={() => handleClick(onNavigateLeaderboard)} active={activeTab === 'leaderboard'} />
            <MobileNavItem icon={<User size={20} />} label="Profile" onClick={() => handleClick(onNavigateProfile)} active={activeTab === 'profile'} />
        </div>
      </nav>
    </>
  );
};

// === SUB COMPONENTS ===

interface NavItemProps {
    icon: React.ReactNode;
    label: string;
    subLabel?: string;
    active?: boolean;
    onClick?: () => void;
    isExpanded?: boolean;
    delay?: number;
}

const NavItem: React.FC<NavItemProps> = ({ icon, label, subLabel, active, onClick, isExpanded, delay = 0 }) => (
    <button 
        onClick={onClick} 
        className={`
            relative flex items-center h-14 w-full transition-all duration-300 group/item
            ${active ? 'bg-white/5' : 'hover:bg-white/5'}
        `}
    >
        {/* Active Indicator (Left Line) */}
        <div className={`absolute left-0 top-1/2 -translate-y-1/2 h-8 w-1 bg-pandora-cyan transition-all duration-300 rounded-r-sm ${active ? 'opacity-100' : 'opacity-0'}`} />

        {/* Icon Container (Standard Rounded Square) */}
        <div className="w-20 flex items-center justify-center shrink-0 relative z-10">
            <div 
                className={`
                    w-10 h-10 flex items-center justify-center transition-all duration-300 rounded-lg
                    ${active ? 'bg-pandora-cyan/20 text-pandora-cyan shadow-[0_0_10px_rgba(0,255,255,0.3)]' : 'bg-white/5 text-gray-500 group-hover/item:text-white group-hover/item:bg-white/10'}
                `}
            >
                {icon}
            </div>
        </div>

        {/* Text Content */}
        <AnimatePresence>
            {isExpanded && (
                <motion.div 
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -10 }}
                    transition={{ delay: delay, duration: 0.3 }}
                    className="flex-1 pl-1 pr-4 whitespace-nowrap overflow-hidden flex justify-between items-center"
                >
                    <div className="text-left">
                        <div className={`text-sm font-bold tracking-wide ${active ? 'text-white' : 'text-gray-400 group-hover/item:text-white'}`}>
                            <Typewriter text={label} delay={delay * 1000} speed={25} />
                        </div>
                        {subLabel && (
                            <div className="text-[10px] font-mono text-gray-600 group-hover/item:text-pandora-cyan transition-colors">
                                <Typewriter text={subLabel} delay={delay * 1000 + 100} speed={15} />
                            </div>
                        )}
                    </div>
                    
                    {active && <ChevronRight size={14} className="text-pandora-cyan animate-pulse" />}
                </motion.div>
            )}
        </AnimatePresence>
        
        {/* Hover Glitch Effect Background (Scanline) */}
        {active && (
             <div className="absolute bottom-0 left-20 right-0 h-[1px] bg-gradient-to-r from-pandora-cyan/50 to-transparent" />
        )}
    </button>
);

const MobileNavItem: React.FC<NavItemProps> = ({ icon, label, active, onClick }) => (
    <button onClick={onClick} className="flex flex-col items-center justify-center gap-1 h-full w-full active:scale-95 transition-transform">
        <div className={`transition-all duration-300 ${active ? 'text-pandora-cyan drop-shadow-[0_0_8px_rgba(0,255,255,0.6)]' : 'text-gray-500'}`}>
            {icon}
        </div>
        <span className={`text-[9px] font-mono font-bold tracking-wider uppercase ${active ? 'text-white' : 'text-gray-600'}`}>
            {label}
        </span>
    </button>
);

export default Navbar;
