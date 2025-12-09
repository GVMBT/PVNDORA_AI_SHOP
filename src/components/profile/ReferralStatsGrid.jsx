import React from 'react'

export function ReferralStatsGrid({ referralStats, currency, formatPrice, t }) {
  return (
    <div className="grid grid-cols-3 gap-3">
      <div className="bg-secondary/20 rounded-2xl p-3 text-center border border-white/5">
        <div className="text-xl font-bold text-foreground">{referralStats?.active_referrals || 0}</div>
        <div className="text-[10px] text-muted-foreground uppercase tracking-wider mt-1">
          {t?.('profile.stats.users') || 'Users'}
        </div>
      </div>
      <div className="bg-secondary/20 rounded-2xl p-3 text-center border border-white/5">
        <div className="text-xl font-bold text-green-500">{referralStats?.conversion_rate || 0}%</div>
        <div className="text-[10px] text-muted-foreground uppercase tracking-wider mt-1">
          {t?.('profile.stats.conv') || 'Conv.'}
        </div>
      </div>
      <div className="bg-secondary/20 rounded-2xl p-3 text-center border border-white/5">
        <div className="text-xl font-bold text-foreground">{formatPrice(referralStats?.avg_order_value || 0, currency)}</div>
        <div className="text-[10px] text-muted-foreground uppercase tracking-wider mt-1">
          {t?.('profile.stats.avg') || 'Avg.'}
        </div>
      </div>
    </div>
  )
}

export default ReferralStatsGrid
