import { useState, useEffect, useCallback } from 'react'
import { useOrders } from '../hooks/useApi'
import { useLocale } from '../hooks/useLocale'
import { useTelegram } from '../hooks/useTelegram'
import { ArrowLeft, Clock, CreditCard, Package, CheckCircle, RotateCcw, XCircle, AlertTriangle, Repeat, Star } from 'lucide-react'
import { Button } from '../components/ui/button'
import { Badge } from '../components/ui/badge'
import { Card, CardContent } from '../components/ui/card'
import { Skeleton } from '../components/ui/skeleton'

const statusConfig = {
  pending: { icon: Clock, color: 'warning', labelKey: 'orders.status.pending' },
  prepaid: { icon: CreditCard, color: 'primary', labelKey: 'orders.status.prepaid' },
  fulfilling: { icon: Package, color: 'primary', labelKey: 'orders.status.fulfilling' },
  ready: { icon: CheckCircle, color: 'success', labelKey: 'orders.status.ready' },
  delivered: { icon: CheckCircle, color: 'success', labelKey: 'orders.status.delivered' },
  refunded: { icon: RotateCcw, color: 'muted', labelKey: 'orders.status.refunded' },
  cancelled: { icon: XCircle, color: 'destructive', labelKey: 'orders.status.cancelled' },
  failed: { icon: AlertTriangle, color: 'destructive', labelKey: 'orders.status.failed' }
}

export default function OrdersPage({ onBack }) {
  const { getOrders, loading, error } = useOrders()
  const { t, formatPrice, formatDate } = useLocale()
  const { setBackButton } = useTelegram()
  
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
  
  return (
    <div className="pb-20">
      {/* Header */}
      <div className="sticky top-0 z-10 bg-background/80 backdrop-blur-md border-b border-border/50 p-4 flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={onBack} className="h-8 w-8 rounded-full">
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div>
          <h1 className="text-lg font-bold">{t('orders.title')}</h1>
          <p className="text-xs text-muted-foreground">{t('orders.subtitle')}</p>
        </div>
      </div>
      
      <div className="p-4 space-y-4">
        {loading ? (
          <>
            <Skeleton className="h-32 w-full rounded-xl" />
            <Skeleton className="h-32 w-full rounded-xl" />
            <Skeleton className="h-32 w-full rounded-xl" />
          </>
        ) : error ? (
          <div className="flex flex-col items-center justify-center py-12 text-center space-y-4">
            <div className="p-4 rounded-full bg-destructive/10 text-destructive">
              <AlertTriangle className="h-8 w-8" />
            </div>
            <p className="text-muted-foreground">{error}</p>
            <Button onClick={loadOrders} variant="outline">
              {t('common.retry')}
            </Button>
          </div>
        ) : orders.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center space-y-4">
            <div className="p-4 rounded-full bg-secondary text-muted-foreground">
              <Package className="h-12 w-12" />
            </div>
            <div>
              <h3 className="font-semibold text-lg">{t('orders.empty')}</h3>
              <p className="text-sm text-muted-foreground">{t('orders.emptyHint')}</p>
            </div>
          </div>
        ) : (
          orders.map((order, index) => {
            const status = statusConfig[order.status] || statusConfig.pending
            const StatusIconComponent = status.icon
            const productName = order.products?.name || t('orders.unknownProduct')
            
            return (
              <Card 
                key={order.id}
                className="stagger-enter border-border/50 bg-card/50"
                style={{ animationDelay: `${index * 0.1}s` }}
              >
                <CardContent className="p-4 space-y-4">
                  {/* Header */}
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="font-semibold text-base">{productName}</h3>
                      <p className="text-xs text-muted-foreground">
                        {formatDate(order.created_at)}
                      </p>
                    </div>
                    <Badge 
                      variant={status.color === 'success' ? 'success' : status.color === 'warning' ? 'warning' : status.color === 'destructive' ? 'destructive' : 'secondary'}
                      className="gap-1.5"
                    >
                      <StatusIconComponent className="h-3 w-3" />
                      {t(status.labelKey)}
                    </Badge>
                  </div>
                  
                  {/* Details */}
                  <div className="flex items-center justify-between bg-secondary/30 p-3 rounded-lg">
                    <div className="space-y-0.5">
                      <span className="text-xs text-muted-foreground">{t('orders.amount')}</span>
                      <p className="font-semibold">{formatPrice(order.amount)}</p>
                    </div>
                    
                    {order.order_type === 'prepaid' && (
                      <Badge variant="outline" className="bg-background/50">
                        {t('orders.prepaid')}
                      </Badge>
                    )}
                  </div>
                  
                  {/* Expiration warning */}
                  {order.status === 'delivered' && order.expires_at && (
                    <div className="flex items-center gap-2 text-xs text-yellow-500 bg-yellow-500/10 p-2 rounded-md border border-yellow-500/20">
                      <Clock className="h-3.5 w-3.5" />
                      <span>{t('orders.expiresOn')}: {formatDate(order.expires_at)}</span>
                    </div>
                  )}
                  
                  {/* Actions */}
                  {order.status === 'delivered' && (
                    <div className="grid grid-cols-2 gap-3 pt-2 border-t border-border/50">
                      <Button variant="outline" size="sm" className="gap-2 h-9">
                        <Repeat className="h-3.5 w-3.5" />
                        {t('orders.buyAgain')}
                      </Button>
                      <Button variant="outline" size="sm" className="gap-2 h-9">
                        <Star className="h-3.5 w-3.5" />
                        {t('orders.leaveReview')}
                      </Button>
                    </div>
                  )}
                </CardContent>
              </Card>
            )
          })
        )}
      </div>
    </div>
  )
}
