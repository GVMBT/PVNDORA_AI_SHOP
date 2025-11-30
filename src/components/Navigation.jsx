import React from 'react'
import { useLocale } from '../hooks/useLocale'

const navItems = [
  { id: 'catalog', icon: '🛍', labelKey: 'nav.catalog' },
  { id: 'orders', icon: '📦', labelKey: 'nav.orders' },
  { id: 'leaderboard', icon: '🏆', labelKey: 'nav.leaderboard' },
  { id: 'faq', icon: '❓', labelKey: 'nav.faq' }
]

export default function Navigation({ currentPage, onNavigate, isAdmin = false }) {
  const { t } = useLocale()
  
  // Hide navigation on admin pages
  if (currentPage.startsWith('admin')) {
    return null
  }
  
  // Add admin button if user is admin
  const items = isAdmin 
    ? [...navItems, { id: 'admin', icon: '🔧', labelKey: 'Админ' }]
    : navItems
  
  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-[var(--color-bg-card)] border-t border-[var(--color-border)] safe-area-bottom z-50">
      <div className="flex justify-around items-center h-16">
        {items.map((item) => {
          const isActive = currentPage === item.id
          
          return (
            <button
              key={item.id}
              onClick={() => onNavigate(item.id)}
              className={`flex flex-col items-center justify-center px-4 py-2 transition-all ${
                isActive 
                  ? 'text-[var(--color-primary)] scale-105' 
                  : 'text-[var(--color-text-muted)] hover:text-[var(--color-text)]'
              }`}
            >
              <span className="text-xl mb-0.5">{item.icon}</span>
              <span className="text-xs font-medium">{item.labelKey || t(item.labelKey)}</span>
              {isActive && (
                <div className="absolute bottom-0 w-12 h-0.5 bg-[var(--color-primary)] rounded-full" />
              )}
            </button>
          )
        })}
      </div>
    </nav>
  )
}


