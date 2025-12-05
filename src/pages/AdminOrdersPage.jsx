import React, { useState, useEffect } from 'react'
import { useAdmin } from '../hooks/useAdmin'
import { useLocale } from '../hooks/useLocale'
import { useTelegram } from '../hooks/useTelegram'
import { ArrowLeft, Search, Filter, Clock, CheckCircle, XCircle, AlertTriangle, RefreshCw } from 'lucide-react'
import { Button } from '../components/ui/button'
import { Card, CardContent } from '../components/ui/card'
import { Input } from '../components/ui/input'
import { Badge } from '../components/ui/badge'
import { Skeleton } from '../components/ui/skeleton'

const statusConfig = {
  pending: { icon: Clock, color: 'warning', label: 'Ожидает' },
  prepaid: { icon: Clock, color: 'primary', label: 'Предоплата' },
  fulfilling: { icon: RefreshCw, color: 'primary', label: 'Выполняется' },
  ready: { icon: CheckCircle, color: 'success', label: 'Готов' },
  delivered: { icon: CheckCircle, color: 'success', label: 'Доставлен' },
  refunded: { icon: RefreshCw, color: 'secondary', label: 'Возврат' },
  cancelled: { icon: XCircle, color: 'destructive', label: 'Отменён' },
  failed: { icon: AlertTriangle, color: 'destructive', label: 'Ошибка' }
}

export default function AdminOrdersPage({ onBack }) {
  const { getOrders, updateOrderStatus, loading } = useAdmin()
  const { formatPrice, formatDate } = useLocale()
  const { showAlert, hapticFeedback } = useTelegram()
  
  const [orders, setOrders] = useState([])
  const [filteredOrders, setFilteredOrders] = useState([])
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')

  useEffect(() => {
    loadOrders()
  }, [])

  useEffect(() => {
    filterOrders()
  }, [orders, search, statusFilter])

  const loadOrders = async () => {
    try {
      const data = await getOrders()
      setOrders(data.orders || [])
    } catch (err) {
      await showAlert(`Error: ${err.message}`)
    }
  }

  const filterOrders = () => {
    let result = [...orders]

    if (search) {
      const lowerSearch = search.toLowerCase()
      result = result.filter(o => 
        o.id.toLowerCase().includes(lowerSearch) ||
        (o.user?.username || '').toLowerCase().includes(lowerSearch) ||
        (o.products?.name || '').toLowerCase().includes(lowerSearch)
      )
    }

    if (statusFilter !== 'all') {
      result = result.filter(o => o.status === statusFilter)
    }

    setFilteredOrders(result)
  }

  const handleStatusChange = async (orderId, newStatus) => {
    hapticFeedback('impact', 'medium')
    try {
      await updateOrderStatus(orderId, newStatus)
      await showAlert(`Статус заказа изменён на ${statusConfig[newStatus]?.label || newStatus}`)
      loadOrders()
    } catch (err) {
      await showAlert(`Error: ${err.message}`)
    }
  }

  return (
    <div className="p-4 pb-20 space-y-6">
      <div className="flex items-center gap-4 sticky top-0 bg-background/80 backdrop-blur-md py-2 z-10 border-b border-border/50">
        <Button variant="ghost" size="icon" onClick={onBack}>
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <h1 className="text-xl font-bold">Заказы</h1>
      </div>

      <div className="space-y-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input 
            placeholder="Поиск заказов..." 
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>

        <div className="flex gap-2 overflow-x-auto pb-2 no-scrollbar">
          <Badge 
            variant={statusFilter === 'all' ? 'default' : 'outline'}
            className="cursor-pointer whitespace-nowrap"
            onClick={() => setStatusFilter('all')}
          >
            All
          </Badge>
          {Object.keys(statusConfig).map(status => (
            <Badge
              key={status}
              variant={statusFilter === status ? 'default' : 'outline'}
              className="cursor-pointer whitespace-nowrap capitalize"
              onClick={() => setStatusFilter(status)}
            >
              {status}
            </Badge>
          ))}
        </div>
      </div>

      {loading && !orders.length ? (
        <div className="space-y-4">
          {[1, 2, 3].map(i => <Skeleton key={i} className="h-32 w-full rounded-xl" />)}
        </div>
      ) : filteredOrders.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">
          No orders found
        </div>
      ) : (
        <div className="space-y-4">
          {filteredOrders.map((order) => {
            const status = statusConfig[order.status] || statusConfig.pending
            const StatusIcon = status.icon
            
            return (
              <Card key={order.id} className="overflow-hidden">
                <CardContent className="p-4 space-y-4">
                  <div className="flex justify-between items-start">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="font-semibold">{order.products?.name || 'Unknown Product'}</h3>
                        <span className="text-xs text-muted-foreground bg-secondary px-1.5 py-0.5 rounded">
                          x{order.quantity || 1}
                        </span>
                      </div>
                      <p className="text-xs text-muted-foreground">
                        User: @{order.users?.username || order.users?.first_name || `ID: ${order.users?.telegram_id}`}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {formatDate(order.created_at)}
                      </p>
                    </div>
                    <Badge variant={status.color}>
                      <StatusIcon className="h-3 w-3 mr-1" />
                      {status.label}
                    </Badge>
                  </div>

                  <div className="flex justify-between items-center p-2 bg-secondary/20 rounded-lg">
                    <span className="text-sm font-medium text-primary">
                      {formatPrice(order.amount)}
                    </span>
                    <span className="text-xs font-mono text-muted-foreground">
                      {order.id.slice(0, 8)}
                    </span>
                  </div>

                  {/* Admin Actions */}
                  <div className="flex gap-2 overflow-x-auto pt-2 border-t border-border/50">
                    {order.status === 'pending' && (
                      <>
                        <Button size="sm" variant="outline" onClick={() => handleStatusChange(order.id, 'delivered')}>
                          Mark Delivered
                        </Button>
                        <Button size="sm" variant="destructive" onClick={() => handleStatusChange(order.id, 'cancelled')}>
                          Cancel
                        </Button>
                      </>
                    )}
                    {order.status === 'delivered' && (
                      <Button size="sm" variant="outline" onClick={() => handleStatusChange(order.id, 'refunded')}>
                        Refund
                      </Button>
                    )}
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}
    </div>
  )
}
