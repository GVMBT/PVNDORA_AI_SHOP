import React, { useMemo } from 'react'
import { useLocale } from '../hooks/useLocale'
import { Star, Clock, Package, Sparkles } from 'lucide-react'
import { Card } from './ui/card'
import { Badge } from './ui/badge'
import { cn } from '../lib/utils'
import { motion } from 'framer-motion'

const GRADIENTS = [
  'from-blue-600 via-indigo-500 to-purple-600',
  'from-emerald-500 via-teal-500 to-cyan-500',
  'from-orange-500 via-amber-500 to-yellow-500',
  'from-pink-500 via-rose-500 to-red-500',
  'from-fuchsia-600 via-purple-600 to-indigo-600',
  'from-sky-500 via-blue-500 to-indigo-500',
]

function getGradient(str) {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
  }
  const index = Math.abs(hash) % GRADIENTS.length;
  return GRADIENTS[index];
}

export default function ProductCard({ product, socialProof, onClick }) {
  const { formatPrice, t } = useLocale()
  
  const {
    id,
    name,
    price,
    msrp,
    discount_percent,
    final_price,
    available_count,
    can_fulfill_on_demand,
    type
  } = product
  
  const hasDiscount = discount_percent > 0
  const isInStock = available_count > 0
  
  const gradientClass = useMemo(() => getGradient(name), [name])

  return (
    <motion.div
      whileHover={{ y: -5, scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: 'spring', stiffness: 300, damping: 20 }}
      className="h-full"
    >
      <Card 
        className="relative overflow-hidden border-0 h-full flex flex-col bg-card/40 backdrop-blur-md ring-1 ring-white/10 shadow-xl cursor-pointer group"
        onClick={() => onClick(id)}
      >
        {/* Generative Art Header */}
        <div className={cn("h-32 w-full relative bg-gradient-to-br p-4", gradientClass)}>
          <div className="absolute inset-0 bg-black/10" />
          <div className="absolute inset-0 bg-[url('/noise.png')] opacity-20 mix-blend-overlay" />
          
          {/* Badges */}
          <div className="relative z-10 flex justify-between items-start">
             <Badge variant="secondary" className="bg-black/30 backdrop-blur-md text-white border-0 text-[10px] uppercase tracking-widest font-bold">
              {type}
            </Badge>
            
            {hasDiscount && (
              <Badge className="bg-white/90 text-black font-bold shadow-lg animate-pulse">
                -{discount_percent}%
              </Badge>
            )}
          </div>
          
          {/* Icon based on type */}
          <div className="absolute bottom-2 right-2 opacity-50 group-hover:opacity-100 group-hover:scale-110 transition-all duration-500">
             {type === 'subscription' ? <Sparkles className="w-12 h-12 text-white" /> : <Package className="w-12 h-12 text-white" />}
          </div>
        </div>

        <div className="p-4 flex-1 flex flex-col relative">
          {/* Glow Effect */}
          <div className="absolute -top-10 left-0 right-0 h-20 bg-gradient-to-b from-black/50 to-transparent pointer-events-none" />

          <h3 className="font-bold text-lg leading-tight mb-1 text-foreground group-hover:text-primary transition-colors line-clamp-2 z-10">
            {name}
          </h3>
          
          {/* Social Proof */}
          <div className="flex items-center gap-3 text-xs text-muted-foreground mb-4 mt-2">
            {socialProof?.rating > 0 && (
              <div className="flex items-center gap-1 text-yellow-500">
                <Star className="w-3.5 h-3.5 fill-current" />
                <span className="font-medium">{socialProof.rating}</span>
              </div>
            )}
             {socialProof?.sales_count > 0 && (
              <div className="flex items-center gap-1">
                <Package className="w-3.5 h-3.5" />
                <span>{socialProof.sales_count}+</span>
              </div>
            )}
          </div>

          <div className="mt-auto pt-4 border-t border-white/5 flex items-end justify-between">
            <div>
              {hasDiscount && msrp && (
                <div className="text-xs text-muted-foreground line-through mb-0.5 font-mono">
                  {formatPrice(msrp)}
                </div>
              )}
              <div className="text-xl font-bold text-primary font-mono tracking-tight">
                {formatPrice(final_price || price)}
              </div>
            </div>

            <div className="flex flex-col items-end">
               {isInStock ? (
                <div className="flex items-center gap-1.5 text-[10px] font-bold text-emerald-400 bg-emerald-500/10 px-2 py-1 rounded-full ring-1 ring-emerald-500/20">
                  <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  {available_count > 10 ? t('product.inStock') : `${available_count} left`}
                </div>
              ) : can_fulfill_on_demand ? (
                <div className="flex items-center gap-1.5 text-[10px] font-bold text-amber-400 bg-amber-500/10 px-2 py-1 rounded-full ring-1 ring-amber-500/20">
                  <Clock className="w-3 h-3" />
                  {t('product.onDemand')}
                </div>
              ) : (
                <div className="flex items-center gap-1.5 text-[10px] font-bold text-red-400 bg-red-500/10 px-2 py-1 rounded-full ring-1 ring-red-500/20">
                  <div className="w-1.5 h-1.5 rounded-full bg-red-400" />
                  {t('product.outOfStock')}
                </div>
              )}
            </div>
          </div>
        </div>
      </Card>
    </motion.div>
  )
}
