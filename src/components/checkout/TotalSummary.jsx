import React from 'react'
import { Card, CardContent } from '../ui/card'
import { Separator } from '../ui/separator'

/**
 * Отображение итогов: subtotal, скидка, total.
 */
export function TotalSummary({ subtotal, discount, total, currency, formatPrice, t }) {
  return (
    <Card className="border-0 bg-gradient-to-br from-card/50 to-background shadow-xl ring-1 ring-white/10">
      <CardContent className="p-6 space-y-3">
        <div className="flex justify-between text-sm">
          <span className="text-muted-foreground">{t('checkout.subtotal')}</span>
          <span className="font-mono">{formatPrice(subtotal, currency)}</span>
        </div>

        {discount > 0 && (
          <div className="flex justify-between text-sm text-green-500">
            <span>{t('checkout.discount')}</span>
            <span className="font-mono">-{formatPrice(discount, currency)}</span>
          </div>
        )}

        <Separator className="bg-white/10 my-2" />

        <div className="flex justify-between items-end">
          <span className="font-bold text-lg">{t('checkout.total')}</span>
          <span className="text-3xl font-bold text-primary font-mono tracking-tighter">
            {formatPrice(total, currency)}
          </span>
        </div>
      </CardContent>
    </Card>
  )
}

export default TotalSummary
