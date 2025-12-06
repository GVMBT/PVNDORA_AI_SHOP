import React, { useState, useEffect, useCallback, useMemo } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { 
  CreditCard, Building2, User, Clock, Copy, Check, 
  AlertCircle, Loader2, ArrowLeft, RefreshCw, Smartphone,
  ExternalLink, QrCode
} from 'lucide-react'
import { Button } from '../components/ui/button'
import { Card, CardContent } from '../components/ui/card'
import QRCode from 'react-qr-code'

// Bank logos and colors
const BANK_CONFIG = {
  'сбербанк': { color: '#21A038', logo: '🟢', name: 'Сбербанк' },
  'сбер': { color: '#21A038', logo: '🟢', name: 'Сбербанк' },
  'тинькофф': { color: '#FFDD2D', logo: '🟡', name: 'Тинькофф' },
  'tinkoff': { color: '#FFDD2D', logo: '🟡', name: 'Тинькофф' },
  'альфа': { color: '#EF3124', logo: '🔴', name: 'Альфа-Банк' },
  'alfa': { color: '#EF3124', logo: '🔴', name: 'Альфа-Банк' },
  'втб': { color: '#0A2972', logo: '🔵', name: 'ВТБ' },
  'vtb': { color: '#0A2972', logo: '🔵', name: 'ВТБ' },
  'райффайзен': { color: '#FEE600', logo: '🟡', name: 'Райффайзен' },
  'raiffeisen': { color: '#FEE600', logo: '🟡', name: 'Райффайзен' },
  'газпром': { color: '#0066B3', logo: '🔵', name: 'Газпромбанк' },
  'открытие': { color: '#00AEEF', logo: '🔵', name: 'Открытие' },
  'росбанк': { color: '#E30613', logo: '🔴', name: 'Росбанк' },
  'мкб': { color: '#00529B', logo: '🔵', name: 'МКБ' },
  'совком': { color: '#EE2E24', logo: '🔴', name: 'Совкомбанк' },
  'почта': { color: '#005BAC', logo: '🔵', name: 'Почта Банк' },
}

// Get bank config from name
const getBankConfig = (bankName) => {
  if (!bankName) return { color: '#6366f1', logo: '🏦', name: bankName || 'Банк' }
  const lower = bankName.toLowerCase()
  for (const [key, config] of Object.entries(BANK_CONFIG)) {
    if (lower.includes(key)) return config
  }
  return { color: '#6366f1', logo: '🏦', name: bankName }
}

// Format card number with spaces
const formatCardNumber = (card) => {
  if (!card) return ''
  return card.replace(/\s/g, '').replace(/(.{4})/g, '$1 ').trim()
}

