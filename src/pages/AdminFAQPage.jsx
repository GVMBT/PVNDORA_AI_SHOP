import React, { useState, useEffect } from 'react'
import { useAdmin } from '../hooks/useAdmin'
import { useTelegram } from '../hooks/useTelegram'
import { ArrowLeft, Plus, HelpCircle } from 'lucide-react'
import { Button } from '../components/ui/button'
import { Card, CardContent } from '../components/ui/card'
import { Input } from '../components/ui/input'
import { Badge } from '../components/ui/badge'
import { Skeleton } from '../components/ui/skeleton'

export default function AdminFAQPage({ onBack }) {
  const { getFAQ, createFAQ, loading } = useAdmin()
  const { showAlert, hapticFeedback } = useTelegram()
  
  const [faq, setFaq] = useState([])
  const [showForm, setShowForm] = useState(false)
  const [formData, setFormData] = useState({
    question: '',
    answer: '',
    language_code: 'ru',
    category: 'general'
  })

  useEffect(() => {
    loadFAQ()
  }, [])

  const loadFAQ = async () => {
    try {
      const data = await getFAQ()
      setFaq(data.faq || [])
    } catch (err) {
      await showAlert(`Error: ${err.message}`)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    hapticFeedback('impact', 'medium')

    try {
      await createFAQ(formData)
      await showAlert('FAQ created!')
      setShowForm(false)
      resetForm()
      loadFAQ()
    } catch (err) {
      await showAlert(`Error: ${err.message}`)
    }
  }

  const resetForm = () => {
    setFormData({
      question: '',
      answer: '',
      language_code: 'ru',
      category: 'general'
    })
  }

  if (showForm) {
    return (
      <div className="p-4 pb-20 space-y-6">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => { setShowForm(false); resetForm() }}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <h1 className="text-xl font-bold">Create FAQ</h1>
        </div>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">Question *</label>
            <Input
              value={formData.question}
              onChange={(e) => setFormData({...formData, question: e.target.value})}
              required
              placeholder="How do I pay?"
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Answer *</label>
            <textarea
              value={formData.answer}
              onChange={(e) => setFormData({...formData, answer: e.target.value})}
              required
              className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 min-h-[120px]"
              placeholder="You can pay via..."
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Language *</label>
              <select
                value={formData.language_code}
                onChange={(e) => setFormData({...formData, language_code: e.target.value})}
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <option value="ru">Русский</option>
                <option value="en">English</option>
                <option value="uk">Українська</option>
                <option value="de">Deutsch</option>
                <option value="es">Español</option>
              </select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Category</label>
              <select
                value={formData.category}
                onChange={(e) => setFormData({...formData, category: e.target.value})}
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <option value="general">General</option>
                <option value="payment">Payment</option>
                <option value="delivery">Delivery</option>
                <option value="warranty">Warranty</option>
              </select>
            </div>
          </div>

          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? 'Creating...' : 'Create FAQ'}
          </Button>
        </form>
      </div>
    )
  }

  return (
    <div className="p-4 pb-20 space-y-6">
      <div className="flex items-center justify-between sticky top-0 bg-background/80 backdrop-blur-md py-2 z-10 border-b border-border/50">
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="icon" onClick={onBack}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <h1 className="text-xl font-bold">FAQ</h1>
        </div>
        <Button onClick={() => setShowForm(true)} size="sm" className="gap-2">
          <Plus className="h-4 w-4" /> Add
        </Button>
      </div>

      {loading && !faq.length ? (
        <div className="space-y-4">
          {[1, 2, 3].map(i => <Skeleton key={i} className="h-24 w-full rounded-xl" />)}
        </div>
      ) : faq.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 text-center space-y-4">
          <div className="p-4 rounded-full bg-secondary text-muted-foreground">
            <HelpCircle className="h-12 w-12" />
          </div>
          <p className="text-muted-foreground">No FAQ items found</p>
          <Button onClick={() => setShowForm(true)}>
            Create First Item
          </Button>
        </div>
      ) : (
        <div className="space-y-4">
          {faq.map((item) => (
            <Card key={item.id} className="overflow-hidden">
              <CardContent className="p-4 space-y-3">
                <div className="flex items-center gap-2 mb-2">
                  <Badge variant="outline" className="uppercase">
                    {item.language_code}
                  </Badge>
                  <Badge variant="secondary" className="capitalize">
                    {item.category}
                  </Badge>
                </div>
                
                <h3 className="font-semibold text-base">
                  {item.question}
                </h3>
                
                <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                  {item.answer}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
