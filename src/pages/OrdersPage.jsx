import React, { useState, useEffect } from 'react'
import { useOrders } from '../hooks/useApi'
import { useLocale } from '../hooks/useLocale'
import { useTelegram } from '../hooks/useTelegram'

const statusConfig = {
  pending: { emoji: '⏳', color: 'warning', labelKey: 'orders.status.pending' },
  prepaid: { emoji: '💳', color: 'primary', labelKey: 'orders.status.prepaid' },
  fulfilling: { emoji: '🔄', color: 'primary', labelKey: 'orders.status.fulfilling' },
  ready: { emoji: '📬', color: 'success', labelKey: 'orders.status.ready' },
  delivered: { emoji: '✅', color: 'success', labelKey: 'orders.status.delivered' },
  refunded: { emoji: '↩️', color: 'muted', labelKey: 'orders.status.refunded' },
  cancelled: { emoji: '❌', color: 'error', labelKey: 'orders.status.cancelled' },
  failed: { emoji: '⚠️', color: 'error', labelKey: 'orders.status.failed' }
}

export default function OrdersPage({ onBack }) {
  const { getOrders, loading, error } = useOrders()
  const { t, formatPrice, formatDate } = useLocale()
  const { setBackButton } = useTelegram()
  
  const [orders, setOrders] = useState([])
  
  useEffect(() => {
    loadOrders()
    
    setBackButton({
      isVisible: true,
      onClick: onBack
    })
    
    return () => {
      setBackButton({ isVisible: false })
    }
  }, [])
  
  const loadOrders = async () => {
    try {
      const data = await getOrders()
      setOrders(data.orders || [])
    } catch (err) {
      console.error('Failed to load orders:', err)
    }
  }
  
  return (
    <div className="p-4">
      {/* Header */}
      <header className="mb-6 stagger-enter">
        <h1 className="text-2xl font-bold text-[var(--color-text)]">
          {t('orders.title')}
        </h1>
        <p className="text-[var(--color-text-muted)]">
          {t('orders.subtitle')}
        </p>
      </header>
      
      {/* Orders list */}
      {loading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="card h-32 skeleton" />
          ))}
        </div>
      ) : error ? (
        <div className="card text-center py-8">
          <p className="text-[var(--color-error)] mb-4">{error}</p>
          <button onClick={loadOrders} className="btn btn-secondary">
            {t('common.retry')}
          </button>
        </div>
      ) : orders.length === 0 ? (
        <div className="card text-center py-12 stagger-enter">
          <span className="text-5xl mb-4 block">📦</span>
          <h3 className="text-lg font-semibold text-[var(--color-text)] mb-2">
            {t('orders.empty')}
          </h3>
          <p className="text-[var(--color-text-muted)]">
            {t('orders.emptyHint')}
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {orders.map((order, index) => {
            const status = statusConfig[order.status] || statusConfig.pending
            const productName = order.products?.name || t('orders.unknownProduct')
            
            return (
              <div 
                key={order.id} 
                className="card stagger-enter"
                style={{ animationDelay: `${index * 0.1}s` }}
              >
                {/* Header */}
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <h3 className="font-semibold text-[var(--color-text)]">
                      {productName}
                    </h3>
                    <span className="text-[var(--color-text-muted)] text-sm">
                      {formatDate(order.created_at)}
                    </span>
                  </div>
                  <span className={`badge badge-${status.color}`}>
                    {status.emoji} {t(status.labelKey)}
                  </span>
                </div>
                
                {/* Details */}
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-[var(--color-text-muted)] text-sm">
                      {t('orders.amount')}:
                    </span>
                    <span className="font-semibold text-[var(--color-text)] ml-1">
                      {formatPrice(order.amount)}
                    </span>
                  </div>
                  
                  {order.order_type === 'prepaid' && (
                    <span className="badge bg-[var(--color-bg-elevated)] text-[var(--color-text-muted)]">
                      {t('orders.prepaid')}
                    </span>
                  )}
                </div>
                
                {/* Expiration warning */}
                {order.status === 'delivered' && order.expires_at && (
                  <div className="mt-3 pt-3 border-t border-[var(--color-border)]">
                    <span className="text-[var(--color-warning)] text-sm">
                      ⏰ {t('orders.expiresOn')}: {formatDate(order.expires_at)}
                    </span>
                  </div>
                )}
                
                {/* Actions */}
                {order.status === 'delivered' && (
                  <div className="mt-3 pt-3 border-t border-[var(--color-border)] flex gap-2">
                    <button className="btn btn-secondary flex-1 text-sm py-2">
                      🔄 {t('orders.buyAgain')}
                    </button>
                    <button className="btn btn-secondary flex-1 text-sm py-2">
                      ⭐ {t('orders.leaveReview')}
                    </button>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}


