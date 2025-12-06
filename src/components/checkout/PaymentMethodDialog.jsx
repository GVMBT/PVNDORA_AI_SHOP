import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { CreditCard, Smartphone, QrCode, Bitcoin, Loader2, ShieldCheck, X } from 'lucide-react'
import { Button } from '../ui/button'

/**
 * Диалог выбора способа оплаты.
 * Открывается при нажатии на кнопку "К оплате" в корзине.
 */

const METHOD_ICONS = {
  card: CreditCard,
  sbp: Smartphone,
  sbp_qr: QrCode,
  crypto: Bitcoin,
}

const METHOD_COLORS = {
  card: 'from-blue-500/20 to-blue-600/10 border-blue-500/30',
  sbp: 'from-green-500/20 to-green-600/10 border-green-500/30',
  sbp_qr: 'from-purple-500/20 to-purple-600/10 border-purple-500/30',
  crypto: 'from-orange-500/20 to-orange-600/10 border-orange-500/30',
}

const METHOD_SELECTED = {
  card: 'ring-2 ring-blue-500 border-blue-500',
  sbp: 'ring-2 ring-green-500 border-green-500',
  sbp_qr: 'ring-2 ring-purple-500 border-purple-500',
  crypto: 'ring-2 ring-orange-500 border-orange-500',
}

export function PaymentMethodDialog({ 
  open, 
  onClose, 
  availableMethods, 
  onConfirm, 
  total, 
  currency, 
  formatPrice,
  isLoading,
  t 
}) {
  const [selectedMethod, setSelectedMethod] = useState(
    availableMethods?.[0]?.system_group || 'card'
  )

  if (!open) return null

  const methods = availableMethods?.length ? availableMethods : [
    { system_group: 'card', name: 'Банковская карта', icon: '💳' },
    { system_group: 'sbp', name: 'СБП', icon: '🏦' },
    { system_group: 'sbp_qr', name: 'QR-код СБП', icon: '📱' },
    { system_group: 'crypto', name: 'Криптовалюта', icon: '₿' },
  ]

  const handleConfirm = () => {
    onConfirm(selectedMethod)
  }

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50">
        {/* Backdrop */}
        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 bg-black/80 backdrop-blur-sm"
          onClick={onClose}
        />
        
        {/* Dialog */}
        <motion.div
          initial={{ opacity: 0, y: 100, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 100, scale: 0.95 }}
          transition={{ type: "spring", damping: 25, stiffness: 300 }}
          className="fixed bottom-0 left-0 right-0 z-50 max-h-[90vh] overflow-hidden"
        >
          <div className="bg-background rounded-t-3xl border-t border-border/50 shadow-2xl">
            {/* Handle bar */}
            <div className="flex justify-center pt-3 pb-2">
              <div className="w-12 h-1.5 bg-muted-foreground/30 rounded-full" />
            </div>
            
            {/* Close button */}
            <button
              onClick={onClose}
              className="absolute top-4 right-4 p-2 rounded-full bg-muted/50 hover:bg-muted transition-colors"
            >
              <X className="w-5 h-5 text-muted-foreground" />
            </button>
            
            {/* Content */}
            <div className="px-5 pb-8 pt-2">
              {/* Header */}
              <div className="text-center mb-6">
                <h2 className="text-xl font-bold mb-1">
                  {t?.('checkout.selectPaymentMethod') || 'Способ оплаты'}
                </h2>
                <p className="text-muted-foreground text-sm">
                  {t?.('checkout.selectPaymentMethodDesc') || 'Выберите удобный способ оплаты'}
                </p>
              </div>

              {/* Payment methods grid */}
              <div className="grid grid-cols-2 gap-3 mb-6">
                {methods.map((method) => {
                  const methodId = typeof method === 'string' ? method : method.system_group
                  const methodName = typeof method === 'string' ? method.toUpperCase() : method.name
                  const IconComponent = METHOD_ICONS[methodId] || CreditCard
                  const isSelected = selectedMethod === methodId

                  return (
                    <motion.button
                      key={methodId}
                      onClick={() => setSelectedMethod(methodId)}
                      whileTap={{ scale: 0.97 }}
                      className={`
                        relative rounded-2xl border p-4 text-left transition-all duration-200
                        bg-gradient-to-br ${METHOD_COLORS[methodId] || 'from-muted/50 to-muted/30 border-border'}
                        ${isSelected ? METHOD_SELECTED[methodId] || 'ring-2 ring-primary border-primary' : 'hover:border-primary/50'}
                      `}
                    >
                      {/* Selected indicator */}
                      {isSelected && (
                        <motion.div
                          layoutId="selected-indicator"
                          className="absolute top-2 right-2 w-5 h-5 bg-primary rounded-full flex items-center justify-center"
                          initial={false}
                          transition={{ type: "spring", stiffness: 500, damping: 30 }}
                        >
                          <svg className="w-3 h-3 text-primary-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                          </svg>
                        </motion.div>
                      )}
                      
                      <div className="flex flex-col gap-2">
                        <div className={`
                          w-10 h-10 rounded-xl flex items-center justify-center
                          ${isSelected ? 'bg-primary/20' : 'bg-muted/50'}
                        `}>
                          <IconComponent className={`w-5 h-5 ${isSelected ? 'text-primary' : 'text-muted-foreground'}`} />
                        </div>
                        <span className={`font-medium text-sm ${isSelected ? 'text-foreground' : 'text-muted-foreground'}`}>
                          {methodName}
                        </span>
                      </div>
                    </motion.button>
                  )
                })}
              </div>

              {/* Total */}
              <div className="bg-muted/30 rounded-2xl p-4 mb-6">
                <div className="flex justify-between items-center">
                  <span className="text-muted-foreground">{t?.('checkout.total') || 'Итого'}</span>
                  <span className="text-2xl font-bold text-primary font-mono">
                    {formatPrice?.(total, currency) || `${total} ${currency}`}
                  </span>
                </div>
              </div>

              {/* Pay button */}
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

              {/* Security note */}
              <div className="flex items-center justify-center gap-2 text-xs text-muted-foreground mt-4">
                <ShieldCheck className="w-4 h-4" />
                <span>{t?.('checkout.securePayment') || 'Безопасная оплата'}</span>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  )
}

export default PaymentMethodDialog