/**
 * Payment Form Page (H2H Integration)
 * 
 * Shows payment requisites received from Rukassa with beautiful UI.
 * Features: QR code, bank logos, SBP deep link, copy buttons.
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
  const [showQR, setShowQR] = useState(false)
  const [autoCheckEnabled, setAutoCheckEnabled] = useState(false)
  const [checkingStatus, setCheckingStatus] = useState(false)
  
  // Bank configuration
  const bankConfig = useMemo(() => getBankConfig(paymentData.bank), [paymentData.bank])
  
  // QR code data for bank apps (simple format)
  const qrData = useMemo(() => {
    // Format: card|amount|receiver
    return `ST00012|Name=${paymentData.receiver}|PersonalAcc=${paymentData.card}|Sum=${Math.round(parseFloat(paymentData.amount || 0) * 100)}|Purpose=Оплата заказа ${paymentData.orderId}`
  }, [paymentData])
  
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
  
  // Auto-check payment status (polling)
  useEffect(() => {
    if (!autoCheckEnabled || confirmed || !paymentData.orderId) return
    
    const checkStatus = async () => {
      try {
        setCheckingStatus(true)
        const response = await fetch(`/api/webapp/orders/${paymentData.orderId}/status`)
        
        if (response.ok) {
          const data = await response.json()
          
          // Check if payment was confirmed
          if (data.status === 'prepaid' || data.status === 'delivered' || data.status === 'ready') {
            setConfirmed(true)
            if (window.Telegram?.WebApp?.HapticFeedback) {
              window.Telegram.WebApp.HapticFeedback.notificationOccurred('success')
            }
            setTimeout(() => onNavigate?.('orders'), 2000)
          }
        }
      } catch (err) {
        console.error('Status check error:', err)
      } finally {
        setCheckingStatus(false)
      }
    }
    
    // Check immediately, then every 5 seconds
    checkStatus()
    const interval = setInterval(checkStatus, 5000)
    
    return () => clearInterval(interval)
  }, [autoCheckEnabled, confirmed, paymentData.orderId, onNavigate])
  
  // Copy to clipboard with haptic feedback
  const copyToClipboard = useCallback(async (text, field) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(field)
      setTimeout(() => setCopied(null), 2000)
      
      if (window.Telegram?.WebApp?.HapticFeedback) {
        window.Telegram.WebApp.HapticFeedback.notificationOccurred('success')
      }
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }, [])

  // Best-effort attempt to open bank app (may not prefill for P2P)
  const openBankApp = useCallback(() => {
    if (!paymentData.card) {
      setShowQR(true)
      return
    }
    // Try generic SBP deep link with amount/purpose hint
    const link = `sbp://qr?type=card&card=${paymentData.card}&sum=${paymentData.amount || ''}&purpose=Оплата заказа ${paymentData.orderId || ''}`
    let fallbackTriggered = false
    try {
      window.location.href = link
    } catch (err) {
      fallbackTriggered = true
      setShowQR(true)
    }
    // If nothing happens within a short delay, show QR as fallback
    setTimeout(() => {
      if (!fallbackTriggered) {
        setShowQR(true)
      }
    }, 1200)
  }, [paymentData])
  
  // Start auto-checking after user transfers
  const handleStartAutoCheck = () => {
    setAutoCheckEnabled(true)
    if (window.Telegram?.WebApp?.HapticFeedback) {
      window.Telegram.WebApp.HapticFeedback.impactOccurred('medium')
    }
  }
  
  // Manual confirm payment (fallback)
  const handleConfirmPayment = async () => {
    setConfirming(true)
    
    try {
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
        if (window.Telegram?.WebApp?.HapticFeedback) {
          window.Telegram.WebApp.HapticFeedback.notificationOccurred('success')
        }
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
          <Card className="overflow-hidden">
            <CardContent className="pt-8 pb-6 text-center">
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                className="w-20 h-20 mx-auto bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center mb-4"
              >
                <AlertCircle className="w-10 h-10 text-red-600 dark:text-red-400" />
              </motion.div>
              <h2 className="text-xl font-bold mb-2">Время истекло</h2>
              <p className="text-muted-foreground mb-6">
                Срок действия платежа истёк. Создайте новый заказ.
              </p>
              <Button onClick={() => onNavigate?.('catalog')} className="w-full">
                <RefreshCw className="w-4 h-4 mr-2" />
                Вернуться в каталог
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    )
  }
  
  // Payment confirmed
  if (confirmed) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-background to-muted/20 p-4">
        <div className="max-w-md mx-auto pt-12">
          <Card className="overflow-hidden">
            <CardContent className="pt-8 pb-6 text-center">
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ type: "spring", stiffness: 200 }}
                className="w-20 h-20 mx-auto bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center mb-4"
              >
                <Check className="w-10 h-10 text-green-600 dark:text-green-400" />
              </motion.div>
              <h2 className="text-xl font-bold mb-2">Платёж отправлен!</h2>
              <p className="text-muted-foreground mb-4">
                Ожидаем подтверждения от банка. Обычно 1-5 минут.
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
    <div className="min-h-screen bg-gradient-to-b from-background to-muted/20 pb-32">
      {/* Header */}
      <div className="sticky top-0 z-20 bg-background/80 backdrop-blur-lg border-b">
        <div className="max-w-md mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <button 
              onClick={onBack}
              className="flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            
            {/* Timer in header */}
            {timeLeft && (
              <motion.div
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium ${
                  timeLeft.total < 300000 
                    ? 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300' 
                    : 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300'
                }`}
              >
                <Clock className="w-4 h-4" />
                <span className="font-mono">
                  {String(timeLeft.minutes).padStart(2, '0')}:{String(timeLeft.seconds).padStart(2, '0')}
                </span>
              </motion.div>
            )}
            
            <button
              onClick={() => setShowQR(!showQR)}
              className="p-2 rounded-full hover:bg-muted transition-colors"
            >
              <QrCode className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>
      
      <div className="max-w-md mx-auto px-4 pt-6 space-y-4">
        {/* QR Code Section (для второго устройства / fallback) */}
        <AnimatePresence>
          {showQR && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="overflow-hidden"
            >
              <Card className="bg-white">
                <CardContent className="pt-6 pb-6">
                  <div className="flex flex-col items-center">
                    <p className="text-sm text-muted-foreground mb-1">
                      Отсканируйте с другого устройства
                    </p>
                    <p className="text-xs text-muted-foreground mb-4">
                      Или сохраните скриншот и загрузите в банк
                    </p>
                    <div className="p-4 bg-white rounded-xl shadow-inner">
                      <QRCode 
                        value={qrData}
                        size={180}
                        level="M"
                      />
                    </div>
                    <p className="text-xs text-muted-foreground mt-4 text-center">
                      QR-код содержит реквизиты для оплаты
                    </p>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          )}
        </AnimatePresence>
        
        {/* Amount Card - Hero */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <Card className="border-2 border-primary overflow-hidden">
            <div 
              className="h-2"
              style={{ backgroundColor: bankConfig.color }}
            />
            <CardContent className="pt-6 pb-6">
              <div className="text-center">
                <p className="text-sm text-muted-foreground mb-2">Сумма к оплате</p>
                <p className="text-5xl font-bold text-primary mb-1">
                  {parseFloat(paymentData.amount).toLocaleString('ru-RU')}
                  <span className="text-2xl ml-1">₽</span>
                </p>
                <p className="text-xs text-muted-foreground">
                  Переведите <strong>точную сумму</strong>
                </p>
              </div>
            </CardContent>
          </Card>
        </motion.div>
        
        {/* Card Number - Main CTA */}
        {paymentData.card && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
          >
            <Card 
              className="cursor-pointer hover:shadow-lg transition-shadow"
              onClick={() => copyToClipboard(paymentData.card, 'card')}
            >
              <CardContent className="pt-5 pb-5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div 
                      className="w-12 h-12 rounded-xl flex items-center justify-center text-2xl"
                      style={{ backgroundColor: `${bankConfig.color}20` }}
                    >
                      {bankConfig.logo}
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground mb-0.5">
                        {bankConfig.name}
                      </p>
                      <p className="font-mono text-xl font-semibold tracking-wider">
                        {formatCardNumber(paymentData.card)}
                      </p>
                    </div>
                  </div>
                  <AnimatePresence mode="wait">
                    <motion.div
                      key={copied === 'card' ? 'check' : 'copy'}
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      exit={{ scale: 0 }}
                      className={`p-2 rounded-full ${
                        copied === 'card' 
                          ? 'bg-green-100 dark:bg-green-900/30' 
                          : 'bg-muted'
                      }`}
                    >
                      {copied === 'card' ? (
                        <Check className="w-5 h-5 text-green-600" />
                      ) : (
                        <Copy className="w-5 h-5 text-muted-foreground" />
                      )}
                    </motion.div>
                  </AnimatePresence>
                </div>
                
                {copied === 'card' && (
                  <motion.p
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="text-center text-sm text-green-600 mt-3 font-medium"
                  >
                    ✓ Номер скопирован
                  </motion.p>
                )}
              </CardContent>
            </Card>
          </motion.div>
        )}
        
        {/* Receiver Info */}
        {paymentData.receiver && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            <Card>
              <CardContent className="pt-4 pb-4">
                <div className="flex items-center gap-3">
                  <div className="p-2.5 bg-muted rounded-xl">
                    <User className="w-5 h-5 text-muted-foreground" />
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Получатель</p>
                    <p className="font-medium">{paymentData.receiver}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}
        
        {/* Quick Actions */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="grid grid-cols-2 gap-3"
        >
          <Button 
            variant="outline" 
            className="h-14 flex-col gap-1"
            onClick={() => copyToClipboard(paymentData.amount, 'amount')}
          >
            <span className="text-lg font-bold">
              {parseFloat(paymentData.amount).toLocaleString('ru-RU')} ₽
            </span>
            <span className="text-xs text-muted-foreground">
              {copied === 'amount' ? '✓ Скопировано' : 'Копировать сумму'}
            </span>
          </Button>
          
          <Button 
            variant="outline" 
            className="h-14 flex-col gap-1"
            onClick={() => setShowQR(true)}
          >
            <QrCode className="w-5 h-5" />
            <span className="text-xs text-muted-foreground">
              QR (второе устройство)
            </span>
          </Button>
        </motion.div>

        {/* Best-effort open bank */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.35 }}
        >
          <Button 
            variant="secondary"
            className="w-full h-12 justify-center gap-2"
            onClick={openBankApp}
          >
            <Smartphone className="w-4 h-4" />
            Открыть банк (beta)
          </Button>
          <p className="text-xs text-muted-foreground mt-2">
            Может не сработать в вашем банке. Реквизиты могут не подставиться — используйте копирование.
          </p>
        </motion.div>
        
        {/* Instructions */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
        >
          <Card className="bg-muted/30 border-dashed">
            <CardContent className="pt-4 pb-4">
              <div className="flex gap-3">
                <div className="flex flex-col items-center">
                  <div className="w-6 h-6 rounded-full bg-primary/10 text-primary text-xs font-bold flex items-center justify-center">1</div>
                  <div className="w-px h-full bg-border my-1" />
                </div>
                <p className="text-sm pb-3">Скопируйте номер карты (нажмите на карту выше)</p>
              </div>
              <div className="flex gap-3">
                <div className="flex flex-col items-center">
                  <div className="w-6 h-6 rounded-full bg-primary/10 text-primary text-xs font-bold flex items-center justify-center">2</div>
                  <div className="w-px h-full bg-border my-1" />
                </div>
                <p className="text-sm pb-3">Откройте приложение банка и переведите <strong>точную сумму</strong></p>
              </div>
              <div className="flex gap-3">
                <div className="flex flex-col items-center">
                  <div className="w-6 h-6 rounded-full bg-primary/10 text-primary text-xs font-bold flex items-center justify-center">3</div>
                </div>
                <p className="text-sm">Нажмите «Я оплатил» после перевода</p>
              </div>
            </CardContent>
          </Card>
        </motion.div>
        
        {/* Order ID */}
        {paymentData.orderId && (
          <p className="text-center text-xs text-muted-foreground pt-2">
            Заказ #{paymentData.orderId}
          </p>
        )}
      </div>
      
      {/* Fixed Bottom */}
      <div className="fixed bottom-0 left-0 right-0 p-4 bg-background/95 backdrop-blur-lg border-t safe-area-bottom">
        <div className="max-w-md mx-auto space-y-3">
          {/* Auto-checking mode */}
          {autoCheckEnabled ? (
            <div className="space-y-3">
              <div className="flex items-center justify-center gap-3 p-4 bg-primary/5 rounded-xl">
                <div className="relative">
                  <Loader2 className="w-6 h-6 animate-spin text-primary" />
                  {checkingStatus && (
                    <span className="absolute -top-1 -right-1 w-2 h-2 bg-green-500 rounded-full animate-ping" />
                  )}
                </div>
                <div className="text-center">
                  <p className="font-medium">Ожидаем оплату...</p>
                  <p className="text-xs text-muted-foreground">
                    Автоматически обнаружим перевод
                  </p>
                </div>
              </div>
              
              {/* Fallback button */}
              <Button 
                variant="outline"
                className="w-full"
                onClick={handleConfirmPayment}
                disabled={confirming}
              >
                {confirming ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Проверяем...
                  </>
                ) : (
                  'Не приходит? Подтвердить вручную'
                )}
              </Button>
            </div>
          ) : (
            <>
              <Button 
                className="w-full h-14 text-lg font-semibold"
                onClick={handleStartAutoCheck}
              >
                <Smartphone className="w-5 h-5 mr-2" />
                Перевёл, жду подтверждения
              </Button>
              
              <p className="text-center text-xs text-muted-foreground">
                Нажмите после перевода — мы автоматически определим оплату
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
