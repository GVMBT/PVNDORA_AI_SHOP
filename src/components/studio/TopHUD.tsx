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
    <header className="pointer-events-none absolute top-0 right-0 left-0 z-30 p-4">
      {/* Top bar with gradient border */}
      <div className="pointer-events-none absolute top-0 right-0 left-0 h-12 bg-gradient-to-b from-black/80 to-transparent" />

      <div className="relative flex items-start justify-between">
        {/* Left side controls */}
        <div className="pointer-events-auto flex items-center gap-3">
          {/* STUDIO Badge */}
          <div className="group relative">
            <div className="absolute -inset-1 rounded-lg bg-pandora-cyan/20 opacity-50 blur-lg transition-opacity group-hover:opacity-80" />
            <div className="relative flex items-center gap-2 border border-pandora-cyan/50 bg-black/80 px-3 py-1.5 shadow-[0_0_20px_rgba(0,255,255,0.2)]">
              <Sparkles className="animate-pulse text-pandora-cyan" size={12} />
              <span className="font-bold text-[10px] text-pandora-cyan tracking-[0.3em]">
                STUDIO
              </span>
              <span className="border border-yellow-500/40 bg-yellow-500/20 px-1.5 py-0.5 font-bold text-[8px] text-yellow-400">
                BETA
              </span>
            </div>
          </div>

          {/* Sidebar Toggle */}
          <button
            className="group flex h-9 w-9 items-center justify-center border border-white/10 bg-black/60 text-gray-400 backdrop-blur-md transition-all hover:border-pandora-cyan/50 hover:text-pandora-cyan"
            onClick={onSidebarToggle}
            type="button"
          >
            <Sidebar className="transition-transform group-hover:scale-110" size={14} />
          </button>

          {/* Domain Switcher - enhanced */}
          <div className="flex gap-0.5 border border-white/10 bg-black/70 p-1 backdrop-blur-md">
            {(["video", "image", "audio"] as const).map((d) => (
              <button
                className={`relative flex items-center gap-2 overflow-hidden px-4 py-1.5 font-bold text-[10px] uppercase transition-all ${activeDomain === d ? "text-pandora-cyan" : "text-gray-600 hover:text-gray-300"}
                `}
                key={d}
                onClick={() => {
                  AudioEngine.click();
                  onDomainSwitch(d);
                }}
                type="button"
              >
                {activeDomain === d && (
                  <>
                    <motion.div
                      className="absolute inset-0 border border-pandora-cyan/30 bg-pandora-cyan/10"
                      layoutId="domainHighlight"
                      transition={{ type: "spring", stiffness: 500, damping: 35 }}
                    />
                    <motion.div
                      className="absolute right-0 bottom-0 left-0 h-[2px] bg-pandora-cyan shadow-[0_0_10px_#00FFFF]"
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
          <button className="group relative overflow-hidden" onClick={onTopUp} type="button">
            <div className="absolute -inset-1 bg-pandora-cyan/10 opacity-0 blur-md transition-opacity group-hover:opacity-100" />
            <div className="relative flex items-center gap-3 border border-pandora-cyan/30 bg-black/70 px-4 py-2 backdrop-blur-md transition-all hover:border-pandora-cyan/60">
              <div className="text-right">
                <div className="font-bold text-[8px] text-pandora-cyan/70 uppercase tracking-wider">
                  CRDTS
                </div>
                <div className="font-bold text-sm text-white tabular-nums">
                  {userBalance.toLocaleString()}
                </div>
              </div>
              <div className="h-6 w-px bg-pandora-cyan/20" />
              <Zap className="text-pandora-cyan group-hover:animate-pulse" size={16} />
            </div>
          </button>

          {/* Exit button */}
          <button
            className="group flex h-9 w-9 items-center justify-center border border-white/10 bg-black/60 text-gray-400 transition-all hover:border-red-500/50 hover:bg-red-500/10 hover:text-red-400"
            onClick={onNavigateHome}
            title="Exit Studio"
            type="button"
          >
            <X className="transition-transform group-hover:rotate-90" size={16} />
          </button>
        </div>
      </div>
    </header>
  );
};
