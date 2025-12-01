import React, { useEffect } from 'react'
import { useLocale } from '../hooks/useLocale'
import { useTelegram } from '../hooks/useTelegram'
import { ArrowLeft, CreditCard, Lock, HelpCircle, Activity } from 'lucide-react'
import { Button } from '../components/ui/button'
import { Card, CardContent } from '../components/ui/card'

export default function PaymentInfoPage({ onBack }) {
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
  
  const sections = [
    { id: 'methods', icon: CreditCard },
    { id: 'process', icon: Activity },
    { id: 'security', icon: Lock }
  ]
  
  return (
    <div className="pb-20">
      <div className="sticky top-0 z-10 bg-background/80 backdrop-blur-md border-b border-border/50 p-4 flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={onBack} className="h-8 w-8 rounded-full">
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <span className="font-semibold">{t('paymentInfo.title')}</span>
      </div>
      
      <div className="p-4 space-y-6">
        <div className="text-center py-4 stagger-enter">
          <h1 className="text-2xl font-bold mb-2">{t('paymentInfo.title')}</h1>
          <p className="text-muted-foreground">{t('paymentInfo.subtitle')}</p>
        </div>
        
        {sections.map((section, index) => {
          const Icon = section.icon
          return (
            <Card key={section.id} className="stagger-enter" style={{ animationDelay: `${index * 0.1}s` }}>
              <CardContent className="p-6 space-y-3">
                <div className="flex items-center gap-3 mb-2">
                  <div className="p-2 rounded-lg bg-primary/10 text-primary">
                    <Icon className="h-5 w-5" />
                  </div>
                  <h3 className="font-semibold text-lg">
                    {t(`paymentInfo.${section.id}`)}
                  </h3>
                </div>
                <div className="text-sm text-muted-foreground whitespace-pre-wrap leading-relaxed pl-12">
                  {t(`paymentInfo.${section.id}Text`)}
                </div>
              </CardContent>
            </Card>
          )
        })}
        
        <Card className="bg-secondary/30 border-none stagger-enter">
          <CardContent className="p-6 text-center space-y-4">
            <div className="mx-auto p-3 rounded-full bg-background w-fit">
              <HelpCircle className="h-6 w-6 text-muted-foreground" />
            </div>
            <div>
              <h3 className="font-semibold mb-1">{t('paymentInfo.questions')}</h3>
              <p className="text-sm text-muted-foreground">{t('paymentInfo.questionsText')}</p>
            </div>
            <Button onClick={() => window.Telegram?.WebApp?.close()} variant="outline" className="w-full">
              {t('paymentInfo.contactSupport')}
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
