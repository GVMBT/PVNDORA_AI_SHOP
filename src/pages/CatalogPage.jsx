import React, { useState, useEffect } from 'react'
import { useProducts } from '../hooks/useApi'
import { useLocale } from '../hooks/useLocale'
import ProductCard from '../components/ProductCard'

const categories = [
  { id: null, labelKey: 'catalog.all' },
  { id: 'student', labelKey: 'catalog.student' },
  { id: 'trial', labelKey: 'catalog.trial' },
  { id: 'shared', labelKey: 'catalog.shared' },
  { id: 'key', labelKey: 'catalog.key' }
]

export default function CatalogPage({ onProductClick }) {
  const { getProducts, loading, error } = useProducts()
  const { t } = useLocale()
  
  const [products, setProducts] = useState([])
  const [activeCategory, setActiveCategory] = useState(null)
  
  useEffect(() => {
    loadProducts()
  }, [activeCategory])
  
  const loadProducts = async () => {
    try {
      const data = await getProducts(activeCategory)
      setProducts(data.products || [])
    } catch (err) {
      console.error('Failed to load products:', err)
    }
  }
  
  return (
    <div className="p-4">
      {/* Header */}
      <header className="mb-6 stagger-enter">
        <h1 className="text-2xl font-bold text-[var(--color-text)] mb-1">
          PVNDORA
        </h1>
        <p className="text-[var(--color-text-muted)]">
          {t('catalog.subtitle')}
        </p>
      </header>
      
      {/* Category filter */}
      <div className="flex gap-2 overflow-x-auto pb-2 mb-6 -mx-4 px-4 scrollbar-hide stagger-enter">
        {categories.map((cat) => (
          <button
            key={cat.id || 'all'}
            onClick={() => setActiveCategory(cat.id)}
            className={`px-4 py-2 rounded-full whitespace-nowrap text-sm font-medium transition-all ${
              activeCategory === cat.id
                ? 'bg-[var(--color-primary)] text-[var(--color-bg-dark)]'
                : 'bg-[var(--color-bg-elevated)] text-[var(--color-text-muted)] hover:text-[var(--color-text)]'
            }`}
          >
            {t(cat.labelKey)}
          </button>
        ))}
      </div>
      
      {/* Products grid */}
      {loading ? (
        <div className="grid gap-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="card h-40 skeleton" />
          ))}
        </div>
      ) : error ? (
        <div className="card text-center py-8">
          <p className="text-[var(--color-error)] mb-4">{error}</p>
          <button onClick={loadProducts} className="btn btn-secondary">
            {t('common.retry')}
          </button>
        </div>
      ) : products.length === 0 ? (
        <div className="card text-center py-8">
          <p className="text-[var(--color-text-muted)]">
            {t('catalog.empty')}
          </p>
        </div>
      ) : (
        <div className="grid gap-4">
          {products.map((product, index) => (
            <div key={product.id} className="stagger-enter" style={{ animationDelay: `${index * 0.1}s` }}>
              <ProductCard
                product={product}
                socialProof={product.social_proof}
                onClick={onProductClick}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  )
}


