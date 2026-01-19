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
      <h3 className="mb-4 flex items-center gap-2 font-mono text-gray-500 text-xs uppercase">
        <ShieldCheck size={14} /> {t("profile.career.title")}
        <button
          className="ml-auto flex items-center gap-1 text-[9px] text-pandora-cyan transition-colors hover:text-white"
          onClick={() => setShowExplainer(true)}
          type="button"
        >
          <HelpCircle size={12} /> {t("profile.career.howItWorks")}
        </button>
      </h3>

      {/* Explainer Modal */}
      <ReferralExplainerModal
        commissions={commissions}
        currency={currency as CurrencyCode}
        currentLevel={currentLevel.id}
        currentTurnover={currentTurnover}
        exchangeRate={exchangeRate}
        isOpen={showExplainer}
        onClose={() => setShowExplainer(false)}
        progressPercent={progressPercent}
        thresholds={thresholds}
      />

      <div className="group relative overflow-hidden border border-white/10 bg-[#080808] p-6 transition-all hover:border-white/20 md:p-8">
        <div className="relative z-10 flex flex-col items-start justify-between gap-6 md:flex-row md:items-center">
          {/* Current Status Info */}
          <div className="w-full shrink-0 md:w-48">
            <div className="mb-1 font-mono text-[10px] text-gray-500 uppercase">
              {t("profile.career.currentRank")}
            </div>
            <div
              className={`font-bold font-display text-2xl ${currentLevel.color} flex items-center gap-2`}
            >
              {currentLevel.label}
              {getLevelIcon(currentLevel.id)}
            </div>
            <div className="mt-1 font-mono text-[10px] text-gray-600">
              {t("profile.career.turnover")}{" "}
              <span className="font-bold text-white">{formatPrice(currentTurnover, currency)}</span>{" "}
              {maxTurnover === Number.POSITIVE_INFINITY
                ? ""
                : `/ ${formatPrice(maxTurnover, currency)}`}
            </div>
          </div>

          {/* Progress Bar Container */}
          <div className="relative w-full flex-1 pt-2 pb-6 md:px-8 md:py-0">
            {/* Background Track */}
            <div className="relative h-3 w-full overflow-hidden rounded-sm border border-white/10 bg-black">
              {/* Fill */}
              <motion.div
                animate={{ width: `${progressPercent}%` }}
                className="relative h-full overflow-hidden bg-gradient-to-r from-gray-500 via-pandora-cyan to-white shadow-[0_0_15px_#00FFFF]"
                initial={{ width: 0 }}
                transition={{ duration: 1.5, ease: "circOut" }}
              >
                {/* Scanline inside bar */}
                <div className="absolute inset-0 h-full w-full translate-x-[-150%] -skew-x-12 animate-[scan_2s_infinite] bg-white/30" />
              </motion.div>
            </div>
            {/* Markers */}
            <div className="absolute bottom-0 mt-2 flex w-full justify-between font-mono text-[9px] text-gray-600 md:static">
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
          <div className="hidden w-40 shrink-0 flex-col items-end text-right opacity-80 md:flex">
            {nextLevel ? (
              <>
                <div className="mb-1 font-mono text-[9px] text-gray-500 uppercase">
                  {t("profile.career.nextUnlock")}
                </div>
                <div className={`font-bold text-sm ${nextLevel.color}`}>{nextLevel.label}</div>
              </>
            ) : (
              <div className="font-bold text-pandora-cyan text-sm">
                {t("profile.career.maximumClearance")}
              </div>
            )}
          </div>
        </div>

        {/* VIP Partner Application Button */}
        {!isVip && onApplyPartner && (
          <div className="relative mt-6 border-white/10 border-t pt-4">
            {/* Glow effect */}
            <div className="absolute inset-0 bg-pandora-cyan/5 opacity-0 blur-xl transition-opacity group-hover:opacity-100" />

            <button
              className="group relative flex w-full items-center justify-center gap-2 overflow-hidden border border-pandora-cyan/30 bg-black/50 py-3.5 font-mono text-pandora-cyan text-xs uppercase tracking-wider transition-all hover:border-pandora-cyan/50 hover:bg-black/70"
              onClick={onApplyPartner}
              type="button"
            >
              {/* Corner accents */}
              <div className="absolute top-0 left-0 h-3 w-3 border-pandora-cyan/50 border-t-2 border-l-2 opacity-0 transition-opacity group-hover:opacity-100" />
              <div className="absolute top-0 right-0 h-3 w-3 border-pandora-cyan/50 border-t-2 border-r-2 opacity-0 transition-opacity group-hover:opacity-100" />
              <div className="absolute bottom-0 left-0 h-3 w-3 border-pandora-cyan/50 border-b-2 border-l-2 opacity-0 transition-opacity group-hover:opacity-100" />
              <div className="absolute right-0 bottom-0 h-3 w-3 border-pandora-cyan/50 border-r-2 border-b-2 opacity-0 transition-opacity group-hover:opacity-100" />

              {/* Scanline effect */}
              <div className="pointer-events-none absolute inset-0 bg-[repeating-linear-gradient(0deg,rgba(0,255,255,0.03)_0px,rgba(0,255,255,0.03)_1px,transparent_1px,transparent_2px)]" />

              {/* Content */}
              <span className="relative z-10 flex items-center gap-2">
                <ShieldCheck className="transition-transform group-hover:scale-110" size={14} />
                <span className="transition-colors group-hover:text-white">
                  {t("profile.career.eliteOperatorApply")}
                </span>
                <Star
                  className="text-pandora-cyan transition-transform duration-500 group-hover:rotate-180"
                  size={12}
                />
              </span>

              {/* Hover glow */}
              <div className="absolute inset-0 translate-y-full bg-pandora-cyan/10 transition-transform duration-300 group-hover:translate-y-0" />
            </button>
          </div>
        )}

        {isVip && (
          <div className="mt-6 border-white/10 border-t pt-4 text-center">
            <div className="inline-flex items-center gap-2 border border-pandora-cyan/30 bg-pandora-cyan/10 px-4 py-2 font-mono text-pandora-cyan text-xs uppercase">
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
