/**
 * ProfileCareer Component
 * 
 * Displays career progress and level information.
 */

import React, { memo } from 'react';
import { ShieldCheck, Wifi, Radio, Crown } from 'lucide-react';
import { motion } from 'framer-motion';
import type { CareerLevelData } from './types';

interface ProfileCareerProps {
  currentLevel: CareerLevelData;
  nextLevel?: CareerLevelData;
  currentTurnover: number;
  maxTurnover: number;
  progressPercent: number;
}

const ProfileCareer: React.FC<ProfileCareerProps> = ({
  currentLevel,
  nextLevel,
  currentTurnover,
  maxTurnover,
  progressPercent,
}) => {
  return (
    <div className="mb-12">
      <h3 className="text-xs font-mono text-gray-500 uppercase mb-4 flex items-center gap-2">
        <ShieldCheck size={14} /> Network Clearance // Career Path
      </h3>
      
      <div className="bg-[#080808] border border-white/10 p-6 md:p-8 relative overflow-hidden group hover:border-white/20 transition-all">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6 relative z-10">
          {/* Current Status Info */}
          <div className="w-full md:w-48 shrink-0">
            <div className="text-[10px] text-gray-500 font-mono uppercase mb-1">Current Rank</div>
            <div className={`text-2xl font-display font-bold ${currentLevel.color} flex items-center gap-2`}>
              {currentLevel.label}
              {currentLevel.id === 1 ? <Wifi size={18} /> : currentLevel.id === 2 ? <Radio size={18} /> : <Crown size={18} />}
            </div>
            <div className="text-[10px] text-gray-600 mt-1 font-mono">
              Turnover: <span className="text-white font-bold">{currentTurnover}$</span> / {maxTurnover}$
            </div>
          </div>

          {/* Progress Bar Container */}
          <div className="flex-1 w-full relative pt-2 pb-6 md:py-0 md:px-8">
            {/* Background Track */}
            <div className="h-3 w-full bg-black border border-white/10 rounded-sm overflow-hidden relative">
              {/* Fill */}
              <motion.div 
                initial={{ width: 0 }}
                animate={{ width: `${progressPercent}%` }}
                transition={{ duration: 1.5, ease: "circOut" }}
                className="h-full bg-gradient-to-r from-gray-500 via-pandora-cyan to-white shadow-[0_0_15px_#00FFFF] relative overflow-hidden"
              >
                {/* Scanline inside bar */}
                <div className="absolute inset-0 bg-white/30 w-full h-full -skew-x-12 translate-x-[-150%] animate-[scan_2s_infinite]" />
              </motion.div>
            </div>
            {/* Markers */}
            <div className="flex justify-between text-[9px] font-mono text-gray-600 mt-2 absolute w-full bottom-0 md:static">
              <span>{currentLevel.min}$</span>
              {nextLevel ? <span>NEXT: {nextLevel.label} ({nextLevel.min}$)</span> : <span>MAX LEVEL</span>}
            </div>
          </div>

          {/* Next Reward Preview */}
          <div className="hidden md:flex flex-col items-end w-40 shrink-0 text-right opacity-80">
            {nextLevel ? (
              <>
                <div className="text-[9px] text-gray-500 font-mono uppercase mb-1">Next Unlock</div>
                <div className={`text-sm font-bold ${nextLevel.color}`}>{nextLevel.label}</div>
              </>
            ) : (
              <div className="text-pandora-cyan font-bold text-sm">MAXIMUM CLEARANCE</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default memo(ProfileCareer);





