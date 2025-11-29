import React, { useState, useEffect } from 'react'
import { useFAQ } from '../hooks/useApi'
import { useLocale } from '../hooks/useLocale'
import { useTelegram } from '../hooks/useTelegram'

export default function FAQPage({ onBack }) {
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
  
  const toggleExpanded = (id) => {
    setExpandedId(expandedId === id ? null : id)
  }
  
  // Group by category
  const groupedFAQ = faqItems.reduce((acc, item) => {
    const category = item.category || 'general'
    if (!acc[category]) acc[category] = []
    acc[category].push(item)
    return acc
  }, {})
  
  return (
    <div className="p-4">
      {/* Header */}
      <header className="mb-6 stagger-enter">
        <h1 className="text-2xl font-bold text-[var(--color-text)]">
          ❓ {t('faq.title')}
        </h1>
        <p className="text-[var(--color-text-muted)]">
          {t('faq.subtitle')}
        </p>
      </header>
      
      {/* FAQ list */}
      {loading ? (
        <div className="space-y-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="card h-20 skeleton" />
          ))}
        </div>
      ) : error ? (
        <div className="card text-center py-8">
          <p className="text-[var(--color-error)] mb-4">{error}</p>
          <button onClick={loadFAQ} className="btn btn-secondary">
            {t('common.retry')}
          </button>
        </div>
      ) : faqItems.length === 0 ? (
        <div className="card text-center py-12 stagger-enter">
          <span className="text-5xl mb-4 block">📚</span>
          <h3 className="text-lg font-semibold text-[var(--color-text)] mb-2">
            {t('faq.empty')}
          </h3>
          <p className="text-[var(--color-text-muted)]">
            {t('faq.emptyHint')}
          </p>
        </div>
      ) : (
        <div className="space-y-6">
          {Object.entries(groupedFAQ).map(([category, items]) => (
            <div key={category} className="stagger-enter">
              {/* Category header */}
              <h2 className="text-lg font-semibold text-[var(--color-primary)] mb-3 capitalize">
                {t(`faq.category.${category}`) || category}
              </h2>
              
              {/* FAQ items */}
              <div className="space-y-3">
                {items.map((item, index) => (
                  <div
                    key={item.id}
                    className="card cursor-pointer"
                    onClick={() => toggleExpanded(item.id)}
                  >
                    {/* Question */}
                    <div className="flex items-start justify-between gap-3">
                      <h3 className="font-medium text-[var(--color-text)] flex-1">
                        {item.question}
                      </h3>
                      <span className={`text-[var(--color-text-muted)] transition-transform ${
                        expandedId === item.id ? 'rotate-180' : ''
                      }`}>
                        ▼
                      </span>
                    </div>
                    
                    {/* Answer */}
                    {expandedId === item.id && (
                      <div className="mt-3 pt-3 border-t border-[var(--color-border)]">
                        <p className="text-[var(--color-text-muted)] whitespace-pre-wrap">
                          {item.answer}
                        </p>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
      
      {/* Contact support */}
      <div className="card mt-6 text-center stagger-enter">
        <span className="text-3xl mb-2 block">💬</span>
        <h3 className="font-semibold text-[var(--color-text)] mb-2">
          {t('faq.stillNeedHelp')}
        </h3>
        <p className="text-[var(--color-text-muted)] text-sm mb-4">
          {t('faq.contactHint')}
        </p>
        <button 
          onClick={() => window.Telegram?.WebApp?.close()}
          className="btn btn-primary"
        >
          {t('faq.askBot')}
        </button>
      </div>
    </div>
  )
}

