import React, { useState, useEffect } from 'react'
import { useAdmin } from '../hooks/useAdmin'
import { useLocale } from '../hooks/useLocale'
import { useTelegram } from '../hooks/useTelegram'

export default function AdminAnalyticsPage({ onBack }) {
  const { getAnalytics, loading } = useAdmin()
  const { formatPrice } = useLocale()
  const { showAlert } = useTelegram()
  
  const [analytics, setAnalytics] = useState(null)
  const [days, setDays] = useState(7)

  useEffect(() => {
    loadAnalytics()
  }, [days])

  const loadAnalytics = async () => {
    try {
      const data = await getAnalytics(days)
      setAnalytics(data)
    } catch (err) {
      await showAlert(`Ошибка: ${err.message}`)
    }
  }

  return (
    <div className="p-4">
      <div className="flex items-center justify-between mb-6">
        <button onClick={onBack} className="text-[var(--color-primary)]">← Назад</button>
        <h1 className="text-xl font-bold">Аналитика</h1>
      </div>

      <div className="flex gap-2 mb-4">
        {[7, 30, 90].map((d) => (
          <button
            key={d}
            onClick={() => setDays(d)}
            className={`px-4 py-2 rounded-full text-sm ${
              days === d
                ? 'bg-[var(--color-primary)] text-white'
                : 'bg-[var(--color-bg-elevated)] text-[var(--color-text-muted)]'
            }`}
          >
            {d} дней
          </button>
        ))}
      </div>

      {loading ? (
        <div className="text-center py-8">Загрузка...</div>
      ) : analytics ? (
        <div className="space-y-4">
          <div className="card">
            <h3 className="font-semibold mb-3">Продажи</h3>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-[var(--color-text-muted)]">Всего заказов:</span>
                <span className="font-semibold">{analytics.total_orders || 0}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--color-text-muted)]">Выручка:</span>
                <span className="font-semibold text-[var(--color-primary)]">
                  {formatPrice(analytics.total_revenue || 0)}₽
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--color-text-muted)]">Средний чек:</span>
                <span className="font-semibold">
                  {formatPrice(analytics.avg_order_value || 0)}₽
                </span>
              </div>
            </div>
          </div>

          {analytics.top_products && analytics.top_products.length > 0 && (
            <div className="card">
              <h3 className="font-semibold mb-3">Топ товары</h3>
              <div className="space-y-2">
                {analytics.top_products.map((product, idx) => (
                  <div key={idx} className="flex justify-between">
                    <span className="text-[var(--color-text-muted)]">{product.name}:</span>
                    <span className="font-semibold">{product.count} продаж</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="card text-center py-8">
          <p className="text-[var(--color-text-muted)]">Нет данных</p>
        </div>
      )}
    </div>
  )
}


