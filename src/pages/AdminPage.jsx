import React from 'react'
import { useLocale } from '../hooks/useLocale'
import { 
  Package, 
  BarChart2, 
  HelpCircle, 
  MessageSquare, 
  Database, 
  LogOut, 
  Users,
  ShoppingCart,
  TrendingUp,
  Headphones
} from 'lucide-react'
import { Card, CardContent } from '../components/ui/card'
import { Button } from '../components/ui/button'
import { Badge } from '../components/ui/badge'

export default function AdminPage({ onNavigate }) {
  const { t } = useLocale()

  // Grouped sections for better organization
  const sectionGroups = [
    {
      title: 'Каталог',
      description: 'Товары и остатки',
      sections: [
        { id: 'products', icon: Package, label: 'Товары', desc: 'Каталог и цены' },
        { id: 'stock', icon: Database, label: 'Склад', desc: 'Остатки и пополнение' }
      ]
    },
    {
      title: 'Продажи',
      description: 'Заказы и аналитика',
      sections: [
        { id: 'orders', icon: ShoppingCart, label: 'Заказы', desc: 'Управление заказами' },
        { id: 'analytics', icon: TrendingUp, label: 'Аналитика', desc: 'Продажи и метрики' }
      ]
    },
    {
      title: 'Партнёры',
      description: 'Реферальная система',
      badge: 'ROI',
      sections: [
        { id: 'referral', icon: Users, label: 'Рефералы', desc: 'CRM, настройки, ROI' }
      ]
    },
    {
      title: 'Поддержка',
      description: 'Обращения и FAQ',
      sections: [
        { id: 'tickets', icon: MessageSquare, label: 'Тикеты', desc: 'Обращения клиентов' },
        { id: 'faq', icon: HelpCircle, label: 'FAQ', desc: 'База знаний' }
      ]
    }
  ]

  return (
    <div className="p-4 space-y-6 pb-24">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Панель администратора</h1>
          <p className="text-sm text-muted-foreground">Управление магазином</p>
        </div>
        <Button 
          variant="ghost" 
          size="icon" 
          onClick={() => onNavigate('catalog')}
          className="text-destructive hover:text-destructive hover:bg-destructive/10"
        >
          <LogOut className="h-5 w-5" />
        </Button>
      </div>

      {/* Section Groups */}
      {sectionGroups.map((group, groupIndex) => (
        <div key={groupIndex} className="space-y-3">
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-semibold">{group.title}</h2>
            {group.badge && (
              <Badge variant="secondary" className="text-xs">{group.badge}</Badge>
            )}
          </div>
          <p className="text-xs text-muted-foreground -mt-1">{group.description}</p>
          
          <div className="grid gap-2">
            {group.sections.map((section) => {
              const Icon = section.icon
              return (
                <Card 
                  key={section.id}
                  className="cursor-pointer hover:border-primary/50 hover:bg-primary/5 transition-all bg-card/50 backdrop-blur-sm"
                  onClick={() => onNavigate(`admin_${section.id}`)}
                >
                  <CardContent className="p-3 flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-primary/10 text-primary">
                      <Icon className="h-5 w-5" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="font-medium text-sm">
                        {section.label}
                      </h3>
                      <p className="text-xs text-muted-foreground truncate">
                        {section.desc}
                      </p>
                    </div>
                  </CardContent>
                </Card>
              )
            })}
          </div>
        </div>
      ))}
      
      {/* Exit Button */}
      <Button 
        variant="outline" 
        className="w-full border-destructive/30 text-destructive hover:bg-destructive/10 hover:text-destructive"
        onClick={() => onNavigate('catalog')}
      >
        <LogOut className="h-4 w-4 mr-2" />
        Выйти из админки
      </Button>
    </div>
  )
}
