import React from 'react'
import { cn } from '../lib/utils'
import { 
  ShoppingBag, 
  Package, 
  Trophy, 
  User, 
  HelpCircle,
  Settings,
  Sparkles,
  ExternalLink
} from 'lucide-react'
import { Button } from './ui/button'

const NAV_ITEMS = [
  { id: 'catalog', label: 'Каталог', icon: ShoppingBag },
  { id: 'orders', label: 'Мои заказы', icon: Package },
  { id: 'leaderboard', label: 'Рейтинг', icon: Trophy },
  { id: 'profile', label: 'Профиль', icon: User },
  { id: 'faq', label: 'FAQ', icon: HelpCircle },
]

const ADMIN_ITEMS = [
  { id: 'admin', label: 'Админ панель', icon: Settings },
]

/**
 * Desktop Layout with sidebar navigation
 * Renders a responsive layout for desktop/web users
 */
export default function DesktopLayout({ 
  children, 
  currentPage, 
  onNavigate, 
  isAdmin,
  user 
}) {
  return (
    <div className="min-h-screen bg-background flex">
      {/* Sidebar */}
      <aside className="w-64 border-r border-border/50 bg-card/50 backdrop-blur-xl fixed h-screen flex flex-col">
        {/* Logo */}
        <div className="p-6 border-b border-border/50">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary/20 to-purple-500/20 flex items-center justify-center">
              <Sparkles className="h-5 w-5 text-primary" />
            </div>
            <div>
              <h1 className="text-xl font-bold bg-gradient-to-r from-primary to-purple-400 bg-clip-text text-transparent">
                PVNDORA
              </h1>
              <p className="text-xs text-muted-foreground">AI Marketplace</p>
            </div>
          </div>
        </div>
        
        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-1">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon
            const isActive = currentPage === item.id || 
              (item.id === 'catalog' && currentPage === 'product')
            
            return (
              <button
                key={item.id}
                onClick={() => onNavigate(item.id)}
                className={cn(
                  "w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all",
                  isActive 
                    ? "bg-primary/10 text-primary" 
                    : "text-muted-foreground hover:text-foreground hover:bg-secondary/50"
                )}
              >
                <Icon className="h-5 w-5" />
                {item.label}
              </button>
            )
          })}
          
          {isAdmin && (
            <>
              <div className="pt-4 pb-2">
                <p className="px-4 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Администрирование
                </p>
              </div>
              {ADMIN_ITEMS.map((item) => {
                const Icon = item.icon
                const isActive = currentPage.startsWith('admin')
                
                return (
                  <button
                    key={item.id}
                    onClick={() => onNavigate(item.id)}
                    className={cn(
                      "w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all",
                      isActive 
                        ? "bg-purple-500/10 text-purple-400" 
                        : "text-muted-foreground hover:text-foreground hover:bg-secondary/50"
                    )}
                  >
                    <Icon className="h-5 w-5" />
                    {item.label}
                  </button>
                )
              })}
            </>
          )}
        </nav>
        
        {/* User Info / CTA */}
        <div className="p-4 border-t border-border/50">
          {user ? (
            <div className="flex items-center gap-3 px-2">
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-primary to-purple-500 flex items-center justify-center text-sm font-bold">
                {user.first_name?.[0] || user.username?.[0] || '?'}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{user.first_name || user.username}</p>
                <p className="text-xs text-muted-foreground truncate">@{user.username}</p>
              </div>
            </div>
          ) : (
            <Button 
              className="w-full gap-2"
              onClick={() => window.open('https://t.me/pvndora_ai_bot', '_blank')}
            >
              <ExternalLink className="h-4 w-4" />
              Открыть в Telegram
            </Button>
          )}
        </div>
      </aside>
      
      {/* Main Content */}
      <main className="flex-1 ml-64">
        <div className="max-w-5xl mx-auto p-8">
          {children}
        </div>
      </main>
    </div>
  )
}

