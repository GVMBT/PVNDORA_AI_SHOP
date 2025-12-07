import React, { useEffect, useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import { CheckCircle, XCircle, Loader2, ArrowLeft, ShoppingBag, MessageCircle } from 'lucide-react'
import { Button } from '../components/ui/button'
import { Card, CardContent } from '../components/ui/card'
import { useLocale } from '../hooks/useLocale'

/**
 * Payment Result Page
 * 
 * Shown after redirect from payment gateway (Rukassa, etc.)
 * URL: /payment/success?order_id=xxx or /payment/fail?order_id=xxx
 */
export default function PaymentResultPage({ 
  isSuccess: propIsSuccess = null, 
  orderId: propOrderId = null,
  onNavigate,
  onBack 
}) {
  const { t } = useLocale()
  const [countdown, setCountdown] = useState(5)
  const [loadingStatus, setLoadingStatus] = useState(false)
  const [status, setStatus] = useState(null)
  const [error, setError] = useState(null)
  
  // Read order_id from URL if not passed via props (fallback for redirect/fallback page)
  const orderId = useMemo(() => {
    if (propOrderId) return propOrderId
    try {
      const params = new URLSearchParams(window.location.search)
      return params.get('order_id') || params.get('id') || null
    } catch {
      return null
    }
  }, [propOrderId])
  
  const derivedSuccess = useMemo(() => {
    if (propIsSuccess !== null) return propIsSuccess
    if (!status) return null
    const successStatuses = ['paid', 'prepaid', 'ready', 'delivered', 'fulfilled', 'completed']
    const failStatuses = ['failed', 'cancelled', 'expired']
    if (successStatuses.includes(status)) return true
    if (failStatuses.includes(status)) return false
    return null
  }, [propIsSuccess, status])
  
  // Auto-redirect to orders page after success
  useEffect(() => {
    if (derivedSuccess && countdown > 0) {
      const timer = setTimeout(() => setCountdown(countdown - 1), 1000)
      return () => clearTimeout(timer)
    } else if (derivedSuccess && countdown === 0) {
      onNavigate?.('orders')
    }
  }, [derivedSuccess, countdown, onNavigate])
  
  // Poll order status if orderId is available and we don't have explicit success flag
  useEffect(() => {
    if (propIsSuccess !== null) return
    if (!orderId) return
    let timer
    let cancelled = false
    
    const fetchStatus = async () => {
      setLoadingStatus(true)
      try {
        const res = await fetch(`/api/webapp/orders/${orderId}/status`)
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const data = await res.json()
        if (cancelled) return
        if (data?.status) {
          setStatus(String(data.status).toLowerCase())
          // Stop polling if не pending/awaiting_payment
          if (!['pending', 'awaiting_payment', 'payment_pending'].includes(String(data.status).toLowerCase())) {
            return
          }
        }
        // continue polling
        timer = setTimeout(fetchStatus, 3000)
      } catch (e) {
        if (!cancelled) {
          setError(e.message)
          timer = setTimeout(fetchStatus, 5000)
        }
      } finally {
        if (!cancelled) setLoadingStatus(false)
      }
    }
    
    fetchStatus()
    return () => {
      cancelled = true
      if (timer) clearTimeout(timer)
    }
  }, [orderId, propIsSuccess])
  
  return (
    <div className="min-h-screen bg-gradient-to-b from-background to-muted/20 p-4">
      <div className="max-w-md mx-auto pt-12">
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.3 }}
        >
          <Card className="overflow-hidden">
            <CardContent className="pt-8 pb-6 text-center">
              {/* Icon */}
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ delay: 0.1, type: "spring", stiffness: 200 }}
                className="mb-6"
              >
                {derivedSuccess ? (
                  <div className="w-20 h-20 mx-auto bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center">
                    <CheckCircle className="w-12 h-12 text-green-600 dark:text-green-400" />
                  </div>
                ) : (
                  <div className="w-20 h-20 mx-auto bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center">
                    <XCircle className="w-12 h-12 text-red-600 dark:text-red-400" />
                  </div>
                )}
              </motion.div>
              
              {/* Title */}
              <h1 className="text-2xl font-bold mb-2">
                {derivedSuccess 
                  ? (t('payment.success.title') || 'Оплата успешна!')
                  : (t('payment.fail.title') || 'Оплата не прошла')
                }
              </h1>
              
              {/* Description */}
              <p className="text-muted-foreground mb-6">
                {derivedSuccess 
                  ? (t('payment.success.description') || 'Ваш заказ оплачен и будет обработан в ближайшее время.')
                  : (t('payment.fail.description') || 'Произошла ошибка при оплате. Попробуйте ещё раз или выберите другой способ оплаты.')
                }
              </p>
              
              {/* Order ID */}
              {orderId && (
                <div className="bg-muted/50 rounded-lg p-3 mb-6">
                  <p className="text-sm text-muted-foreground">
                    {t('payment.orderId') || 'Номер заказа'}
                  </p>
                  <p className="font-mono font-medium">{orderId}</p>
                </div>
              )}
              
              {/* Auto-redirect countdown for success */}
              {derivedSuccess && countdown > 0 && (
                <p className="text-sm text-muted-foreground mb-4 flex items-center justify-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  {t('payment.redirecting') || 'Переход к заказам через'} {countdown}...
                </p>
              )}
              
              {/* Loading or error */}
              {!derivedSuccess && loadingStatus && (
                <p className="text-sm text-muted-foreground mb-4 flex items-center justify-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  {t('payment.checkingStatus') || 'Проверяем статус платежа...'}
                </p>
              )}
              {error && !derivedSuccess && (
                <p className="text-xs text-destructive mb-2 text-center">
                  {t('payment.statusCheckError') || 'Ошибка проверки статуса'}: {error}
                </p>
              )}
              
              {/* Actions */}
              <div className="space-y-3">
                {derivedSuccess ? (
                  <>
                    <Button 
                      className="w-full"
                      onClick={() => onNavigate?.('orders')}
                    >
                      <ShoppingBag className="w-4 h-4 mr-2" />
                      {t('payment.viewOrders') || 'Мои заказы'}
                    </Button>
                    <Button 
                      variant="outline"
                      className="w-full"
                      onClick={() => onNavigate?.('catalog')}
                    >
                      {t('payment.continueShopping') || 'Продолжить покупки'}
                    </Button>
                  </>
                ) : (
                  <>
                    <Button 
                      className="w-full"
                      onClick={() => onBack?.()}
                    >
                      <ArrowLeft className="w-4 h-4 mr-2" />
                      {t('payment.tryAgain') || 'Попробовать снова'}
                    </Button>
                    <Button 
                      variant="outline"
                      className="w-full"
                      onClick={() => onNavigate?.('contacts')}
                    >
                      <MessageCircle className="w-4 h-4 mr-2" />
                      {t('payment.contactSupport') || 'Связаться с поддержкой'}
                    </Button>
                  </>
                )}
              </div>
            </CardContent>
          </Card>
        </motion.div>
        
        {/* Security note */}
        <p className="text-xs text-center text-muted-foreground mt-6">
                {derivedSuccess 
            ? (t('payment.success.note') || 'Товар будет доставлен автоматически после подтверждения платежа.')
            : (t('payment.fail.note') || 'Если средства были списаны, но заказ не создан, свяжитесь с поддержкой.')
          }
        </p>
      </div>
    </div>
  )
}
