import React, { useState, useEffect, useRef, memo } from "react";
import {
  Activity,
  Box,
  ChevronRight,
  Command,
  LayoutGrid,
  LogOut,
  Shield,
  ShoppingCart,
  Trophy,
  User,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { AudioEngine } from "../../lib/AudioEngine";
import { generateShortId } from "../../utils/id";
import { useLocale } from "../../hooks/useLocale";
import { removeSessionToken } from "../../utils/auth";

interface NavbarProps {
  showMobile?: boolean;
  cartCount?: number;
  onOpenCart?: () => void;
  onNavigateHome?: () => void;
  onNavigateOrders?: () => void;
  onNavigateProfile?: () => void;
  onNavigateLeaderboard?: () => void;
  activeTab?: "catalog" | "orders" | "profile" | "leaderboard";
  onHaptic?: () => void;
  onLogout?: () => void;
}

// --- UTILITY: TYPEWRITER EFFECT ---
const Typewriter: React.FC<{ text: string; delay?: number; speed?: number }> = ({
  text,
  delay = 0,
  speed = 30,
}) => {
  const [displayedText, setDisplayedText] = useState("");

  useEffect(() => {
    // Reset on mount/change
    setDisplayedText("");

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

const NavbarComponent: React.FC<NavbarProps> = ({
  showMobile = true,
  cartCount = 0,
  onOpenCart,
  onNavigateHome,
  onNavigateOrders,
  onNavigateProfile,
  onNavigateLeaderboard,
  activeTab = "catalog",
  onHaptic,
  onLogout,
}) => {
  const { t } = useLocale();
  const [isHovered, setIsHovered] = useState(false);
  const wasHoveredRef = useRef(false);
  const logoId = useRef(generateShortId("navbar-logo")).current;

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
        transition={{ type: "spring", stiffness: 400, damping: 35 }}
        className="hidden md:flex fixed top-0 left-0 h-screen z-50 flex-col bg-[#050505] border-r border-white/10 overflow-hidden shadow-[10px_0_30px_rgba(0,0,0,0.5)]"
        style={{ willChange: "width" }}
      >
        {/* Logo Section */}
        <button
          type="button"
          className="h-24 flex items-center shrink-0 relative cursor-pointer border-0 bg-transparent w-full"
          onClick={() => handleClick(onNavigateHome)}
        >
          {/* Unified Logo Container - fixed position, flex layout */}
          <motion.div
            className="absolute left-0 h-full flex items-center gap-3"
            animate={{
              paddingLeft: isHovered ? 20 : 0,
              justifyContent: isHovered ? "flex-start" : "center",
              width: isHovered ? "auto" : "100%",
            }}
            transition={{ type: "spring", stiffness: 400, damping: 35 }}
            style={{ willChange: "padding-left, justify-content" }}
          >
            {/* Logo Icon Container - always centered with nav icons when collapsed */}
            <div
              className="w-10 h-10 flex items-center justify-center relative z-10 group shrink-0"
              style={{ willChange: "transform" }}
            >
              {/* Logo Glow (Internal Core) */}
              <div className="absolute inset-0 bg-pandora-cyan blur-md opacity-40 group-hover:opacity-60 transition-opacity duration-200" />

              {/* PVNDORA Logo */}
              <svg
                width="36"
                height="40"
                viewBox="0 0 195 215"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
                className="relative z-10 drop-shadow-[0_0_10px_rgba(0,255,255,0.3)] group-hover:drop-shadow-[0_0_15px_rgba(0,255,255,0.5)]"
              >
                <g filter={`url(#${logoId}-filter0_f)`}>
                  <path
                    d="M173.2 63.7952C173.2 108.53 113.7 168.295 90.7 193.795C65.2 164.295 8.19995 108.53 8.19995 63.7952C8.19995 19.0601 45.4126 92.2952 90.7 92.2952C135.987 92.2952 173.2 19.0601 173.2 63.7952Z"
                    fill="#2ED0CF"
                    fillOpacity="0.5"
                  />
                </g>
                <g filter={`url(#${logoId}-filter1_d)`}>
                  <rect
                    width="99.2765"
                    height="99.272"
                    transform="matrix(0.866025 -0.5 0.866025 0.5 4.80518 51.1382)"
                    fill="#06F8F7"
                    fillOpacity="0.01"
                  />
                </g>
                <g filter={`url(#${logoId}-filter2_d)`}>
                  <rect
                    width="98.1495"
                    height="98.1249"
                    transform="matrix(0.866025 0.5 0 1 5.19995 55.2204)"
                    fill="#06F8F7"
                    fillOpacity="0.01"
                  />
                </g>
                <rect
                  width="100"
                  height="100"
                  transform="matrix(0.866025 0.5 0 1 3.19995 54.2952)"
                  fill="#D9D9D9"
                />
                <rect
                  width="100"
                  height="100"
                  transform="matrix(0.866025 0.5 0 1 3.19995 54.2952)"
                  fill={`url(#${logoId}-paint0_linear)`}
                />
                <rect
                  width="100"
                  height="100"
                  transform="matrix(0.866025 0.5 0 1 3.19995 54.2952)"
                  fill={`url(#${logoId}-paint1_linear)`}
                />
                <rect
                  width="100"
                  height="100"
                  transform="matrix(0.866025 -0.5 0.866025 0.5 4.19995 50.2952)"
                  fill="#D9D9D9"
                />
                <rect
                  width="100"
                  height="100"
                  transform="matrix(0.866025 -0.5 0.866025 0.5 4.19995 50.2952)"
                  fill="#272928"
                />
                <g filter={`url(#${logoId}-filter3_dd)`}>
                  <rect
                    width="100"
                    height="100"
                    transform="matrix(0.866025 -0.5 0 1 98.2 105.295)"
                    fill="#06F8F7"
                  />
                </g>
                <rect
                  width="100"
                  height="100"
                  transform="matrix(0.866025 -0.5 0 1 107.2 112.295)"
                  fill="#D9D9D9"
                />
                <rect
                  width="100"
                  height="100"
                  transform="matrix(0.866025 -0.5 0 1 107.2 112.295)"
                  fill={`url(#${logoId}-paint2_linear)`}
                />
                <defs>
                  <filter
                    id={`${logoId}-filter0_f`}
                    x="-4.86374e-05"
                    y="41.12"
                    width="181.4"
                    height="160.875"
                    filterUnits="userSpaceOnUse"
                    colorInterpolationFilters="sRGB"
                  >
                    <feFlood floodOpacity="0" result="BackgroundImageFix" />
                    <feBlend
                      mode="normal"
                      in="SourceGraphic"
                      in2="BackgroundImageFix"
                      result="shape"
                    />
                    <feGaussianBlur stdDeviation="4.1" result="effect1_foregroundBlur_120_61" />
                  </filter>
                  <filter
                    id={`${logoId}-filter1_d`}
                    x="3.30518"
                    y="0"
                    width="174.948"
                    height="102.274"
                    filterUnits="userSpaceOnUse"
                    colorInterpolationFilters="sRGB"
                  >
                    <feFlood floodOpacity="0" result="BackgroundImageFix" />
                    <feColorMatrix
                      in="SourceAlpha"
                      type="matrix"
                      values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 127 0"
                      result="hardAlpha"
                    />
                    <feOffset />
                    <feGaussianBlur stdDeviation="0.75" />
                    <feColorMatrix
                      type="matrix"
                      values="0 0 0 0 0.0196078 0 0 0 0 0.972549 0 0 0 0 0.976471 0 0 0 1 0"
                    />
                    <feBlend
                      mode="normal"
                      in2="BackgroundImageFix"
                      result="effect1_dropShadow_120_61"
                    />
                    <feBlend
                      mode="normal"
                      in="SourceGraphic"
                      in2="effect1_dropShadow_120_61"
                      result="shape"
                    />
                  </filter>
                  <filter
                    id={`${logoId}-filter2_d`}
                    x="3.09995"
                    y="53.1204"
                    width="89.2"
                    height="151.4"
                    filterUnits="userSpaceOnUse"
                    colorInterpolationFilters="sRGB"
                  >
                    <feFlood floodOpacity="0" result="BackgroundImageFix" />
                    <feColorMatrix
                      in="SourceAlpha"
                      type="matrix"
                      values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 127 0"
                      result="hardAlpha"
                    />
                    <feOffset />
                    <feGaussianBlur stdDeviation="1.05" />
                    <feColorMatrix
                      type="matrix"
                      values="0 0 0 0 0.0196078 0 0 0 0 0.972549 0 0 0 0 0.976471 0 0 0 1 0"
                    />
                    <feBlend
                      mode="normal"
                      in2="BackgroundImageFix"
                      result="effect1_dropShadow_120_61"
                    />
                    <feBlend
                      mode="normal"
                      in="SourceGraphic"
                      in2="effect1_dropShadow_120_61"
                      result="shape"
                    />
                  </filter>
                  <filter
                    id={`${logoId}-filter3_dd`}
                    x="88.624"
                    y="45.7192"
                    width="105.755"
                    height="169.152"
                    filterUnits="userSpaceOnUse"
                    colorInterpolationFilters="sRGB"
                  >
                    <feFlood floodOpacity="0" result="BackgroundImageFix" />
                    <feColorMatrix
                      in="SourceAlpha"
                      type="matrix"
                      values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 127 0"
                      result="hardAlpha"
                    />
                    <feOffset />
                    <feGaussianBlur stdDeviation="0.684" />
                    <feColorMatrix
                      type="matrix"
                      values="0 0 0 0 0.0196078 0 0 0 0 0.972549 0 0 0 0 0.976471 0 0 0 1 0"
                    />
                    <feBlend
                      mode="normal"
                      in2="BackgroundImageFix"
                      result="effect1_dropShadow_120_61"
                    />
                    <feColorMatrix
                      in="SourceAlpha"
                      type="matrix"
                      values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 127 0"
                      result="hardAlpha"
                    />
                    <feOffset />
                    <feGaussianBlur stdDeviation="4.788" />
                    <feColorMatrix
                      type="matrix"
                      values="0 0 0 0 0.0196078 0 0 0 0 0.972549 0 0 0 0 0.976471 0 0 0 1 0"
                    />
                    <feBlend
                      mode="normal"
                      in2="effect1_dropShadow_120_61"
                      result="effect2_dropShadow_120_61"
                    />
                    <feBlend
                      mode="normal"
                      in="SourceGraphic"
                      in2="effect2_dropShadow_120_61"
                      result="shape"
                    />
                  </filter>
                  <linearGradient
                    id={`${logoId}-paint0_linear`}
                    x1="213.042"
                    y1="27.4789"
                    x2="111.971"
                    y2="-40.2546"
                    gradientUnits="userSpaceOnUse"
                  >
                    <stop stopColor="#444444" />
                    <stop offset="1" stopColor="#212121" />
                  </linearGradient>
                  <linearGradient
                    id={`${logoId}-paint1_linear`}
                    x1="-3.00935e-09"
                    y1="54.5"
                    x2="99.2591"
                    y2="41.2692"
                    gradientUnits="userSpaceOnUse"
                  >
                    <stop stopColor="#252422" />
                    <stop offset="1" stopColor="#222220" />
                  </linearGradient>
                  <linearGradient
                    id={`${logoId}-paint2_linear`}
                    x1="9.36506e-07"
                    y1="-26.5"
                    x2="117.96"
                    y2="42.2236"
                    gradientUnits="userSpaceOnUse"
                  >
                    <stop stopColor="#2E2D2B" />
                    <stop offset="1" stopColor="#222220" />
                  </linearGradient>
                </defs>
              </svg>
            </div>

            {/* Text Logo (Visible on Expand) - part of the same flex container */}
            <AnimatePresence mode="wait">
              {isHovered && (
                <motion.div
                  key="logo-text"
                  initial={{ opacity: 0, width: 0, marginLeft: 0 }}
                  animate={{ opacity: 1, width: "auto", marginLeft: 12 }}
                  exit={{ opacity: 0, width: 0, marginLeft: 0 }}
                  transition={{
                    width: { duration: 0.25, ease: "easeOut" },
                    opacity: { duration: 0.2, delay: 0.05 },
                    marginLeft: { duration: 0.25 },
                  }}
                  className="overflow-hidden whitespace-nowrap"
                  style={{ willChange: "width, opacity, margin-left" }}
                >
                  <div>
                    <h1 className="font-display font-bold text-xl text-white tracking-widest h-6 flex items-center">
                      <Typewriter text="PVNDORA" speed={40} delay={150} />
                    </h1>
                    <div className="text-[9px] font-mono text-gray-500 tracking-widest h-4 flex items-center">
                      <span className="text-pandora-cyan mr-1 opacity-50">&gt;</span>
                      <Typewriter text="MARKET_PROTOCOL_V2" delay={500} speed={20} />
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        </button>

        {/* Navigation Items */}
        <div className="flex-1 flex flex-col gap-4 py-6 px-3 w-full">
          <NavItem
            icon={<LayoutGrid size={18} />}
            label={t("navbar.catalog")}
            subLabel={t("navbar.catalogSub")}
            onClick={() => handleClick(onNavigateHome)}
            active={activeTab === "catalog"}
            isExpanded={isHovered}
            delay={0.1}
          />
          <NavItem
            icon={<Box size={18} />}
            label={t("navbar.orders")}
            subLabel={t("navbar.ordersSub")}
            onClick={() => handleClick(onNavigateOrders)}
            active={activeTab === "orders"}
            isExpanded={isHovered}
            delay={0.2}
          />
          <NavItem
            icon={<Trophy size={18} />}
            label={t("navbar.leaderboard")}
            subLabel={t("navbar.leaderboardSub")}
            onClick={() => handleClick(onNavigateLeaderboard)}
            active={activeTab === "leaderboard"}
            isExpanded={isHovered}
            delay={0.3}
          />
          <NavItem
            icon={<User size={18} />}
            label={t("navbar.profile")}
            subLabel={t("navbar.profileSub")}
            onClick={() => handleClick(onNavigateProfile)}
            active={activeTab === "profile"}
            isExpanded={isHovered}
            delay={0.4}
          />
        </div>

        {/* Footer Info (Visible on Expand) */}
        <div
          className="mt-auto border-t border-white/5 bg-white/[0.02] relative overflow-hidden"
          style={{ minHeight: isHovered ? "80px" : "60px" }}
        >
          {/* Collapsed View: Hint for CMD+K */}
          <div
            className={`absolute inset-0 flex flex-col items-center justify-center transition-opacity duration-200 ${isHovered ? "opacity-0 pointer-events-none" : "opacity-100"}`}
          >
            <div className="w-8 h-8 flex items-center justify-center rounded bg-white/5 border border-white/10 mb-1">
              <Command size={14} className="text-gray-600" />
            </div>
            <span className="text-[8px] text-gray-600 font-mono tracking-wider">CMD+K</span>
          </div>

          {/* Expanded View */}
          <AnimatePresence>
            {isHovered && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ delay: 0.2 }}
                className="flex flex-col gap-3 p-4"
              >
                <div className="flex items-center justify-between text-[10px] font-mono text-gray-400">
                  <span className="flex items-center gap-2">
                    <Shield size={10} /> <Typewriter text="ENCRYPTED" delay={200} />
                  </span>
                  <span className="text-pandora-cyan">
                    <Typewriter text="V.2.4.0" delay={400} />
                  </span>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded bg-gray-800 border border-white/10 flex items-center justify-center">
                    <Activity size={14} className="text-green-500" />
                  </div>
                  <div className="flex-1">
                    <div className="text-[10px] text-gray-500 font-mono uppercase">
                      <Typewriter text={t("navbar.status")} delay={500} />
                    </div>
                    <div className="text-xs text-white font-bold">
                      <Typewriter text={t("navbar.online").toUpperCase()} delay={700} />
                    </div>
                  </div>
                </div>
                <button
                  onClick={() => {
                    if (onHaptic) onHaptic();
                    if (onLogout) {
                      onLogout();
                    } else {
                      // Fallback: direct logout if no handler provided
                      removeSessionToken();
                      globalThis.location.reload();
                    }
                  }}
                  className="flex items-center gap-2 mt-2 text-xs text-red-400 hover:text-red-300 transition-colors font-mono uppercase cursor-pointer"
                >
                  <LogOut size={12} />{" "}
                  <Typewriter text={t("navbar.disconnect").toUpperCase()} delay={900} speed={50} />
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
            ${showMobile ? "translate-y-0" : "translate-y-[120%]"}
        `}
      >
        <div className="grid grid-cols-4 h-16 items-center relative gap-1">
          {/* Active Indicator Line */}
          <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-pandora-cyan/50 to-transparent opacity-50" />

          <MobileNavItem
            icon={<LayoutGrid size={20} />}
            label={t("navbar.mobile.catalog")}
            onClick={() => handleClick(onNavigateHome)}
            active={activeTab === "catalog"}
          />
          <MobileNavItem
            icon={<Box size={20} />}
            label={t("navbar.mobile.orders")}
            onClick={() => handleClick(onNavigateOrders)}
            active={activeTab === "orders"}
          />
          <MobileNavItem
            icon={<Trophy size={20} />}
            label={t("navbar.mobile.leaderboard")}
            onClick={() => handleClick(onNavigateLeaderboard)}
            active={activeTab === "leaderboard"}
          />
          <MobileNavItem
            icon={<User size={20} />}
            label={t("navbar.mobile.profile")}
            onClick={() => handleClick(onNavigateProfile)}
            active={activeTab === "profile"}
          />
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

const NavItem: React.FC<NavItemProps> = ({
  icon,
  label,
  subLabel,
  active,
  onClick,
  isExpanded,
  delay = 0,
}) => (
  <motion.button
    onClick={onClick}
    className={`
            relative flex items-center justify-center md:justify-start h-12 md:h-14 w-full group/item
            ${active ? "bg-white/5" : "hover:bg-white/5"}
        `}
    animate={{
      paddingLeft: isExpanded ? 12 : 0,
      paddingRight: isExpanded ? 16 : 0,
      justifyContent: isExpanded ? "flex-start" : "center",
    }}
    transition={{ type: "spring", stiffness: 400, damping: 35 }}
    style={{ willChange: "padding-left, padding-right" }}
    title={!isExpanded ? label : undefined}
  >
    {/* Active Indicator (Left Line) */}
    <motion.div
      className="absolute left-0 top-1/2 -translate-y-1/2 h-8 w-1 bg-pandora-cyan rounded-r-sm"
      animate={{ opacity: active ? 1 : 0 }}
      transition={{ duration: 0.2 }}
    />

    {/* Icon Container (Standard Rounded Square) */}
    <motion.div
      className="flex items-center justify-center shrink-0 relative z-10"
      animate={{ width: isExpanded ? 80 : "100%" }}
      transition={{ type: "spring", stiffness: 400, damping: 35 }}
      style={{ willChange: "width" }}
    >
      <div
        className={`
                    w-10 h-10 flex items-center justify-center rounded-lg transition-colors duration-200
                    ${active ? "bg-pandora-cyan/20 text-pandora-cyan shadow-[0_0_10px_rgba(0,255,255,0.3)]" : "bg-white/5 text-gray-500 group-hover/item:text-white group-hover/item:bg-white/10"}
                `}
      >
        {icon}
      </div>
    </motion.div>

    {/* Text Content */}
    <AnimatePresence mode="wait">
      {isExpanded && (
        <motion.div
          key="nav-text"
          initial={{ opacity: 0, x: -10, width: 0 }}
          animate={{ opacity: 1, x: 0, width: "auto" }}
          exit={{ opacity: 0, x: -10, width: 0 }}
          transition={{
            delay: delay * 0.1,
            duration: 0.25,
            ease: "easeOut",
          }}
          className="flex-1 pl-1 pr-4 whitespace-nowrap overflow-hidden flex justify-between items-center"
          style={{ willChange: "width, opacity" }}
        >
          <div className="text-left">
            <div
              className={`text-sm font-bold tracking-wide ${active ? "text-white" : "text-gray-400 group-hover/item:text-white"}`}
            >
              <Typewriter text={label} delay={delay * 1000} speed={25} />
            </div>
            {subLabel && (
              <div className="text-[10px] font-mono text-gray-600 group-hover/item:text-pandora-cyan transition-colors duration-200">
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
  </motion.button>
);

const MobileNavItem: React.FC<NavItemProps> = ({ icon, label, active, onClick }) => (
  <button
    onClick={onClick}
    className="flex flex-col items-center justify-center gap-1 h-full w-full active:scale-95 transition-transform"
  >
    <div
      className={`transition-all duration-300 ${active ? "text-pandora-cyan drop-shadow-[0_0_8px_rgba(0,255,255,0.6)]" : "text-gray-500"}`}
    >
      {icon}
    </div>
    <span
      className={`text-[9px] font-mono font-bold tracking-wider uppercase ${active ? "text-white" : "text-gray-600"}`}
    >
      {label}
    </span>
  </button>
);

const Navbar = memo(NavbarComponent);
export default Navbar;
