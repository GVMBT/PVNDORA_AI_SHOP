import React, { useState, useEffect } from 'react'
import { useProducts } from '../hooks/useApi'
import { useLocale } from '../hooks/useLocale'
import { useTelegram } from '../hooks/useTelegram'
import ProductCard from '../components/ProductCard'
import { Search, SlidersHorizontal } from 'lucide-react'
import { Input } from '../components/ui/input'
import { Button } from '../components/ui/button'
import { Skeleton } from '../components/ui/skeleton'
import { Badge } from '../components/ui/badge'

export default function CatalogPage({ onProductClick }) {
  const { getProducts, loading, error } = useProducts()
  const { t } = useLocale()
  const { hapticFeedback } = useTelegram()
  
  const [products, setProducts] = useState([])
  const [filter, setFilter] = useState('all')
  const [searchQuery, setSearchQuery] = useState('')
  
  useEffect(() => {
    loadProducts()
  }, [])
  
  const loadProducts = async () => {
    try {
      const data = await getProducts()
      setProducts(data.products || [])
    } catch (err) {
      console.error('Failed to load products:', err)
    }
  }
  
  const handleProductClick = (id) => {
    hapticFeedback('light')
    onProductClick(id)
  }
  
  // Filter products
  const filteredProducts = products.filter(p => {
    const matchesType = filter === 'all' || p.type === filter
    const matchesSearch = p.name.toLowerCase().includes(searchQuery.toLowerCase()) || 
                         (p.description && p.description.toLowerCase().includes(searchQuery.toLowerCase()))
    return matchesType && matchesSearch
  })
  
  const categories = [
    { id: 'all', label: t('catalog.all') },
    { id: 'subscription', label: t('catalog.subscription') || 'Subscriptions' },
    { id: 'key', label: t('catalog.key') }
  ]

  return (
    <div className="p-4 space-y-6">
      {/* Header */}
      <div className="stagger-enter">
        <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-primary to-primary/60 mb-2">
          PVNDORA
        </h1>
        <p className="text-muted-foreground text-sm">
          {t('catalog.subtitle')}
        </p>
      </div>
      
      {/* Search & Filter */}
      <div className="flex gap-3 stagger-enter" style={{ animationDelay: '0.1s' }}>
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input 
            placeholder="Search AI tools..." 
            className="pl-9 bg-card/50 border-border/50 focus:border-primary/50 transition-all"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
        {/* Future filter dialog trigger could go here */}
        {/* <Button variant="outline" size="icon" className="shrink-0">
          <SlidersHorizontal className="h-4 w-4" />
        </Button> */}
      </div>
      
      {/* Categories */}
      <div className="flex gap-2 overflow-x-auto pb-2 -mx-4 px-4 no-scrollbar stagger-enter" style={{ animationDelay: '0.2s' }}>
        {categories.map(cat => (
          <button
            key={cat.id}
            onClick={() => {
              hapticFeedback('selection')
              setFilter(cat.id)
            }}
            className={`
              px-4 py-1.5 rounded-full text-sm font-medium whitespace-nowrap transition-all
              ${filter === cat.id 
                ? 'bg-primary text-primary-foreground shadow-lg shadow-primary/20' 
                : 'bg-secondary text-secondary-foreground hover:bg-secondary/80'}
            `}
          >
            {cat.label}
          </button>
        ))}
      </div>
      
      {/* Product Grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="space-y-3">
              <Skeleton className="h-40 w-full rounded-xl" />
              <div className="space-y-2">
                <Skeleton className="h-4 w-3/4" />
                <Skeleton className="h-4 w-1/2" />
              </div>
            </div>
          ))}
        </div>
      ) : error ? (
        <div className="text-center py-12 space-y-4">
          <div className="p-4 rounded-full bg-destructive/10 text-destructive w-fit mx-auto">
            <SlidersHorizontal className="h-8 w-8" />
          </div>
          <p className="text-muted-foreground">{error}</p>
          <Button onClick={loadProducts} variant="outline">
            {t('common.retry')}
          </Button>
        </div>
      ) : filteredProducts.length === 0 ? (
        <div className="text-center py-12 space-y-2 stagger-enter">
          <div className="text-4xl mb-2">🔍</div>
          <h3 className="font-medium text-foreground">
            {t('catalog.empty')}
          </h3>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 pb-20">
          {filteredProducts.map((product, index) => (
            <div 
              key={product.id} 
              className="stagger-enter" 
              style={{ animationDelay: `${0.2 + (index * 0.05)}s` }}
            >
              <ProductCard
                product={product}
                socialProof={product.social_proof}
                onClick={handleProductClick}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
