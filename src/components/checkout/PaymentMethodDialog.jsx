import React, { useState, useEffect } from 'react'
import { motion as Motion, AnimatePresence } from 'framer-motion'
import { CreditCard, Smartphone, QrCode, Bitcoin, Loader2, ShieldCheck, X, Check as CheckIcon } from 'lucide-react'
import { Button } from '../ui/button'
import { PaymentMethodList } from './PaymentMethodList'
import { IconCard, IconSBP, IconSBPQR, IconCrypto, MIN_BY_METHOD_FALLBACK } from './payment-method-icons.jsx'

/**
 * Диалог выбора способа оплаты.
 * Открывается при нажатии на кнопку "К оплате" в корзине.
 */

// Минимальные суммы по методам - fallback если API не вернул

export function PaymentMethodDialog({ 
  open, 
  onClose, 
  availableMethods, 
  onConfirm, 
  total, 
  currency, 
  formatPrice,
  isLoading,
  t,
  gateways = [
    { id: 'rukassa', name: 'Rukassa' },
    { id: 'crystalpay', name: 'CrystalPay' },
  ],
  selectedGateway = 'rukassa',
  onGatewayChange,
}) {
  const allowed = ['card', 'sbp', 'sbp_qr', 'crypto']
  const methodsRaw = availableMethods?.length ? availableMethods : [
    { system_group: 'card', name: 'Банковская карта', icon: '💳', enabled: true, min_amount: 1000 },
    { system_group: 'sbp', name: 'СБП', icon: '🏦', enabled: true, min_amount: 1000 },
    { system_group: 'sbp_qr', name: 'QR-код СБП', icon: '📱', enabled: true, min_amount: 10 },
    { system_group: 'crypto', name: 'Криптовалюта', icon: '₿', enabled: true, min_amount: 50 },
  ]
  const methods = methodsRaw.filter((m) => allowed.includes((typeof m === 'string' ? m : m.system_group) || ''))
  
  // Find first enabled method that user can afford
  const getDefaultMethod = () => {
    for (const m of methods) {
      const methodId = typeof m === 'string' ? m : m.system_group
      const isEnabled = typeof m === 'object' ? (m.enabled !== false) : true
      const minAmount = typeof m === 'object' && m.min_amount ? m.min_amount : MIN_BY_METHOD_FALLBACK[methodId] || 0
      if (isEnabled && total >= minAmount) {
        return methodId
      }
    }
    // Fallback to first enabled method even if can't afford
    for (const m of methods) {
      const methodId = typeof m === 'string' ? m : m.system_group
      const isEnabled = typeof m === 'object' ? (m.enabled !== false) : true
      if (isEnabled) return methodId
    }
    return 'card'
  }
  
  const [selectedMethod, setSelectedMethod] = useState(getDefaultMethod)

  // Recompute selected method when methods/amount/currency/gateway change
  useEffect(() => {
    const next = selectedGateway === 'crystalpay' ? 'card' : getDefaultMethod()
    if (next && next !== selectedMethod) {
      setSelectedMethod(next)
    }
  }, [availableMethods, total, currency, selectedGateway]) // eslint-disable-line react-hooks/exhaustive-deps

  if (!open) return null

  const handleConfirm = () => {
    onConfirm(selectedMethod)
  }

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50">
        {/* Backdrop */}
        <Motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 bg-black/80 backdrop-blur-sm"
          onClick={onClose}
        />
        
        {/* Dialog - поднят выше навигации */}
        <Motion.div
          initial={{ opacity: 0, y: 100, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 100, scale: 0.95 }}
          transition={{ type: "spring", damping: 25, stiffness: 300 }}
          className="fixed left-0 right-0 z-50 max-h-[85vh] overflow-hidden"
          style={{ bottom: '70px' }}
        >
          <div className="bg-background rounded-3xl border border-border/50 shadow-2xl mx-2">
            {/* Handle bar */}
            <div className="flex justify-center pt-3 pb-2">
              <div className="w-12 h-1.5 bg-muted-foreground/30 rounded-full" />
            </div>
            
            {/* Close button */}
            <button
              onClick={onClose}
              className="absolute top-4 right-4 p-2 rounded-full bg-muted/50 hover:bg-muted transition-colors z-10"
            >
              <X className="w-5 h-5 text-muted-foreground" />
            </button>
            
            {/* Content with scroll + sticky CTA for desktop/mini-app */}
            <div className="px-5 pt-2 pb-4 flex flex-col max-h-[75vh] overflow-hidden">
              <div className="flex-1 min-h-0 overflow-y-auto pr-1">
                {/* Header */}
                <div className="text-center mb-6">
                  <h2 className="text-xl font-bold mb-1">
                    {t?.('checkout.selectPaymentMethod') || 'Способ оплаты'}
                  </h2>
                  <p className="text-muted-foreground text-sm">
                    {t?.('checkout.selectPaymentMethodDesc') || 'Выберите удобный способ оплаты'}
                  </p>
                </div>

                {/* Gateway selection */}
                <div className="grid grid-cols-2 gap-2 mb-4">
                  {gateways.map((gw) => {
                    const active = selectedGateway === gw.id
                    return (
                      <button
                        key={gw.id}
                        onClick={() => onGatewayChange?.(gw.id)}
                        className={`
                          rounded-xl border px-3 py-3 text-sm font-semibold transition-all
                          ${active ? 'border-primary bg-primary/10 text-primary' : 'border-border bg-muted/40 text-foreground'}
                        `}
                      >
                        {gw.name}
                      </button>
                    )
                  })}
                </div>

                {selectedGateway !== 'crystalpay' ? (
                  <PaymentMethodList
                    methods={methods}
                    selectedMethod={selectedMethod}
                    onSelect={setSelectedMethod}
                    total={total}
                  />
                ) : (
                  <div className="mb-6 text-sm text-muted-foreground text-center">
                    Способ оплаты выбирается на стороне CrystalPay. Нажмите «Оплатить», чтобы продолжить.
                  </div>
                )}

                {/* Total */}
                <div className="bg-muted/30 rounded-2xl p-4 mb-4">
                  <div className="flex justify-between items-center">
                    <span className="text-muted-foreground">{t?.('checkout.total') || 'Итого'}</span>
                    <span className="text-2xl font-bold text-primary font-mono">
                      {formatPrice?.(total, currency) || `${total} ${currency}`}
                    </span>
                  </div>
                </div>
              </div>

              {/* CTA */}
              <div className="pt-3 pb-2">
                <Button
                  onClick={handleConfirm}
                  disabled={isLoading}
                  className="w-full h-14 text-lg font-semibold rounded-2xl"
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                      {t?.('common.loading') || 'Обработка...'}
                    </>
                  ) : (
                    <>
                      {t?.('checkout.pay') || 'Оплатить'} {formatPrice?.(total, currency) || `${total} ${currency}`}
                    </>
                  )}
                </Button>

                <div className="flex items-center justify-center gap-2 text-xs text-muted-foreground mt-3">
                  <ShieldCheck className="w-4 h-4" />
                  <span>{t?.('checkout.securePayment') || 'Безопасная оплата'}</span>
                </div>
              </div>
            </div>
          </div>
        </Motion.div>
      </div>
    </AnimatePresence>
  )
}

export default PaymentMethodDialog
