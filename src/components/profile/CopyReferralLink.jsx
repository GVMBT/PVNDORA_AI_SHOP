import React, { useState } from 'react'
import { Button } from '../ui/button'
import { Copy, Check } from 'lucide-react'
import { cn } from '../../lib/utils'

export function CopyReferralLink({ userId, t, onCopy }) {
  const link = `t.me/pvndora_bot?start=ref_${userId}`
  const [copied, setCopied] = useState(false)

  const handleCopy = (e) => {
    e.stopPropagation()
    onCopy()
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="bg-secondary/20 rounded-2xl p-4 flex items-center justify-between gap-4 border border-white/5 group active:bg-secondary/30 transition-colors" onClick={handleCopy}>
      <div className="min-w-0">
        <p className="text-xs font-medium text-muted-foreground mb-1 uppercase tracking-wider">{t('profile.yourReferralLink')}</p>
        <p className="text-sm font-mono truncate text-foreground/90">{link}</p>
      </div>
      <Button 
        variant="secondary" 
        size="icon" 
        onClick={handleCopy} 
        className={cn(
          "shrink-0 rounded-xl transition-all duration-300",
          copied ? "bg-green-500/20 text-green-500 hover:bg-green-500/30" : ""
        )}
      >
        {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
      </Button>
    </div>
  )
}

export default CopyReferralLink
