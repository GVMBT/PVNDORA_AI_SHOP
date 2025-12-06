import React from 'react'
import { Button } from '../ui/button'
import { Copy } from 'lucide-react'

export function CopyReferralLink({ userId, t, onCopy }) {
  const link = `t.me/pvndora_bot?start=ref_${userId}`
  return (
    <div className="bg-secondary/20 rounded-2xl p-4 flex items-center justify-between gap-4 border border-white/5">
      <div className="min-w-0">
        <p className="text-xs font-medium text-muted-foreground mb-1">{t('profile.yourReferralLink')}</p>
        <p className="text-sm font-mono truncate opacity-80">{link}</p>
      </div>
      <Button variant="secondary" size="icon" onClick={onCopy} className="shrink-0 rounded-xl">
        <Copy className="h-4 w-4" />
      </Button>
    </div>
  )
}

export default CopyReferralLink
