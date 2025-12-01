import React, { useState, useEffect } from 'react'
import { useFAQ } from '../hooks/useApi'
import { useLocale } from '../hooks/useLocale'
import { useTelegram } from '../hooks/useTelegram'
import { ArrowLeft, HelpCircle, MessageCircle, ChevronDown } from 'lucide-react'
import { Button } from '../components/ui/button'
import { Card, CardContent } from '../components/ui/card'
import { Skeleton } from '../components/ui/skeleton'
import { cn } from '../lib/utils'

export default function FAQPage({ onBack, onNavigate }) {
  const { getFAQ, loading, error } = useFAQ()
  const { t, locale } = useLocale()
  const { setBackButton } = useTelegram()
  
  const [faqItems, setFaqItems] = useState([])
  const [expandedId, setExpandedId] = useState(null)
  
  useEffect(() => {
    loadFAQ()
    
    setBackButton({
      isVisible: true,
      onClick: onBack
    })
    
    return () => {
      setBackButton({ isVisible: false })
    }
  }, [locale])
  
  const loadFAQ = async () => {
    try {
      const data = await getFAQ(locale)
      setFaqItems(data.faq || [])
    } catch (err) {
      console.error('Failed to load FAQ:', err)
    }
  }
  
  const groupedFAQ = faqItems.reduce((acc, item) => {
    const category = item.category || 'general'
    if (!acc[category]) acc[category] = []
    acc[category].push(item)
    return acc
  }, {})
  
  return (
    <div className="pb-20">
      {/* Header */}
      <div className="sticky top-0 z-10 bg-background/80 backdrop-blur-md border-b border-border/50 p-4 flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={onBack} className="h-8 w-8 rounded-full">
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <span className="font-semibold">{t('faq.title')}</span>
      </div>
      
      <div className="p-4 space-y-6">
        {/* Hero */}
        <div className="text-center py-6 stagger-enter">
          <h1 className="text-2xl font-bold mb-2">{t('faq.subtitle')}</h1>
          <p className="text-muted-foreground text-sm">
            Find answers to common questions below
          </p>
        </div>
        
        {/* FAQ List */}
        {loading ? (
          <div className="space-y-4">
            {[1, 2, 3, 4].map((i) => (
              <Skeleton key={i} className="h-16 w-full rounded-xl" />
            ))}
          </div>
        ) : error ? (
          <div className="text-center py-8 text-destructive">
            <p>{error}</p>
            <Button onClick={loadFAQ} variant="outline" className="mt-4">
              {t('common.retry')}
            </Button>
          </div>
        ) : faqItems.length === 0 ? (
          <div className="text-center py-12 text-muted-foreground">
            <HelpCircle className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>{t('faq.empty')}</p>
          </div>
        ) : (
          <div className="space-y-6">
            {Object.entries(groupedFAQ).map(([category, items], catIndex) => (
              <div key={category} className="stagger-enter" style={{ animationDelay: `${catIndex * 0.1}s` }}>
                <h2 className="text-sm font-semibold text-primary uppercase tracking-wider mb-3 pl-1">
                  {t(`faq.category.${category}`) || category}
                </h2>
                <div className="space-y-3">
                  {items.map((item) => (
                    <Card 
                      key={item.id}
                      className={cn(
                        "cursor-pointer transition-all duration-200 hover:border-primary/50",
                        expandedId === item.id && "border-primary shadow-lg shadow-primary/5"
                      )}
                      onClick={() => setExpandedId(expandedId === item.id ? null : item.id)}
                    >
                      <CardContent className="p-4">
                        <div className="flex justify-between items-start gap-3">
                          <h3 className="font-medium text-sm leading-snug">
                            {item.question}
                          </h3>
                          <ChevronDown 
                            className={cn(
                              "h-4 w-4 shrink-0 text-muted-foreground transition-transform duration-200",
                              expandedId === item.id && "rotate-180 text-primary"
                            )} 
                          />
                        </div>
                        {expandedId === item.id && (
                          <div className="mt-3 pt-3 border-t border-border/50 text-sm text-muted-foreground leading-relaxed whitespace-pre-wrap animate-in slide-in-from-top-2 fade-in duration-200">
                            {item.answer}
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
        
        {/* Support CTA */}
        <Card className="bg-primary/5 border-primary/20 stagger-enter">
          <CardContent className="p-6 text-center space-y-4">
            <div className="p-3 rounded-full bg-primary/10 text-primary w-fit mx-auto">
              <MessageCircle className="h-6 w-6" />
            </div>
            <div>
              <h3 className="font-semibold mb-1">{t('faq.stillNeedHelp')}</h3>
              <p className="text-sm text-muted-foreground">{t('faq.contactHint')}</p>
            </div>
            <Button onClick={() => window.Telegram?.WebApp?.close()}>
              {t('faq.askBot')}
            </Button>
          </CardContent>
        </Card>
        
        {/* Legal Links */}
        {onNavigate && (
          <div className="flex flex-wrap justify-center gap-x-4 gap-y-2 text-xs text-muted-foreground pt-4">
            {['contacts', 'refund', 'payment', 'terms', 'privacy'].map((link) => (
              <button
                key={link}
                onClick={() => onNavigate(link)}
                className="hover:text-primary hover:underline transition-colors"
              >
                {t(`legal.${link}`)}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
