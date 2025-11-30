import React, { useState, useEffect } from 'react'
import { useAdmin } from '../hooks/useAdmin'
import { useLocale } from '../hooks/useLocale'
import { useTelegram } from '../hooks/useTelegram'

export default function AdminProductsPage({ onBack }) {
  const { getProducts, createProduct, updateProduct, loading } = useAdmin()
  const { t, formatPrice } = useLocale()
  const { showAlert, hapticFeedback } = useTelegram()
  
  const [products, setProducts] = useState([])
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState(null)
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    price: '',
    type: 'shared',
    fulfillment_time_hours: 48,
    warranty_hours: 24,
    instructions: '',
    msrp: '',
    duration_days: ''
  })

  useEffect(() => {
    loadProducts()
  }, [])

  const loadProducts = async () => {
    try {
      const data = await getProducts()
      setProducts(data.products || [])
    } catch (err) {
      await showAlert(`Ошибка: ${err.message}`)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    hapticFeedback('impact', 'medium')

    try {
      const payload = {
        ...formData,
        price: parseFloat(formData.price),
        fulfillment_time_hours: parseInt(formData.fulfillment_time_hours),
        warranty_hours: parseInt(formData.warranty_hours),
        msrp: formData.msrp ? parseFloat(formData.msrp) : null,
        duration_days: formData.duration_days ? parseInt(formData.duration_days) : null
      }

      if (editing) {
        await updateProduct(editing.id, payload)
        await showAlert('Товар обновлён!')
      } else {
        await createProduct(payload)
        await showAlert('Товар создан!')
      }

      setShowForm(false)
      setEditing(null)
      resetForm()
      loadProducts()
    } catch (err) {
      await showAlert(`Ошибка: ${err.message}`)
    }
  }

  const resetForm = () => {
    setFormData({
      name: '',
      description: '',
      price: '',
      type: 'shared',
      fulfillment_time_hours: 48,
      warranty_hours: 24,
      instructions: '',
      msrp: '',
      duration_days: ''
    })
  }

  const startEdit = (product) => {
    setEditing(product)
    setFormData({
      name: product.name || '',
      description: product.description || '',
      price: product.price || '',
      type: product.type || 'shared',
      fulfillment_time_hours: product.fulfillment_time_hours || 48,
      warranty_hours: product.warranty_hours || 24,
      instructions: product.instructions || '',
      msrp: product.msrp || '',
      duration_days: product.duration_days || ''
    })
    setShowForm(true)
  }

  if (showForm) {
    return (
      <div className="p-4">
        <button onClick={() => { setShowForm(false); setEditing(null); resetForm() }} className="mb-4 text-[var(--color-primary)]">
          ← Назад
        </button>
        <h2 className="text-xl font-bold mb-4">{editing ? 'Редактировать' : 'Создать'} товар</h2>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm mb-1">Название *</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({...formData, name: e.target.value})}
              required
              className="w-full bg-[var(--color-bg-elevated)] border border-[var(--color-border)] rounded-lg px-4 py-2"
            />
          </div>

          <div>
            <label className="block text-sm mb-1">Описание</label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({...formData, description: e.target.value})}
              className="w-full bg-[var(--color-bg-elevated)] border border-[var(--color-border)] rounded-lg px-4 py-2"
              rows="3"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm mb-1">Цена (₽) *</label>
              <input
                type="number"
                step="0.01"
                value={formData.price}
                onChange={(e) => setFormData({...formData, price: e.target.value})}
                required
                className="w-full bg-[var(--color-bg-elevated)] border border-[var(--color-border)] rounded-lg px-4 py-2"
              />
            </div>
            <div>
              <label className="block text-sm mb-1">MSRP (₽)</label>
              <input
                type="number"
                step="0.01"
                value={formData.msrp}
                onChange={(e) => setFormData({...formData, msrp: e.target.value})}
                className="w-full bg-[var(--color-bg-elevated)] border border-[var(--color-border)] rounded-lg px-4 py-2"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm mb-1">Тип *</label>
            <select
              value={formData.type}
              onChange={(e) => setFormData({...formData, type: e.target.value})}
              className="w-full bg-[var(--color-bg-elevated)] border border-[var(--color-border)] rounded-lg px-4 py-2"
            >
              <option value="shared">Shared</option>
              <option value="student">Student</option>
              <option value="trial">Trial</option>
              <option value="key">API Key</option>
            </select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm mb-1">Изготовление (часов)</label>
              <input
                type="number"
                value={formData.fulfillment_time_hours}
                onChange={(e) => setFormData({...formData, fulfillment_time_hours: e.target.value})}
                className="w-full bg-[var(--color-bg-elevated)] border border-[var(--color-border)] rounded-lg px-4 py-2"
              />
            </div>
            <div>
              <label className="block text-sm mb-1">Гарантия (часов)</label>
              <input
                type="number"
                value={formData.warranty_hours}
                onChange={(e) => setFormData({...formData, warranty_hours: e.target.value})}
                className="w-full bg-[var(--color-bg-elevated)] border border-[var(--color-border)] rounded-lg px-4 py-2"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm mb-1">Срок действия (дней)</label>
            <input
              type="number"
              value={formData.duration_days}
              onChange={(e) => setFormData({...formData, duration_days: e.target.value})}
              className="w-full bg-[var(--color-bg-elevated)] border border-[var(--color-border)] rounded-lg px-4 py-2"
            />
          </div>

          <div>
            <label className="block text-sm mb-1">Инструкция</label>
            <textarea
              value={formData.instructions}
              onChange={(e) => setFormData({...formData, instructions: e.target.value})}
              className="w-full bg-[var(--color-bg-elevated)] border border-[var(--color-border)] rounded-lg px-4 py-2"
              rows="3"
            />
          </div>

          <button type="submit" className="btn btn-primary w-full" disabled={loading}>
            {loading ? 'Сохранение...' : editing ? 'Обновить' : 'Создать'}
          </button>
        </form>
      </div>
    )
  }

  return (
    <div className="p-4">
      <div className="flex items-center justify-between mb-6">
        <button onClick={onBack} className="text-[var(--color-primary)]">← Назад</button>
        <h1 className="text-xl font-bold">Товары</h1>
        <button onClick={() => setShowForm(true)} className="btn btn-primary text-sm px-4 py-2">
          + Создать
        </button>
      </div>

      {loading && !products.length ? (
        <div className="text-center py-8 text-[var(--color-text-muted)]">Загрузка...</div>
      ) : products.length === 0 ? (
        <div className="card text-center py-8">
          <p className="text-[var(--color-text-muted)] mb-4">Нет товаров</p>
          <button onClick={() => setShowForm(true)} className="btn btn-primary">
            Создать первый товар
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {products.map((product) => (
            <div key={product.id} className="card">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <h3 className="font-semibold text-[var(--color-text)] mb-1">
                    {product.name}
                  </h3>
                  <p className="text-sm text-[var(--color-text-muted)] mb-2">
                    {product.description || 'Нет описания'}
                  </p>
                  <div className="flex gap-4 text-sm">
                    <span className="text-[var(--color-primary)]">
                      {formatPrice(product.price)}₽
                    </span>
                    <span className="badge">{product.type}</span>
                    <span className="badge">{product.status}</span>
                  </div>
                </div>
                <button
                  onClick={() => startEdit(product)}
                  className="btn btn-secondary text-sm px-3 py-1"
                >
                  Редактировать
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

