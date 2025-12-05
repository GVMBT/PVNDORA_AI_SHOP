import React, { useState, useEffect, useMemo } from 'react'
import { useProducts } from '../hooks/useApi'
import { useLocale } from '../hooks/useLocale'
import { useTelegram } from '../hooks/useTelegram'
import StarRating from '../components/StarRating'
import { 
  Star, 
  Clock, 
  Package, 
  ShieldCheck, 
  FileText, 
  Zap,
  Users,
  Sparkles,
  ChevronRight,
  ArrowLeft
} from 'lucide-react'
import { Button } from '../components/ui/button'
import { Badge } from '../components/ui/badge'
import { Skeleton } from '../components/ui/skeleton'
import { Card, CardContent } from '../components/ui/card'
import { motion, AnimatePresence } from 'framer-motion'
import { cn } from '../lib/utils'
import { HeaderBar } from '../components/ui/header-bar'

const GRADIENTS = [
  'from-blue-600 via-indigo-500 to-purple-600',
  'from-emerald-500 via-teal-500 to-cyan-500',
  'from-orange-500 via-amber-500 to-yellow-500',
  'from-pink-500 via-rose-500 to-red-500',
  'from-fuchsia-600 via-purple-600 to-indigo-600',
  'from-sky-500 via-blue-500 to-indigo-500',
]

function getGradient(str) {
  if (!str) return GRADIENTS[0]
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
  }
  const index = Math.abs(hash) % GRADIENTS.length;
  return GRADIENTS[index];
}

