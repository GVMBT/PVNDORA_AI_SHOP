import React, { useState, useEffect } from 'react'
import { useAdmin } from '../hooks/useAdmin'
import { useLocale } from '../hooks/useLocale'
import { useTelegram } from '../hooks/useTelegram'
import { ArrowLeft, Plus, Edit2, Package } from 'lucide-react'
import { Button } from '../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Input } from '../components/ui/input'
import { Badge } from '../components/ui/badge'
import { Skeleton } from '../components/ui/skeleton'

export default function AdminProductsPage({ onBack }) {
  const { getProducts, createProduct, updateProduct, loading } = useAdmin()
  const { formatPrice } = useLocale()
  const { showAlert, hapticFeedback } = useTelegram()
  
  const [products, setProducts] = useState([])
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState(null)
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    price: '',
    type: 'shared',
    fulfillment_time_hours: 48,
    warranty_hours: 24,
    instructions: '',
    msrp: '',
    duration_days: ''
  })

  useEffect(() => {
    loadProducts()
  }, [])

  const loadProducts = async () => {
    try {
      const data = await getProducts()
      setProducts(data.products || [])
    } catch (err) {
      await showAlert(`Error: ${err.message}`)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    hapticFeedback('impact', 'medium')

    try {
      const payload = {
        ...formData,
        price: parseFloat(formData.price),
        fulfillment_time_hours: parseInt(formData.fulfillment_time_hours) || 0,
        warranty_hours: parseInt(formData.warranty_hours) || 0,
        msrp: formData.msrp ? parseFloat(formData.msrp) : null,
        duration_days: formData.duration_days ? parseInt(formData.duration_days) : null
      }

      if (editing) {
        await updateProduct(editing.id, payload)
        await showAlert('Product updated!')
      } else {
        await createProduct(payload)
        await showAlert('Product created!')
      }

      setShowForm(false)
      setEditing(null)
      resetForm()
      loadProducts()
    } catch (err) {
      await showAlert(`Error: ${err.message}`)
    }
  }

  const resetForm = () => {
    setFormData({
      name: '',
      description: '',
      price: '',
      type: 'shared',
      fulfillment_time_hours: 48,
      warranty_hours: 24,
      instructions: '',
      msrp: '',
      duration_days: ''
    })
  }

  const startEdit = (product) => {
    setEditing(product)
    setFormData({
      name: product.name || '',
      description: product.description || '',
      price: product.price || '',
      type: product.type || 'shared',
      fulfillment_time_hours: product.fulfillment_time_hours || 48,
      warranty_hours: product.warranty_hours || 24,
      instructions: product.instructions || '',
      msrp: product.msrp || '',
      duration_days: product.duration_days || ''
    })
    setShowForm(true)
  }

  if (showForm) {
    return (
      <div className="p-4 pb-20 space-y-6">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => { setShowForm(false); setEditing(null); resetForm() }}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <h1 className="text-xl font-bold">{editing ? 'Edit Product' : 'New Product'}</h1>
        </div>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">Name *</label>
            <Input
              value={formData.name}
              onChange={(e) => setFormData({...formData, name: e.target.value})}
              required
              placeholder="Product Name"
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Description</label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({...formData, description: e.target.value})}
              className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 min-h-[80px]"
              placeholder="Description..."
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Price (₽) *</label>
              <Input
                type="number"
                step="0.01"
                value={formData.price}
                onChange={(e) => setFormData({...formData, price: e.target.value})}
                required
                placeholder="0.00"
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">MSRP (₽)</label>
              <Input
                type="number"
                step="0.01"
                value={formData.msrp}
                onChange={(e) => setFormData({...formData, msrp: e.target.value})}
                placeholder="0.00"
              />
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Type *</label>
            <select
              value={formData.type}
              onChange={(e) => setFormData({...formData, type: e.target.value})}
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <option value="shared">Личный</option>
              <option value="student">Student</option>
              <option value="trial">Trial</option>
              <option value="key">API Key</option>
            </select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Fulfillment (hours)</label>
              <Input
                type="number"
                value={formData.fulfillment_time_hours}
                onChange={(e) => setFormData({...formData, fulfillment_time_hours: e.target.value})}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Warranty (hours)</label>
              <Input
                type="number"
                value={formData.warranty_hours}
                onChange={(e) => setFormData({...formData, warranty_hours: e.target.value})}
              />
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Duration (days)</label>
            <Input
              type="number"
              value={formData.duration_days}
              onChange={(e) => setFormData({...formData, duration_days: e.target.value})}
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Instructions</label>
            <textarea
              value={formData.instructions}
              onChange={(e) => setFormData({...formData, instructions: e.target.value})}
              className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 min-h-[80px]"
              placeholder="Instructions for user..."
            />
          </div>

          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? 'Saving...' : editing ? 'Update Product' : 'Create Product'}
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
          <h1 className="text-xl font-bold">Products</h1>
        </div>
        <Button onClick={() => setShowForm(true)} size="sm" className="gap-2">
          <Plus className="h-4 w-4" /> Add
        </Button>
      </div>

      {loading && !products.length ? (
        <div className="space-y-4">
          {[1, 2, 3].map(i => <Skeleton key={i} className="h-24 w-full rounded-xl" />)}
        </div>
      ) : products.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 text-center space-y-4">
          <div className="p-4 rounded-full bg-secondary text-muted-foreground">
            <Package className="h-12 w-12" />
          </div>
          <p className="text-muted-foreground">No products found</p>
          <Button onClick={() => setShowForm(true)}>
            Create First Product
          </Button>
        </div>
      ) : (
        <div className="grid gap-4">
          {products.map((product) => (
            <Card key={product.id} className="overflow-hidden">
              <CardContent className="p-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="space-y-1">
                    <h3 className="font-semibold text-base">
                      {product.name}
                    </h3>
                    <p className="text-sm text-muted-foreground line-clamp-2">
                      {product.description || 'No description'}
                    </p>
                    <div className="flex flex-wrap gap-2 mt-2">
                      <span className="text-primary font-bold">
                        {formatPrice(product.price)}
                      </span>
                      <Badge variant="secondary" className="text-xs">
                        {product.type}
                      </Badge>
                      <Badge variant={product.available_count > 0 ? "outline" : "destructive"} className="text-xs">
                        Stock: {product.available_count}
                      </Badge>
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => startEdit(product)}
                    className="shrink-0"
                  >
                    <Edit2 className="h-4 w-4" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
