import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { CreditCard, Smartphone, QrCode, Bitcoin, Loader2, ShieldCheck, X, Check as CheckIcon } from 'lucide-react'
import { Button } from '../ui/button'
import cardIcon from '../../assets/icons/payments/visa-10.svg'
import sbpIcon from '../../assets/icons/payments/sbp.svg'
import cryptoIcon from '../../assets/icons/payments/tether-usdt-1.svg'

/**
 * Диалог выбора способа оплаты.
 * Открывается при нажатии на кнопку "К оплате" в корзине.
 */

// Локальные мини-иконки под конкретные системы
const IconCard = () => (
  <div className="relative w-6 h-4 rounded-[6px] bg-gradient-to-r from-slate-800 to-slate-700">
    <div className="absolute left-1 top-[6px] w-3 h-[6px] rounded bg-yellow-400/90" />
    <div className="absolute right-1 bottom-[5px] w-[14px] h-[2px] bg-white/70" />
  </div>
)

const IconSBP = () => (
  <div className="w-6 h-6 rounded-md bg-white flex items-center justify-center overflow-hidden border border-slate-200">
    <svg viewBox="0 0 64 64" className="w-5 h-5">
      <path fill="#7b61ff" d="M6 6h22l-8 14H6z" />
      <path fill="#00c3ff" d="M36 6h22L34 50l-8-14z" />
      <path fill="#ff8c37" d="M6 44h22l-8 14H6z" />
      <path fill="#13ce66" d="M36 44h22l-14 14-14-14z" />
    </svg>
  </div>
)

const IconSBPQR = () => (
  <div className="w-6 h-6 rounded-md bg-white flex items-center justify-center overflow-hidden border border-slate-200">
    <svg viewBox="0 0 24 24" className="w-4 h-4 text-slate-700" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M5 3h4v4H5zM15 3h4v4h-4zM5 17h4v4H5zM15 17h4v4h-4z" />
      <path d="M9 5h6M9 19h6M5 9v6M19 9v6M9 9h6v6H9z" />
    </svg>
  </div>
)

const IconCrypto = () => (
  <div className="w-6 h-6 rounded-full bg-[#26a17b]/10 text-[#26a17b] flex items-center justify-center border border-[#26a17b]/40">
    <span className="text-[11px] font-bold">USDT</span>
  </div>
)

const METHOD_ICONS = {
  card: () => <img src={cardIcon} alt="Card" className="h-5" />,
  sbp: () => <img src={sbpIcon} alt="SBP" className="h-5" />,
  sbp_qr: () => <img src={sbpIcon} alt="SBP QR" className="h-5" />,
  crypto: () => <img src={cryptoIcon} alt="Crypto" className="h-5" />,
}

// Минимальные суммы по методам (Rukassa пороги)
const MIN_BY_METHOD = {
  card: 1000,
  sbp: 1000,
  sbp_qr: 10,
  crypto: 50, // если Rukassa ставит другой порог — поправим при необходимости
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

  const allowed = ['card', 'sbp', 'sbp_qr', 'crypto']
  const methodsRaw = availableMethods?.length ? availableMethods : [
    { system_group: 'card', name: 'Банковская карта', icon: '💳' },
    { system_group: 'sbp', name: 'СБП', icon: '🏦' },
    { system_group: 'sbp_qr', name: 'QR-код СБП', icon: '📱' },
    { system_group: 'crypto', name: 'Криптовалюта', icon: '₿' },
  ]
  const methods = methodsRaw.filter((m) => allowed.includes((typeof m === 'string' ? m : m.system_group) || ''))

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
            {/* Add bottom padding so nav не перекрывает CTA */}
            <div className="px-5 pb-24 pt-2">
              {/* Header */}
              <div className="text-center mb-6">
                <h2 className="text-xl font-bold mb-1">
                  {t?.('checkout.selectPaymentMethod') || 'Способ оплаты'}
                </h2>
                <p className="text-muted-foreground text-sm">
                  {t?.('checkout.selectPaymentMethodDesc') || 'Выберите удобный способ оплаты'}
                </p>
              </div>

              {/* Payment methods list (компактный, без радуги) */}
              <div className="space-y-2 mb-6">
                {methods.map((method) => {
                  const methodId = typeof method === 'string' ? method : method.system_group
                  const methodName = typeof method === 'string' ? method.toUpperCase() : method.name
                  const IconComponent = METHOD_ICONS[methodId] || CreditCard
                  const isSelected = selectedMethod === methodId
                  const minAmount = MIN_BY_METHOD[methodId] || 0
                  const disabled = total < minAmount

                  const handleClick = () => {
                    if (disabled) {
                      window.alert(`Недоступно для суммы ${total.toLocaleString('ru-RU')} ₽. Минимум для метода ${methodName} — ${minAmount.toLocaleString('ru-RU')} ₽`)
                      return
                    }
                    setSelectedMethod(methodId)
                  }

                  return (
                    <motion.button
                      key={methodId}
                      onClick={handleClick}
                      whileTap={disabled ? undefined : { scale: 0.99 }}
                      className={`
                        w-full rounded-2xl border p-4 text-left transition-all duration-150
                        ${disabled ? 'opacity-50 cursor-not-allowed bg-muted/40 border-border' : isSelected ? 'border-primary ring-1 ring-primary/50 bg-primary/5' : 'border-border hover:border-primary/40'}
                        flex items-center justify-between gap-3
                      `}
                        >
                      <div className="flex items-center gap-3">
                        <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${disabled ? 'bg-muted text-muted-foreground' : isSelected ? 'bg-primary/10' : 'bg-muted'}`}>
                          <IconComponent />
                        </div>
                        <div className="flex flex-col">
                          <span className="font-medium text-sm text-foreground">{methodName}</span>
                          <span className="text-xs text-muted-foreground">
                            {methodId === 'sbp_qr' ? 'QR СБП' : methodId === 'sbp' ? 'Приложение банка' : methodId === 'crypto' ? 'USDT / ₿' : ''}
                            {minAmount ? ` • от ${minAmount.toLocaleString('ru-RU')} ₽` : ''}
                        </span>
                        </div>
                      </div>
                      <div className={`w-5 h-5 rounded-full border flex items-center justify-center ${disabled ? 'border-muted-foreground/30' : isSelected ? 'bg-primary border-primary' : 'border-muted-foreground/30'}`}>
                        {isSelected && !disabled && <CheckIcon className="w-3 h-3 text-primary-foreground" strokeWidth={3} />}
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
