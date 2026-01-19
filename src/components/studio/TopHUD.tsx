import { motion } from "framer-motion";
import { ImageIcon, Music, Sidebar, Sparkles, Video, X, Zap } from "lucide-react";
import type React from "react";
import { AudioEngine } from "../../lib/AudioEngine";
import type { DomainType } from "./types";

interface TopHUDProps {
  activeDomain: DomainType;
  userBalance: number;
  onNavigateHome: () => void;
  onTopUp: () => void;
  onDomainSwitch: (domain: DomainType) => void;
  onSidebarToggle: () => void;
  isSidebarOpen: boolean;
}

export const TopHUD: React.FC<TopHUDProps> = ({
  activeDomain,
  userBalance,
  onNavigateHome,
  onTopUp,
  onDomainSwitch,
  onSidebarToggle,
  isSidebarOpen: _isSidebarOpen,
}) => {
  return (
    <header className="absolute top-0 left-0 right-0 p-4 z-30 pointer-events-none">
      {/* Top bar with gradient border */}
      <div className="absolute top-0 left-0 right-0 h-12 bg-gradient-to-b from-black/80 to-transparent pointer-events-none" />

      <div className="flex justify-between items-start relative">
        {/* Left side controls */}
        <div className="pointer-events-auto flex items-center gap-3">
          {/* STUDIO Badge */}
          <div className="relative group">
            <div className="absolute -inset-1 bg-pandora-cyan/20 blur-lg opacity-50 group-hover:opacity-80 transition-opacity rounded-lg" />
            <div className="relative px-3 py-1.5 bg-black/80 border border-pandora-cyan/50 flex items-center gap-2 shadow-[0_0_20px_rgba(0,255,255,0.2)]">
              <Sparkles size={12} className="text-pandora-cyan animate-pulse" />
              <span className="text-[10px] font-bold text-pandora-cyan tracking-[0.3em]">
                STUDIO
              </span>
              <span className="text-[8px] px-1.5 py-0.5 bg-yellow-500/20 border border-yellow-500/40 text-yellow-400 font-bold">
                BETA
              </span>
            </div>
          </div>

          {/* Sidebar Toggle */}
          <button
            type="button"
            onClick={onSidebarToggle}
            className="w-9 h-9 flex items-center justify-center bg-black/60 backdrop-blur-md border border-white/10 hover:border-pandora-cyan/50 text-gray-400 hover:text-pandora-cyan transition-all group"
          >
            <Sidebar size={14} className="group-hover:scale-110 transition-transform" />
          </button>

          {/* Domain Switcher - enhanced */}
          <div className="flex bg-black/70 backdrop-blur-md border border-white/10 p-1 gap-0.5">
            {(["video", "image", "audio"] as const).map((d) => (
              <button
                type="button"
                key={d}
                onClick={() => {
                  AudioEngine.click();
                  onDomainSwitch(d);
                }}
                className={`
                  relative px-4 py-1.5 text-[10px] font-bold uppercase transition-all flex items-center gap-2 overflow-hidden
                  ${activeDomain === d ? "text-pandora-cyan" : "text-gray-600 hover:text-gray-300"}
                `}
              >
                {activeDomain === d && (
                  <>
                    <motion.div
                      layoutId="domainHighlight"
                      className="absolute inset-0 bg-pandora-cyan/10 border border-pandora-cyan/30"
                      transition={{ type: "spring", stiffness: 500, damping: 35 }}
                    />
                    <motion.div
                      className="absolute bottom-0 left-0 right-0 h-[2px] bg-pandora-cyan shadow-[0_0_10px_#00FFFF]"
                      layoutId="domainUnderline"
                    />
                  </>
                )}
                <span className="relative z-10 flex items-center gap-2">
                  {d === "video" && <Video size={12} />}
                  {d === "image" && <ImageIcon size={12} />}
                  {d === "audio" && <Music size={12} />}
                  <span className="hidden sm:inline">{d}</span>
                </span>
              </button>
            ))}
          </div>
        </div>

        {/* Right side - Credits & Exit */}
        <div className="pointer-events-auto flex items-center gap-3">
          {/* Credits display */}
          <button type="button" onClick={onTopUp} className="relative group overflow-hidden">
            <div className="absolute -inset-1 bg-pandora-cyan/10 blur-md opacity-0 group-hover:opacity-100 transition-opacity" />
            <div className="relative flex items-center gap-3 bg-black/70 backdrop-blur-md border border-pandora-cyan/30 px-4 py-2 hover:border-pandora-cyan/60 transition-all">
              <div className="text-right">
                <div className="text-[8px] text-pandora-cyan/70 uppercase tracking-wider font-bold">
                  CRDTS
                </div>
                <div className="text-sm font-bold text-white tabular-nums">
                  {userBalance.toLocaleString()}
                </div>
              </div>
              <div className="w-px h-6 bg-pandora-cyan/20" />
              <Zap size={16} className="text-pandora-cyan group-hover:animate-pulse" />
            </div>
          </button>

          {/* Exit button */}
          <button
            type="button"
            onClick={onNavigateHome}
            className="w-9 h-9 flex items-center justify-center bg-black/60 border border-white/10 hover:border-red-500/50 hover:bg-red-500/10 text-gray-400 hover:text-red-400 transition-all group"
            title="Exit Studio"
          >
            <X size={16} className="group-hover:rotate-90 transition-transform" />
          </button>
        </div>
      </div>
    </header>
  );
};
