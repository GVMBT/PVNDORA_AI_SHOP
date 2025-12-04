import React, { useEffect, useRef, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card'
import { Button } from '../components/ui/button'
import { Loader2, Monitor, Smartphone, ArrowRight } from 'lucide-react'

/**
 * Login Page for Desktop/Web access
 * Uses Telegram Login Widget for authentication
 */
export default function LoginPage({ onLogin, botUsername = 'pvndora_ai_bot' }) {
  const widgetRef = useRef(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  
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
    script.setAttribute('data-radius', '8')
    script.setAttribute('data-request-access', 'write')
    script.setAttribute('data-userpic', 'true')
    script.setAttribute('data-onauth', 'onTelegramAuth(user)')
    script.async = true
    
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
          const data = await response.json()
          throw new Error(data.detail || 'Authentication failed')
        }
        
        const { session_token, user: userData } = await response.json()
        
        // Store session token
        localStorage.setItem('pvndora_session', session_token)
        localStorage.setItem('pvndora_user', JSON.stringify(userData))
        
        // Notify parent
        onLogin?.(userData, session_token)
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
            Войдите через Telegram для доступа к панели управления
          </CardDescription>
        </CardHeader>
        
        <CardContent className="space-y-6">
          {/* Telegram Login Widget */}
          <div className="flex justify-center">
            {loading ? (
              <div className="flex items-center gap-2 text-muted-foreground">
                <Loader2 className="h-5 w-5 animate-spin" />
                <span>Авторизация...</span>
              </div>
            ) : (
              <div ref={widgetRef} className="telegram-login-widget" />
            )}
          </div>
          
          {error && (
            <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg text-center">
              <p className="text-destructive text-sm">{error}</p>
            </div>
          )}
          
          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <span className="w-full border-t" />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-card px-2 text-muted-foreground">или</span>
            </div>
          </div>
          
          {/* Alternative: Open in Telegram */}
          <Button 
            variant="outline" 
            className="w-full gap-2"
            onClick={openInTelegram}
          >
            <Smartphone className="h-4 w-4" />
            Открыть в Telegram
            <ArrowRight className="h-4 w-4 ml-auto" />
          </Button>
          
          {/* Info */}
          <div className="text-center space-y-2">
            <div className="flex items-center justify-center gap-2 text-xs text-muted-foreground">
              <Monitor className="h-4 w-4" />
              <span>Веб-версия для администраторов</span>
            </div>
            <p className="text-xs text-muted-foreground">
              Для полного функционала используйте Telegram Mini App
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

