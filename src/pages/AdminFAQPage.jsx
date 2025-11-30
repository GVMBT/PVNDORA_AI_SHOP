import React, { useState, useEffect } from 'react'
import { useAdmin } from '../hooks/useAdmin'
import { useTelegram } from '../hooks/useTelegram'

export default function AdminFAQPage({ onBack }) {
  const { getFAQ, createFAQ, loading } = useAdmin()
  const { showAlert, hapticFeedback } = useTelegram()
  
  const [faq, setFaq] = useState([])
  const [showForm, setShowForm] = useState(false)
  const [formData, setFormData] = useState({
    question: '',
    answer: '',
    language_code: 'ru',
    category: 'general'
  })

  useEffect(() => {
    loadFAQ()
  }, [])

  const loadFAQ = async () => {
    try {
      const data = await getFAQ()
      setFaq(data.faq || [])
    } catch (err) {
      await showAlert(`Ошибка: ${err.message}`)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    hapticFeedback('impact', 'medium')

    try {
      await createFAQ(formData)
      await showAlert('FAQ создан!')
      setShowForm(false)
      resetForm()
      loadFAQ()
    } catch (err) {
      await showAlert(`Ошибка: ${err.message}`)
    }
  }

  const resetForm = () => {
    setFormData({
      question: '',
      answer: '',
      language_code: 'ru',
      category: 'general'
    })
  }

  if (showForm) {
    return (
      <div className="p-4">
        <button onClick={() => { setShowForm(false); resetForm() }} className="mb-4 text-[var(--color-primary)]">
          ← Назад
        </button>
        <h2 className="text-xl font-bold mb-4">Создать FAQ</h2>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm mb-1">Вопрос *</label>
            <input
              type="text"
              value={formData.question}
              onChange={(e) => setFormData({...formData, question: e.target.value})}
              required
              className="w-full bg-[var(--color-bg-elevated)] border border-[var(--color-border)] rounded-lg px-4 py-2"
            />
          </div>

          <div>
            <label className="block text-sm mb-1">Ответ *</label>
            <textarea
              value={formData.answer}
              onChange={(e) => setFormData({...formData, answer: e.target.value})}
              required
              className="w-full bg-[var(--color-bg-elevated)] border border-[var(--color-border)] rounded-lg px-4 py-2"
              rows="5"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm mb-1">Язык *</label>
              <select
                value={formData.language_code}
                onChange={(e) => setFormData({...formData, language_code: e.target.value})}
                className="w-full bg-[var(--color-bg-elevated)] border border-[var(--color-border)] rounded-lg px-4 py-2"
              >
                <option value="ru">Русский</option>
                <option value="en">English</option>
                <option value="uk">Українська</option>
              </select>
            </div>
            <div>
              <label className="block text-sm mb-1">Категория</label>
              <select
                value={formData.category}
                onChange={(e) => setFormData({...formData, category: e.target.value})}
                className="w-full bg-[var(--color-bg-elevated)] border border-[var(--color-border)] rounded-lg px-4 py-2"
              >
                <option value="general">Общие</option>
                <option value="payment">Оплата</option>
                <option value="delivery">Доставка</option>
                <option value="warranty">Гарантия</option>
              </select>
            </div>
          </div>

          <button type="submit" className="btn btn-primary w-full" disabled={loading}>
            {loading ? 'Создание...' : 'Создать'}
          </button>
        </form>
      </div>
    )
  }

  return (
    <div className="p-4">
      <div className="flex items-center justify-between mb-6">
        <button onClick={onBack} className="text-[var(--color-primary)]">← Назад</button>
        <h1 className="text-xl font-bold">FAQ</h1>
        <button onClick={() => setShowForm(true)} className="btn btn-primary text-sm px-4 py-2">
          + Создать
        </button>
      </div>

      {loading && !faq.length ? (
        <div className="text-center py-8">Загрузка...</div>
      ) : faq.length === 0 ? (
        <div className="card text-center py-8">
          <p className="text-[var(--color-text-muted)] mb-4">Нет FAQ</p>
          <button onClick={() => setShowForm(true)} className="btn btn-primary">
            Создать первый
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {faq.map((item) => (
            <div key={item.id} className="card">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="badge">{item.language_code}</span>
                    <span className="badge bg-[var(--color-bg-elevated)]">{item.category}</span>
                  </div>
                  <h3 className="font-semibold text-[var(--color-text)] mb-1">
                    {item.question}
                  </h3>
                  <p className="text-sm text-[var(--color-text-muted)]">
                    {item.answer}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

