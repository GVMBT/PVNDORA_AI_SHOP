/**
 * ReferralExplainerModal Component
 *
 * Cyberpunk-styled modal explaining the Network Clearance / Referral Program
 */

import { AnimatePresence, motion } from "framer-motion";
import { ArrowRight, Shield, Sparkles, Target, Users, X, Zap } from "lucide-react";
import type React from "react";
import { memo } from "react";
import { useLocale } from "../../hooks/useLocale";
import type { CurrencyCode } from "../../utils/currency";

// Helper for level card styling (avoid nested ternaries)
const getLevelCardClasses = (
  isCurrentLevel: boolean,
  isUnlocked: boolean,
  bgColor: string,
  borderColor: string
): string => {
  if (isCurrentLevel) {
    return `${bgColor} ${borderColor}`;
  }
  if (isUnlocked) {
    return "bg-white/5 border-white/10";
  }
  return "bg-black/30 border-white/5 opacity-60";
};

// Helper for threshold value
const getLevelThreshold = (
  level: number,
  thresholdLevel2: number,
  thresholdLevel3: number
): number | null => {
  if (level === 2) {
    return thresholdLevel2;
  }
  if (level === 3) {
    return thresholdLevel3;
  }
  return null;
};

interface ReferralExplainerModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentLevel?: number; // 0, 1, 2, 3
  currentTurnover?: number; // Current turnover (already converted to user currency)
  progressPercent?: number; // Pre-calculated progress percentage (from adapter)
  thresholds?: {
    level2: number; // Anchor thresholds in display currency (RUB: 20000, USD: 250)
    level3: number; // Anchor thresholds in display currency (RUB: 80000, USD: 1000)
  };
  commissions?: {
    level1: number;
    level2: number;
    level3: number;
  };
  currency?: CurrencyCode; // User's currency (RUB, USD, etc.)
  exchangeRate?: number; // Exchange rate for conversion (for fallback only)
}

// Career levels - matches profileAdapter.ts naming
const LEVELS = [
  {
    level: 1,
    name: "PROXY",
    color: "text-gray-400",
    bgColor: "bg-gray-500/10",
    borderColor: "border-gray-500/30",
    icon: "📡",
    description_ru: "Стартовый допуск. Доступ к уровню 1 сети.",
    description_en: "Entry clearance. Level 1 network access.",
  },
  {
    level: 2,
    name: "OPERATOR",
    color: "text-purple-400",
    bgColor: "bg-purple-500/10",
    borderColor: "border-purple-500/30",
    icon: "⚡",
    description_ru: "Расширенный допуск. Уровни 1-2 разблокированы.",
    description_en: "Extended clearance. Levels 1-2 unlocked.",
  },
  {
    level: 3,
    name: "ARCHITECT",
    color: "text-yellow-500",
    bgColor: "bg-yellow-500/10",
    borderColor: "border-yellow-500/30",
    icon: "👑",
    description_ru: "Максимальный допуск. Все 3 уровня активны.",
    description_en: "Maximum clearance. All 3 levels active.",
  },
];

