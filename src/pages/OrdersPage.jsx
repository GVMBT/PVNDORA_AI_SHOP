import { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import { useOrders } from '../hooks/useApi'
import { useLocale } from '../hooks/useLocale'
import { useTelegram } from '../hooks/useTelegram'
import { 
  Clock, CreditCard, Package, CheckCircle, RotateCcw, XCircle, AlertTriangle, 
  Repeat, Star, ExternalLink, Copy, Timer, ChevronDown, ChevronUp, Loader2 
} from 'lucide-react'
import { Button } from '../components/ui/button'
import { Badge } from '../components/ui/badge'
import { Card, CardContent } from '../components/ui/card'
import { Skeleton } from '../components/ui/skeleton'
import { Tabs, TabsList, TabsTrigger } from '../components/ui/tabs'
import { motion, AnimatePresence } from 'framer-motion'
import { cn } from '../lib/utils'
import { HeaderBar } from '../components/ui/header-bar'

// Countdown timer component for pending orders (payment deadline)
function PaymentCountdown({ expiresAt }) {
  const [timeLeft, setTimeLeft] = useState(null)
  
  useEffect(() => {
    if (!expiresAt) return
    
    const calculateTimeLeft = () => {
      const now = new Date()
      const expiry = new Date(expiresAt)
      const diff = expiry - now
      
      if (diff <= 0) {
        return { expired: true, minutes: 0, seconds: 0 }
      }
      
      const minutes = Math.floor(diff / 60000)
      const seconds = Math.floor((diff % 60000) / 1000)
      return { expired: false, minutes, seconds }
    }
    
    setTimeLeft(calculateTimeLeft())
    
    const interval = setInterval(() => {
      const newTimeLeft = calculateTimeLeft()
      setTimeLeft(newTimeLeft)
      if (newTimeLeft.expired) {
        clearInterval(interval)
      }
    }, 1000)
    
    return () => clearInterval(interval)
  }, [expiresAt])
  
  if (!timeLeft) return null
  
  if (timeLeft.expired) {
    return (
      <div className="flex items-center gap-2 text-xs text-destructive bg-destructive/10 p-2 rounded-lg border border-destructive/20">
        <XCircle className="h-4 w-4" />
        <span className="font-medium">Время на оплату истекло</span>
      </div>
    )
  }
  
  const isUrgent = timeLeft.minutes < 5
  
  return (
    <div className={cn(
      "flex items-center gap-2 text-xs p-2 rounded-lg border",
      isUrgent 
        ? "text-destructive bg-destructive/10 border-destructive/20 animate-pulse" 
        : "text-amber-500 bg-amber-500/10 border-amber-500/20"
    )}>
      <Timer className="h-4 w-4" />
      <span className="font-mono font-bold">
        {String(timeLeft.minutes).padStart(2, '0')}:{String(timeLeft.seconds).padStart(2, '0')}
      </span>
      <span className="font-medium">на оплату</span>
    </div>
  )
}

// Fulfillment countdown for prepaid orders
function FulfillmentCountdown({ deadline, t }) {
  const [timeLeft, setTimeLeft] = useState(null)
  
  useEffect(() => {
    if (!deadline) return
    
    const calculateTimeLeft = () => {
      const now = new Date()
      const end = new Date(deadline)
      const diff = end - now
      
      if (diff <= 0) {
        return { expired: true, hours: 0, minutes: 0 }
      }
      
      const hours = Math.floor(diff / 3600000)
      const minutes = Math.floor((diff % 3600000) / 60000)
      return { expired: false, hours, minutes }
    }
    
    setTimeLeft(calculateTimeLeft())
    
    const interval = setInterval(() => {
      const newTimeLeft = calculateTimeLeft()
      setTimeLeft(newTimeLeft)
      if (newTimeLeft.expired) {
        clearInterval(interval)
      }
    }, 60000) // Update every minute
    
    return () => clearInterval(interval)
  }, [deadline])
  
  if (!timeLeft) return null
  
  if (timeLeft.expired) {
    return (
      <div className="flex items-center gap-2 text-xs text-amber-500 bg-amber-500/10 p-2 rounded-lg border border-amber-500/20">
        <Clock className="h-4 w-4" />
        <span className="font-medium">{t('orders.fulfillmentExpired') || 'Ожидает возврата'}</span>
      </div>
    )
  }
  
  return (
    <div className="flex items-center gap-2 text-xs text-blue-500 bg-blue-500/10 p-2 rounded-lg border border-blue-500/20">
      <Package className="h-4 w-4" />
      <span className="font-medium">
        {t('orders.fulfillmentGuarantee') || 'Гарантия поставки:'} {timeLeft.hours}ч {timeLeft.minutes}м
      </span>
      <span className="text-blue-400 text-[10px]">
        {t('orders.orRefund') || 'или возврат'}
      </span>
    </div>
  )
}

const statusConfig = {
  pending: { icon: Clock, color: 'text-amber-500', bg: 'bg-amber-500/10', border: 'border-amber-500/20', labelKey: 'orders.status.pending' },
  prepaid: { icon: CreditCard, color: 'text-blue-500', bg: 'bg-blue-500/10', border: 'border-blue-500/20', labelKey: 'orders.status.prepaid' },
  fulfilling: { icon: Package, color: 'text-purple-500', bg: 'bg-purple-500/10', border: 'border-purple-500/20', labelKey: 'orders.status.fulfilling' },
  ready: { icon: CheckCircle, color: 'text-emerald-500', bg: 'bg-emerald-500/10', border: 'border-emerald-500/20', labelKey: 'orders.status.ready' },
  delivered: { icon: CheckCircle, color: 'text-emerald-500', bg: 'bg-emerald-500/10', border: 'border-emerald-500/20', labelKey: 'orders.status.delivered' },
  refunded: { icon: RotateCcw, color: 'text-muted-foreground', bg: 'bg-secondary', border: 'border-border', labelKey: 'orders.status.refunded' },
  cancelled: { icon: XCircle, color: 'text-destructive', bg: 'bg-destructive/10', border: 'border-destructive/20', labelKey: 'orders.status.cancelled' },
  expired: { icon: XCircle, color: 'text-muted-foreground', bg: 'bg-secondary', border: 'border-border', labelKey: 'orders.status.expired' },
  failed: { icon: AlertTriangle, color: 'text-destructive', bg: 'bg-destructive/10', border: 'border-destructive/20', labelKey: 'orders.status.failed' }
}

const TABS = [
  { id: 'all', labelKey: 'orders.tabs.all' },
  { id: 'active', labelKey: 'orders.tabs.active' },
  { id: 'completed', labelKey: 'orders.tabs.completed' },
]

const ACTIVE_STATUSES = new Set(['pending', 'prepaid', 'fulfilling', 'ready'])
const COMPLETED_STATUSES = new Set(['delivered', 'fulfilled', 'completed'])

const PAGE_SIZE = 10

export default function OrdersPage({ onBack }) {
  const { getOrders, loading, error } = useOrders()
  const { t, formatPrice, formatDate } = useLocale()
  const { setBackButton, hapticFeedback } = useTelegram()
  
  const [orders, setOrders] = useState([])
  const [currency, setCurrency] = useState('USD')
  const [activeTab, setActiveTab] = useState('all')
  const [expandedItems, setExpandedItems] = useState({}) // { orderId: boolean }
  
  // Infinite scroll state
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const observerRef = useRef(null)
  const sentinelRef = useRef(null)
  
  const loadOrders = useCallback(async (pageNum = 1, append = false) => {
    try {
      if (pageNum > 1) setLoadingMore(true)
      
      const data = await getOrders({ limit: PAGE_SIZE, offset: (pageNum - 1) * PAGE_SIZE })
      const newOrders = data.orders || []
      
      if (append) {
        setOrders(prev => [...prev, ...newOrders])
      } else {
        setOrders(newOrders)
      }
      
      setCurrency(data.currency || 'USD')
      setHasMore(newOrders.length === PAGE_SIZE)
      setPage(pageNum)
    } catch (err) {
      console.error('Failed to load orders:', err)
    } finally {
      setLoadingMore(false)
    }
  }, [getOrders])
  
  // Initial load
  useEffect(() => {
    loadOrders(1, false)
    
    setBackButton({
      isVisible: true,
      onClick: onBack
    })
    
    return () => {
      setBackButton({ isVisible: false })
    }
  }, [onBack, loadOrders, setBackButton])
  
  // Infinite scroll observer
  useEffect(() => {
    if (!hasMore || loading || loadingMore) return
    
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasMore && !loadingMore) {
          loadOrders(page + 1, true)
        }
      },
      { threshold: 0.1 }
    )
    
    if (sentinelRef.current) {
      observer.observe(sentinelRef.current)
    }
    
    observerRef.current = observer
    
    return () => {
      if (observerRef.current) {
        observerRef.current.disconnect()
      }
    }
  }, [hasMore, loading, loadingMore, page, loadOrders])
  
  // Filter orders by tab
  const filteredOrders = useMemo(() => {
    if (activeTab === 'all') return orders
    if (activeTab === 'active') return orders.filter(o => ACTIVE_STATUSES.has(o.status))
    if (activeTab === 'completed') return orders.filter(o => COMPLETED_STATUSES.has(o.status))
    return orders
  }, [orders, activeTab])
  
  const toggleItemsExpand = (orderId) => {
    setExpandedItems(prev => ({ ...prev, [orderId]: !prev[orderId] }))
    hapticFeedback('selection')
  }

  const container = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1
      }
    }
  }

  const item = {
    hidden: { opacity: 0, y: 20 },
    show: { opacity: 1, y: 0 }
  }
  
  const deliveredStates = new Set(['delivered','fulfilled','completed','ready'])
  const waitingStates = new Set(['prepaid','fulfilling'])
  
  return (
    <div className="min-h-screen pb-20 bg-background relative">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-primary/5 via-background to-background pointer-events-none" />

      <HeaderBar
        title={t('orders.title')}
        subtitle={t('orders.subtitle')}
        onBack={onBack}
        className="z-20"
      />
      
      {/* Tabs */}
      <div className="sticky top-0 z-30 bg-background/80 backdrop-blur-xl px-4 py-2 border-b border-border/30">
        <Tabs value={activeTab} onValueChange={(v) => { setActiveTab(v); hapticFeedback('selection') }}>
          <TabsList className="grid grid-cols-3 w-full">
            {TABS.map((tab) => (
              <TabsTrigger key={tab.id} value={tab.id} className="text-xs">
                {t(tab.labelKey) || tab.id}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
      </div>
      
      <div className="p-4 space-y-4 relative z-10">
        {loading && orders.length === 0 ? (
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
               <Skeleton key={i} className="h-40 w-full rounded-2xl bg-secondary/50" />
            ))}
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center py-20 text-center space-y-6">
            <div className="p-6 rounded-full bg-destructive/10 text-destructive animate-pulse">
              <AlertTriangle className="h-10 w-10" />
            </div>
            <p className="text-muted-foreground font-medium">{error}</p>
            <Button onClick={() => loadOrders(1, false)} variant="outline" className="rounded-full">
              {t('common.retry')}
            </Button>
          </div>
        ) : filteredOrders.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-center space-y-6">
            <div className="p-8 rounded-full bg-secondary/30 text-muted-foreground">
              <Package className="h-16 w-16 opacity-50" />
            </div>
            <div>
              <h3 className="font-bold text-xl mb-2">{t('orders.empty')}</h3>
              <p className="text-sm text-muted-foreground max-w-[200px] mx-auto">{t('orders.emptyHint')}</p>
            </div>
          </div>
        ) : (
          <motion.div 
            variants={container}
            initial="hidden"
            animate="show"
            className="space-y-4"
          >
            {filteredOrders.map((order) => {
              const status = statusConfig[order.status] || statusConfig.pending
              const StatusIconComponent = status.icon
              const productName = order.product_name || order.products?.name || t('orders.unknownProduct')
              const itemsList = order.items || []
              const isExpanded = expandedItems[order.id]
              const showExpandButton = itemsList.length > 2
              const visibleItems = isExpanded ? itemsList : itemsList.slice(0, 2)
              
              return (
                <motion.div variants={item} key={order.id}>
                  <div className="group relative">
                    {/* Ticket Perforation Effect */}
                    <div className="absolute -left-2 top-1/2 -translate-y-1/2 w-4 h-4 rounded-full bg-background z-20" />
                    <div className="absolute -right-2 top-1/2 -translate-y-1/2 w-4 h-4 rounded-full bg-background z-20" />
                    
                    <Card className="border-0 bg-card/40 backdrop-blur-lg overflow-hidden shadow-lg ring-1 ring-white/5 hover:ring-primary/30 transition-all duration-300">
                      <CardContent className="p-0">
                        {/* Ticket Header */}
                        <div className="p-4 pb-6 border-b border-dashed border-white/10 bg-white/5">
                          <div className="flex justify-between items-start mb-3">
                            <Badge
                              variant="outline"
                              className={cn(
                                "flex items-center gap-1.5 px-2 py-1 text-[10px] font-bold uppercase tracking-wider border",
                                status.color,
                                status.bg,
                                status.border
                              )}
                            >
                              <StatusIconComponent className="h-3 w-3" />
                              {t(status.labelKey)}
                            </Badge>
                            <p className="font-mono text-xs text-muted-foreground opacity-70">
                              #{order.id.slice(0, 8)}
                            </p>
                          </div>
                          
                          <h3 className="font-bold text-lg leading-tight mb-1">{productName}</h3>
                          <p className="text-xs text-muted-foreground">
                            {formatDate(order.created_at)}
                          </p>
                        </div>
                        
                        {/* Ticket Body */}
                        <div className="p-4 pt-6 bg-gradient-to-b from-transparent to-black/20">
                           <div className="flex justify-between items-center mb-4">
                             <div>
                               <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-0.5">{t('orders.amount')}</p>
                               <p className="text-xl font-bold font-mono tracking-tight">{formatPrice(order.amount, order.currency || currency)}</p>
                             </div>
                             
                             {order.order_type === 'prepaid' && (
                                <Badge variant="outline" className="bg-background/50 backdrop-blur-md border-white/10">
                                  {t('orders.prepaid')}
                                </Badge>
                             )}
                           </div>
                           
                           {/* Payment Timer for pending */}
                           {order.status === 'pending' && order.expires_at && (
                             <div className="mb-4">
                               <PaymentCountdown expiresAt={order.expires_at} />
                             </div>
                           )}
                           
                           {/* Fulfillment Guarantee for prepaid/fulfilling */}
                           {waitingStates.has(order.status) && order.fulfillment_deadline && (
                             <div className="mb-4">
                               <FulfillmentCountdown deadline={order.fulfillment_deadline} t={t} />
                             </div>
                           )}
                           
                           {/* License Expiration for delivered */}
                           {order.status === 'delivered' && order.expires_at && (
                              <div className="flex items-center gap-2 text-xs text-amber-500 bg-amber-500/10 p-3 rounded-xl border border-amber-500/10 mb-4">
                                <Clock className="h-4 w-4 shrink-0" />
                                <span className="font-medium">{t('orders.licenseExpires') || 'Лицензия до'}: {formatDate(order.expires_at)}</span>
                              </div>
                            )}

                           {/* Actions Grid */}
                           {order.status === 'delivered' && (
                              <div className="grid grid-cols-2 gap-3 mb-4">
                                <Button variant="secondary" size="sm" className="h-10 gap-2 bg-white/5 hover:bg-white/10 border border-white/5" onClick={() => hapticFeedback('selection')}>
                                  <Repeat className="h-4 w-4 opacity-70" />
                                  {t('orders.buyAgain')}
                                </Button>
                                <Button variant="secondary" size="sm" className="h-10 gap-2 bg-white/5 hover:bg-white/10 border border-white/5" onClick={() => hapticFeedback('selection')}>
                                  <Star className="h-4 w-4 opacity-70" />
                                  {t('orders.leaveReview')}
                                </Button>
                              </div>
                           )}
                           
                           {/* Payment Button for Pending Orders */}
                           {order.status === 'pending' && order.payment_url && (
                              <div className="mb-4">
                                <Button 
                                  className="w-full bg-primary text-black hover:bg-primary/90 font-bold" 
                                  onClick={() => {
                                    hapticFeedback('impact', 'medium')
                                    if (window.Telegram?.WebApp?.openLink) {
                                      window.Telegram.WebApp.openLink(order.payment_url)
                                    } else {
                                      window.open(order.payment_url, '_blank')
                                    }
                                  }}
                                >
                                  {t('checkout.pay') || 'Оплатить'}
                                  <ExternalLink className="h-4 w-4 ml-2" />
                                </Button>
                              </div>
                           )}

                           {/* Items list with Accordion */}
                           {itemsList.length > 0 && (
                             <div className="space-y-2">
                               <p className="text-xs uppercase tracking-wider text-muted-foreground font-semibold">
                                 {t('orders.items') || 'Позиции заказа'} ({itemsList.length})
                               </p>
                               <div className="space-y-2">
                                 <AnimatePresence initial={false}>
                                   {visibleItems.map((it) => {
                                     const itStatus = statusConfig[it.status] || statusConfig.pending
                                     const showContent = deliveredStates.has(it.status) && it.delivery_content
                                     return (
                                       <motion.div 
                                         key={it.id} 
                                         initial={{ opacity: 0, height: 0 }}
                                         animate={{ opacity: 1, height: 'auto' }}
                                         exit={{ opacity: 0, height: 0 }}
                                         className="rounded-xl border border-border/40 bg-background/40 p-3"
                                       >
                                         <div className="flex items-start justify-between gap-2">
                                           <div className="flex-1">
                                             <p className="font-medium text-sm text-foreground">{it.product_name}</p>
                                             <div className={`inline-flex items-center gap-1 px-2 py-1 mt-1 rounded-full text-[11px] font-semibold ${itStatus.bg} ${itStatus.color} ${itStatus.border}`}>
                                               <itStatus.icon className="h-3 w-3" />
                                               <span>{t(itStatus.labelKey) || it.status}</span>
                                             </div>
                                           </div>
                                           {showContent && (
                                             <Button
                                               variant="ghost"
                                               size="sm"
                                               className="h-8 w-8 p-0"
                                               onClick={() => {
                                                 navigator.clipboard?.writeText(it.delivery_content)
                                                 hapticFeedback('impact', 'light')
                                               }}
                                             >
                                               <Copy className="h-4 w-4" />
                                             </Button>
                                           )}
                                         </div>
                                         {showContent && (
                                           <div className="mt-2 bg-muted/30 border border-border/40 rounded-lg p-2">
                                             <pre className="whitespace-pre-wrap break-words text-sm font-mono text-foreground">
                                               {it.delivery_content}
                                             </pre>
                                             {it.delivery_instructions && (
                                               <p className="text-xs text-muted-foreground mt-1">
                                                 {it.delivery_instructions}
                                               </p>
                                             )}
                                           </div>
                                         )}
                                         {!showContent && waitingStates.has(it.status) && (
                                           <p className="text-xs text-muted-foreground mt-2">
                                             {t('orders.waitingStock') || 'Ожидает поставки'}
                                           </p>
                                         )}
                                       </motion.div>
                                     )
                                   })}
                                 </AnimatePresence>
                                 
                                 {/* Expand/Collapse button */}
                                 {showExpandButton && (
                                   <Button
                                     variant="ghost"
                                     size="sm"
                                     className="w-full text-xs text-muted-foreground"
                                     onClick={() => toggleItemsExpand(order.id)}
                                   >
                                     {isExpanded ? (
                                       <>
                                         <ChevronUp className="h-4 w-4 mr-1" />
                                         {t('orders.showLess') || 'Скрыть'}
                                       </>
                                     ) : (
                                       <>
                                         <ChevronDown className="h-4 w-4 mr-1" />
                                         {t('orders.showMore') || `Ещё ${itemsList.length - 2} позиций`}
                                       </>
                                     )}
                                   </Button>
                                 )}
                               </div>
                             </div>
                           )}

                           {/* Legacy: Delivery content for old orders without items array */}
                           {deliveredStates.has(order.status) && order.delivery_content && !itemsList.length && (
                             <div className="mt-4 space-y-2">
                               <p className="text-xs uppercase tracking-wider text-muted-foreground font-semibold">
                                 {t('orders.delivery') || 'Доступ'}
                               </p>
                               <div className="bg-muted/30 border border-border/50 rounded-xl p-3">
                                 <div className="flex justify-between items-start gap-2">
                                   <pre className="whitespace-pre-wrap break-words text-sm font-mono text-foreground flex-1">
                                     {order.delivery_content}
                                   </pre>
                                   <Button
                                     variant="ghost"
                                     size="sm"
                                     className="h-8 w-8 p-0"
                                     onClick={() => {
                                       navigator.clipboard?.writeText(order.delivery_content)
                                       hapticFeedback('impact', 'light')
                                     }}
                                   >
                                     <Copy className="h-4 w-4" />
                                   </Button>
                                 </div>
                                 {order.delivery_instructions && (
                                   <p className="text-xs text-muted-foreground mt-2">
                                     {order.delivery_instructions}
                                   </p>
                                 )}
                               </div>
                             </div>
                           )}
                        </div>
                      </CardContent>
                    </Card>
                  </div>
                </motion.div>
              )
            })}
            
            {/* Infinite scroll sentinel */}
            <div ref={sentinelRef} className="h-10 flex items-center justify-center">
              {loadingMore && (
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              )}
            </div>
          </motion.div>
        )}
      </div>
    </div>
  )
}
