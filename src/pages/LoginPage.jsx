import React, { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card'
import { Button } from '../components/ui/button'
import { Loader2, Monitor, Smartphone, ArrowRight, AlertCircle } from 'lucide-react'

/**
 * Login Page for Desktop/Web access
 * 
 * NOTE: Telegram Login Widget requires domain to be configured in BotFather:
 * /mybots -> @pvndora_ai_bot -> Bot Settings -> Domain -> Add domain
 * 
 * For now, redirects users to Telegram Mini App.
 */
export default function LoginPage({ botUsername = 'pvndora_ai_bot' }) {
  const [loading] = useState(false)
  
  const openInTelegram = () => {
    // Deep link to Mini App
    window.location.href = `https://t.me/${botUsername}/app`
  }
  
  const openBot = () => {
    window.open(`https://t.me/${botUsername}`, '_blank')
  }
  
  return (
    <div className="min-h-screen bg-gradient-animated flex items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="mx-auto mb-4 w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center">
            <span className="text-3xl">🔐</span>
          </div>
          <CardTitle className="text-2xl">PVNDORA Admin</CardTitle>
          <CardDescription>
            Панель управления доступна только через Telegram
          </CardDescription>
        </CardHeader>
        
        <CardContent className="space-y-6">
          {/* Info about web access */}
          <div className="p-4 bg-amber-500/10 border border-amber-500/20 rounded-lg">
            <div className="flex gap-3">
              <AlertCircle className="h-5 w-5 text-amber-500 flex-shrink-0 mt-0.5" />
              <div className="space-y-1">
                <p className="text-sm font-medium text-amber-500">Веб-доступ ограничен</p>
                <p className="text-xs text-muted-foreground">
                  Для безопасности админ-панель работает только внутри Telegram Mini App.
                </p>
              </div>
            </div>
          </div>
          
          {/* Primary CTA: Open Mini App */}
          <Button 
            className="w-full gap-2 h-12"
            onClick={openInTelegram}
            disabled={loading}
          >
            {loading ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              <>
                <Smartphone className="h-5 w-5" />
                Открыть Mini App
                <ArrowRight className="h-4 w-4 ml-auto" />
              </>
            )}
          </Button>
          
          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <span className="w-full border-t" />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-card px-2 text-muted-foreground">или</span>
            </div>
          </div>
          
          {/* Secondary: Open bot */}
          <Button 
            variant="outline" 
            className="w-full gap-2"
            onClick={openBot}
          >
            Написать боту
          </Button>
          
          {/* Info */}
          <div className="text-center space-y-2">
            <div className="flex items-center justify-center gap-2 text-xs text-muted-foreground">
              <Monitor className="h-4 w-4" />
              <span>Десктоп-версия в разработке</span>
            </div>
            <p className="text-xs text-muted-foreground">
              Скоро: авторизация через Telegram Login Widget
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