const ReferralExplainerModal: React.FC<ReferralExplainerModalProps> = ({
  isOpen,
  onClose,
  currentLevel = 0,
  currentTurnover = 0,
  progressPercent: propProgressPercent,
  thresholds = { level2: 250, level3: 1000 },
  commissions = { level1: 10, level2: 7, level3: 3 },
  currency = "USD",
  exchangeRate: _exchangeRate = 1,
}) => {
  const { locale, formatPrice } = useLocale();
  const isRu = locale === "ru";

  // Thresholds are anchor thresholds in display currency (from backend):
  // RUB: 20000/80000, USD: 250/1000
  // No conversion needed - thresholds are already in display currency
  const thresholdLevel2 = thresholds.level2;
  const thresholdLevel3 = thresholds.level3;

  const getLevelDescription = (lvl: (typeof LEVELS)[number]) => {
    return isRu ? lvl.description_ru : lvl.description_en;
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          animate={{ opacity: 1 }}
          className="fixed inset-0 z-[100] flex items-center justify-center p-4"
          exit={{ opacity: 0 }}
          initial={{ opacity: 0 }}
        >
          {/* Backdrop */}
          <motion.div
            animate={{ opacity: 1 }}
            className="absolute inset-0 bg-black/90 backdrop-blur-sm"
            exit={{ opacity: 0 }}
            initial={{ opacity: 0 }}
            onClick={onClose}
          />

          {/* Modal */}
          <motion.div
            animate={{ scale: 1, y: 0, opacity: 1 }}
            className="relative max-h-[90vh] w-full max-w-2xl overflow-y-auto border border-pandora-cyan/30 bg-[#050505] shadow-2xl shadow-pandora-cyan/10"
            exit={{ scale: 0.9, y: 50, opacity: 0 }}
            initial={{ scale: 0.9, y: 50, opacity: 0 }}
            transition={{ type: "spring", damping: 25, stiffness: 300 }}
          >
            {/* Animated top border */}
            <div className="absolute top-0 left-0 h-[2px] w-full bg-gradient-to-r from-transparent via-pandora-cyan to-transparent" />

            {/* Close button */}
            <button
              className="absolute top-4 right-4 z-10 flex h-8 w-8 items-center justify-center text-gray-500 transition-colors hover:text-white"
              onClick={onClose}
              type="button"
            >
              <X size={20} />
            </button>

            {/* Header */}
            <div className="border-white/5 border-b p-6 pb-4">
              <div className="mb-2 flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-sm border border-pandora-cyan/30 bg-pandora-cyan/10">
                  <Shield className="text-pandora-cyan" size={20} />
                </div>
                <div>
                  <h2 className="font-bold font-display text-white text-xl tracking-tight">
                    {isRu ? "ПРОТОКОЛ АПЛИНКА" : "UPLINK PROTOCOL"}
                  </h2>
                  <p className="font-mono text-[10px] text-gray-500 uppercase tracking-widest">
                    {isRu ? "РЕФЕРАЛЬНАЯ СИСТЕМА PVNDORA" : "PVNDORA REFERRAL SYSTEM"}
                  </p>
                </div>
              </div>
            </div>

            {/* Content */}
            <div className="space-y-6 p-6">
              {/* How It Works Section */}
              <div>
                <h3 className="mb-3 flex items-center gap-2 font-bold text-pandora-cyan text-sm">
                  <Zap size={14} /> {isRu ? "КАК ЭТО РАБОТАЕТ" : "HOW IT WORKS"}
                </h3>
                <div className="rounded-sm border border-white/10 bg-white/5 p-4">
                  <p className="text-gray-300 text-sm leading-relaxed">
                    {isRu
                      ? "Каждый пользователь получает уникальный реферальный код. Когда приглашённый вами пользователь совершает покупку, вы получаете комиссию. Чем больше ваш оборот — тем выше уровень допуска и глубже сеть."
                      : "Every user gets a unique referral code. When your invited user makes a purchase, you earn a commission. Higher turnover = higher clearance level = deeper network access."}
                  </p>
                </div>
              </div>

              {/* Network Levels Visualization */}
              <div>
                <h3 className="mb-3 flex items-center gap-2 font-bold text-pandora-cyan text-sm">
                  <Users size={14} /> {isRu ? "УРОВНИ СЕТИ" : "NETWORK LEVELS"}
                </h3>

                {/* Visual Flow */}
                <div className="mb-4 rounded-sm border border-white/10 bg-black/50 p-4">
                  <div className="flex flex-wrap items-center justify-center gap-2">
                    <div className="text-center">
                      <div className="mx-auto mb-1 flex h-12 w-12 items-center justify-center rounded-full border border-pandora-cyan/50 bg-pandora-cyan/20">
                        <span className="font-bold text-pandora-cyan">ВЫ</span>
                      </div>
                      <span className="font-mono text-[9px] text-gray-500">UPLINK</span>
                    </div>

                    <ArrowRight className="text-pandora-cyan/50" size={16} />

                    <div className="text-center">
                      <div className="mx-auto mb-1 flex h-12 w-12 items-center justify-center rounded-full border border-green-500/50 bg-green-500/20">
                        <span className="font-bold text-green-500 text-sm">
                          {commissions.level1}%
                        </span>
                      </div>
                      <span className="font-mono text-[9px] text-gray-500">
                        {isRu ? "УР.1" : "LV.1"}
                      </span>
                    </div>

                    <ArrowRight className="text-yellow-500/50" size={16} />

                    <div className="text-center">
                      <div className="mx-auto mb-1 flex h-12 w-12 items-center justify-center rounded-full border border-yellow-500/50 bg-yellow-500/20">
                        <span className="font-bold text-sm text-yellow-500">
                          {commissions.level2}%
                        </span>
                      </div>
                      <span className="font-mono text-[9px] text-gray-500">
                        {isRu ? "УР.2" : "LV.2"}
                      </span>
                    </div>

                    <ArrowRight className="text-red-500/50" size={16} />

                    <div className="text-center">
                      <div className="mx-auto mb-1 flex h-12 w-12 items-center justify-center rounded-full border border-red-500/50 bg-red-500/20">
                        <span className="font-bold text-red-500 text-sm">
                          {commissions.level3}%
                        </span>
                      </div>
                      <span className="font-mono text-[9px] text-gray-500">
                        {isRu ? "УР.3" : "LV.3"}
                      </span>
                    </div>
                  </div>

                  <p className="mt-3 text-center font-mono text-[10px] text-gray-500">
                    {isRu
                      ? "Уровень 1 = ваши прямые рефералы. Уровни 2-3 = рефералы ваших рефералов."
                      : "Level 1 = your direct referrals. Levels 2-3 = referrals of your referrals."}
                  </p>
                </div>
              </div>

              {/* Clearance Levels */}
              <div>
                <h3 className="mb-3 flex items-center gap-2 font-bold text-pandora-cyan text-sm">
                  <Target size={14} /> {isRu ? "УРОВНИ ДОПУСКА" : "CLEARANCE LEVELS"}
                </h3>

                <div className="space-y-2">
                  {LEVELS.map((lvl, _i) => {
                    const isCurrentLevel = lvl.level === currentLevel;
                    const isUnlocked = lvl.level <= currentLevel;
                    const threshold = getLevelThreshold(
                      lvl.level,
                      thresholdLevel2,
                      thresholdLevel3
                    );

                    return (
                      <div
                        className={`rounded-sm border p-3 transition-all ${getLevelCardClasses(isCurrentLevel, isUnlocked, lvl.bgColor, lvl.borderColor)}`}
                        key={lvl.level}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <span className="text-lg">{lvl.icon}</span>
                            <div>
                              <div className={`font-bold font-display ${lvl.color}`}>
                                {lvl.name}
                                {isCurrentLevel && (
                                  <span className="ml-2 rounded-full bg-pandora-cyan/20 px-2 py-0.5 font-mono text-[9px] text-pandora-cyan">
                                    {isRu ? "ТЕКУЩИЙ" : "CURRENT"}
                                  </span>
                                )}
                              </div>
                              <div className="font-mono text-[10px] text-gray-500">
                                {getLevelDescription(lvl)}
                              </div>
                            </div>
                          </div>

                          {threshold !== null && (
                            <div className="text-right">
                              <div className="font-mono text-gray-500 text-xs">
                                {isRu ? "ПОРОГ" : "THRESHOLD"}
                              </div>
                              <div
                                className={`font-bold ${isUnlocked ? "text-green-500" : "text-gray-400"}`}
                              >
                                {formatPrice(threshold, currency as CurrencyCode)}
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>

                {/* Progress to next level */}
                {currentLevel < 3
                  ? (() => {
                      // Determine next level threshold (anchor threshold in display currency from backend)
                      let nextThreshold: number;
                      if (currentLevel === 1) {
                        nextThreshold = thresholds.level2; // PROXY -> OPERATOR (20000 RUB or 250 USD)
                      } else if (currentLevel === 2) {
                        nextThreshold = thresholds.level3; // OPERATOR -> ARCHITECT (80000 RUB or 1000 USD)
                      } else {
                        return null; // Already max level
                      }

                      // Use pre-calculated progress from adapter (if provided), otherwise calculate
                      // The adapter calculates it correctly: converts turnover to display currency and compares with anchor threshold
                      const progressPercent =
                        propProgressPercent ??
                        Math.min(100, Math.max(0, (currentTurnover / nextThreshold) * 100));

                      return (
                        <div className="mt-4 rounded-sm border border-pandora-cyan/20 bg-pandora-cyan/5 p-3">
                          <div className="mb-2 flex items-center justify-between font-mono text-[10px] text-gray-500">
                            <span>{isRu ? "ВАШ ОБОРОТ" : "YOUR TURNOVER"}</span>
                            <span>
                              {formatPrice(currentTurnover, currency as CurrencyCode)} /{" "}
                              {formatPrice(nextThreshold, currency as CurrencyCode)}
                            </span>
                          </div>
                          <div className="h-2 overflow-hidden rounded-full bg-black/50">
                            <div
                              className="h-full bg-gradient-to-r from-pandora-cyan to-white transition-all duration-500"
                              style={{
                                width: `${progressPercent}%`,
                              }}
                            />
                          </div>
                          {progressPercent >= 100 && currentLevel < 3 && (
                            <div className="mt-2 text-center font-mono text-[9px] text-green-500">
                              {isRu
                                ? "✓ Порог достигнут! Обновите профиль."
                                : "✓ Threshold reached! Refresh profile."}
                            </div>
                          )}
                        </div>
                      );
                    })()
                  : null}
              </div>

              {/* Examples */}
              <div>
                <h3 className="mb-3 flex items-center gap-2 font-bold text-pandora-cyan text-sm">
                  <Sparkles size={14} /> {isRu ? "ПРИМЕР ЗАРАБОТКА" : "EARNINGS EXAMPLE"}
                </h3>
                <div className="rounded-sm border border-green-500/20 bg-green-500/5 p-4">
                  <p className="text-gray-300 text-sm leading-relaxed">
                    {isRu
                      ? `Ваш реферал покупает подписку за $20. При уровне PROXY вы получаете ${commissions.level1}% = $2. При уровне OPERATOR вы также получите ${commissions.level2}% = $1.40 с покупок 2-й линии. При ARCHITECT — ещё ${commissions.level3}% с 3-й линии.`
                      : `Your referral buys a $20 subscription. At PROXY level, you earn ${commissions.level1}% = $2. At OPERATOR level, you also earn ${commissions.level2}% = $1.40 from Level 2 purchases. At ARCHITECT — additional ${commissions.level3}% from Level 3.`}
                  </p>
                </div>
              </div>
            </div>

            {/* Footer */}
            <div className="border-white/5 border-t p-6 pt-4">
              <button
                className="flex w-full items-center justify-center gap-2 rounded-sm bg-pandora-cyan py-3 font-bold text-black uppercase tracking-widest transition-colors hover:bg-white"
                onClick={onClose}
                type="button"
              >
                {isRu ? "ПОНЯТНО" : "GOT IT"}
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default memo(ReferralExplainerModal);
