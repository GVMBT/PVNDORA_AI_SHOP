import React, { useEffect, useRef, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card'
import { Button } from '../components/ui/button'
import { Loader2, Smartphone, ArrowRight, ShieldCheck, Sparkles } from 'lucide-react'

/**
 * Login Page for Desktop/Web access
 * Uses Telegram Login Widget for authentication
 * 
 * Domain must be configured in BotFather:
 * /mybots -> @pvndora_ai_bot -> Bot Settings -> Domain -> pvndora.app
 */
export default function LoginPage({ onLogin, botUsername = 'pvndora_ai_bot' }) {
  const widgetRef = useRef(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [widgetReady, setWidgetReady] = useState(false)
  
  useEffect(() => {
    // Clear any previous widget
    if (widgetRef.current) {
      widgetRef.current.innerHTML = ''
    }
    
    // Create Telegram Login Widget script
    const script = document.createElement('script')
    script.src = 'https://telegram.org/js/telegram-widget.js?22'
    script.setAttribute('data-telegram-login', botUsername)
    script.setAttribute('data-size', 'large')
    script.setAttribute('data-radius', '12')
    script.setAttribute('data-request-access', 'write')
    script.setAttribute('data-userpic', 'true')
    script.setAttribute('data-onauth', 'onTelegramAuth(user)')
    script.async = true
    
    script.onload = () => {
      setWidgetReady(true)
    }
    
    script.onerror = () => {
      setError('Не удалось загрузить виджет Telegram')
    }
    
    // Global callback function for widget
    window.onTelegramAuth = async (user) => {
      console.log('Telegram auth callback:', user)
      setLoading(true)
      setError(null)
      
      try {
        // Send auth data to backend for verification
        const response = await fetch('/api/webapp/auth/telegram-login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(user)
        })
        
        if (!response.ok) {
          const data = await response.json().catch(() => ({}))
          throw new Error(data.detail || 'Authentication failed')
        }
        
        const { session_token, user: userData } = await response.json()
        
        // Store session token
        localStorage.setItem('pvndora_session', session_token)
        localStorage.setItem('pvndora_user', JSON.stringify(userData))
        
        // Notify parent and redirect
        onLogin?.(userData, session_token)
        
        // Redirect to admin page after successful login
        if (userData.is_admin) {
          window.location.href = '/#admin'
        } else {
          window.location.href = '/#catalog'
        }
      } catch (err) {
        console.error('Auth error:', err)
        setError(err.message)
        setLoading(false)
      }
    }
    
    widgetRef.current?.appendChild(script)
    
    return () => {
      delete window.onTelegramAuth
    }
  }, [botUsername, onLogin])
  
  const openInTelegram = () => {
    window.location.href = `https://t.me/${botUsername}/app`
  }
  
  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-background to-primary/5 flex items-center justify-center p-4">
      {/* Background decorations */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-primary/10 rounded-full blur-3xl" />
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-purple-500/10 rounded-full blur-3xl" />
      </div>
      
      <Card className="w-full max-w-md relative z-10 border-border/50 bg-card/80 backdrop-blur-xl">
        <CardHeader className="text-center pb-2">
          <div className="mx-auto mb-4 w-20 h-20 rounded-2xl bg-gradient-to-br from-primary/20 to-purple-500/20 flex items-center justify-center border border-primary/20">
            <Sparkles className="h-10 w-10 text-primary" />
          </div>
          <CardTitle className="text-3xl font-bold bg-gradient-to-r from-primary to-purple-400 bg-clip-text text-transparent">
            PVNDORA
          </CardTitle>
          <CardDescription className="text-base mt-1">
            AI-Powered Digital Marketplace
          </CardDescription>
          <p className="text-xs text-muted-foreground mt-2">
            Премиум AI-подписки по лучшим ценам
          </p>
        </CardHeader>
        
        <CardContent className="space-y-6">
          {/* Telegram Login Widget */}
          <div className="flex flex-col items-center gap-4">
            {loading ? (
              <div className="flex items-center gap-2 text-muted-foreground py-4">
                <Loader2 className="h-5 w-5 animate-spin" />
                <span>Авторизация...</span>
              </div>
            ) : (
              <div ref={widgetRef} className="telegram-login-widget min-h-[40px]" />
            )}
            
            {!widgetReady && !error && !loading && (
              <div className="flex items-center gap-2 text-muted-foreground text-sm">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Загрузка виджета...</span>
              </div>
            )}
          </div>
          
          {error && (
            <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-xl text-center">
              <p className="text-destructive text-sm">{error}</p>
              <Button 
                variant="link" 
                size="sm" 
                onClick={() => window.location.reload()}
                className="mt-1"
              >
                Попробовать снова
              </Button>
            </div>
          )}
          
          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <span className="w-full border-t border-border/50" />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-card px-3 text-muted-foreground">или</span>
            </div>
          </div>
          
          {/* Alternative: Open Mini App */}
          <Button 
            variant="outline" 
            className="w-full gap-2 h-12 border-border/50"
            onClick={openInTelegram}
          >
            <Smartphone className="h-5 w-5" />
            Открыть в Telegram
            <ArrowRight className="h-4 w-4 ml-auto" />
          </Button>
          
          {/* Trust Badges */}
          <div className="flex items-center justify-center gap-4 pt-2">
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <ShieldCheck className="h-4 w-4 text-green-500" />
              <span>Безопасно</span>
            </div>
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <div className="w-4 h-4 rounded-full bg-blue-500/20 flex items-center justify-center">
                <span className="text-[10px]">✓</span>
              </div>
              <span>Telegram OAuth</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
