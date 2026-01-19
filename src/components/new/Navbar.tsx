import { AnimatePresence, motion } from "framer-motion";
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
import type React from "react";
import { memo, useEffect, useRef, useState } from "react";
import { useAdmin } from "../../hooks/useAdmin";
import { useLocale } from "../../hooks/useLocale";
import { AudioEngine } from "../../lib/AudioEngine";
import { removeSessionToken } from "../../utils/auth";
import { generateShortId } from "../../utils/id";

interface NavbarProps {
  showMobile?: boolean;
  cartCount?: number;
  onOpenCart?: () => void;
  onNavigateHome?: () => void;
  onNavigateOrders?: () => void;
  onNavigateProfile?: () => void;
  onNavigateLeaderboard?: () => void;
  onNavigateStudio?: () => void;
  activeTab?: "catalog" | "orders" | "profile" | "leaderboard" | "studio";
  onHaptic?: () => void;
  onLogout?: () => void;
}

// --- UTILITY: TYPEWRITER EFFECT ---
// Helper to create typewriter interval (reduces nesting depth)
const startTypewriterInterval = (
  text: string,
  speed: number,
  setDisplayedText: React.Dispatch<React.SetStateAction<string>>
): NodeJS.Timeout => {
  let index = 0;
  if (text.length > 0) {
    setDisplayedText(text[0]);
  }

  return setInterval(() => {
    index++;
    if (index < text.length) {
      setDisplayedText(text.slice(0, index + 1));
    }
  }, speed);
};

