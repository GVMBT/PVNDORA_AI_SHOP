import React, { useState, useEffect } from 'react'
import { useAdmin } from '../hooks/useAdmin'
import { useTelegram } from '../hooks/useTelegram'
import { ArrowLeft, Plus, Database, Calendar, BoxSelect, Check, X, AlertCircle } from 'lucide-react'
import { Button } from '../components/ui/button'
import { Card, CardContent } from '../components/ui/card'
import { Input } from '../components/ui/input'
import { Badge } from '../components/ui/badge'
import { Skeleton } from '../components/ui/skeleton'

export default function AdminStockPage({ onBack }) {
  const { getStock, addStock, addStockBulk, getProducts, loading } = useAdmin()
  const { showAlert, hapticFeedback } = useTelegram()
  
  const [stock, setStock] = useState([])
  const [products, setProducts] = useState([])
  const [showForm, setShowForm] = useState(false)
  const [formData, setFormData] = useState({
    product_id: '',
    content: '',
    expires_at: '',
    supplier_id: ''
  })
  const [bulkMode, setBulkMode] = useState(false)
  const [bulkContent, setBulkContent] = useState('')

  useEffect(() => {
    loadStock()
    loadProducts()
  }, [])

  const loadStock = async () => {
    try {
      const data = await getStock()
      setStock(data.stock || [])
    } catch (err) {
      await showAlert(`Error: ${err.message}`)
    }
  }

  const loadProducts = async () => {
    try {
      const data = await getProducts()
      setProducts(data.products || [])
    } catch (err) {
      // Ignore
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    hapticFeedback('impact', 'medium')

    try {
      if (bulkMode) {
        const lines = bulkContent.split('\n').filter(l => l.trim())
        await addStockBulk({
          product_id: formData.product_id,
          items: lines.map(line => ({
            content: line.trim(),
            expires_at: formData.expires_at || null,
            supplier_id: formData.supplier_id || null
          }))
        })
        await showAlert(`Added ${lines.length} items!`)
      } else {
        await addStock({
          product_id: formData.product_id,
          content: formData.content,
          expires_at: formData.expires_at || null,
          supplier_id: formData.supplier_id || null
        })
        await showAlert('Stock item added!')
      }

      setShowForm(false)
      resetForm()
      loadStock()
    } catch (err) {
      await showAlert(`Error: ${err.message}`)
    }
  }

  const resetForm = () => {
    setFormData({
      product_id: '',
      content: '',
      expires_at: '',
      supplier_id: ''
    })
    setBulkContent('')
  }

  if (showForm) {
    return (
      <div className="p-4 pb-20 space-y-6">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => { setShowForm(false); resetForm() }}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <h1 className="text-xl font-bold">Add Stock</h1>
        </div>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">Product *</label>
            <select
              value={formData.product_id}
              onChange={(e) => setFormData({...formData, product_id: e.target.value})}
              required
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <option value="">Select Product</option>
              {products.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">
              {bulkMode ? 'Content (one per line) *' : 'Content (Login:Pass or Link) *'}
            </label>
            {bulkMode ? (
              <textarea
                value={bulkContent}
                onChange={(e) => setBulkContent(e.target.value)}
                required
                className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 min-h-[200px] font-mono"
                placeholder={'user1@example.com:pass123\nuser2@example.com:pass456'}
              />
            ) : (
              <Input
                value={formData.content}
                onChange={(e) => setFormData({...formData, content: e.target.value})}
                required
                placeholder="user@example.com:password"
                className="font-mono"
              />
            )}
          </div>

          <div className="flex items-center gap-2 p-2 rounded-lg border border-border bg-secondary/20">
            <input
              type="checkbox"
              id="bulk"
              checked={bulkMode}
              onChange={(e) => setBulkMode(e.target.checked)}
              className="w-4 h-4 accent-primary"
            />
            <label htmlFor="bulk" className="text-sm cursor-pointer select-none flex-1">Bulk Add Mode</label>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Expires At (Optional)</label>
            <Input
              type="datetime-local"
              value={formData.expires_at}
              onChange={(e) => setFormData({...formData, expires_at: e.target.value})}
            />
          </div>

          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? 'Adding...' : 'Add Stock'}
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
          <h1 className="text-xl font-bold">Stock</h1>
        </div>
        <Button onClick={() => setShowForm(true)} size="sm" className="gap-2">
          <Plus className="h-4 w-4" /> Add
        </Button>
      </div>

      {loading && !stock.length ? (
        <div className="space-y-4">
          {[1, 2, 3].map(i => <Skeleton key={i} className="h-20 w-full rounded-xl" />)}
        </div>
      ) : stock.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 text-center space-y-4">
          <div className="p-4 rounded-full bg-secondary text-muted-foreground">
            <Database className="h-12 w-12" />
          </div>
          <p className="text-muted-foreground">No stock items found</p>
          <Button onClick={() => setShowForm(true)}>
            Add First Item
          </Button>
        </div>
      ) : (
        <div className="grid gap-4">
          {stock.map((item) => {
            const isAvailable = item.status === 'available'
            const isSold = item.status === 'sold' || item.is_sold
            const isReserved = item.status === 'reserved'

            return (
              <Card key={item.id} className="overflow-hidden">
                <CardContent className="p-4">
                  <div className="flex items-start justify-between gap-4">
                    <div className="space-y-2 w-full">
                      <div className="flex items-center justify-between">
                        <Badge 
                          variant={isAvailable ? "success" : isSold ? "destructive" : "warning"}
                          className="gap-1"
                        >
                          {isAvailable ? <Check className="h-3 w-3" /> : 
                           isSold ? <X className="h-3 w-3" /> : 
                           <AlertCircle className="h-3 w-3" />}
                          {item.status}
                        </Badge>
                        {item.expires_at && (
                          <span className="text-xs text-muted-foreground flex items-center gap-1">
                            <Calendar className="h-3 w-3" />
                            {new Date(item.expires_at).toLocaleDateString()}
                          </span>
                        )}
                      </div>
                      
                      <div className="p-2 bg-secondary/30 rounded-md font-mono text-xs break-all border border-border/50">
                        {item.content}
                      </div>

                      {item.product_name && (
                        <div className="flex items-center gap-1 text-xs text-muted-foreground">
                          <BoxSelect className="h-3 w-3" />
                          {item.product_name}
                        </div>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}
    </div>
  )
}
