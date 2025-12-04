import React from 'react'
import { useLocale } from '../hooks/useLocale'
import { Package, BarChart2, Settings, HelpCircle, MessageSquare, Database, LogOut, Users } from 'lucide-react'
import { Card, CardContent } from '../components/ui/card'
import { Button } from '../components/ui/button'

export default function AdminPage({ onNavigate }) {
  const { t } = useLocale()

  const sections = [
    { id: 'products', icon: Package, label: 'Products', desc: 'Manage catalog & prices' },
    { id: 'stock', icon: Database, label: 'Stock', desc: 'Inventory management' },
    { id: 'orders', icon: BarChart2, label: 'Orders', desc: 'View & manage orders' },
    { id: 'referral', icon: Users, label: 'Referrals', desc: 'Partners, ROI & settings' },
    { id: 'tickets', icon: MessageSquare, label: 'Tickets', desc: 'Support requests' },
    { id: 'analytics', icon: BarChart2, label: 'Analytics', desc: 'Sales & performance' },
    { id: 'faq', icon: HelpCircle, label: 'FAQ', desc: 'Manage common questions' }
  ]

  return (
    <div className="p-4 space-y-6 pb-20">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">
          Admin Panel
        </h1>
        <Button 
          variant="ghost" 
          size="icon" 
          onClick={() => onNavigate('catalog')}
          className="text-destructive hover:text-destructive hover:bg-destructive/10"
        >
          <LogOut className="h-5 w-5" />
        </Button>
      </div>

      <div className="grid gap-4">
        {sections.map((section) => {
          const Icon = section.icon
          return (
            <Card 
              key={section.id}
              className="cursor-pointer hover:border-primary transition-all bg-card/50 backdrop-blur-sm"
              onClick={() => onNavigate(`admin_${section.id}`)}
            >
              <CardContent className="p-4 flex items-center gap-4">
                <div className="p-3 rounded-xl bg-primary/10 text-primary">
                  <Icon className="h-6 w-6" />
                </div>
                <div className="flex-1">
                  <h3 className="font-semibold text-lg mb-0.5">
                    {section.label}
                  </h3>
                  <p className="text-sm text-muted-foreground">
                    {section.desc}
                  </p>
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>
      
      <Button 
        variant="outline" 
        className="w-full mt-8 border-destructive/50 text-destructive hover:bg-destructive/10 hover:text-destructive"
        onClick={() => onNavigate('catalog')}
      >
        Exit Admin Mode
      </Button>
    </div>
  )
}
