import React from 'react'
import { Sparkles, ExternalLink, Send, MessageCircle, Shield, FileText, Scale } from 'lucide-react'

/**
 * Footer component with social links, legal info, and copyright
 */
export default function Footer({ onNavigate }) {
  const currentYear = new Date().getFullYear()
  
  const socialLinks = [
    { 
      icon: Send, 
      label: 'Telegram Channel', 
      href: 'https://t.me/pvndora_news' 
    },
    { 
      icon: MessageCircle, 
      label: 'Support', 
      href: 'https://t.me/gvmbt158' 
    },
  ]
  
  const legalLinks = [
    { label: 'Условия использования', page: 'terms' },
    { label: 'Политика конфиденциальности', page: 'privacy' },
    { label: 'Политика возврата', page: 'refund' },
    { label: 'Способы оплаты', page: 'payment' },
  ]
  
  return (
    <footer className="border-t border-border/50 bg-card/30 backdrop-blur-xl mt-auto">
      <div className="max-w-5xl mx-auto px-6 py-12">
        {/* Top Section */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-8">
          {/* Brand */}
          <div>
            <div className="flex items-center gap-2 mb-4">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary/20 to-purple-500/20 flex items-center justify-center">
                <Sparkles className="h-4 w-4 text-primary" />
              </div>
              <span className="text-lg font-bold">PVNDORA</span>
            </div>
            <p className="text-sm text-muted-foreground leading-relaxed">
              Премиум AI подписки по лучшим ценам. Моментальная доставка, гарантия качества, поддержка 24/7.
            </p>
          </div>
          
          {/* Social Links */}
          <div>
            <h3 className="font-semibold mb-4">Связаться с нами</h3>
            <div className="space-y-3">
              {socialLinks.map((link) => (
                <a
                  key={link.label}
                  href={link.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
                >
                  <link.icon className="h-4 w-4" />
                  {link.label}
                  <ExternalLink className="h-3 w-3 opacity-50" />
                </a>
              ))}
            </div>
          </div>
          
          {/* Legal Links */}
          <div>
            <h3 className="font-semibold mb-4">Информация</h3>
            <div className="space-y-3">
              {legalLinks.map((link) => (
                <button
                  key={link.page}
                  onClick={() => onNavigate?.(link.page)}
                  className="block text-sm text-muted-foreground hover:text-foreground transition-colors text-left"
                >
                  {link.label}
                </button>
              ))}
            </div>
          </div>
        </div>
        
        {/* Divider */}
        <div className="border-t border-border/50 pt-6">
          <div className="flex flex-col md:flex-row justify-between items-center gap-4">
            {/* Copyright */}
            <p className="text-xs text-muted-foreground">
              © {currentYear} PVNDORA. Все права защищены.
            </p>
            
            {/* Trust badges */}
            <div className="flex items-center gap-4 text-xs text-muted-foreground">
              <div className="flex items-center gap-1">
                <Shield className="h-3.5 w-3.5 text-green-500" />
                <span>Безопасные платежи</span>
              </div>
              <div className="flex items-center gap-1">
                <Scale className="h-3.5 w-3.5 text-blue-500" />
                <span>Гарантия качества</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </footer>
  )
}

