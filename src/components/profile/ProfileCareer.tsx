/**
 * ProfileCareer Component
 *
 * Displays career progress and level information.
 */

import { motion } from "framer-motion";
import { Crown, HelpCircle, Radio, ShieldCheck, Star, Wifi } from "lucide-react";
import type React from "react";
import { memo, useState } from "react";
import { useLocale } from "../../hooks/useLocale";
import type { CurrencyCode } from "../../utils/currency";
import ReferralExplainerModal from "./ReferralExplainerModal";
import type { CareerLevelData } from "./types";

// Helper to get level icon (avoid nested ternary)
const getLevelIcon = (levelId: number) => {
  if (levelId === 1) return <Wifi size={18} />;
  if (levelId === 2) return <Radio size={18} />;
  return <Crown size={18} />;
};

interface ProfileCareerProps {
  currentLevel: CareerLevelData;
  nextLevel?: CareerLevelData;
  currentTurnover: number; // Already converted to user currency
  maxTurnover: number; // Already converted to user currency
  progressPercent: number;
  thresholds?: { level2: number; level3: number }; // USD thresholds
  commissions?: { level1: number; level2: number; level3: number };
  currency?: CurrencyCode; // User's currency
  exchangeRate?: number; // Exchange rate for threshold conversion
  isVip?: boolean; // Whether user is already a VIP partner
  onApplyPartner?: () => void; // Handler for opening partner application
}

const ProfileCareer: React.FC<ProfileCareerProps> = ({
  currentLevel,
  nextLevel,
  currentTurnover,
  maxTurnover,
  progressPercent,
  thresholds = { level2: 250, level3: 1000 },
  commissions = { level1: 10, level2: 7, level3: 3 },
  currency: propCurrency,
  exchangeRate = 1,
  isVip = false,
  onApplyPartner,
}) => {
  const { currency: localeCurrency, formatPrice, t } = useLocale();
  const currency = propCurrency || localeCurrency;
  const [showExplainer, setShowExplainer] = useState(false);

  return (
    <div className="mb-12">
      <h3 className="text-xs font-mono text-gray-500 uppercase mb-4 flex items-center gap-2">
        <ShieldCheck size={14} /> {t("profile.career.title")}
        <button
          type="button"
          onClick={() => setShowExplainer(true)}
          className="ml-auto text-pandora-cyan hover:text-white transition-colors flex items-center gap-1 text-[9px]"
        >
          <HelpCircle size={12} /> {t("profile.career.howItWorks")}
        </button>
      </h3>

      {/* Explainer Modal */}
      <ReferralExplainerModal
        isOpen={showExplainer}
        onClose={() => setShowExplainer(false)}
        currentLevel={currentLevel.id}
        currentTurnover={currentTurnover}
        progressPercent={progressPercent}
        thresholds={thresholds}
        commissions={commissions}
        currency={currency as CurrencyCode}
        exchangeRate={exchangeRate}
      />

      <div className="bg-[#080808] border border-white/10 p-6 md:p-8 relative overflow-hidden group hover:border-white/20 transition-all">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6 relative z-10">
          {/* Current Status Info */}
          <div className="w-full md:w-48 shrink-0">
            <div className="text-[10px] text-gray-500 font-mono uppercase mb-1">
              {t("profile.career.currentRank")}
            </div>
            <div
              className={`text-2xl font-display font-bold ${currentLevel.color} flex items-center gap-2`}
            >
              {currentLevel.label}
              {getLevelIcon(currentLevel.id)}
            </div>
            <div className="text-[10px] text-gray-600 mt-1 font-mono">
              {t("profile.career.turnover")}{" "}
              <span className="text-white font-bold">{formatPrice(currentTurnover, currency)}</span>{" "}
              {maxTurnover === Infinity ? "" : `/ ${formatPrice(maxTurnover, currency)}`}
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
              <span>{formatPrice(currentLevel.min, currency)}</span>
              {nextLevel ? (
                <span>
                  {t("profile.career.nextLevelFormat", {
                    label: nextLevel.label,
                    price: formatPrice(nextLevel.min, currency),
                  })}
                </span>
              ) : (
                <span>{t("profile.career.maxLevel")}</span>
              )}
            </div>
          </div>

          {/* Next Reward Preview */}
          <div className="hidden md:flex flex-col items-end w-40 shrink-0 text-right opacity-80">
            {nextLevel ? (
              <>
                <div className="text-[9px] text-gray-500 font-mono uppercase mb-1">
                  {t("profile.career.nextUnlock")}
                </div>
                <div className={`text-sm font-bold ${nextLevel.color}`}>{nextLevel.label}</div>
              </>
            ) : (
              <div className="text-pandora-cyan font-bold text-sm">
                {t("profile.career.maximumClearance")}
              </div>
            )}
          </div>
        </div>

        {/* VIP Partner Application Button */}
        {!isVip && onApplyPartner && (
          <div className="mt-6 pt-4 border-t border-white/10 relative">
            {/* Glow effect */}
            <div className="absolute inset-0 bg-pandora-cyan/5 blur-xl opacity-0 group-hover:opacity-100 transition-opacity" />

            <button
              type="button"
              onClick={onApplyPartner}
              className="relative w-full py-3.5 bg-black/50 hover:bg-black/70 border border-pandora-cyan/30 hover:border-pandora-cyan/50 text-pandora-cyan font-mono text-xs uppercase tracking-wider flex items-center justify-center gap-2 transition-all group overflow-hidden"
            >
              {/* Corner accents */}
              <div className="absolute top-0 left-0 w-3 h-3 border-l-2 border-t-2 border-pandora-cyan/50 opacity-0 group-hover:opacity-100 transition-opacity" />
              <div className="absolute top-0 right-0 w-3 h-3 border-r-2 border-t-2 border-pandora-cyan/50 opacity-0 group-hover:opacity-100 transition-opacity" />
              <div className="absolute bottom-0 left-0 w-3 h-3 border-l-2 border-b-2 border-pandora-cyan/50 opacity-0 group-hover:opacity-100 transition-opacity" />
              <div className="absolute bottom-0 right-0 w-3 h-3 border-r-2 border-b-2 border-pandora-cyan/50 opacity-0 group-hover:opacity-100 transition-opacity" />

              {/* Scanline effect */}
              <div className="absolute inset-0 bg-[repeating-linear-gradient(0deg,rgba(0,255,255,0.03)_0px,rgba(0,255,255,0.03)_1px,transparent_1px,transparent_2px)] pointer-events-none" />

              {/* Content */}
              <span className="relative z-10 flex items-center gap-2">
                <ShieldCheck size={14} className="group-hover:scale-110 transition-transform" />
                <span className="group-hover:text-white transition-colors">
                  {t("profile.career.eliteOperatorApply")}
                </span>
                <Star
                  size={12}
                  className="text-pandora-cyan group-hover:rotate-180 transition-transform duration-500"
                />
              </span>

              {/* Hover glow */}
              <div className="absolute inset-0 bg-pandora-cyan/10 translate-y-full group-hover:translate-y-0 transition-transform duration-300" />
            </button>
          </div>
        )}

        {isVip && (
          <div className="mt-6 pt-4 border-t border-white/10 text-center">
            <div className="inline-flex items-center gap-2 text-pandora-cyan font-mono text-xs uppercase bg-pandora-cyan/10 border border-pandora-cyan/30 px-4 py-2">
              <ShieldCheck size={14} />
              <span>{t("profile.career.eliteOperatorActive")}</span>
              <Star size={12} />
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default memo(ProfileCareer);
