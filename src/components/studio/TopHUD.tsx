import { motion } from "framer-motion";
import { ImageIcon, LogOut, Music, Sidebar, Video, Zap } from "lucide-react";
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
    <header className="absolute top-0 left-0 right-0 p-4 z-30 pointer-events-none flex justify-between items-start">
      <div className="pointer-events-auto flex items-center gap-4">
        {/* BACK / EXIT BUTTON */}
        <button
          type="button"
          onClick={onNavigateHome}
          className="h-8 px-4 flex items-center gap-2 bg-red-900/20 border border-red-500/30 text-red-400 hover:bg-red-500 hover:text-white transition-all rounded-sm group uppercase font-bold text-[10px] tracking-wider"
        >
          <LogOut size={12} className="group-hover:-translate-x-1 transition-transform" />
          EXIT STUDIO
        </button>

        {/* Sidebar Toggle */}
        <button
          type="button"
          onClick={onSidebarToggle}
          className="w-8 h-8 flex items-center justify-center bg-black/60 backdrop-blur-md border border-white/10 hover:border-pandora-cyan text-gray-400 hover:text-pandora-cyan transition-all rounded-sm group"
        >
          <Sidebar size={14} className="group-hover:scale-110 transition-transform" />
        </button>

        {/* Domain Switcher */}
        <div className="flex bg-black/60 backdrop-blur-md border border-white/10 rounded-sm p-1 gap-1">
          {(["video", "image", "audio"] as const).map((d) => (
            <button
              type="button"
              key={d}
              onClick={() => {
                AudioEngine.click();
                onDomainSwitch(d);
              }}
              className={`
                px-3 py-1 text-[10px] font-bold uppercase transition-all flex items-center gap-2 rounded-sm relative overflow-hidden
                ${activeDomain === d ? "bg-white/10 text-white shadow-inner" : "text-gray-600 hover:text-gray-300"}
              `}
            >
              {activeDomain === d && (
                <motion.div layoutId="domainHighlight" className="absolute inset-0 bg-white/10" />
              )}
              {d === "video" && <Video size={12} />}
              {d === "image" && <ImageIcon size={12} />}
              {d === "audio" && <Music size={12} />}
              <span className="hidden sm:inline">{d}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Right Side Info */}
      <div className="pointer-events-auto flex gap-3">
        <button
          type="button"
          onClick={onTopUp}
          className="flex items-center gap-3 bg-black/60 backdrop-blur-md border border-pandora-cyan/30 px-4 py-1.5 hover:bg-pandora-cyan/10 transition-all group rounded-sm"
        >
          <div className="text-right">
            <div className="text-[8px] text-pandora-cyan uppercase tracking-wider opacity-70 group-hover:opacity-100">
              Credits
            </div>
            <div className="text-xs font-bold text-white">{userBalance}</div>
          </div>
          <Zap size={14} className="text-pandora-cyan group-hover:animate-pulse" />
        </button>
      </div>
    </header>
  );
};
