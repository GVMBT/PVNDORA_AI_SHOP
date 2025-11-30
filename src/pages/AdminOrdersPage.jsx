import React, { useState, useEffect } from 'react'
import { useAdmin } from '../hooks/useAdmin'
import { useLocale } from '../hooks/useLocale'
import { useTelegram } from '../hooks/useTelegram'

export default function AdminOrdersPage({ onBack }) {
  const { getOrders, loading } = useAdmin()
  const { formatPrice } = useLocale()
  const { showAlert } = useTelegram()
  
  const [orders, setOrders] = useState([])
  const [statusFilter, setStatusFilter] = useState(null)

  useEffect(() => {
    loadOrders()
  }, [statusFilter])

  const loadOrders = async () => {
    try {
      const data = await getOrders(statusFilter)
      setOrders(data.orders || [])
    } catch (err) {
      await showAlert(`Ошибка: ${err.message}`)
    }
  }

  return (
    <div className="p-4">
      <div className="flex items-center justify-between mb-6">
        <button onClick={onBack} className="text-[var(--color-primary)]">← Назад</button>
        <h1 className="text-xl font-bold">Заказы</h1>
      </div>

      <div className="flex gap-2 mb-4 overflow-x-auto">
        <button
          onClick={() => setStatusFilter(null)}
          className={`px-4 py-2 rounded-full text-sm whitespace-nowrap ${
            statusFilter === null
              ? 'bg-[var(--color-primary)] text-white'
              : 'bg-[var(--color-bg-elevated)] text-[var(--color-text-muted)]'
          }`}
        >
          Все
        </button>
        {['pending', 'prepaid', 'fulfilling', 'ready', 'delivered', 'refunded'].map((status) => (
          <button
            key={status}
            onClick={() => setStatusFilter(status)}
            className={`px-4 py-2 rounded-full text-sm whitespace-nowrap ${
              statusFilter === status
                ? 'bg-[var(--color-primary)] text-white'
                : 'bg-[var(--color-bg-elevated)] text-[var(--color-text-muted)]'
            }`}
          >
            {status}
          </button>
        ))}
      </div>

      {loading && !orders.length ? (
        <div className="text-center py-8">Загрузка...</div>
      ) : orders.length === 0 ? (
        <div className="card text-center py-8">
          <p className="text-[var(--color-text-muted)]">Нет заказов</p>
        </div>
      ) : (
        <div className="space-y-3">
          {orders.map((order) => (
            <div key={order.id} className="card">
              <div className="flex items-start justify-between mb-2">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <span className={`badge ${
                      order.status === 'delivered' ? 'badge-success' :
                      order.status === 'pending' ? 'badge-warning' :
                      order.status === 'refunded' ? 'badge-error' : ''
                    }`}>
                      {order.status}
                    </span>
                    <span className="text-sm text-[var(--color-text-muted)]">
                      #{order.id.slice(0, 8)}
                    </span>
                  </div>
                  <p className="font-semibold text-[var(--color-text)] mb-1">
                    {order.products?.name || 'Неизвестный товар'}
                  </p>
                  <p className="text-sm text-[var(--color-text-muted)]">
                    {order.users?.first_name} (@{order.users?.username || 'нет'})
                  </p>
                </div>
                <div className="text-right">
                  <p className="font-semibold text-[var(--color-primary)]">
                    {formatPrice(order.amount)}₽
                  </p>
                  {order.discount_percent > 0 && (
                    <p className="text-xs text-[var(--color-success)]">
                      -{order.discount_percent}%
                    </p>
                  )}
                </div>
              </div>
              <p className="text-xs text-[var(--color-text-muted)]">
                {new Date(order.created_at).toLocaleString()}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}


