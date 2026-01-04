/**
 * ReferralExplainerModal Component
 * 
 * Cyberpunk-styled modal explaining the Network Clearance / Referral Program
 */

import React, { memo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Zap, Users, TrendingUp, Percent, DollarSign, Gift, ChevronRight, Shield, Target, ArrowRight, Sparkles } from 'lucide-react';
import { useLocale } from '../../hooks/useLocale';

interface ReferralExplainerModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentLevel?: number;  // 0, 1, 2, 3
  currentTurnover?: number;  // Current USD turnover
  thresholds?: {
    level2: number;
    level3: number;
  };
  commissions?: {
    level1: number;
    level2: number;
    level3: number;
  };
}

// Career levels - matches profileAdapter.ts naming
const LEVELS = [
  { 
    level: 1, 
    name: 'PROXY', 
    color: 'text-gray-400',
    bgColor: 'bg-gray-500/10',
    borderColor: 'border-gray-500/30',
    icon: '📡',
    description_ru: 'Стартовый допуск. Доступ к уровню 1 сети.',
    description_en: 'Entry clearance. Level 1 network access.'
  },
  { 
    level: 2, 
    name: 'OPERATOR', 
    color: 'text-purple-400',
    bgColor: 'bg-purple-500/10',
    borderColor: 'border-purple-500/30',
    icon: '⚡',
    description_ru: 'Расширенный допуск. Уровни 1-2 разблокированы.',
    description_en: 'Extended clearance. Levels 1-2 unlocked.'
  },
  { 
    level: 3, 
    name: 'ARCHITECT', 
    color: 'text-yellow-500',
    bgColor: 'bg-yellow-500/10',
    borderColor: 'border-yellow-500/30',
    icon: '👑',
    description_ru: 'Максимальный допуск. Все 3 уровня активны.',
    description_en: 'Maximum clearance. All 3 levels active.'
  },
];

