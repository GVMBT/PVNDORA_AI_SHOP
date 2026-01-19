/**
 * ReferralDossier Component
 *
 * Side drawer modal displaying detailed referral information.
 */

import { AnimatePresence, motion } from "framer-motion";
import { Activity, ShieldCheck, User, X } from "lucide-react";
import type React from "react";
import { memo } from "react";
import DecryptedText from "./DecryptedText";
import type { NetworkNodeData } from "./types";

// Helper for status color (avoid nested ternary)
const getStatusColor = (status: string): string => {
  if (status === "VIP") {
    return "text-yellow-500";
  }
  if (status === "SLEEP") {
    return "text-red-500";
  }
  return "text-green-500";
};

interface ReferralDossierProps {
  referral: NetworkNodeData | null;
  onClose: () => void;
}

const ReferralDossier: React.FC<ReferralDossierProps> = ({ referral, onClose }) => {
  if (!referral) {
    return null;
  }

  const activityData = referral.activityData || [20, 35, 45, 30, 55, 40, 50];

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-[200] flex justify-end">
        {/* Backdrop */}
        <motion.div
          animate={{ opacity: 1 }}
          className="absolute inset-0 bg-black/60 backdrop-blur-sm"
          exit={{ opacity: 0 }}
          initial={{ opacity: 0 }}
          onClick={onClose}
        />

        {/* Drawer */}
        <motion.div
          animate={{ x: 0 }}
          className="relative h-full w-full max-w-md overflow-y-auto border-pandora-cyan/30 border-l bg-[#050505] shadow-[-20px_0_50px_rgba(0,0,0,0.8)]"
          exit={{ x: "100%" }}
          initial={{ x: "100%" }}
          transition={{ type: "spring", damping: 25, stiffness: 200 }}
        >
          {/* Header */}
          <div className="sticky top-0 z-20 flex items-start justify-between border-white/10 border-b bg-[#0a0a0a] p-6">
            <div>
              <div className="mb-1 flex animate-pulse items-center gap-2 font-mono text-[10px] text-pandora-cyan">
                <ShieldCheck size={12} />
                DECRYPTING_SECURE_FILE...
              </div>
              <h2 className="flex items-center gap-2 font-bold font-display text-2xl text-white uppercase">
                <DecryptedText speed={40} text={referral.handle} />
              </h2>
              {referral.invitedBy && (
                <div className="mt-1 font-mono text-[10px] text-gray-500">
                  UPLINK_SOURCE: {referral.invitedBy}
                </div>
              )}
            </div>
            <button
              className="text-gray-500 transition-colors hover:text-white"
              onClick={onClose}
              type="button"
            >
              <X size={24} />
            </button>
          </div>

          <div className="relative space-y-8 p-6 pb-24">
            {/* Identity Matrix */}
            <div className="flex items-center gap-4">
              <div className="relative h-20 w-20 border border-white/20 bg-black p-1">
                <div className="flex h-full w-full items-center justify-center overflow-hidden bg-gray-900">
                  {referral.photoUrl ? (
                    <img
                      alt={referral.handle}
                      className="h-full w-full object-cover"
                      src={referral.photoUrl}
                    />
                  ) : (
                    <User className="text-gray-600" size={32} />
                  )}
                </div>
                <div className="absolute top-0 right-0 h-3 w-3 border-pandora-cyan border-t border-r" />
                <div className="absolute bottom-0 left-0 h-3 w-3 border-pandora-cyan border-b border-l" />
              </div>
              <div className="space-y-1">
                <div className="font-mono text-gray-500 text-xs">
                  <span>STATUS:</span>
                  <span className={`ml-2 font-bold ${getStatusColor(referral.status)}`}>
                    <DecryptedText reveal={true} text={referral.status} />
                  </span>
                </div>
                {referral.lastActive && (
                  <div className="font-mono text-gray-500 text-xs">
                    LAST_SEEN: <span className="text-white">{referral.lastActive}</span>
                  </div>
                )}
                {referral.rank && (
                  <div className="font-mono text-gray-500 text-xs">
                    RANK: <span className="text-pandora-cyan">{referral.rank}</span>
                  </div>
                )}
              </div>
            </div>

            {/* Visual Activity Graph */}
            <div className="group relative rounded-sm border border-white/10 bg-white/5 p-4">
              <div className="mb-4 flex items-center justify-between">
                <div className="flex items-center gap-2 font-mono text-[10px] text-gray-500 uppercase">
                  <Activity size={12} /> Signal Activity (7D)
                </div>
                <div className="font-bold text-pandora-cyan text-xs">+12.4%</div>
              </div>

              <div className="relative flex h-32 w-full items-end gap-1">
                {/* Grid lines */}
                <div className="pointer-events-none absolute inset-0 flex flex-col justify-between opacity-10">
                  <div className="h-px w-full bg-white" />
                  <div className="h-px w-full bg-white" />
                  <div className="h-px w-full bg-white" />
                </div>

                {activityData.map((val, idx) => (
                  <div
                    className="group/bar flex h-full flex-1 flex-col justify-end"
                    key={`activity-${idx}-${val}`}
                  >
                    <motion.div
                      animate={{ height: `${val}%` }}
                      className="relative w-full border-pandora-cyan border-t bg-pandora-cyan/20 transition-colors hover:bg-pandora-cyan/40"
                      initial={{ height: 0 }}
                      transition={{ duration: 0.5, delay: 0.1 * idx }}
                    >
                      <div className="absolute -top-6 left-1/2 -translate-x-1/2 bg-black px-1 text-[9px] text-white opacity-0 transition-opacity group-hover/bar:opacity-100">
                        {val}
                      </div>
                    </motion.div>
                  </div>
                ))}
              </div>
            </div>

            {/* Financial Metrics */}
            <div className="grid grid-cols-2 gap-4">
              <div className="border border-white/10 bg-[#0e0e0e] p-3">
                <div className="mb-1 font-mono text-[9px] text-gray-500 uppercase">
                  Total Volume
                </div>
                <div className="flex items-center gap-1 font-bold text-white text-xl">
                  <DecryptedText text={referral.volume || 0} /> $
                </div>
              </div>
              <div className="border border-white/10 bg-[#0e0e0e] p-3">
                <div className="mb-1 font-mono text-[9px] text-gray-500 uppercase">
                  Commission Earned
                </div>
                <div className="flex items-center gap-1 font-bold text-pandora-cyan text-xl">
                  +<DecryptedText text={referral.profit || referral.earned || 0} /> $
                </div>
              </div>
            </div>

            {/* Connection Details */}
            <div className="space-y-3">
              <h4 className="border-white/10 border-b pb-2 font-mono text-gray-500 text-xs uppercase">
                Connection Telemetry
              </h4>
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-400">Signal Strength</span>
                <div className="flex items-center gap-1">
                  <div className="h-1 w-12 overflow-hidden rounded-full bg-gray-800">
                    <div
                      className="h-full bg-green-500"
                      style={{ width: `${referral.signal || 75}%` }}
                    />
                  </div>
                  <span className="font-mono text-green-500">{referral.signal || 75}%</span>
                </div>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-400">Downlink Nodes</span>
                <span className="font-mono text-white">{referral.subs || 0} Active</span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-400">Encryption</span>
                <span className="font-mono text-pandora-cyan">AES-256</span>
              </div>
            </div>

            {/* Close Button */}
            <button
              className="mt-8 w-full border border-white/10 py-4 font-mono text-gray-500 text-xs uppercase tracking-widest transition-colors hover:bg-white/5 hover:text-white"
              onClick={onClose}
              type="button"
            >
              {"// CLOSE_FILE"}
            </button>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};

export default memo(ReferralDossier);
