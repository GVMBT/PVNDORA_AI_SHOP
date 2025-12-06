import React from 'react'
import { motion } from 'framer-motion'
import { Wallet, Share2, Lock } from 'lucide-react'
import { Button } from '../ui/button'

export function BalanceCard({
  balance = 0,
  currency = 'USD',
  formatPrice,
  t,
  onWithdraw,
  onShare,
  shareLoading,
  minWithdrawal = 500,
}) {
  const disabled = balance < minWithdrawal

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="relative rounded-3xl overflow-hidden bg-gradient-to-br from-primary/20 via-background to-background border border-primary/20 shadow-[0_0_30px_rgba(0,245,212,0.15)]"
    >
      <div className="absolute top-0 right-0 w-32 h-32 bg-primary/20 blur-3xl rounded-full -mr-10 -mt-10 pointer-events-none" />

      <div className="p-6">
        <p className="text-sm text-muted-foreground mb-1">{t('profile.balance')}</p>
        <div className="flex items-baseline gap-1">
          <span className="text-4xl font-black tracking-tighter bg-clip-text text-transparent bg-gradient-to-r from-primary to-emerald-400">
            {formatPrice(balance || 0, currency)}
          </span>
        </div>

        <div className="mt-6 grid grid-cols-2 gap-3">
          <Button
            onClick={onWithdraw}
            disabled={disabled}
            className="bg-background/50 backdrop-blur-md border border-white/10 hover:bg-background/80 shadow-sm"
          >
            <Wallet className="h-4 w-4 mr-2" />
            {t('profile.withdraw')}
          </Button>
          <Button
            onClick={onShare}
            disabled={shareLoading}
            className="bg-primary text-primary-foreground hover:bg-primary/90 shadow-[0_0_15px_rgba(0,245,212,0.4)]"
          >
            <Share2 className="h-4 w-4 mr-2" />
            {t('profile.invite')}
          </Button>
        </div>

        {disabled && (
          <div className="mt-3 flex items-center justify-center gap-1.5 text-[10px] text-muted-foreground opacity-70">
            <Lock className="h-3 w-3" />
            {t('profile.minWithdrawalNote', { min: formatPrice(minWithdrawal, currency) })}
          </div>
        )}
      </div>
    </motion.div>
  )
}

export default BalanceCard
