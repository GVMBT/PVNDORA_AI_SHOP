import React from 'react'
import { useLocale } from '../hooks/useLocale'
import { Star, Clock, ShieldCheck, Package } from 'lucide-react'
import { Card, CardContent, CardFooter } from './ui/card'
import { Badge } from './ui/badge'
import { cn } from '../lib/utils'

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
  const savings = msrp && final_price ? msrp - final_price : 0
  
  return (
    <Card 
      className="overflow-hidden hover:border-primary transition-colors cursor-pointer group h-full flex flex-col bg-card/50 backdrop-blur-sm"
      onClick={() => onClick(id)}
    >
      <CardContent className="p-4 flex-1 flex flex-col">
        {/* Header */}
        <div className="flex items-start justify-between mb-3">
          <Badge variant="secondary" className="text-[10px] uppercase tracking-wider bg-secondary/50">
            {type}
          </Badge>
          
          {hasDiscount && (
            <Badge variant="success" className="bg-primary/10 text-primary">
              -{discount_percent}%
            </Badge>
          )}
        </div>
        
        {/* Name */}
        <h3 className="font-bold text-lg leading-tight mb-2 group-hover:text-primary transition-colors line-clamp-2">
          {name}
        </h3>
        
        {/* Social Proof */}
        {socialProof && (socialProof.review_count > 0 || socialProof.sales_count > 0) && (
          <div className="flex items-center gap-3 text-xs text-muted-foreground mb-4 mt-auto">
            {socialProof.rating > 0 && (
              <div className="flex items-center gap-1">
                <Star className="w-3.5 h-3.5 fill-yellow-500 text-yellow-500" />
                <span className="font-medium text-foreground">{socialProof.rating}</span>
                <span>({socialProof.review_count})</span>
              </div>
            )}
            
            {socialProof.sales_count > 0 && (
              <div className="flex items-center gap-1">
                <Package className="w-3.5 h-3.5" />
                <span>{socialProof.sales_count} {t('product.sold')}</span>
              </div>
            )}
          </div>
        )}
      </CardContent>
      
      <CardFooter className="p-4 pt-0 flex items-end justify-between">
        <div>
          {hasDiscount && msrp && (
            <div className="text-xs text-muted-foreground line-through mb-0.5">
              {formatPrice(msrp)}
            </div>
          )}
          <div className="text-xl font-bold text-primary">
            {formatPrice(final_price || price)}
          </div>
        </div>
        
        <div>
          {isInStock ? (
            <div className="flex items-center gap-1.5 text-[10px] font-medium text-primary bg-primary/10 px-2 py-1 rounded-full">
              <div className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
              {t('product.inStock')}
            </div>
          ) : can_fulfill_on_demand ? (
            <div className="flex items-center gap-1.5 text-[10px] font-medium text-yellow-500 bg-yellow-500/10 px-2 py-1 rounded-full">
              <Clock className="w-3 h-3" />
              {t('product.onDemand')}
            </div>
          ) : (
            <div className="flex items-center gap-1.5 text-[10px] font-medium text-destructive bg-destructive/10 px-2 py-1 rounded-full">
              <div className="w-1.5 h-1.5 rounded-full bg-destructive" />
              {t('product.outOfStock')}
            </div>
          )}
        </div>
      </CardFooter>
    </Card>
  )
}
