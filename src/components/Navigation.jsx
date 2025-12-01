import React from 'react'
import { useLocale } from '../hooks/useLocale'
import { ShoppingBag, Package, Trophy, HelpCircle, Shield } from 'lucide-react'
import { cn } from '../lib/utils'

const navItems = [
  { id: 'catalog', icon: ShoppingBag, labelKey: 'nav.catalog' },
  { id: 'orders', icon: Package, labelKey: 'nav.orders' },
  { id: 'leaderboard', icon: Trophy, labelKey: 'nav.leaderboard' },
  { id: 'faq', icon: HelpCircle, labelKey: 'nav.faq' }
]

export default function Navigation({ currentPage, onNavigate, isAdmin = false }) {
  const { t } = useLocale()
  
  // Hide navigation on admin pages
  if (currentPage.startsWith('admin')) {
    return null
  }
  
  // Add admin button if user is admin
  const items = isAdmin 
    ? [...navItems, { id: 'admin', icon: Shield, label: 'Admin' }]
    : navItems
  
  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-background/95 backdrop-blur-lg border-t border-border safe-area-bottom z-50">
      <div className="flex justify-around items-center h-16">
        {items.map((item) => {
          const isActive = currentPage === item.id
          const label = item.label || (item.labelKey ? t(item.labelKey) : '')
          const Icon = item.icon
          
          return (
            <button
              key={item.id}
              onClick={() => onNavigate(item.id)}
              className={cn(
                "flex flex-col items-center justify-center w-full h-full transition-all duration-200",
                isActive 
                  ? "text-primary" 
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              <Icon className={cn("h-6 w-6 mb-1", isActive && "fill-primary/20")} strokeWidth={isActive ? 2.5 : 2} />
              <span className="text-[10px] font-medium">{label}</span>
              {isActive && (
                <div className="absolute bottom-1 w-1 h-1 bg-primary rounded-full" />
              )}
            </button>
          )
        })}
      </div>
    </nav>
  )
}
