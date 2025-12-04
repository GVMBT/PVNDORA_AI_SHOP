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
  LogIn,
  Send,
  MessageCircle,
  ExternalLink,
  Shield,
  Scale
} from 'lucide-react'
import { Button } from './ui/button'

const NAV_ITEMS = [
  { id: 'catalog', label: 'Каталог', icon: ShoppingBag },
  { id: 'orders', label: 'Мои заказы', icon: Package, requiresAuth: true },
  { id: 'leaderboard', label: 'Рейтинг', icon: Trophy },
  { id: 'profile', label: 'Профиль', icon: User, requiresAuth: true },
  { id: 'faq', label: 'FAQ', icon: HelpCircle },
]

const ADMIN_ITEMS = [
  { id: 'admin', label: 'Админ панель', icon: Settings },
]

const SOCIAL_LINKS = [
  { icon: Send, label: 'Telegram', href: 'https://t.me/pvndora_news' },
  { icon: MessageCircle, label: 'Поддержка', href: 'https://t.me/pvndora_support' },
]

const LEGAL_LINKS = [
  { label: 'Условия', page: 'terms' },
  { label: 'Конфиденциальность', page: 'privacy' },
  { label: 'Возврат', page: 'refund' },
  { label: 'Оплата', page: 'payment' },
]

/**
 * Desktop Layout with sidebar navigation and footer
 * Renders a responsive layout for desktop/web users
 */
export default function DesktopLayout({ 
  children, 
  currentPage, 
  onNavigate, 
  isAdmin,
  user,
  onLogin
}) {
  const currentYear = new Date().getFullYear()
  
  const handleNavClick = (item) => {
    if (item.requiresAuth && !user) {
      // Show login prompt for protected pages
      onLogin?.()
      return
    }
    onNavigate(item.id)
  }
  
  return (
    <div className="min-h-screen bg-background flex flex-col">
      <div className="flex flex-1">
        {/* Sidebar */}
        <aside className="w-64 border-r border-border/50 bg-card/50 backdrop-blur-xl fixed h-screen flex flex-col z-40">
          {/* Logo */}
          <div className="p-6 border-b border-border/50">
            <button 
              onClick={() => onNavigate('catalog')}
              className="flex items-center gap-3 hover:opacity-80 transition-opacity"
            >
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary/20 to-purple-500/20 flex items-center justify-center">
                <Sparkles className="h-5 w-5 text-primary" />
              </div>
              <div>
                <h1 className="text-xl font-bold bg-gradient-to-r from-primary to-purple-400 bg-clip-text text-transparent">
                  PVNDORA
                </h1>
                <p className="text-xs text-muted-foreground">AI Marketplace</p>
              </div>
            </button>
          </div>
          
          {/* Navigation */}
          <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
            {NAV_ITEMS.map((item) => {
              const Icon = item.icon
              const isActive = currentPage === item.id || 
                (item.id === 'catalog' && currentPage === 'product')
              const isDisabled = item.requiresAuth && !user
              
              return (
                <button
                  key={item.id}
                  onClick={() => handleNavClick(item)}
                  className={cn(
                    "w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all",
                    isActive 
                      ? "bg-primary/10 text-primary" 
                      : isDisabled
                        ? "text-muted-foreground/50 cursor-not-allowed"
                        : "text-muted-foreground hover:text-foreground hover:bg-secondary/50"
                  )}
                >
                  <Icon className="h-5 w-5" />
                  {item.label}
                  {isDisabled && <span className="ml-auto text-[10px] opacity-50">🔒</span>}
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
          
          {/* User Info / Login */}
          <div className="p-4 border-t border-border/50">
            {user ? (
              <div className="flex items-center gap-3 px-2">
                <div className="w-10 h-10 rounded-full bg-gradient-to-br from-primary to-purple-500 flex items-center justify-center text-sm font-bold text-white">
                  {user.first_name?.[0] || user.username?.[0] || '?'}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{user.first_name || user.username}</p>
                  <p className="text-xs text-muted-foreground truncate">
                    {user.username ? `@${user.username}` : 'Авторизован'}
                  </p>
                </div>
              </div>
            ) : (
              <div className="space-y-2">
                <Button 
                  className="w-full gap-2"
                  onClick={onLogin}
                >
                  <LogIn className="h-4 w-4" />
                  Войти через Telegram
                </Button>
                <p className="text-[10px] text-muted-foreground text-center">
                  Для заказов и профиля
                </p>
              </div>
            )}
          </div>
        </aside>
        
        {/* Main Content */}
        <main className="flex-1 ml-64 flex flex-col min-h-screen">
          <div className="flex-1 max-w-5xl mx-auto p-8 w-full">
            {children}
          </div>
          
          {/* Footer */}
          <footer className="border-t border-border/50 bg-card/30 mt-auto">
            <div className="max-w-5xl mx-auto px-8 py-8">
              <div className="grid grid-cols-4 gap-8 mb-6">
                {/* Brand */}
                <div className="col-span-2">
                  <div className="flex items-center gap-2 mb-3">
                    <Sparkles className="h-4 w-4 text-primary" />
                    <span className="font-bold">PVNDORA</span>
                  </div>
                  <p className="text-xs text-muted-foreground leading-relaxed max-w-sm">
                    Премиум AI подписки: ChatGPT Plus, Gemini Pro, Claude Pro. 
                    Моментальная доставка, гарантия качества.
                  </p>
                </div>
                
                {/* Social */}
                <div>
                  <h4 className="text-xs font-semibold mb-3 uppercase tracking-wider text-muted-foreground">
                    Связь
                  </h4>
                  <div className="space-y-2">
                    {SOCIAL_LINKS.map((link) => (
                      <a
                        key={link.label}
                        href={link.href}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground transition-colors"
                      >
                        <link.icon className="h-3.5 w-3.5" />
                        {link.label}
                      </a>
                    ))}
                  </div>
                </div>
                
                {/* Legal */}
                <div>
                  <h4 className="text-xs font-semibold mb-3 uppercase tracking-wider text-muted-foreground">
                    Информация
                  </h4>
                  <div className="space-y-2">
                    {LEGAL_LINKS.map((link) => (
                      <button
                        key={link.page}
                        onClick={() => onNavigate(link.page)}
                        className="block text-xs text-muted-foreground hover:text-foreground transition-colors"
                      >
                        {link.label}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
              
              {/* Bottom bar */}
              <div className="border-t border-border/50 pt-4 flex justify-between items-center">
                <p className="text-[10px] text-muted-foreground">
                  © {currentYear} PVNDORA. Все права защищены.
                </p>
                <div className="flex items-center gap-4 text-[10px] text-muted-foreground">
                  <div className="flex items-center gap-1">
                    <Shield className="h-3 w-3 text-green-500" />
                    <span>Безопасные платежи</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <Scale className="h-3 w-3 text-blue-500" />
                    <span>Гарантия</span>
                  </div>
                </div>
              </div>
            </div>
          </footer>
        </main>
      </div>
    </div>
  )
}
