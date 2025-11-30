import React, { useState, useEffect } from 'react'
import { useAdmin } from '../hooks/useAdmin'
import { useTelegram } from '../hooks/useTelegram'

export default function AdminStockPage({ onBack }) {
  const { getStock, addStock, addStockBulk, getProducts, loading } = useAdmin()
  const { showAlert, hapticFeedback } = useTelegram()
  
  const [stock, setStock] = useState([])
  const [products, setProducts] = useState([])
  const [showForm, setShowForm] = useState(false)
  const [formData, setFormData] = useState({
    product_id: '',
    content: '',
    expires_at: '',
    supplier_id: ''
  })
  const [bulkMode, setBulkMode] = useState(false)
  const [bulkContent, setBulkContent] = useState('')

  useEffect(() => {
    loadStock()
    loadProducts()
  }, [])

  const loadStock = async () => {
    try {
      const data = await getStock()
      setStock(data.stock || [])
    } catch (err) {
      await showAlert(`Ошибка: ${err.message}`)
    }
  }

  const loadProducts = async () => {
    try {
      const data = await getProducts()
      setProducts(data.products || [])
    } catch (err) {
      // Ignore
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    hapticFeedback('impact', 'medium')

    try {
      if (bulkMode) {
        // Parse bulk content (one per line)
        const lines = bulkContent.split('\n').filter(l => l.trim())
        await addStockBulk({
          product_id: formData.product_id,
          items: lines.map(line => ({
            content: line.trim(),
            expires_at: formData.expires_at || null,
            supplier_id: formData.supplier_id || null
          }))
        })
        await showAlert(`Добавлено ${lines.length} позиций!`)
      } else {
        await addStock({
          product_id: formData.product_id,
          content: formData.content,
          expires_at: formData.expires_at || null,
          supplier_id: formData.supplier_id || null
        })
        await showAlert('Stock item добавлен!')
      }

      setShowForm(false)
      resetForm()
      loadStock()
    } catch (err) {
      await showAlert(`Ошибка: ${err.message}`)
    }
  }

  const resetForm = () => {
    setFormData({
      product_id: '',
      content: '',
      expires_at: '',
      supplier_id: ''
    })
    setBulkContent('')
  }

  if (showForm) {
    return (
      <div className="p-4">
        <button onClick={() => { setShowForm(false); resetForm() }} className="mb-4 text-[var(--color-primary)]">
          ← Назад
        </button>
        <h2 className="text-xl font-bold mb-4">Добавить stock</h2>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm mb-1">Товар *</label>
            <select
              value={formData.product_id}
              onChange={(e) => setFormData({...formData, product_id: e.target.value})}
              required
              className="w-full bg-[var(--color-bg-elevated)] border border-[var(--color-border)] rounded-lg px-4 py-2"
            >
              <option value="">Выберите товар</option>
              {products.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm mb-1">
              {bulkMode ? 'Содержимое (по одному на строку)' : 'Содержимое (Login:Pass или ссылка)'} *
            </label>
            {bulkMode ? (
              <textarea
                value={bulkContent}
                onChange={(e) => setBulkContent(e.target.value)}
                required
                className="w-full bg-[var(--color-bg-elevated)] border border-[var(--color-border)] rounded-lg px-4 py-2"
                rows="10"
                placeholder="user1@example.com:pass123&#10;user2@example.com:pass456&#10;..."
              />
            ) : (
              <input
                type="text"
                value={formData.content}
                onChange={(e) => setFormData({...formData, content: e.target.value})}
                required
                className="w-full bg-[var(--color-bg-elevated)] border border-[var(--color-border)] rounded-lg px-4 py-2"
                placeholder="user@example.com:password"
              />
            )}
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="bulk"
              checked={bulkMode}
              onChange={(e) => setBulkMode(e.target.checked)}
              className="w-4 h-4"
            />
            <label htmlFor="bulk" className="text-sm">Массовое добавление</label>
          </div>

          <div>
            <label className="block text-sm mb-1">Истекает (опционально)</label>
            <input
              type="datetime-local"
              value={formData.expires_at}
              onChange={(e) => setFormData({...formData, expires_at: e.target.value})}
              className="w-full bg-[var(--color-bg-elevated)] border border-[var(--color-border)] rounded-lg px-4 py-2"
            />
          </div>

          <button type="submit" className="btn btn-primary w-full" disabled={loading}>
            {loading ? 'Добавление...' : 'Добавить'}
          </button>
        </form>
      </div>
    )
  }

  return (
    <div className="p-4">
      <div className="flex items-center justify-between mb-6">
        <button onClick={onBack} className="text-[var(--color-primary)]">← Назад</button>
        <h1 className="text-xl font-bold">Склад</h1>
        <button onClick={() => setShowForm(true)} className="btn btn-primary text-sm px-4 py-2">
          + Добавить
        </button>
      </div>

      {loading && !stock.length ? (
        <div className="text-center py-8">Загрузка...</div>
      ) : stock.length === 0 ? (
        <div className="card text-center py-8">
          <p className="text-[var(--color-text-muted)] mb-4">Нет stock items</p>
          <button onClick={() => setShowForm(true)} className="btn btn-primary">
            Добавить первый
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {stock.map((item) => (
            <div key={item.id} className="card">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <span className={`badge ${
                      item.status === 'available' ? 'badge-success' :
                      item.status === 'reserved' ? 'badge-warning' :
                      'badge-error'
                    }`}>
                      {item.status}
                    </span>
                    {item.is_sold && <span className="badge badge-error">Продано</span>}
                  </div>
                  <p className="text-sm text-[var(--color-text)] font-mono mb-1">
                    {item.content}
                  </p>
                  {item.expires_at && (
                    <p className="text-xs text-[var(--color-text-muted)]">
                      Истекает: {new Date(item.expires_at).toLocaleDateString()}
                    </p>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}


