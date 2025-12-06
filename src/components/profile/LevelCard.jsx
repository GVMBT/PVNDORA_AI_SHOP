import React from 'react'
import { motion } from 'framer-motion'
import { Lock } from 'lucide-react'
import { cn } from '../../lib/utils'

export function LevelCard({ level, commission, threshold, isUnlocked, isProgramLocked, count, earnings, formatPrice, t, color, isInstant }) {
  const isLocked = !isUnlocked

  const colors = {
    green: {
      gradient: 'from-emerald-500/20 to-teal-500/5',
      border: 'border-emerald-500/20',
      text: 'text-emerald-500',
      bg: 'bg-emerald-500/10',
      shadow: 'shadow-emerald-500/10'
    },
    blue: {
      gradient: 'from-blue-500/20 to-indigo-500/5',
      border: 'border-blue-500/20',
      text: 'text-blue-500',
      bg: 'bg-blue-500/10',
      shadow: 'shadow-blue-500/10'
    },
    purple: {
      gradient: 'from-purple-500/20 to-fuchsia-500/5',
      border: 'border-purple-500/20',
      text: 'text-purple-500',
      bg: 'bg-purple-500/10',
      shadow: 'shadow-purple-500/10'
    }
  }

  const cfg = colors[color] || colors.green

  return (
    <motion.div
      whileHover={{ scale: isLocked ? 1 : 1.02 }}
      whileTap={{ scale: isLocked ? 1 : 0.98 }}
      className={cn(
        'relative overflow-hidden rounded-2xl border p-4 transition-all duration-300',
        isLocked ? 'bg-card/30 border-white/5 grayscale opacity-60' : `bg-gradient-to-br ${cfg.gradient} ${cfg.border} shadow-lg ${cfg.shadow}`
      )}
    >
      <div className="absolute inset-0 bg-[url('/noise.png')] opacity-10 mix-blend-overlay pointer-events-none" />

      <div className="flex justify-between items-start relative z-10">
        <div className="flex gap-3">
          <div className={cn('w-10 h-10 rounded-xl flex items-center justify-center font-bold text-lg shadow-inner', isLocked ? 'bg-white/5 text-muted-foreground' : `${cfg.bg} ${cfg.text}`)}>
            {isLocked ? <Lock className="w-4 h-4" /> : level}
          </div>
          <div>
            <h3 className="font-bold text-sm">{t(`profile.level${level}`)}</h3>
            <p className="text-xs text-muted-foreground mt-0.5">
              {isUnlocked ? `${commission} ${t('profile.commission')}` : isInstant ? t('profile.unlockOnPurchase') : `${t('profile.unlockAt')} $${threshold}`}
            </p>
          </div>
        </div>

        <div className="text-right">
          <div className="text-xl font-bold font-mono tracking-tight">{count}</div>
          <div className={cn('text-[10px] font-medium', isLocked ? 'text-muted-foreground' : cfg.text)}>
            {isUnlocked && earnings > 0 ? `+${formatPrice(earnings)}` : 'Referrals'}
          </div>
        </div>
      </div>

      {!isUnlocked && !isInstant && !isProgramLocked && (
        <div className="mt-3 h-1 bg-white/5 rounded-full overflow-hidden">
          <div className="h-full bg-white/20 w-1/3" />
        </div>
      )}
    </motion.div>
  )
}

export default LevelCard
