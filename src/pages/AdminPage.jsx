import React from 'react'
import { useLocale } from '../hooks/useLocale'

export default function AdminPage({ onNavigate }) {
  const { t } = useLocale()

  const sections = [
    { id: 'products', icon: '📦', label: 'Товары', desc: 'Управление ассортиментом' },
    { id: 'stock', icon: '📊', label: 'Склад', desc: 'Добавление stock items' },
    { id: 'orders', icon: '🛒', label: 'Заказы', desc: 'Все заказы и статусы' },
    { id: 'tickets', icon: '🎫', label: 'Тикеты', desc: 'Поддержка и замены' },
    { id: 'analytics', icon: '📈', label: 'Аналитика', desc: 'Продажи и метрики' },
    { id: 'faq', icon: '❓', label: 'FAQ', desc: 'Частые вопросы' },
    { id: 'users', icon: '👥', label: 'Пользователи', desc: 'Управление пользователями' }
  ]

  return (
    <div className="p-4">
      <h1 className="text-2xl font-bold text-[var(--color-text)] mb-6">
        🔧 Админ-панель
      </h1>

      <div className="grid gap-4">
        {sections.map((section) => (
          <button
            key={section.id}
            onClick={() => onNavigate(`admin_${section.id}`)}
            className="card text-left hover:border-[var(--color-primary)] transition-all"
          >
            <div className="flex items-center gap-4">
              <span className="text-3xl">{section.icon}</span>
              <div className="flex-1">
                <h3 className="font-semibold text-[var(--color-text)] mb-1">
                  {section.label}
                </h3>
                <p className="text-sm text-[var(--color-text-muted)]">
                  {section.desc}
                </p>
              </div>
              <span className="text-[var(--color-text-muted)]">→</span>
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}