export default function ProductPage({ productId, onBack, onCheckout }) {
  const { getProduct, loading, error } = useProducts()
  const { t, formatPrice } = useLocale()
  const { setBackButton, hapticFeedback } = useTelegram()
  
  const [product, setProduct] = useState(null)
  const [socialProof, setSocialProof] = useState(null)
  
  useEffect(() => {
    loadProduct()
    
    // Setup back button
    setBackButton({
      isVisible: true,
      onClick: onBack
    })
    
    return () => {
      setBackButton({ isVisible: false })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [productId])
  
  const loadProduct = async () => {
    try {
      const data = await getProduct(productId)
      if (data && data.product) {
        setProduct(data.product)
        setSocialProof(data.social_proof || null)
      } else {
        console.error('Invalid product data:', data)
        setProduct(null)
      }
    } catch (err) {
      console.error('Failed to load product:', err)
      setProduct(null)
    }
  }
  
  const handleBuy = () => {
    hapticFeedback('impact', 'medium')
    onCheckout()
  }

  const gradientClass = useMemo(() => getGradient(product?.name), [product?.name])
  
  if (loading) {
    return (
      <div className="p-4 space-y-4">
        <Skeleton className="h-64 w-full rounded-3xl" />
        <Skeleton className="h-8 w-3/4 rounded-full" />
        <Skeleton className="h-20 w-full rounded-xl" />
        <div className="grid grid-cols-2 gap-4">
          <Skeleton className="h-24 w-full rounded-xl" />
          <Skeleton className="h-24 w-full rounded-xl" />
        </div>
      </div>
    )
  }
  
  if (error || !product) {
    return (
      <div className="flex flex-col items-center justify-center h-[80vh] p-6 text-center space-y-6">
        <div className="p-6 rounded-full bg-destructive/10 text-destructive animate-pulse">
          <Package className="h-12 w-12" />
        </div>
        <h3 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-b from-foreground to-foreground/50">
          {error || t('product.notFound')}
        </h3>
        <Button onClick={onBack} variant="secondary" className="rounded-full px-8">
          {t('common.back')}
        </Button>
      </div>
    )
  }
  
  const {
    name = '',
    description = '',
    price = 0,
    msrp = null,
    discount_percent = 0,
    final_price = 0,
    available_count = 0,
    can_fulfill_on_demand = false,
    fulfillment_time_hours = 48,
    type = 'key',
    warranty_days = 0,
    duration_days = null,
    instructions = null,
    currency = 'USD'
  } = product || {}
  
  const hasDiscount = discount_percent > 0
  const isInStock = available_count > 0
  
  return (
    <div className="pb-32 bg-background min-h-screen">
      <HeaderBar title={product?.name || t('product.title')} onBack={onBack} />

      {/* Immersive Header */}
      <div className={cn("relative h-72 w-full overflow-hidden bg-gradient-to-br", gradientClass)}>
        <div className="absolute inset-0 bg-black/20" />
        <div className="absolute inset-0 bg-[url('/noise.png')] opacity-30 mix-blend-overlay" />

        {/* Hero Content */}
        <div className="absolute bottom-0 left-0 right-0 p-6 bg-gradient-to-t from-background via-background/80 to-transparent pt-20">
           <motion.div 
             initial={{ opacity: 0, y: 20 }}
             animate={{ opacity: 1, y: 0 }}
             className="space-y-2"
           >
             <div className="flex gap-2 flex-wrap mb-2">
              <Badge variant="secondary" className="bg-white/10 backdrop-blur-md text-white border-white/10 text-[10px] uppercase tracking-wider font-bold shadow-lg">
                {type}
              </Badge>
              {hasDiscount && (
                <Badge className="bg-emerald-500 text-white border-0 shadow-lg shadow-emerald-500/20 animate-pulse">
                  -{discount_percent}% SAVE
                </Badge>
              )}
            </div>
            <h1 className="text-3xl font-black leading-tight tracking-tight text-foreground">
              {name}
            </h1>
           </motion.div>
        </div>
      </div>

      <div className="px-4 -mt-2 space-y-8 relative z-10">
        {/* Price Section */}
        <motion.div 
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="flex items-center justify-between bg-card/30 backdrop-blur-sm border border-white/5 p-4 rounded-2xl"
        >
          <div>
             <p className="text-xs text-muted-foreground mb-0.5">{t('product.price')}</p>
             <div className="flex items-baseline gap-2">
               <span className="text-3xl font-bold text-primary font-mono tracking-tight">
                  {formatPrice(final_price || price, currency)}
                </span>
                {hasDiscount && msrp && (
                  <span className="text-sm text-muted-foreground line-through decoration-destructive/50">
                    {formatPrice(msrp, currency)}
                  </span>
                )}
             </div>
          </div>
          
           {isInStock ? (
            <div className="text-right">
              <div className="flex items-center gap-1.5 text-xs font-bold text-emerald-400 justify-end mb-1">
                <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse shadow-[0_0_10px_#34d399]" />
                {t('product.inStock')}
              </div>
              <p className="text-[10px] text-muted-foreground">{available_count} {t('product.units')}</p>
            </div>
          ) : can_fulfill_on_demand ? (
             <div className="text-right">
               <div className="flex items-center gap-1.5 text-xs font-bold text-amber-400 justify-end mb-1">
                <Clock className="w-3 h-3" />
                {t('product.onDemand')}
              </div>
               <p className="text-[10px] text-muted-foreground">~{fulfillment_time_hours}h wait</p>
             </div>
          ) : (
            <Badge variant="destructive">{t('product.outOfStock')}</Badge>
          )}
        </motion.div>

        {/* Description */}
        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
          className="prose prose-sm dark:prose-invert max-w-none text-muted-foreground"
        >
          {description}
        </motion.div>

        {/* Key Stats Grid */}
        <div className="grid grid-cols-2 gap-3">
          {warranty_days > 0 && (
            <motion.div 
              whileHover={{ scale: 1.02 }}
              className="bg-secondary/20 border border-white/5 p-4 rounded-2xl flex flex-col items-center text-center gap-2"
            >
              <div className="p-2 bg-blue-500/10 rounded-full text-blue-500">
                <ShieldCheck className="h-5 w-5" />
              </div>
              <div>
                <p className="text-[10px] text-muted-foreground uppercase tracking-wider">{t('product.warranty')}</p>
                <p className="font-bold text-lg text-foreground">{warranty_days}d</p>
              </div>
            </motion.div>
          )}
          
          {duration_days > 0 && (
             <motion.div 
              whileHover={{ scale: 1.02 }}
              className="bg-secondary/20 border border-white/5 p-4 rounded-2xl flex flex-col items-center text-center gap-2"
            >
               <div className="p-2 bg-purple-500/10 rounded-full text-purple-500">
                <Clock className="h-5 w-5" />
              </div>
              <div>
                <p className="text-[10px] text-muted-foreground uppercase tracking-wider">{t('product.duration')}</p>
                <p className="font-bold text-lg text-foreground">{duration_days}d</p>
              </div>
            </motion.div>
          )}

           {socialProof?.sales_count > 0 && (
             <motion.div 
              whileHover={{ scale: 1.02 }}
              className="bg-secondary/20 border border-white/5 p-4 rounded-2xl flex flex-col items-center text-center gap-2 col-span-2"
            >
               <div className="p-2 bg-orange-500/10 rounded-full text-orange-500">
                <Users className="h-5 w-5" />
              </div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-lg text-foreground">{socialProof.sales_count}+</span>
                <span className="text-sm text-muted-foreground">{t('product.sold')}</span>
              </div>
            </motion.div>
          )}
        </div>

        {/* Instructions Accordion (Simplified) */}
        {instructions && (
          <div className="bg-secondary/10 rounded-2xl p-5 border border-white/5">
            <h3 className="font-bold flex items-center gap-2 mb-3 text-foreground">
              <FileText className="h-4 w-4 text-primary" />
              {t('product.instructions')}
            </h3>
            <div className="text-sm text-muted-foreground whitespace-pre-wrap leading-relaxed">
              {instructions}
            </div>
          </div>
        )}

        {/* Reviews Preview */}
        {socialProof?.recent_reviews?.length > 0 && (
          <div className="space-y-4">
             <div className="flex items-center justify-between">
                <h3 className="font-bold text-lg">{t('product.recentReviews')}</h3>
                <div className="flex items-center gap-1 text-yellow-500 bg-yellow-500/10 px-2 py-1 rounded-lg">
                  <Star className="w-4 h-4 fill-current" />
                  <span className="font-bold">{socialProof.rating}</span>
                </div>
             </div>
             
             <div className="space-y-3">
              {socialProof.recent_reviews.slice(0, 3).map((review, index) => (
                <motion.div 
                  key={index} 
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.3 + (index * 0.1) }}
                  className="bg-card/30 p-4 rounded-xl border border-white/5"
                >
                  <div className="flex justify-between items-start mb-2">
                    <span className="font-medium text-sm">{review.author}</span>
                    <StarRating rating={review.rating} size="xs" />
                  </div>
                  <p className="text-xs text-muted-foreground leading-relaxed italic">"{review.text}"</p>
                </motion.div>
              ))}
             </div>
          </div>
        )}
      </div>
      
      {/* Floating Action Button (raised above bottom nav) */}
      <div className="fixed bottom-[calc(5.5rem+env(safe-area-inset-bottom))] left-4 right-4 z-40">
        <div className="absolute inset-0 bg-background/50 blur-xl -z-10 rounded-full transform scale-y-50 translate-y-4" />
        <Button
          onClick={handleBuy}
          disabled={!isInStock && !can_fulfill_on_demand}
          className={cn(
            "w-full h-14 text-lg font-bold rounded-2xl shadow-lg transition-all duration-200 hover:scale-[1.01] active:scale-[0.99]",
            isInStock || can_fulfill_on_demand
              ? "bg-gradient-to-r from-primary via-emerald-400 to-primary text-black hover:brightness-[1.05]"
              : "bg-secondary text-muted-foreground hover:bg-secondary"
          )}
        >
          {isInStock ? (
            <div className="flex items-center gap-2">
              <Zap className="w-5 h-5 fill-current" />
              {t('product.buyNow')}
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <Clock className="w-5 h-5" />
              {can_fulfill_on_demand ? t('product.preorder') : t('product.notifyMe')}
            </div>
          )}
        </Button>
      </div>
    </div>
  )
}
