import React, { useState, useEffect, useCallback, useRef } from 'react'
import { useProducts, useCart } from '../hooks/useApi'
import { useLocale } from '../hooks/useLocale'
import { useTelegram } from '../hooks/useTelegram'
import ProductCard from '../components/ProductCard'
import { Search, SlidersHorizontal, Sparkles, Brain, Paintbrush, Code, Zap, CheckCircle2, Shield, FileText, MessageCircle, HelpCircle } from 'lucide-react'
import { Input } from '../components/ui/input'
import { Button } from '../components/ui/button'
import { Skeleton } from '../components/ui/skeleton'
import { motion, AnimatePresence } from 'framer-motion'
import { Tabs, TabsList, TabsTrigger } from '../components/ui/tabs'

export default function CatalogPage({ onProductClick, onGoCart, onNavigate }) {
  const { getProducts, loading, error } = useProducts()
  const { addToCart, getCart } = useCart()
  const { t } = useLocale()
  const { hapticFeedback } = useTelegram()
  
  const [products, setProducts] = useState([])
  const [filter, setFilter] = useState('all')
  const [searchQuery, setSearchQuery] = useState('')
  const [toast, setToast] = useState(null)
  const [cartCount, setCartCount] = useState(0)
  const toastTimeoutRef = useRef(null)
  
  const loadProducts = useCallback(async () => {
    try {
      const data = await getProducts()
      setProducts(data.products || [])
    } catch (err) {
      console.error('Failed to load products:', err)
    }
  }, [getProducts])

  useEffect(() => {
    loadProducts()
    getCart()
      .then((data) => {
        if (data && Array.isArray(data.items)) {
          const totalQty = data.items.reduce((sum, item) => sum + (item.quantity || 0), 0)
          setCartCount(totalQty)
        }
      })
      .catch(() => {})
  }, [loadProducts, getCart])
  
  const handleProductClick = (id) => {
    hapticFeedback('light')
    onProductClick(id)
  }

  const showToast = (toastValue, duration = 2000) => {
    if (toastTimeoutRef.current) {
      clearTimeout(toastTimeoutRef.current)
    }
    setToast(toastValue)
    toastTimeoutRef.current = setTimeout(() => setToast(null), duration)
  }

  const handleAddToCart = async (product) => {
    try {
      hapticFeedback('impact', 'light')
      const cart = await addToCart(product.id, 1)
      // Refresh cart cache/count
      if (cart && Array.isArray(cart.items)) {
        const totalQty = cart.items.reduce((sum, item) => sum + (item.quantity || 0), 0)
        setCartCount(totalQty)
      } else {
        const data = await getCart().catch(() => null)
        if (data && Array.isArray(data.items)) {
          const totalQty = data.items.reduce((sum, item) => sum + (item.quantity || 0), 0)
          setCartCount(totalQty)
        }
      }
      showToast({ type: 'success', message: t('product.addedToCart') || 'Added to cart' })
    } catch (err) {
      showToast({ type: 'error', message: err.message || t('common.error') }, 2500)
    }
  }

  useEffect(() => {
    return () => {
      if (toastTimeoutRef.current) {
        clearTimeout(toastTimeoutRef.current)
      }
    }
  }, [])
  
  // Build categories dynamically based on product types
  const productTypes = Array.from(new Set(products.map((p) => p.type).filter(Boolean)))
  const typeOrder = ['ai', 'design', 'dev', 'music']
  const typeIconMap = {
    ai: Brain,
    design: Paintbrush,
    dev: Code,
    music: Sparkles
  }
  const typeLabelMap = {
    ai: t('catalog.category.ai') || t('catalog.category.aiSolutions'),
    design: t('catalog.category.design') || t('catalog.category.designTools'),
    dev: t('catalog.category.dev') || t('catalog.category.developerAccess'),
    music: t('catalog.category.music') || 'Музыка'
  }

  const categories = [
    { id: 'all', label: t('catalog.all'), icon: null },
    ...typeOrder
      .filter((type) => productTypes.includes(type))
      .map((type) => ({
        id: type,
        label: typeLabelMap[type],
        icon: typeIconMap[type] || null,
      })),
  ]

  // Filter products
  const filteredProducts = products.filter(p => {
    const matchesType = filter === 'all' || p.type === filter
    const matchesSearch = p.name.toLowerCase().includes(searchQuery.toLowerCase()) || 
                         (p.description && p.description.toLowerCase().includes(searchQuery.toLowerCase()))
    return matchesType && matchesSearch
  })

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
        <Tabs
          value={filter}
          onValueChange={(value) => {
            hapticFeedback('selection')
            setFilter(value)
          }}
        >
          <TabsList className="flex overflow-x-auto no-scrollbar gap-2 px-1.5">
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
        
        {/* Legal Links Section */}
        {onNavigate && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.7 }}
            className="mt-8 pt-6 border-t border-border/30"
          >
            <div className="flex flex-wrap justify-center gap-3">
              <Button
                variant="ghost"
                size="sm"
                className="text-xs"
                onClick={() => onNavigate('faq')}
              >
                <HelpCircle className="h-3.5 w-3.5 mr-1.5" />
                {t('faq.title')}
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="text-xs"
                onClick={() => onNavigate('terms')}
              >
                <FileText className="h-3.5 w-3.5 mr-1.5" />
                {t('terms.title')}
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="text-xs"
                onClick={() => onNavigate('contacts')}
              >
                <MessageCircle className="h-3.5 w-3.5 mr-1.5" />
                {t('contacts.support')}
              </Button>
            </div>
          </motion.div>
        )}
      </div>

      {/* Toast */}
      {toast && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50">
          <div
            className={`px-4 py-3 rounded-xl shadow-lg text-sm font-semibold backdrop-blur flex items-center gap-2 ${
              toast.type === 'success'
                ? 'bg-primary text-black'
                : 'bg-destructive text-white'
            }`}
          >
            <span>{toast.type === 'success' ? '✅' : '⚠️'}</span>
            {toast.message}
          </div>
        </div>
      )}

      {/* Floating Cart Button */}
      {cartCount > 0 && (
        <div className="fixed bottom-24 right-4 z-40">
          <Button
            className="rounded-full shadow-lg bg-primary text-black hover:bg-primary/90 px-4 py-3"
            onClick={() => onGoCart && onGoCart()}
          >
            🛒 {t('nav.cart') || 'Cart'} ({cartCount})
          </Button>
        </div>
      )}
    </div>
  )
}