const Typewriter: React.FC<{ text: string; delay?: number; speed?: number }> = ({
  text,
  delay = 0,
  speed = 30,
}) => {
  const [displayedText, setDisplayedText] = useState("");

  useEffect(() => {
    setDisplayedText("");
    let intervalId: NodeJS.Timeout | null = null;

    const startTimeout = setTimeout(() => {
      intervalId = startTypewriterInterval(text, speed, setDisplayedText);
    }, delay);

    return () => {
      clearTimeout(startTimeout);
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [text, delay, speed]);

  return <span>{displayedText}</span>;
};

// Helper: Handle click with haptic feedback (extracted to reduce cognitive complexity)
const createClickHandler = (onHaptic?: () => void) => (callback?: () => void) => {
  if (onHaptic) {
    onHaptic();
  }
  if (callback) {
    callback();
  }
};

const NavbarComponent: React.FC<NavbarProps> = ({
  showMobile = true,
  cartCount = 0,
  onOpenCart,
  onNavigateHome,
  onNavigateOrders,
  onNavigateProfile,
  onNavigateLeaderboard,
  onNavigateStudio,
  activeTab = "catalog",
  onHaptic,
  onLogout,
}) => {
  const { t } = useLocale();
  const { isAdmin } = useAdmin();
  const [isHovered, setIsHovered] = useState(false);
  const wasHoveredRef = useRef(false);
  const logoId = useRef(generateShortId("navbar-logo")).current;
  const handleClick = createClickHandler(onHaptic);

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

  return (
    <>
      {/* === DESKTOP SIDEBAR (Expandable) === */}
      <motion.nav
        animate={{ width: isHovered ? 288 : 80 }}
        className="fixed top-0 left-0 z-50 hidden h-screen flex-col overflow-hidden border-white/10 border-r bg-[#050505] shadow-[10px_0_30px_rgba(0,0,0,0.5)] md:flex"
        initial={{ width: 80 }}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        style={{ willChange: "width" }}
        transition={{ type: "spring", stiffness: 400, damping: 35 }}
      >
        {/* Logo Section */}
        <button
          className="relative flex h-24 w-full shrink-0 cursor-pointer items-center border-0 bg-transparent"
          onClick={() => handleClick(onNavigateHome)}
          type="button"
        >
          {/* Unified Logo Container - fixed position, flex layout */}
          <motion.div
            animate={{
              paddingLeft: isHovered ? 20 : 0,
              justifyContent: isHovered ? "flex-start" : "center",
              width: isHovered ? "auto" : "100%",
            }}
            className="absolute left-0 flex h-full items-center gap-3"
            style={{ willChange: "padding-left, justify-content" }}
            transition={{ type: "spring", stiffness: 400, damping: 35 }}
          >
            {/* Logo Icon Container - always centered with nav icons when collapsed */}
            <div
              className="group relative z-10 flex h-10 w-10 shrink-0 items-center justify-center"
              style={{ willChange: "transform" }}
            >
              {/* Logo Glow (Internal Core) */}
              <div className="absolute inset-0 bg-pandora-cyan opacity-40 blur-md transition-opacity duration-200 group-hover:opacity-60" />

              {/* PVNDORA Logo */}
              <svg
                aria-labelledby="pvndora-logo-title"
                className="relative z-10 drop-shadow-[0_0_10px_rgba(0,255,255,0.3)] group-hover:drop-shadow-[0_0_15px_rgba(0,255,255,0.5)]"
                fill="none"
                height="40"
                viewBox="0 0 195 215"
                width="36"
                xmlns="http://www.w3.org/2000/svg"
              >
                <title id="pvndora-logo-title">PVNDORA Logo</title>
                <g filter={`url(#${logoId}-filter0_f)`}>
                  <path
                    d="M173.2 63.7952C173.2 108.53 113.7 168.295 90.7 193.795C65.2 164.295 8.19995 108.53 8.19995 63.7952C8.19995 19.0601 45.4126 92.2952 90.7 92.2952C135.987 92.2952 173.2 19.0601 173.2 63.7952Z"
                    fill="#2ED0CF"
                    fillOpacity="0.5"
                  />
                </g>
                <g filter={`url(#${logoId}-filter1_d)`}>
                  <rect
                    fill="#06F8F7"
                    fillOpacity="0.01"
                    height="99.272"
                    transform="matrix(0.866025 -0.5 0.866025 0.5 4.80518 51.1382)"
                    width="99.2765"
                  />
                </g>
                <g filter={`url(#${logoId}-filter2_d)`}>
                  <rect
                    fill="#06F8F7"
                    fillOpacity="0.01"
                    height="98.1249"
                    transform="matrix(0.866025 0.5 0 1 5.19995 55.2204)"
                    width="98.1495"
                  />
                </g>
                <rect
                  fill="#D9D9D9"
                  height="100"
                  transform="matrix(0.866025 0.5 0 1 3.19995 54.2952)"
                  width="100"
                />
                <rect
                  fill={`url(#${logoId}-paint0_linear)`}
                  height="100"
                  transform="matrix(0.866025 0.5 0 1 3.19995 54.2952)"
                  width="100"
                />
                <rect
                  fill={`url(#${logoId}-paint1_linear)`}
                  height="100"
                  transform="matrix(0.866025 0.5 0 1 3.19995 54.2952)"
                  width="100"
                />
                <rect
                  fill="#D9D9D9"
                  height="100"
                  transform="matrix(0.866025 -0.5 0.866025 0.5 4.19995 50.2952)"
                  width="100"
                />
                <rect
                  fill="#272928"
                  height="100"
                  transform="matrix(0.866025 -0.5 0.866025 0.5 4.19995 50.2952)"
                  width="100"
                />
                <g filter={`url(#${logoId}-filter3_dd)`}>
                  <rect
                    fill="#06F8F7"
                    height="100"
                    transform="matrix(0.866025 -0.5 0 1 98.2 105.295)"
                    width="100"
                  />
                </g>
                <rect
                  fill="#D9D9D9"
                  height="100"
                  transform="matrix(0.866025 -0.5 0 1 107.2 112.295)"
                  width="100"
                />
                <rect
                  fill={`url(#${logoId}-paint2_linear)`}
                  height="100"
                  transform="matrix(0.866025 -0.5 0 1 107.2 112.295)"
                  width="100"
                />
                <defs>
                  <filter
                    colorInterpolationFilters="sRGB"
                    filterUnits="userSpaceOnUse"
                    height="160.875"
                    id={`${logoId}-filter0_f`}
                    width="181.4"
                    x="-4.86374e-05"
                    y="41.12"
                  >
                    <feFlood floodOpacity="0" result="BackgroundImageFix" />
                    <feBlend
                      in="SourceGraphic"
                      in2="BackgroundImageFix"
                      mode="normal"
                      result="shape"
                    />
                    <feGaussianBlur result="effect1_foregroundBlur_120_61" stdDeviation="4.1" />
                  </filter>
                  <filter
                    colorInterpolationFilters="sRGB"
                    filterUnits="userSpaceOnUse"
                    height="102.274"
                    id={`${logoId}-filter1_d`}
                    width="174.948"
                    x="3.30518"
                    y="0"
                  >
                    <feFlood floodOpacity="0" result="BackgroundImageFix" />
                    <feColorMatrix
                      in="SourceAlpha"
                      result="hardAlpha"
                      type="matrix"
                      values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 127 0"
                    />
                    <feOffset />
                    <feGaussianBlur stdDeviation="0.75" />
                    <feColorMatrix
                      type="matrix"
                      values="0 0 0 0 0.0196078 0 0 0 0 0.972549 0 0 0 0 0.976471 0 0 0 1 0"
                    />
                    <feBlend
                      in2="BackgroundImageFix"
                      mode="normal"
                      result="effect1_dropShadow_120_61"
                    />
                    <feBlend
                      in="SourceGraphic"
                      in2="effect1_dropShadow_120_61"
                      mode="normal"
                      result="shape"
                    />
                  </filter>
                  <filter
                    colorInterpolationFilters="sRGB"
                    filterUnits="userSpaceOnUse"
                    height="151.4"
                    id={`${logoId}-filter2_d`}
                    width="89.2"
                    x="3.09995"
                    y="53.1204"
                  >
                    <feFlood floodOpacity="0" result="BackgroundImageFix" />
                    <feColorMatrix
                      in="SourceAlpha"
                      result="hardAlpha"
                      type="matrix"
                      values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 127 0"
                    />
                    <feOffset />
                    <feGaussianBlur stdDeviation="1.05" />
                    <feColorMatrix
                      type="matrix"
                      values="0 0 0 0 0.0196078 0 0 0 0 0.972549 0 0 0 0 0.976471 0 0 0 1 0"
                    />
                    <feBlend
                      in2="BackgroundImageFix"
                      mode="normal"
                      result="effect1_dropShadow_120_61"
                    />
                    <feBlend
                      in="SourceGraphic"
                      in2="effect1_dropShadow_120_61"
                      mode="normal"
                      result="shape"
                    />
                  </filter>
                  <filter
                    colorInterpolationFilters="sRGB"
                    filterUnits="userSpaceOnUse"
                    height="169.152"
                    id={`${logoId}-filter3_dd`}
                    width="105.755"
                    x="88.624"
                    y="45.7192"
                  >
                    <feFlood floodOpacity="0" result="BackgroundImageFix" />
                    <feColorMatrix
                      in="SourceAlpha"
                      result="hardAlpha"
                      type="matrix"
                      values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 127 0"
                    />
                    <feOffset />
                    <feGaussianBlur stdDeviation="0.684" />
                    <feColorMatrix
                      type="matrix"
                      values="0 0 0 0 0.0196078 0 0 0 0 0.972549 0 0 0 0 0.976471 0 0 0 1 0"
                    />
                    <feBlend
                      in2="BackgroundImageFix"
                      mode="normal"
                      result="effect1_dropShadow_120_61"
                    />
                    <feColorMatrix
                      in="SourceAlpha"
                      result="hardAlpha"
                      type="matrix"
                      values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 127 0"
                    />
                    <feOffset />
                    <feGaussianBlur stdDeviation="4.788" />
                    <feColorMatrix
                      type="matrix"
                      values="0 0 0 0 0.0196078 0 0 0 0 0.972549 0 0 0 0 0.976471 0 0 0 1 0"
                    />
                    <feBlend
                      in2="effect1_dropShadow_120_61"
                      mode="normal"
                      result="effect2_dropShadow_120_61"
                    />
                    <feBlend
                      in="SourceGraphic"
                      in2="effect2_dropShadow_120_61"
                      mode="normal"
                      result="shape"
                    />
                  </filter>
                  <linearGradient
                    gradientUnits="userSpaceOnUse"
                    id={`${logoId}-paint0_linear`}
                    x1="213.042"
                    x2="111.971"
                    y1="27.4789"
                    y2="-40.2546"
                  >
                    <stop stopColor="#444444" />
                    <stop offset="1" stopColor="#212121" />
                  </linearGradient>
                  <linearGradient
                    gradientUnits="userSpaceOnUse"
                    id={`${logoId}-paint1_linear`}
                    x1="-3.00935e-09"
                    x2="99.2591"
                    y1="54.5"
                    y2="41.2692"
                  >
                    <stop stopColor="#252422" />
                    <stop offset="1" stopColor="#222220" />
                  </linearGradient>
                  <linearGradient
                    gradientUnits="userSpaceOnUse"
                    id={`${logoId}-paint2_linear`}
                    x1="9.36506e-07"
                    x2="117.96"
                    y1="-26.5"
                    y2="42.2236"
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
                  animate={{ opacity: 1, width: "auto", marginLeft: 12 }}
                  className="overflow-hidden whitespace-nowrap"
                  exit={{ opacity: 0, width: 0, marginLeft: 0 }}
                  initial={{ opacity: 0, width: 0, marginLeft: 0 }}
                  key="logo-text"
                  style={{ willChange: "width, opacity, margin-left" }}
                  transition={{
                    width: { duration: 0.25, ease: "easeOut" },
                    opacity: { duration: 0.2, delay: 0.05 },
                    marginLeft: { duration: 0.25 },
                  }}
                >
                  <div>
                    <h1 className="flex h-6 items-center font-bold font-display text-white text-xl tracking-widest">
                      <Typewriter delay={150} speed={40} text="PVNDORA" />
                    </h1>
                    <div className="flex h-4 items-center font-mono text-[9px] text-gray-500 tracking-widest">
                      <span className="mr-1 text-pandora-cyan opacity-50">&gt;</span>
                      <Typewriter delay={500} speed={20} text="MARKET_PROTOCOL_V2" />
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        </button>

        {/* Navigation Items */}
        <div className="flex w-full flex-1 flex-col gap-4 px-3 py-6">
          <NavItem
            active={activeTab === "catalog"}
            delay={0.1}
            icon={<LayoutGrid size={18} />}
            isExpanded={isHovered}
            label={t("navbar.catalog")}
            onClick={() => handleClick(onNavigateHome)}
            subLabel={t("navbar.catalogSub")}
          />
          <NavItem
            active={activeTab === "orders"}
            delay={0.2}
            icon={<Box size={18} />}
            isExpanded={isHovered}
            label={t("navbar.orders")}
            onClick={() => handleClick(onNavigateOrders)}
            subLabel={t("navbar.ordersSub")}
          />
          <NavItem
            active={activeTab === "leaderboard"}
            delay={0.3}
            icon={<Trophy size={18} />}
            isExpanded={isHovered}
            label={t("navbar.leaderboard")}
            onClick={() => handleClick(onNavigateLeaderboard)}
            subLabel={t("navbar.leaderboardSub")}
          />
          <NavItem
            active={activeTab === "profile"}
            delay={0.4}
            icon={<User size={18} />}
            isExpanded={isHovered}
            label={t("navbar.profile")}
            onClick={() => handleClick(onNavigateProfile)}
            subLabel={t("navbar.profileSub")}
          />
          <NavItem
            active={activeTab === "studio"}
            delay={0.5}
            icon={<Command size={18} />}
            isExpanded={isHovered}
            label={t("navbar.studio")}
            onClick={isAdmin ? () => handleClick(onNavigateStudio) : undefined}
            subLabel={t("navbar.studioSub")}
          />
        </div>

        {/* Footer Info (Visible on Expand) */}
        <div
          className="relative mt-auto overflow-hidden border-white/5 border-t bg-white/[0.02]"
          style={{ minHeight: isHovered ? "80px" : "60px" }}
        >
          {/* Collapsed View: Hint for CMD+K */}
          <div
            className={`absolute inset-0 flex flex-col items-center justify-center transition-opacity duration-200 ${isHovered ? "pointer-events-none opacity-0" : "opacity-100"}`}
          >
            <div className="mb-1 flex h-8 w-8 items-center justify-center rounded border border-white/10 bg-white/5">
              <Command className="text-gray-600" size={14} />
            </div>
            <span className="font-mono text-[8px] text-gray-600 tracking-wider">CMD+K</span>
          </div>

          {/* Expanded View */}
          <AnimatePresence>
            {isHovered && (
              <motion.div
                animate={{ opacity: 1 }}
                className="flex flex-col gap-3 p-4"
                exit={{ opacity: 0 }}
                initial={{ opacity: 0 }}
                transition={{ delay: 0.2 }}
              >
                <div className="flex items-center justify-between font-mono text-[10px] text-gray-400">
                  <span className="flex items-center gap-2">
                    <Shield size={10} /> <Typewriter delay={200} text="ENCRYPTED" />
                  </span>
                  <span className="text-pandora-cyan">
                    <Typewriter delay={400} text="V.2.4.0" />
                  </span>
                </div>
                <div className="flex items-center gap-3">
                  <div className="flex h-8 w-8 items-center justify-center rounded border border-white/10 bg-gray-800">
                    <Activity className="text-green-500" size={14} />
                  </div>
                  <div className="flex-1">
                    <div className="font-mono text-[10px] text-gray-500 uppercase">
                      <Typewriter delay={500} text={t("navbar.status")} />
                    </div>
                    <div className="font-bold text-white text-xs">
                      <Typewriter delay={700} text={t("navbar.online").toUpperCase()} />
                    </div>
                  </div>
                </div>
                <button
                  className="mt-2 flex cursor-pointer items-center gap-2 font-mono text-red-400 text-xs uppercase transition-colors hover:text-red-300"
                  onClick={() => {
                    if (onHaptic) {
                      onHaptic();
                    }
                    if (onLogout) {
                      onLogout();
                    } else {
                      // Fallback: direct logout if no handler provided
                      removeSessionToken();
                      globalThis.location.reload();
                    }
                  }}
                  type="button"
                >
                  <LogOut size={12} />{" "}
                  <Typewriter delay={900} speed={50} text={t("navbar.disconnect").toUpperCase()} />
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
            animate={{ scale: 1, rotate: 0 }}
            className="group fixed bottom-20 left-4 z-[110] md:top-6 md:right-6 md:bottom-auto md:left-auto"
            exit={{ scale: 0, rotate: -180 }}
            initial={{ scale: 0, rotate: 180 }}
            onClick={onOpenCart}
          >
            <div className="relative rounded-full bg-pandora-cyan p-3 text-black shadow-[0_0_20px_rgba(0,255,255,0.4)] transition-all duration-300 hover:bg-white hover:shadow-[0_0_30px_#FFFFFF] md:p-4">
              <ShoppingCart className="transition-transform group-hover:scale-110" size={22} />

              {/* Count Badge */}
              <div className="absolute -top-1 -right-1 flex h-5 w-5 animate-pulse items-center justify-center rounded-full bg-red-500 font-bold text-[10px] text-white shadow-[0_0_10px_red]">
                {cartCount}
              </div>
            </div>
          </motion.button>
        )}
      </AnimatePresence>

      {/* === MOBILE BOTTOM BAR === */}
      <nav
        className={`fixed bottom-0 left-0 z-50 w-full border-white/10 border-t bg-[#050505]/95 pb-safe backdrop-blur-xl transition-transform duration-500 ease-in-out md:hidden ${showMobile ? "translate-y-0" : "translate-y-[120%]"}
        `}
      >
        <div className="relative grid h-16 grid-cols-4 items-center gap-1">
          {/* Active Indicator Line */}
          <div className="absolute top-0 left-0 h-[1px] w-full bg-gradient-to-r from-transparent via-pandora-cyan/50 to-transparent opacity-50" />

          <MobileNavItem
            active={activeTab === "catalog"}
            icon={<LayoutGrid size={20} />}
            label={t("navbar.mobile.catalog")}
            onClick={() => handleClick(onNavigateHome)}
          />
          <MobileNavItem
            active={activeTab === "orders"}
            icon={<Box size={20} />}
            label={t("navbar.mobile.orders")}
            onClick={() => handleClick(onNavigateOrders)}
          />
          <MobileNavItem
            active={activeTab === "leaderboard"}
            icon={<Trophy size={20} />}
            label={t("navbar.mobile.leaderboard")}
            onClick={() => handleClick(onNavigateLeaderboard)}
          />
          <MobileNavItem
            active={activeTab === "profile"}
            icon={<User size={20} />}
            label={t("navbar.mobile.profile")}
            onClick={() => handleClick(onNavigateProfile)}
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
}) => {
  // Determine background class (avoid nested ternary)
  let bgClass = "";
  if (active) {
    bgClass = "bg-white/5";
  } else if (onClick) {
    bgClass = "hover:bg-white/5";
  }

  return (
    <motion.button
      animate={{
        paddingLeft: isExpanded ? 12 : 0,
        paddingRight: isExpanded ? 16 : 0,
        justifyContent: isExpanded ? "flex-start" : "center",
      }}
      className={`group/item relative flex h-12 w-full items-center justify-center md:h-14 md:justify-start ${bgClass}
            ${onClick ? "cursor-pointer" : "cursor-not-allowed opacity-50"}
        `}
      disabled={!onClick}
      onClick={onClick}
      style={{ willChange: "padding-left, padding-right" }}
      title={isExpanded ? undefined : label}
      transition={{ type: "spring", stiffness: 400, damping: 35 }}
      type="button"
    >
      {/* Active Indicator (Left Line) */}
      <motion.div
        animate={{ opacity: active ? 1 : 0 }}
        className="absolute top-1/2 left-0 h-8 w-1 -translate-y-1/2 rounded-r-sm bg-pandora-cyan"
        transition={{ duration: 0.2 }}
      />

      {/* Icon Container (Standard Rounded Square) */}
      <motion.div
        animate={{ width: isExpanded ? 80 : "100%" }}
        className="relative z-10 flex shrink-0 items-center justify-center"
        style={{ willChange: "width" }}
        transition={{ type: "spring", stiffness: 400, damping: 35 }}
      >
        <div
          className={`flex h-10 w-10 items-center justify-center rounded-lg transition-colors duration-200 ${active ? "bg-pandora-cyan/20 text-pandora-cyan shadow-[0_0_10px_rgba(0,255,255,0.3)]" : "bg-white/5 text-gray-500 group-hover/item:bg-white/10 group-hover/item:text-white"}
                `}
        >
          {icon}
        </div>
      </motion.div>

      {/* Text Content */}
      <AnimatePresence mode="wait">
        {isExpanded && (
          <motion.div
            animate={{ opacity: 1, x: 0, width: "auto" }}
            className="flex flex-1 items-center justify-between overflow-hidden whitespace-nowrap pr-4 pl-1"
            exit={{ opacity: 0, x: -10, width: 0 }}
            initial={{ opacity: 0, x: -10, width: 0 }}
            key="nav-text"
            style={{ willChange: "width, opacity" }}
            transition={{
              delay: delay * 0.1,
              duration: 0.25,
              ease: "easeOut",
            }}
          >
            <div className="text-left">
              <div
                className={`font-bold text-sm tracking-wide ${active ? "text-white" : "text-gray-400 group-hover/item:text-white"}`}
              >
                <Typewriter delay={delay * 1000} speed={25} text={label} />
              </div>
              {subLabel && (
                <div className="font-mono text-[10px] text-gray-600 transition-colors duration-200 group-hover/item:text-pandora-cyan">
                  <Typewriter delay={delay * 1000 + 100} speed={15} text={subLabel} />
                </div>
              )}
            </div>

            {active && <ChevronRight className="animate-pulse text-pandora-cyan" size={14} />}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Hover Glitch Effect Background (Scanline) */}
      {active && (
        <div className="absolute right-0 bottom-0 left-20 h-[1px] bg-gradient-to-r from-pandora-cyan/50 to-transparent" />
      )}
    </motion.button>
  );
};

interface MobileNavItemProps {
  icon: React.ReactNode;
  label: string;
  active?: boolean;
  onClick?: () => void;
}

const MobileNavItem: React.FC<MobileNavItemProps> = ({ icon, label, active, onClick }) => (
  <button
    className="flex h-full w-full flex-col items-center justify-center gap-1 transition-transform active:scale-95"
    onClick={onClick}
    type="button"
  >
    <div
      className={`transition-all duration-300 ${active ? "text-pandora-cyan drop-shadow-[0_0_8px_rgba(0,255,255,0.6)]" : "text-gray-500"}`}
    >
      {icon}
    </div>
    <span
      className={`font-bold font-mono text-[9px] uppercase tracking-wider ${active ? "text-white" : "text-gray-600"}`}
    >
      {label}
    </span>
  </button>
);

const Navbar = memo(NavbarComponent);
export default Navbar;
