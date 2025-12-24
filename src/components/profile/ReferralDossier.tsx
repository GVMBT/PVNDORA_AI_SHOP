/**
 * ReferralDossier Component
 * 
 * Side drawer modal displaying detailed referral information.
 */

import React, { memo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, ShieldCheck, User, Activity } from 'lucide-react';
import DecryptedText from './DecryptedText';
import type { NetworkNodeData } from './types';

interface ReferralDossierProps {
  referral: NetworkNodeData | null;
  onClose: () => void;
}

const ReferralDossier: React.FC<ReferralDossierProps> = ({ referral, onClose }) => {
  if (!referral) return null;

  const activityData = referral.activityData || [20, 35, 45, 30, 55, 40, 50];

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-[200] flex justify-end">
        {/* Backdrop */}
        <motion.div 
          initial={{ opacity: 0 }} 
          animate={{ opacity: 1 }} 
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        />
        
        {/* Drawer */}
        <motion.div 
          initial={{ x: "100%" }}
          animate={{ x: 0 }}
          exit={{ x: "100%" }}
          transition={{ type: "spring", damping: 25, stiffness: 200 }}
          className="relative w-full max-w-md bg-[#050505] border-l border-pandora-cyan/30 shadow-[-20px_0_50px_rgba(0,0,0,0.8)] h-full overflow-y-auto"
        >
          {/* Header */}
          <div className="p-6 border-b border-white/10 bg-[#0a0a0a] flex justify-between items-start sticky top-0 z-20">
            <div>
              <div className="flex items-center gap-2 text-[10px] font-mono text-pandora-cyan mb-1 animate-pulse">
                <ShieldCheck size={12} />
                DECRYPTING_SECURE_FILE...
              </div>
              <h2 className="text-2xl font-display font-bold text-white uppercase flex items-center gap-2">
                <DecryptedText text={referral.handle} speed={40} />
              </h2>
              {referral.invitedBy && (
                <div className="text-[10px] font-mono text-gray-500 mt-1">
                  UPLINK_SOURCE: {referral.invitedBy}
                </div>
              )}
            </div>
            <button onClick={onClose} className="text-gray-500 hover:text-white transition-colors">
              <X size={24} />
            </button>
          </div>

          <div className="p-6 pb-24 space-y-8 relative">
            {/* Identity Matrix */}
            <div className="flex gap-4 items-center">
              <div className="w-20 h-20 bg-black border border-white/20 p-1 relative">
                <div className="w-full h-full bg-gray-900 flex items-center justify-center overflow-hidden">
                  {referral.photoUrl ? (
                    <img src={referral.photoUrl} alt={referral.handle} className="w-full h-full object-cover" />
                  ) : (
                    <User size={32} className="text-gray-600" />
                  )}
                </div>
                <div className="absolute top-0 right-0 w-3 h-3 border-t border-r border-pandora-cyan" />
                <div className="absolute bottom-0 left-0 w-3 h-3 border-b border-l border-pandora-cyan" />
              </div>
              <div className="space-y-1">
                <div className="text-xs text-gray-500 font-mono">
                  STATUS: 
                  <span className={`ml-2 font-bold ${
                    referral.status === 'VIP' ? 'text-yellow-500' : 
                    referral.status === 'SLEEP' ? 'text-red-500' : 
                    'text-green-500'
                  }`}>
                    <DecryptedText text={referral.status} reveal={true} />
                  </span>
                </div>
                {referral.lastActive && (
                  <div className="text-xs text-gray-500 font-mono">
                    LAST_SEEN: <span className="text-white">{referral.lastActive}</span>
                  </div>
                )}
                {referral.rank && (
                  <div className="text-xs text-gray-500 font-mono">
                    RANK: <span className="text-pandora-cyan">{referral.rank}</span>
                  </div>
                )}
              </div>
            </div>

            {/* Visual Activity Graph */}
            <div className="bg-white/5 border border-white/10 p-4 rounded-sm relative group">
              <div className="flex justify-between items-center mb-4">
                <div className="text-[10px] font-mono text-gray-500 uppercase flex items-center gap-2">
                  <Activity size={12} /> Signal Activity (7D)
                </div>
                <div className="text-pandora-cyan text-xs font-bold">+12.4%</div>
              </div>
              
              <div className="h-32 w-full flex items-end gap-1 relative">
                {/* Grid lines */}
                <div className="absolute inset-0 flex flex-col justify-between opacity-10 pointer-events-none">
                  <div className="w-full h-px bg-white" />
                  <div className="w-full h-px bg-white" />
                  <div className="w-full h-px bg-white" />
                </div>
                
                {activityData.map((val, i) => (
                  <div key={i} className="flex-1 flex flex-col justify-end group/bar h-full">
                    <motion.div 
                      initial={{ height: 0 }}
                      animate={{ height: `${val}%` }}
                      transition={{ duration: 0.5, delay: 0.1 * i }}
                      className="w-full bg-pandora-cyan/20 border-t border-pandora-cyan relative hover:bg-pandora-cyan/40 transition-colors"
                    >
                      <div className="absolute -top-6 left-1/2 -translate-x-1/2 bg-black text-white text-[9px] px-1 opacity-0 group-hover/bar:opacity-100 transition-opacity">
                        {val}
                      </div>
                    </motion.div>
                  </div>
                ))}
              </div>
            </div>

            {/* Financial Metrics */}
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-[#0e0e0e] p-3 border border-white/10">
                <div className="text-[9px] text-gray-500 font-mono uppercase mb-1">Total Volume</div>
                <div className="text-xl font-bold text-white flex items-center gap-1">
                  <DecryptedText text={referral.volume || 0} /> $
                </div>
              </div>
              <div className="bg-[#0e0e0e] p-3 border border-white/10">
                <div className="text-[9px] text-gray-500 font-mono uppercase mb-1">Commission Earned</div>
                <div className="text-xl font-bold text-pandora-cyan flex items-center gap-1">
                  +<DecryptedText text={referral.profit || referral.earned || 0} /> $
                </div>
              </div>
            </div>

            {/* Connection Details */}
            <div className="space-y-3">
              <h4 className="text-xs font-mono text-gray-500 uppercase border-b border-white/10 pb-2">
                Connection Telemetry
              </h4>
              <div className="flex justify-between items-center text-xs">
                <span className="text-gray-400">Signal Strength</span>
                <div className="flex items-center gap-1">
                  <div className="w-12 h-1 bg-gray-800 rounded-full overflow-hidden">
                    <div className="h-full bg-green-500" style={{ width: `${referral.signal || 75}%` }} />
                  </div>
                  <span className="font-mono text-green-500">{referral.signal || 75}%</span>
                </div>
              </div>
              <div className="flex justify-between items-center text-xs">
                <span className="text-gray-400">Downlink Nodes</span>
                <span className="font-mono text-white">{referral.subs || 0} Active</span>
              </div>
              <div className="flex justify-between items-center text-xs">
                <span className="text-gray-400">Encryption</span>
                <span className="font-mono text-pandora-cyan">AES-256</span>
              </div>
            </div>

            {/* Close Button */}
            <button 
              onClick={onClose}
              className="w-full py-4 border border-white/10 text-gray-500 hover:text-white hover:bg-white/5 text-xs font-mono uppercase tracking-widest transition-colors mt-8"
            >
              // CLOSE_FILE
            </button>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};

export default memo(ReferralDossier);


































