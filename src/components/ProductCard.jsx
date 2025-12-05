import React, { useMemo } from 'react'
import { useLocale } from '../hooks/useLocale'
import { Star, Clock, Package, Sparkles } from 'lucide-react'
import { Card } from './ui/card'
import { Badge } from './ui/badge'
import { Button } from './ui/button'
import { cn } from '../lib/utils'
import { motion } from 'framer-motion'

// Dark elegant textures with subtle accents
const TEXTURES = [
  { bg: 'from-zinc-800 via-zinc-900 to-neutral-900', accent: 'cyan' },
  { bg: 'from-slate-800 via-slate-900 to-zinc-900', accent: 'emerald' },
  { bg: 'from-neutral-800 via-stone-900 to-zinc-900', accent: 'amber' },
  { bg: 'from-gray-800 via-zinc-900 to-slate-900', accent: 'purple' },
  { bg: 'from-stone-800 via-neutral-900 to-zinc-900', accent: 'rose' },
  { bg: 'from-zinc-800 via-gray-900 to-neutral-900', accent: 'blue' },
]

function getTexture(str) {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
  }
  const index = Math.abs(hash) % TEXTURES.length;
  return TEXTURES[index];
}

export default function ProductCard({ product, socialProof, onClick, onAddToCart }) {
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
    type,
    currency
  } = product
  
  const hasDiscount = discount_percent > 0
  const isInStock = available_count > 0
  
  const texture = useMemo(() => getTexture(name), [name])

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
        {/* Elegant Dark Header with subtle pattern */}
        <div className={cn("h-32 w-full relative bg-gradient-to-br p-4", texture.bg)}>
          {/* Grid pattern overlay */}
          <div className="absolute inset-0 opacity-[0.03]" style={{
            backgroundImage: 'linear-gradient(to right, white 1px, transparent 1px), linear-gradient(to bottom, white 1px, transparent 1px)',
            backgroundSize: '20px 20px'
          }} />
          {/* Subtle accent glow */}
          <div className={cn(
            "absolute -bottom-10 -right-10 w-40 h-40 rounded-full blur-3xl opacity-20",
            texture.accent === 'cyan' && 'bg-cyan-500',
            texture.accent === 'emerald' && 'bg-emerald-500',
            texture.accent === 'amber' && 'bg-amber-500',
            texture.accent === 'purple' && 'bg-purple-500',
            texture.accent === 'rose' && 'bg-rose-500',
            texture.accent === 'blue' && 'bg-blue-500',
          )} />
          
          {/* Badges */}
          <div className="relative z-10 flex justify-between items-start">
             <Badge variant="secondary" className="bg-black/30 backdrop-blur-md text-white border-0 text-[10px] uppercase tracking-widest font-bold">
              {type}
            </Badge>
            
              {hasDiscount && (
              <Badge className="bg-primary text-black font-bold border-primary/30">
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
                  {formatPrice(msrp, currency)}
                </div>
              )}
              <div className="text-xl font-bold text-primary font-mono tracking-tight">
                {formatPrice(final_price || price, currency)}
              </div>
            </div>

            <div className="flex flex-col items-end">
               {isInStock ? (
              <div className="flex items-center gap-1.5 text-[10px] font-bold text-primary bg-primary/10 px-2 py-1 rounded-full ring-1 ring-primary/20">
                <div className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
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

          <div className="mt-4 flex gap-2">
            <Button
              className="flex-1"
              onClick={(e) => {
                e.stopPropagation()
                onClick(id)
              }}
            >
              {t('product.buyNow') || 'Buy now'}
            </Button>
            {onAddToCart && (
              <Button
                variant="outline"
                className="flex-1 border-primary/40 text-primary hover:bg-primary/10"
                onClick={(e) => {
                  e.stopPropagation()
                  onAddToCart(product)
                }}
              >
                {t('product.addToCart') || 'Add to cart'}
              </Button>
            )}
          </div>
        </div>
      </Card>
    </motion.div>
  )
}
