import React from 'react'
import { motion as Motion, AnimatePresence } from 'framer-motion'
import { Tag, Check, X } from 'lucide-react'

import { Card, CardContent } from '../ui/card'
import { Button } from '../ui/button'
import { Input } from '../ui/input'

/**
 * Промо-блок: ввод и отображение статуса промокода.
 */
export function PromoBlock({
  promoCode,
  setPromoCode,
  promoResult,
  cart,
  isCartMode,
  promoLoading,
  onApply,
  onRemove,
  t,
}) {
  return (
    <Motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.1 }}
    >
      <Card className="border-0 bg-card/40 backdrop-blur-xl shadow-lg ring-1 ring-white/10">
        <CardContent className="p-4">
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Tag className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                value={promoCode}
                onChange={(e) => {
                  setPromoCode(e.target.value.toUpperCase())
                  if (promoResult) {
                    // сбрасываем прошлый результат при вводе
                    // (опционально: можно вынести наружу)
                  }
                }}
                placeholder={t('checkout.promoPlaceholder')}
                className="pl-9 uppercase font-mono placeholder:normal-case bg-secondary/30 border-transparent focus:border-primary/50"
              />
            </div>
            <Button
              variant="secondary"
              onClick={onApply}
              disabled={!promoCode.trim() || promoLoading}
              className="bg-secondary/50 hover:bg-secondary"
            >
              {promoLoading ? '...' : t('checkout.apply')}
            </Button>
          </div>

          <AnimatePresence>
            {(promoResult || (isCartMode && cart?.promo_code)) && (
              <Motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="overflow-hidden"
              >
                <div
                  className={`flex items-center justify-between text-sm mt-3 p-2 rounded-lg ${
                    (promoResult?.is_valid || cart?.promo_discount_percent > 0)
                      ? 'bg-green-500/10 text-green-500'
                      : 'bg-destructive/10 text-destructive'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    {promoResult?.is_valid || cart?.promo_discount_percent > 0 ? (
                      <>
                        <Check className="h-4 w-4" />
                        <span className="font-bold">
                          {t('checkout.promoApplied')} -{promoResult?.discount_percent || cart?.promo_discount_percent || 0}%
                        </span>
                      </>
                    ) : (
                      <>
                        <X className="h-4 w-4" />
                        <span>{promoResult?.error || t('checkout.promoInvalid')}</span>
                      </>
                    )}
                  </div>
                  {(promoResult?.is_valid || cart?.promo_discount_percent > 0) && (
                    <Button variant="ghost" size="icon" className="h-7 w-7" onClick={onRemove}>
                      <X className="h-4 w-4" />
                    </Button>
                  )}
                </div>
              </Motion.div>
            )}
          </AnimatePresence>
        </CardContent>
      </Card>
    </Motion.div>
  )
}

export default PromoBlock
