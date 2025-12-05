import React, { useState, useEffect } from 'react'
import { useProducts, useCart } from '../hooks/useApi'
import { useLocale } from '../hooks/useLocale'
import { useTelegram } from '../hooks/useTelegram'
import ProductCard from '../components/ProductCard'
import { Search, SlidersHorizontal, Sparkles, Brain, Paintbrush, Code, Shield, Zap, CheckCircle2 } from 'lucide-react'
import { Input } from '../components/ui/input'
import { Button } from '../components/ui/button'
import { Skeleton } from '../components/ui/skeleton'
import { motion, AnimatePresence } from 'framer-motion'
import { Tabs, TabsList, TabsTrigger } from '../components/ui/tabs'

export default function CatalogPage({ onProductClick }) {
  const { getProducts, loading, error } = useProducts()
  const { addToCart, getCart } = useCart()
  const { t } = useLocale()
  const { hapticFeedback, showAlert } = useTelegram()
  
  const [products, setProducts] = useState([])
  const [filter, setFilter] = useState('all')
  const [searchQuery, setSearchQuery] = useState('')
  const [toast, setToast] = useState(null)
  
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

  const handleAddToCart = async (product) => {
    try {
      hapticFeedback('impact', 'light')
      await addToCart(product.id, 1)
      // Refresh cart cache (optional, but keeps totals in checkout mode)
      await getCart()
      setToast({ type: 'success', message: t('product.addedToCart') || 'Added to cart' })
      setTimeout(() => setToast(null), 2000)
    } catch (err) {
      setToast({ type: 'error', message: err.message || t('common.error') })
      setTimeout(() => setToast(null), 2500)
    }
  }
  
  // Filter products
  const filteredProducts = products.filter(p => {
    const matchesType = filter === 'all' || p.type === filter
    const matchesSearch = p.name.toLowerCase().includes(searchQuery.toLowerCase()) || 
                         (p.description && p.description.toLowerCase().includes(searchQuery.toLowerCase()))
    return matchesType && matchesSearch
  })
  
  const categories = [
    { id: 'all', label: t('catalog.all'), icon: null },
    { id: 'ai_solutions', label: t('catalog.category.aiSolutions'), icon: Brain },
    { id: 'design_tools', label: t('catalog.category.designTools'), icon: Paintbrush },
    { id: 'developer_access', label: t('catalog.category.developerAccess'), icon: Code }
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
        </motion.div>
        
        {/* About Service Block */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-gradient-to-br from-card/50 to-background rounded-2xl p-5 border border-white/10 shadow-xl"
        >
          <h2 className="text-xl font-bold mb-3">{t('catalog.about.title')}</h2>
          <p className="text-sm text-muted-foreground leading-relaxed whitespace-pre-line">
            {t('catalog.about.description')}
          </p>
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
          <div className="bg-background/70 backdrop-blur-xl p-2 rounded-2xl border border-white/10 shadow-lg min-w-max">
            <Tabs
              value={filter}
              onValueChange={(value) => {
                hapticFeedback('selection')
                setFilter(value)
              }}
            >
              <TabsList className="flex gap-2 bg-transparent p-0 border-0 shadow-none">
                {categories.map((cat) => {
                  const Icon = cat.icon
                  return (
                    <TabsTrigger
                      key={cat.id}
                      value={cat.id}
                      className={`
                        px-4 py-2 h-auto rounded-full text-sm font-semibold whitespace-nowrap border flex items-center gap-2
                        data-[state=active]:bg-primary data-[state=active]:text-black data-[state=active]:border-primary data-[state=active]:shadow-[0_10px_30px_rgba(0,245,212,0.25)]
                        data-[state=inactive]:bg-white/5 data-[state=inactive]:text-muted-foreground data-[state=inactive]:border-white/10
                        transition-all
                      `}
                    >
                      {Icon && <Icon className="h-4 w-4" />}
                      {cat.label}
                    </TabsTrigger>
                  )
                })}
              </TabsList>
            </Tabs>
          </div>
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
                    onAddToCart={handleAddToCart}
                  />
                </motion.div>
              ))}
            </AnimatePresence>
          </motion.div>
        )}
        
        {/* Security & Guarantees Block */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="space-y-4 pt-6"
        >
          <h2 className="text-xl font-bold flex items-center gap-2">
            <Shield className="h-5 w-5 text-primary" />
            {t('catalog.security.title')}
          </h2>
          
          <div className="grid grid-cols-1 gap-4">
            {/* Instant Delivery */}
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.4 }}
              className="bg-gradient-to-br from-card/50 to-background rounded-xl p-4 border border-white/10"
            >
              <div className="flex items-start gap-3">
                <div className="p-2 rounded-lg bg-primary/10">
                  <Zap className="h-5 w-5 text-primary" />
                </div>
                <div className="flex-1">
                  <h3 className="font-semibold mb-1">{t('catalog.security.instantDelivery.title')}</h3>
                  <p className="text-sm text-muted-foreground">
                    {t('catalog.security.instantDelivery.description')}
                  </p>
                </div>
              </div>
            </motion.div>
            
            {/* Validity Guarantee */}
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.5 }}
              className="bg-gradient-to-br from-card/50 to-background rounded-xl p-4 border border-white/10"
            >
              <div className="flex items-start gap-3">
                <div className="p-2 rounded-lg bg-primary/10">
                  <CheckCircle2 className="h-5 w-5 text-primary" />
                </div>
                <div className="flex-1">
                  <h3 className="font-semibold mb-1">{t('catalog.security.validity.title')}</h3>
                  <p className="text-sm text-muted-foreground">
                    {t('catalog.security.validity.description')}
                  </p>
                </div>
              </div>
            </motion.div>
            
            {/* Customer Support */}
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.6 }}
              className="bg-gradient-to-br from-card/50 to-background rounded-xl p-4 border border-white/10"
            >
              <div className="flex items-start gap-3">
                <div className="p-2 rounded-lg bg-primary/10">
                  <Shield className="h-5 w-5 text-primary" />
                </div>
                <div className="flex-1">
                  <h3 className="font-semibold mb-1">{t('catalog.security.support.title')}</h3>
                  <p className="text-sm text-muted-foreground">
                    {t('catalog.security.support.description')}
                  </p>
                </div>
              </div>
            </motion.div>
          </div>
        </motion.div>
      </div>

      {/* Toast */}
      {toast && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50">
          <div
            className={`px-4 py-3 rounded-xl shadow-lg text-sm font-semibold backdrop-blur ${
              toast.type === 'success'
                ? 'bg-emerald-500/90 text-white'
                : 'bg-destructive/90 text-white'
            }`}
          >
            {toast.message}
          </div>
        </div>
      )}
    </div>
  )
}
