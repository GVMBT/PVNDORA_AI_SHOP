import React from 'react'
import { useLocale } from '../hooks/useLocale'
import { ShoppingBag, Package, Trophy, User, Shield, ShoppingCart } from 'lucide-react'
import { cn } from '../lib/utils'
import { motion } from 'framer-motion'

const navItems = [
  { id: 'catalog', icon: ShoppingBag, labelKey: 'nav.catalog' },
  { id: 'checkout', icon: ShoppingCart, labelKey: 'nav.cart' },
  { id: 'orders', icon: Package, labelKey: 'nav.orders' },
  { id: 'profile', icon: User, labelKey: 'nav.profile' },
  { id: 'leaderboard', icon: Trophy, labelKey: 'nav.leaderboard' }
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
  
  const handleNavigate = (id) => {
    if (window.Telegram?.WebApp?.HapticFeedback) {
      window.Telegram.WebApp.HapticFeedback.impactOccurred('light')
    }
    onNavigate(id)
  }

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 p-4 pb-6 safe-area-bottom pointer-events-none">
      <nav className="pointer-events-auto mx-auto max-w-md bg-background/80 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl shadow-black/50">
        <div className="flex justify-around items-center h-16 px-2">
          {items.map((item) => {
            const isActive = currentPage === item.id
            const label = item.label || (item.labelKey ? t(item.labelKey) : '')
            const Icon = item.icon
            
            return (
              <button
                key={item.id}
                onClick={() => handleNavigate(item.id)}
                className="relative flex flex-col items-center justify-center flex-1 h-full group"
              >
                {isActive && (
                  <motion.div
                    layoutId="nav-pill"
                    className="absolute inset-x-2 top-2 bottom-2 bg-primary/15 rounded-xl"
                    transition={{ type: "spring", bounce: 0.2, duration: 0.6 }}
                  />
                )}
                
                <motion.div
                  whileTap={{ scale: 0.8 }}
                  transition={{ duration: 0.1 }}
                  className="relative z-10 flex flex-col items-center gap-1"
                >
                  <div className={cn(
                    "relative transition-all duration-300",
                    isActive ? "text-primary -translate-y-1" : "text-muted-foreground group-hover:text-foreground"
                  )}>
                    <Icon 
                      className={cn("w-6 h-6 transition-all duration-300", isActive && "fill-primary/20")} 
                      strokeWidth={isActive ? 2.5 : 2} 
                    />
                    {isActive && (
                      <motion.div
                        initial={{ opacity: 0, scale: 0 }}
                        animate={{ opacity: 1, scale: 1 }}
                        className="absolute -top-1 -right-1 w-2 h-2 bg-primary rounded-full shadow-[0_0_8px_rgba(0,245,212,0.6)]"
                      />
                    )}
                  </div>
                  
                  <span className={cn(
                    "text-[10px] font-medium transition-all duration-300",
                    isActive ? "text-primary translate-y-0" : "text-muted-foreground opacity-70 group-hover:opacity-100"
                  )}>
                    {label}
                  </span>
                </motion.div>
              </button>
            )
          })}
        </div>
      </nav>
    </div>
  )
}