const ReferralExplainerModal: React.FC<ReferralExplainerModalProps> = ({
  isOpen,
  onClose,
  currentLevel = 0,
  currentTurnover = 0,
  thresholds = { level2: 250, level3: 1000 },
  commissions = { level1: 10, level2: 7, level3: 3 },
}) => {
  const { t, locale } = useLocale();
  const isRu = locale === 'ru';

  const getLevelDescription = (lvl: typeof LEVELS[number]) => {
    return isRu ? lvl.description_ru : lvl.description_en;
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div 
          className="fixed inset-0 z-[100] flex items-center justify-center p-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          {/* Backdrop */}
          <motion.div 
            className="absolute inset-0 bg-black/90 backdrop-blur-sm"
            onClick={onClose}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          />
          
          {/* Modal */}
          <motion.div 
            className="relative w-full max-w-2xl max-h-[90vh] overflow-y-auto bg-[#050505] border border-pandora-cyan/30 shadow-2xl shadow-pandora-cyan/10"
            initial={{ scale: 0.9, y: 50, opacity: 0 }}
            animate={{ scale: 1, y: 0, opacity: 1 }}
            exit={{ scale: 0.9, y: 50, opacity: 0 }}
            transition={{ type: "spring", damping: 25, stiffness: 300 }}
          >
            {/* Animated top border */}
            <div className="absolute top-0 left-0 w-full h-[2px] bg-gradient-to-r from-transparent via-pandora-cyan to-transparent" />
            
            {/* Close button */}
            <button 
              onClick={onClose}
              className="absolute top-4 right-4 w-8 h-8 flex items-center justify-center text-gray-500 hover:text-white transition-colors z-10"
            >
              <X size={20} />
            </button>
            
            {/* Header */}
            <div className="p-6 pb-4 border-b border-white/5">
              <div className="flex items-center gap-3 mb-2">
                <div className="w-10 h-10 bg-pandora-cyan/10 border border-pandora-cyan/30 rounded-sm flex items-center justify-center">
                  <Shield size={20} className="text-pandora-cyan" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-white font-display tracking-tight">
                    {isRu ? 'ПРОТОКОЛ АПЛИНКА' : 'UPLINK PROTOCOL'}
                  </h2>
                  <p className="text-[10px] font-mono text-gray-500 uppercase tracking-widest">
                    {isRu ? 'РЕФЕРАЛЬНАЯ СИСТЕМА PVNDORA' : 'PVNDORA REFERRAL SYSTEM'}
                  </p>
                </div>
              </div>
            </div>
            
            {/* Content */}
            <div className="p-6 space-y-6">
              
              {/* How It Works Section */}
              <div>
                <h3 className="text-sm font-bold text-pandora-cyan mb-3 flex items-center gap-2">
                  <Zap size={14} /> {isRu ? 'КАК ЭТО РАБОТАЕТ' : 'HOW IT WORKS'}
                </h3>
                <div className="bg-white/5 border border-white/10 p-4 rounded-sm">
                  <p className="text-sm text-gray-300 leading-relaxed">
                    {isRu 
                      ? 'Каждый пользователь получает уникальный реферальный код. Когда приглашённый вами пользователь совершает покупку, вы получаете комиссию. Чем больше ваш оборот — тем выше уровень допуска и глубже сеть.'
                      : 'Every user gets a unique referral code. When your invited user makes a purchase, you earn a commission. Higher turnover = higher clearance level = deeper network access.'}
                  </p>
                </div>
              </div>
              
              {/* Network Levels Visualization */}
              <div>
                <h3 className="text-sm font-bold text-pandora-cyan mb-3 flex items-center gap-2">
                  <Users size={14} /> {isRu ? 'УРОВНИ СЕТИ' : 'NETWORK LEVELS'}
                </h3>
                
                {/* Visual Flow */}
                <div className="bg-black/50 border border-white/10 p-4 rounded-sm mb-4">
                  <div className="flex items-center justify-center gap-2 flex-wrap">
                    <div className="text-center">
                      <div className="w-12 h-12 bg-pandora-cyan/20 border border-pandora-cyan/50 rounded-full flex items-center justify-center mb-1 mx-auto">
                        <span className="text-pandora-cyan font-bold">ВЫ</span>
                      </div>
                      <span className="text-[9px] text-gray-500 font-mono">UPLINK</span>
                    </div>
                    
                    <ArrowRight size={16} className="text-pandora-cyan/50" />
                    
                    <div className="text-center">
                      <div className="w-12 h-12 bg-green-500/20 border border-green-500/50 rounded-full flex items-center justify-center mb-1 mx-auto">
                        <span className="text-green-500 text-sm font-bold">{commissions.level1}%</span>
                      </div>
                      <span className="text-[9px] text-gray-500 font-mono">{isRu ? 'УР.1' : 'LV.1'}</span>
                    </div>
                    
                    <ArrowRight size={16} className="text-yellow-500/50" />
                    
                    <div className="text-center">
                      <div className="w-12 h-12 bg-yellow-500/20 border border-yellow-500/50 rounded-full flex items-center justify-center mb-1 mx-auto">
                        <span className="text-yellow-500 text-sm font-bold">{commissions.level2}%</span>
                      </div>
                      <span className="text-[9px] text-gray-500 font-mono">{isRu ? 'УР.2' : 'LV.2'}</span>
                    </div>
                    
                    <ArrowRight size={16} className="text-red-500/50" />
                    
                    <div className="text-center">
                      <div className="w-12 h-12 bg-red-500/20 border border-red-500/50 rounded-full flex items-center justify-center mb-1 mx-auto">
                        <span className="text-red-500 text-sm font-bold">{commissions.level3}%</span>
                      </div>
                      <span className="text-[9px] text-gray-500 font-mono">{isRu ? 'УР.3' : 'LV.3'}</span>
                    </div>
                  </div>
                  
                  <p className="text-[10px] text-gray-500 text-center mt-3 font-mono">
                    {isRu 
                      ? 'Уровень 1 = ваши прямые рефералы. Уровни 2-3 = рефералы ваших рефералов.'
                      : 'Level 1 = your direct referrals. Levels 2-3 = referrals of your referrals.'}
                  </p>
                </div>
              </div>
              
              {/* Clearance Levels */}
              <div>
                <h3 className="text-sm font-bold text-pandora-cyan mb-3 flex items-center gap-2">
                  <Target size={14} /> {isRu ? 'УРОВНИ ДОПУСКА' : 'CLEARANCE LEVELS'}
                </h3>
                
                <div className="space-y-2">
                  {LEVELS.map((lvl, i) => {
                    const isCurrentLevel = lvl.level === currentLevel;
                    const isUnlocked = lvl.level <= currentLevel;
                    const threshold = lvl.level === 2 ? thresholds.level2 : lvl.level === 3 ? thresholds.level3 : null;
                    
                    return (
                      <div 
                        key={lvl.level}
                        className={`p-3 border rounded-sm transition-all ${
                          isCurrentLevel 
                            ? `${lvl.bgColor} ${lvl.borderColor}` 
                            : isUnlocked 
                              ? 'bg-white/5 border-white/10' 
                              : 'bg-black/30 border-white/5 opacity-60'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <span className="text-lg">{lvl.icon}</span>
                            <div>
                              <div className={`font-bold font-display ${lvl.color}`}>
                                {lvl.name}
                                {isCurrentLevel && (
                                  <span className="ml-2 text-[9px] bg-pandora-cyan/20 text-pandora-cyan px-2 py-0.5 rounded-full font-mono">
                                    {isRu ? 'ТЕКУЩИЙ' : 'CURRENT'}
                                  </span>
                                )}
                              </div>
                              <div className="text-[10px] text-gray-500 font-mono">
                                {getLevelDescription(lvl)}
                              </div>
                            </div>
                          </div>
                          
                          {threshold && (
                            <div className="text-right">
                              <div className="text-xs text-gray-500 font-mono">
                                {isRu ? 'ПОРОГ' : 'THRESHOLD'}
                              </div>
                              <div className={`font-bold ${isUnlocked ? 'text-green-500' : 'text-gray-400'}`}>
                                ${threshold.toLocaleString()}
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
                
                {/* Progress to next level */}
                {currentLevel < 3 && (
                  <div className="mt-4 p-3 bg-pandora-cyan/5 border border-pandora-cyan/20 rounded-sm">
                    <div className="flex items-center justify-between text-[10px] font-mono text-gray-500 mb-2">
                      <span>{isRu ? 'ВАШ ОБОРОТ' : 'YOUR TURNOVER'}</span>
                      <span>${currentTurnover.toLocaleString()} / ${(currentLevel === 1 ? thresholds.level2 : thresholds.level3).toLocaleString()}</span>
                    </div>
                    <div className="h-2 bg-black/50 rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-gradient-to-r from-pandora-cyan to-white transition-all duration-500"
                        style={{ 
                          width: `${Math.min(100, (currentTurnover / (currentLevel === 1 ? thresholds.level2 : thresholds.level3)) * 100)}%` 
                        }}
                      />
                    </div>
                  </div>
                )}
              </div>
              
              {/* Examples */}
              <div>
                <h3 className="text-sm font-bold text-pandora-cyan mb-3 flex items-center gap-2">
                  <Sparkles size={14} /> {isRu ? 'ПРИМЕР ЗАРАБОТКА' : 'EARNINGS EXAMPLE'}
                </h3>
                <div className="bg-green-500/5 border border-green-500/20 p-4 rounded-sm">
                  <p className="text-sm text-gray-300 leading-relaxed">
                    {isRu 
                      ? `Ваш реферал покупает подписку за $20. При уровне PROXY вы получаете ${commissions.level1}% = $2. При уровне OPERATOR вы также получите ${commissions.level2}% = $1.40 с покупок 2-й линии. При ARCHITECT — ещё ${commissions.level3}% с 3-й линии.`
                      : `Your referral buys a $20 subscription. At PROXY level, you earn ${commissions.level1}% = $2. At OPERATOR level, you also earn ${commissions.level2}% = $1.40 from Level 2 purchases. At ARCHITECT — additional ${commissions.level3}% from Level 3.`}
                  </p>
                </div>
              </div>
              
            </div>
            
            {/* Footer */}
            <div className="p-6 pt-4 border-t border-white/5">
              <button
                onClick={onClose}
                className="w-full bg-pandora-cyan text-black font-bold py-3 uppercase tracking-widest hover:bg-white transition-colors flex items-center justify-center gap-2 rounded-sm"
              >
                {isRu ? 'ПОНЯТНО' : 'GOT IT'}
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default memo(ReferralExplainerModal);
