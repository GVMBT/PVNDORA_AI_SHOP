import React from 'react'

export function ReferralStatsGrid({ referralStats, currency, formatPrice, t }) {
  const l1Count = referralStats?.level1_count || 0
  const l1Active = referralStats?.active_referrals || 0
  const l1Earnings = referralStats?.level1_earnings || 0

  const l2Count = referralStats?.level2_count || 0
  const l3Count = referralStats?.level3_count || 0
  const totalNetwork = l1Count + l2Count + l3Count

  return (
    <div className="space-y-3">
      <div className="space-y-2">
        <div className="text-xs text-muted-foreground uppercase tracking-wide">
          {t?.('profile.stats.l1Title') || 'Direct (L1)'}
        </div>
        <div className="grid grid-cols-3 gap-3">
          <div className="bg-secondary/20 rounded-2xl p-3 text-center border border-white/5">
            <div className="text-xl font-bold text-foreground">{l1Count}</div>
            <div className="text-[10px] text-muted-foreground uppercase tracking-wider mt-1">
              {t?.('profile.stats.l1Users') || 'Direct (L1)'}
            </div>
          </div>
          <div className="bg-secondary/20 rounded-2xl p-3 text-center border border-white/5">
            <div className="text-xl font-bold text-green-500">{l1Active}</div>
            <div className="text-[10px] text-muted-foreground uppercase tracking-wider mt-1">
              {t?.('profile.stats.l1Active') || 'Active L1'}
            </div>
          </div>
          <div className="bg-secondary/20 rounded-2xl p-3 text-center border border-white/5">
            <div className="text-xl font-bold text-foreground">{formatPrice(l1Earnings, currency)}</div>
            <div className="text-[10px] text-muted-foreground uppercase tracking-wider mt-1">
              {t?.('profile.stats.l1Earnings') || 'Earnings L1'}
            </div>
          </div>
        </div>
      </div>

      <div className="space-y-2">
        <div className="text-xs text-muted-foreground uppercase tracking-wide">
          {t?.('profile.stats.networkTitle') || 'Network (L1-L3)'}
        </div>
        <div className="grid grid-cols-3 gap-3">
          <div className="bg-secondary/10 rounded-2xl p-3 text-center border border-white/5">
            <div className="text-xl font-bold text-foreground">{totalNetwork}</div>
            <div className="text-[10px] text-muted-foreground uppercase tracking-wider mt-1">
              {t?.('profile.stats.networkTotal') || 'Total network'}
            </div>
          </div>
          <div className="bg-secondary/10 rounded-2xl p-3 text-center border border-white/5">
            <div className="text-xl font-bold text-foreground">{l2Count}</div>
            <div className="text-[10px] text-muted-foreground uppercase tracking-wider mt-1">
              {t?.('profile.stats.networkL2') || 'Level 2'}
            </div>
          </div>
          <div className="bg-secondary/10 rounded-2xl p-3 text-center border border-white/5">
            <div className="text-xl font-bold text-foreground">{l3Count}</div>
            <div className="text-[10px] text-muted-foreground uppercase tracking-wider mt-1">
              {t?.('profile.stats.networkL3') || 'Level 3'}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default ReferralStatsGrid
