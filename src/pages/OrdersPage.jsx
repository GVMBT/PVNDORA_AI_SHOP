import { useState, useEffect, useCallback } from 'react'
import { useOrders } from '../hooks/useApi'
import { useLocale } from '../hooks/useLocale'
import { useTelegram } from '../hooks/useTelegram'
import { ArrowLeft, Clock, CreditCard, Package, CheckCircle, RotateCcw, XCircle, AlertTriangle, Repeat, Star, ExternalLink, Copy } from 'lucide-react'
import { Button } from '../components/ui/button'
import { Badge } from '../components/ui/badge'
import { Card, CardContent } from '../components/ui/card'
import { Skeleton } from '../components/ui/skeleton'
import { motion } from 'framer-motion'
import { cn } from '../lib/utils'

const statusConfig = {
  pending: { icon: Clock, color: 'text-amber-500', bg: 'bg-amber-500/10', border: 'border-amber-500/20', labelKey: 'orders.status.pending' },
  prepaid: { icon: CreditCard, color: 'text-blue-500', bg: 'bg-blue-500/10', border: 'border-blue-500/20', labelKey: 'orders.status.prepaid' },
  fulfilling: { icon: Package, color: 'text-purple-500', bg: 'bg-purple-500/10', border: 'border-purple-500/20', labelKey: 'orders.status.fulfilling' },
  ready: { icon: CheckCircle, color: 'text-emerald-500', bg: 'bg-emerald-500/10', border: 'border-emerald-500/20', labelKey: 'orders.status.ready' },
  delivered: { icon: CheckCircle, color: 'text-emerald-500', bg: 'bg-emerald-500/10', border: 'border-emerald-500/20', labelKey: 'orders.status.delivered' },
  refunded: { icon: RotateCcw, color: 'text-muted-foreground', bg: 'bg-secondary', border: 'border-border', labelKey: 'orders.status.refunded' },
  cancelled: { icon: XCircle, color: 'text-destructive', bg: 'bg-destructive/10', border: 'border-destructive/20', labelKey: 'orders.status.cancelled' },
  failed: { icon: AlertTriangle, color: 'text-destructive', bg: 'bg-destructive/10', border: 'border-destructive/20', labelKey: 'orders.status.failed' }
}

export default function OrdersPage({ onBack }) {
  const { getOrders, loading, error } = useOrders()
  const { t, formatPrice, formatDate } = useLocale()
  const { setBackButton, hapticFeedback } = useTelegram()
  
  const [orders, setOrders] = useState([])
  
  const loadOrders = useCallback(async () => {
    try {
      const data = await getOrders()
      setOrders(data.orders || [])
    } catch (err) {
      console.error('Failed to load orders:', err)
    }
  }, [getOrders])
  
  useEffect(() => {
    loadOrders()
    
    setBackButton({
      isVisible: true,
      onClick: onBack
    })
    
    return () => {
      setBackButton({ isVisible: false })
    }
  }, [onBack, loadOrders, setBackButton])

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
  
  return (
    <div className="min-h-screen pb-20 bg-background relative">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-primary/5 via-background to-background pointer-events-none" />

      {/* Header */}
      <div className="sticky top-0 z-10 backdrop-blur-xl border-b border-white/5 p-4 flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={onBack} className="h-10 w-10 rounded-full bg-secondary/30 hover:bg-secondary/50">
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div>
          <h1 className="text-xl font-bold tracking-tight">{t('orders.title')}</h1>
          <p className="text-xs text-muted-foreground font-medium">{t('orders.subtitle')}</p>
        </div>
      </div>
      
      <div className="p-4 space-y-4 relative z-10">
        {loading ? (
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
            <Button onClick={loadOrders} variant="outline" className="rounded-full">
              {t('common.retry')}
            </Button>
          </div>
        ) : orders.length === 0 ? (
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
            {orders.map((order) => {
              const status = statusConfig[order.status] || statusConfig.pending
              const StatusIconComponent = status.icon
              const productName = order.product_name || order.products?.name || t('orders.unknownProduct')
              
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
                            <div className={cn("flex items-center gap-1.5 px-2 py-1 rounded-lg text-[10px] font-bold uppercase tracking-wider border", status.color, status.bg, status.border)}>
                               <StatusIconComponent className="h-3 w-3" />
                               {t(status.labelKey)}
                            </div>
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
                               <p className="text-xl font-bold font-mono tracking-tight">{formatPrice(order.amount)}</p>
                             </div>
                             
                             {order.order_type === 'prepaid' && (
                                <Badge variant="outline" className="bg-background/50 backdrop-blur-md border-white/10">
                                  {t('orders.prepaid')}
                                </Badge>
                             )}
                           </div>
                           
                           {/* Expiration */}
                            {order.status === 'delivered' && order.expires_at && (
                              <div className="flex items-center gap-2 text-xs text-amber-500 bg-amber-500/10 p-3 rounded-xl border border-amber-500/10 mb-4">
                                <Clock className="h-4 w-4 shrink-0" />
                                <span className="font-medium">{t('orders.expiresOn')}: {formatDate(order.expires_at)}</span>
                              </div>
                            )}

                           {/* Actions Grid */}
                           {order.status === 'delivered' && (
                              <div className="grid grid-cols-2 gap-3">
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
                           
                           {/* Pay Button if Pending */}
                           {order.status === 'pending' && order.payment_url && (
                              <Button className="w-full bg-primary text-black hover:bg-primary/90 font-bold" onClick={() => window.open(order.payment_url, '_blank')}>
                                {t('checkout.pay')}
                                <ExternalLink className="h-4 w-4 ml-2" />
                              </Button>
                           )}
                        </div>
                      </CardContent>
                    </Card>
                  </div>
                </motion.div>
              )
            })}
          </motion.div>
        )}
      </div>
    </div>
  )
}
