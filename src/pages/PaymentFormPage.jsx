import React, { useState, useEffect, useCallback } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { 
  CreditCard, Building2, User, Clock, Copy, Check, 
  AlertCircle, Loader2, ArrowLeft, RefreshCw 
} from 'lucide-react'
import { Button } from '../components/ui/button'
import { Card, CardContent } from '../components/ui/card'

/**
 * Payment Form Page (H2H Integration)
 * 
 * Shows payment requisites received from Rukassa.
 * User makes manual transfer and confirms payment.
 * 
 * URL: /payment/form?card=...&bank=...&receiver=...&amount=...&date=...&order_id=...
 */
export default function PaymentFormPage({ 
  onNavigate,
  onBack 
}) {
  // Parse URL parameters
  const [paymentData] = useState(() => {
    const params = new URLSearchParams(window.location.search)
    return {
      card: params.get('card') || '',
      bank: params.get('bank') || '',
      receiver: params.get('receiver') || '',
      amount: params.get('amount') || '',
      date: params.get('date') || '',
      orderId: params.get('order_id') || params.get('id') || '',
      hash: params.get('hash') || '',
    }
  })
  
  const [copied, setCopied] = useState(null)
  const [timeLeft, setTimeLeft] = useState(null)
  const [confirming, setConfirming] = useState(false)
  const [confirmed, setConfirmed] = useState(false)
  
  // Calculate time remaining
  useEffect(() => {
    if (!paymentData.date) return
    
    const updateTimer = () => {
      const expiresAt = new Date(paymentData.date).getTime()
      const now = Date.now()
      const diff = expiresAt - now
      
      if (diff <= 0) {
        setTimeLeft(0)
        return
      }
      
      const minutes = Math.floor(diff / 60000)
      const seconds = Math.floor((diff % 60000) / 1000)
      setTimeLeft({ minutes, seconds, total: diff })
    }
    
    updateTimer()
    const interval = setInterval(updateTimer, 1000)
    return () => clearInterval(interval)
  }, [paymentData.date])
  
  // Copy to clipboard
  const copyToClipboard = useCallback(async (text, field) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(field)
      setTimeout(() => setCopied(null), 2000)
      
      // Telegram haptic feedback
      if (window.Telegram?.WebApp?.HapticFeedback) {
        window.Telegram.WebApp.HapticFeedback.notificationOccurred('success')
      }
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }, [])
  
  // Confirm payment (user says they've paid)
  const handleConfirmPayment = async () => {
    setConfirming(true)
    
    try {
      // Notify our backend that user claims to have paid
      // Backend will check with Rukassa or wait for webhook
      const response = await fetch('/api/webapp/orders/confirm-payment', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          order_id: paymentData.orderId,
          hash: paymentData.hash,
        })
      })
      
      if (response.ok) {
        setConfirmed(true)
        // Redirect to orders after 3 seconds
        setTimeout(() => onNavigate?.('orders'), 3000)
      }
    } catch (err) {
      console.error('Confirm payment error:', err)
    } finally {
      setConfirming(false)
    }
  }
  
  // Payment expired
  if (timeLeft === 0) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-background to-muted/20 p-4">
        <div className="max-w-md mx-auto pt-12">
          <Card>
            <CardContent className="pt-8 pb-6 text-center">
              <div className="w-16 h-16 mx-auto bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center mb-4">
                <AlertCircle className="w-8 h-8 text-red-600 dark:text-red-400" />
              </div>
              <h2 className="text-xl font-bold mb-2">Время истекло</h2>
              <p className="text-muted-foreground mb-6">
                Срок действия платежа истёк. Пожалуйста, создайте новый заказ.
              </p>
              <Button onClick={() => onNavigate?.('catalog')} className="w-full">
                <RefreshCw className="w-4 h-4 mr-2" />
                Создать новый заказ
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    )
  }
  
  // Payment confirmed - waiting for verification
  if (confirmed) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-background to-muted/20 p-4">
        <div className="max-w-md mx-auto pt-12">
          <Card>
            <CardContent className="pt-8 pb-6 text-center">
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                className="w-16 h-16 mx-auto bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center mb-4"
              >
                <Check className="w-8 h-8 text-green-600 dark:text-green-400" />
              </motion.div>
              <h2 className="text-xl font-bold mb-2">Платёж подтверждён</h2>
              <p className="text-muted-foreground mb-4">
                Ожидаем подтверждения от банка. Обычно это занимает 1-5 минут.
              </p>
              <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="w-4 h-4 animate-spin" />
                Переход к заказам...
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    )
  }
  
  return (
    <div className="min-h-screen bg-gradient-to-b from-background to-muted/20 p-4 pb-24">
      {/* Header */}
      <div className="max-w-md mx-auto mb-6">
        <button 
          onClick={onBack}
          className="flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors mb-4"
        >
          <ArrowLeft className="w-4 h-4" />
          Назад
        </button>
        
        <h1 className="text-2xl font-bold">Оплата заказа</h1>
        <p className="text-muted-foreground">
          Переведите указанную сумму по реквизитам ниже
        </p>
      </div>
      
      <div className="max-w-md mx-auto space-y-4">
        {/* Timer */}
        {timeLeft && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className={`rounded-lg p-4 text-center ${
              timeLeft.total < 300000 
                ? 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300' 
                : 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300'
            }`}
          >
            <div className="flex items-center justify-center gap-2 mb-1">
              <Clock className="w-4 h-4" />
              <span className="font-medium">Время на оплату</span>
            </div>
            <div className="text-2xl font-bold font-mono">
              {String(timeLeft.minutes).padStart(2, '0')}:{String(timeLeft.seconds).padStart(2, '0')}
            </div>
          </motion.div>
        )}
        
        {/* Amount - Most important */}
        <Card className="border-2 border-primary">
          <CardContent className="pt-6">
            <div className="text-center">
              <p className="text-sm text-muted-foreground mb-1">Сумма к оплате</p>
              <p className="text-4xl font-bold text-primary">
                {parseFloat(paymentData.amount).toLocaleString('ru-RU')} ₽
              </p>
              <p className="text-xs text-muted-foreground mt-2">
                Переведите точную сумму для автоматического зачисления
              </p>
            </div>
          </CardContent>
        </Card>
        
        {/* Card Number */}
        {paymentData.card && (
          <Card>
            <CardContent className="pt-4 pb-4">
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-3">
                  <div className="p-2 bg-muted rounded-lg">
                    <CreditCard className="w-5 h-5 text-muted-foreground" />
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Номер карты</p>
                    <p className="font-mono text-lg font-medium tracking-wider">
                      {paymentData.card.replace(/(.{4})/g, '$1 ').trim()}
                    </p>
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => copyToClipboard(paymentData.card, 'card')}
                  className="shrink-0"
                >
                  <AnimatePresence mode="wait">
                    {copied === 'card' ? (
                      <motion.div
                        key="check"
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        exit={{ scale: 0 }}
                      >
                        <Check className="w-4 h-4 text-green-500" />
                      </motion.div>
                    ) : (
                      <motion.div
                        key="copy"
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        exit={{ scale: 0 }}
                      >
                        <Copy className="w-4 h-4" />
                      </motion.div>
                    )}
                  </AnimatePresence>
                </Button>
              </div>
            </CardContent>
          </Card>
        )}
        
        {/* Bank */}
        {paymentData.bank && (
          <Card>
            <CardContent className="pt-4 pb-4">
              <div className="flex items-start gap-3">
                <div className="p-2 bg-muted rounded-lg">
                  <Building2 className="w-5 h-5 text-muted-foreground" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Банк</p>
                  <p className="font-medium">{paymentData.bank}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
        
        {/* Receiver */}
        {paymentData.receiver && (
          <Card>
            <CardContent className="pt-4 pb-4">
              <div className="flex items-start gap-3">
                <div className="p-2 bg-muted rounded-lg">
                  <User className="w-5 h-5 text-muted-foreground" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Получатель</p>
                  <p className="font-medium">{paymentData.receiver}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
        
        {/* Instructions */}
        <Card className="bg-muted/50">
          <CardContent className="pt-4 pb-4">
            <h3 className="font-medium mb-3">Инструкция:</h3>
            <ol className="space-y-2 text-sm text-muted-foreground">
              <li className="flex gap-2">
                <span className="font-medium text-foreground">1.</span>
                Скопируйте номер карты
              </li>
              <li className="flex gap-2">
                <span className="font-medium text-foreground">2.</span>
                Откройте приложение вашего банка
              </li>
              <li className="flex gap-2">
                <span className="font-medium text-foreground">3.</span>
                Переведите <strong>точную сумму</strong> на указанную карту
              </li>
              <li className="flex gap-2">
                <span className="font-medium text-foreground">4.</span>
                Нажмите "Я оплатил" после перевода
              </li>
            </ol>
          </CardContent>
        </Card>
        
        {/* Order ID */}
        {paymentData.orderId && (
          <p className="text-center text-xs text-muted-foreground">
            Заказ: {paymentData.orderId}
          </p>
        )}
      </div>
      
      {/* Fixed bottom button */}
      <div className="fixed bottom-0 left-0 right-0 p-4 bg-background/80 backdrop-blur-lg border-t">
        <div className="max-w-md mx-auto">
          <Button 
            className="w-full h-12 text-lg"
            onClick={handleConfirmPayment}
            disabled={confirming}
          >
            {confirming ? (
              <>
                <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                Проверяем...
              </>
            ) : (
              <>
                <Check className="w-5 h-5 mr-2" />
                Я оплатил
              </>
            )}
          </Button>
        </div>
      </div>
    </div>
  )
}
