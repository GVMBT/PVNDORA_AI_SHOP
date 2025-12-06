import React, { useEffect } from 'react'
import { useLocale } from '../hooks/useLocale'
import { useTelegram } from '../hooks/useTelegram'
import { ArrowLeft, MessageCircle, Mail, Clock } from 'lucide-react'
import { Button } from '../components/ui/button'
import { Card, CardContent } from '../components/ui/card'

export default function ContactsPage({ onBack }) {
  const { t } = useLocale()
  const { setBackButton } = useTelegram()
  
  useEffect(() => {
    setBackButton({
      isVisible: true,
      onClick: onBack
    })
    
    return () => {
      setBackButton({ isVisible: false })
    }
  }, [])
  
  return (
    <div className="pb-20">
      {/* Header */}
      <div className="sticky top-0 z-10 bg-background/80 backdrop-blur-md border-b border-border/50 p-4 flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={onBack} className="h-8 w-8 rounded-full">
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <span className="font-semibold">{t('contacts.title')}</span>
      </div>
      
      <div className="p-4 space-y-4">
        {/* Hero Section */}
        <div className="text-center py-8 stagger-enter">
          <h1 className="text-2xl font-bold mb-2">{t('contacts.subtitle')}</h1>
          <p className="text-muted-foreground">{t('contacts.supportDescription')}</p>
        </div>

        {/* Support Action */}
        <Card className="stagger-enter" style={{ animationDelay: '0.1s' }}>
          <CardContent className="p-6 flex flex-col items-center text-center gap-4">
            <div className="p-4 rounded-full bg-primary/10 text-primary">
              <MessageCircle className="h-8 w-8" />
            </div>
            <div>
              <h3 className="font-semibold text-lg mb-1">{t('contacts.support')}</h3>
              <p className="text-sm text-muted-foreground mb-2">
                {t('contacts.contactHint') || "Напишите нам в Telegram"}
              </p>
              <a
                href="https://t.me/gvmbt158"
                target="_blank"
                rel="noopener noreferrer"
                className="block"
              >
                <Button className="w-full min-w-[200px]">
                  @gvmbt158
                </Button>
              </a>
            </div>
          </CardContent>
        </Card>
        
        {/* Email */}
        <Card className="stagger-enter" style={{ animationDelay: '0.2s' }}>
          <CardContent className="p-4 flex items-center gap-4">
            <div className="p-2 rounded-lg bg-secondary text-foreground">
              <Mail className="h-5 w-5" />
            </div>
            <div className="flex-1">
              <p className="text-sm text-muted-foreground">{t('contacts.email')}</p>
              <a 
                href={`mailto:${t('contacts.emailAddress')}`}
                className="font-medium text-primary hover:underline"
              >
                {t('contacts.emailAddress')}
              </a>
            </div>
          </CardContent>
        </Card>
        
        {/* Hours */}
        <Card className="stagger-enter" style={{ animationDelay: '0.3s' }}>
          <CardContent className="p-4 flex items-center gap-4">
            <div className="p-2 rounded-lg bg-secondary text-foreground">
              <Clock className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">{t('contacts.workingHours')}</p>
              <p className="font-medium">{t('contacts.workingHoursText')}</p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
