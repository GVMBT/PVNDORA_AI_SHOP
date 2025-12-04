import React, { useState, useEffect } from 'react'
import { useProducts } from '../hooks/useApi'
import { useLocale } from '../hooks/useLocale'
import { useTelegram } from '../hooks/useTelegram'
import ProductCard from '../components/ProductCard'
import { Search, SlidersHorizontal, Sparkles } from 'lucide-react'
import { Input } from '../components/ui/input'
import { Button } from '../components/ui/button'
import { Skeleton } from '../components/ui/skeleton'
import { motion, AnimatePresence } from 'framer-motion'

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
    { id: 'subscription', label: t('catalog.subscription') },
    { id: 'shared', label: 'Shared' },
    { id: 'key', label: t('catalog.key') }
  ]

  const containerVariants = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1
      }
    }
  }

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    show: { opacity: 1, y: 0 }
  }

  return (
    <div className="min-h-screen pb-20 relative">
      {/* Gradient Header Background */}
      <div className="absolute top-0 left-0 right-0 h-64 bg-gradient-to-b from-primary/10 via-background/50 to-transparent pointer-events-none" />

      <div className="p-4 space-y-6 relative z-10">
        {/* Header */}
        <motion.div 
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex justify-between items-center"
        >
          <div>
             <h1 className="text-4xl font-black tracking-tighter bg-clip-text text-transparent bg-gradient-to-r from-primary via-cyan-400 to-emerald-400 drop-shadow-[0_0_15px_rgba(0,245,212,0.3)]">
              PVNDORA
            </h1>
            <p className="text-muted-foreground text-sm font-medium">
              {t('catalog.subtitle')}
            </p>
          </div>
          {/* Optional User Avatar or Menu could go here */}
        </motion.div>
        
        {/* Search & Filter - Sticky-ish */}
        <div className="sticky top-2 z-30 pt-2">
           <div className="bg-background/80 backdrop-blur-xl p-1 rounded-2xl border border-white/10 shadow-lg">
             <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input 
                  placeholder={t('catalog.search')}
                  className="pl-9 bg-white/5 border-transparent focus:border-primary/50 rounded-xl h-10 transition-all placeholder:text-muted-foreground/50"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
             </div>
           </div>
        </div>
        
        {/* Categories */}
        <div className="overflow-x-auto -mx-4 px-4 no-scrollbar">
          <motion.div 
            className="flex gap-2 min-w-max"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.2 }}
          >
            {categories.map(cat => (
              <motion.button
                key={cat.id}
                whileTap={{ scale: 0.95 }}
                onClick={() => {
                  hapticFeedback('selection')
                  setFilter(cat.id)
                }}
                className={`
                  px-5 py-2 rounded-full text-sm font-bold whitespace-nowrap transition-all border
                  ${filter === cat.id 
                    ? 'bg-primary text-black border-primary shadow-[0_0_15px_rgba(0,245,212,0.4)]' 
                    : 'bg-secondary/50 text-muted-foreground border-transparent hover:bg-secondary hover:text-foreground'}
                `}
              >
                {cat.label}
              </motion.button>
            ))}
          </motion.div>
        </div>
        
        {/* Product Grid */}
        {loading ? (
          <div className="grid grid-cols-1 gap-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="space-y-3">
                <Skeleton className="h-48 w-full rounded-2xl bg-secondary/50" />
              </div>
            ))}
          </div>
        ) : error ? (
          <div className="text-center py-20 space-y-4">
            <div className="p-6 rounded-full bg-destructive/10 text-destructive w-fit mx-auto animate-pulse">
              <SlidersHorizontal className="h-10 w-10" />
            </div>
            <p className="text-muted-foreground font-medium">{error}</p>
            <Button onClick={loadProducts} variant="outline" className="rounded-full">
              {t('common.retry')}
            </Button>
          </div>
        ) : filteredProducts.length === 0 ? (
          <motion.div 
            initial={{ opacity: 0 }} 
            animate={{ opacity: 1 }}
            className="text-center py-20 space-y-4"
          >
            <div className="w-20 h-20 bg-secondary/30 rounded-full mx-auto flex items-center justify-center">
               <Sparkles className="w-10 h-10 text-muted-foreground" />
            </div>
            <h3 className="font-medium text-foreground">
              {t('catalog.empty')}
            </h3>
          </motion.div>
        ) : (
          <motion.div 
            variants={containerVariants}
            initial="hidden"
            animate="show"
            className="grid grid-cols-1 gap-5"
          >
            <AnimatePresence>
              {filteredProducts.map((product) => (
                <motion.div 
                  key={product.id} 
                  variants={itemVariants}
                  layout
                >
                  <ProductCard
                    product={product}
                    socialProof={product.social_proof}
                    onClick={handleProductClick}
                  />
                </motion.div>
              ))}
            </AnimatePresence>
          </motion.div>
        )}
      </div>
    </div>
  )
}
