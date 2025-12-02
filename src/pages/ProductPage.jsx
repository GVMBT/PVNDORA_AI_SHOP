import React, { useState, useEffect } from 'react'
import { useProducts } from '../hooks/useApi'
import { useLocale } from '../hooks/useLocale'
import { useTelegram } from '../hooks/useTelegram'
import StarRating from '../components/StarRating'
import { 
  ArrowLeft, 
  Star, 
  Clock, 
  Package, 
  ShieldCheck, 
  FileText, 
  Share2, 
  Heart,
  Zap,
  Users,
  CheckCircle
} from 'lucide-react'
import { Button } from '../components/ui/button'
import { Badge } from '../components/ui/badge'
import { Skeleton } from '../components/ui/skeleton'
import { Card, CardContent } from '../components/ui/card'
import { Separator } from '../components/ui/separator'

export default function ProductPage({ productId, onBack, onCheckout }) {
  const { getProduct, loading, error } = useProducts()
  const { t, formatPrice, formatDate } = useLocale()
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
  }, [productId])
  
  const loadProduct = async () => {
    try {
      const data = await getProduct(productId)
      setProduct(data.product)
      setSocialProof(data.social_proof)
    } catch (err) {
      console.error('Failed to load product:', err)
    }
  }
  
  const handleBuy = () => {
    hapticFeedback('impact', 'medium')
    onCheckout()
  }
  
  if (loading) {
    return (
      <div className="p-4 space-y-4">
        <div className="flex gap-2">
          <Skeleton className="h-8 w-8 rounded-full" />
          <Skeleton className="h-8 w-24 rounded-full" />
        </div>
        <Skeleton className="h-10 w-3/4 rounded-xl" />
        <Skeleton className="h-32 w-full rounded-xl" />
        <div className="grid grid-cols-2 gap-4">
          <Skeleton className="h-20 w-full rounded-xl" />
          <Skeleton className="h-20 w-full rounded-xl" />
        </div>
      </div>
    )
  }
  
  if (error || !product) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] p-6 text-center space-y-4">
        <div className="p-4 rounded-full bg-destructive/10 text-destructive">
          <Package className="h-8 w-8" />
        </div>
        <h3 className="text-xl font-semibold">
          {error || t('product.notFound')}
        </h3>
        <Button onClick={onBack} variant="outline">
          {t('common.back')}
        </Button>
      </div>
    )
  }
  
  const {
    name,
    description,
    price,
    msrp,
    discount_percent,
    final_price,
    available_count,
    can_fulfill_on_demand,
    fulfillment_time_hours,
    type,
    warranty_days,
    duration_days,
    instructions
  } = product
  
  const hasDiscount = discount_percent > 0
  const isInStock = available_count > 0
  const savings = msrp && final_price ? msrp - final_price : 0
  
  return (
    <div className="pb-32">
      {/* Navigation Header */}
      <div className="sticky top-0 z-10 bg-background/80 backdrop-blur-md border-b border-border/50 p-4 flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={onBack} className="h-8 w-8 rounded-full">
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <span className="font-semibold truncate">{name}</span>
      </div>

      <div className="p-4 space-y-6">
        {/* Badges */}
        <div className="flex gap-2 flex-wrap">
          <Badge variant="secondary" className="text-xs uppercase tracking-wider">
            {type}
          </Badge>
          {hasDiscount && (
            <Badge variant="success" className="bg-primary/10 text-primary">
              -{discount_percent}% OFF
            </Badge>
          )}
          {isInStock ? (
            <Badge variant="outline" className="text-primary border-primary/20 bg-primary/5">
              {t('product.inStock')}
            </Badge>
          ) : can_fulfill_on_demand ? (
            <Badge variant="warning" className="bg-yellow-500/10 text-yellow-500">
              {t('product.onDemand')}
            </Badge>
          ) : (
            <Badge variant="destructive" className="bg-destructive/10 text-destructive">
              {t('product.outOfStock')}
            </Badge>
          )}
        </div>

        {/* Title & Price */}
        <div className="space-y-2">
          <h1 className="text-3xl font-bold leading-tight">{name}</h1>
          
          <div className="flex items-end gap-3">
            <span className="text-3xl font-bold text-primary">
              {formatPrice(final_price || price)}
            </span>
            {hasDiscount && msrp && (
              <span className="text-lg text-muted-foreground line-through mb-1">
                {formatPrice(msrp)}
              </span>
            )}
          </div>
          
          {savings > 0 && (
            <p className="text-sm text-green-500 font-medium">
              {t('product.save')} {formatPrice(savings)}
            </p>
          )}
        </div>

        {/* Description */}
        {description && (
          <p className="text-muted-foreground leading-relaxed">
            {description}
          </p>
        )}

        {/* Key Benefits */}
        <div className="flex flex-wrap gap-2">
          {isInStock && (
            <div className="flex items-center gap-1.5 text-xs bg-green-500/10 text-green-500 px-3 py-1.5 rounded-full">
              <Zap className="h-3 w-3" />
              <span>{t('product.instantDelivery')}</span>
            </div>
          )}
          {warranty_days > 0 && (
            <div className="flex items-center gap-1.5 text-xs bg-blue-500/10 text-blue-500 px-3 py-1.5 rounded-full">
              <ShieldCheck className="h-3 w-3" />
              <span>{warranty_days}d {t('product.warranty')}</span>
            </div>
          )}
          {socialProof?.sales_count > 10 && (
            <div className="flex items-center gap-1.5 text-xs bg-purple-500/10 text-purple-500 px-3 py-1.5 rounded-full">
              <Users className="h-3 w-3" />
              <span>{socialProof.sales_count}+ {t('product.sold')}</span>
            </div>
          )}
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 gap-3">
          {warranty_days > 0 && (
            <Card className="bg-card/50 border-none">
              <CardContent className="p-4 flex flex-col items-center text-center gap-2">
                <ShieldCheck className="h-6 w-6 text-primary" />
                <div>
                  <p className="text-xs text-muted-foreground">{t('product.warranty')}</p>
                  <p className="font-semibold">{warranty_days} {t('common.days')}</p>
                </div>
              </CardContent>
            </Card>
          )}
          
          {duration_days > 0 && (
            <Card className="bg-card/50 border-none">
              <CardContent className="p-4 flex flex-col items-center text-center gap-2">
                <Clock className="h-6 w-6 text-primary" />
                <div>
                  <p className="text-xs text-muted-foreground">{t('product.duration')}</p>
                  <p className="font-semibold">{duration_days} {t('common.days')}</p>
                </div>
              </CardContent>
            </Card>
          )}
          
          {fulfillment_time_hours && !isInStock && can_fulfill_on_demand && (
            <Card className="bg-card/50 border-none">
              <CardContent className="p-4 flex flex-col items-center text-center gap-2">
                <Clock className="h-6 w-6 text-yellow-500" />
                <div>
                  <p className="text-xs text-muted-foreground">{t('product.fulfillmentTime')}</p>
                  <p className="font-semibold">{fulfillment_time_hours}h</p>
                </div>
              </CardContent>
            </Card>
          )}
          
          {available_count > 0 && (
            <Card className="bg-card/50 border-none">
              <CardContent className="p-4 flex flex-col items-center text-center gap-2">
                <Package className="h-6 w-6 text-green-500" />
                <div>
                  <p className="text-xs text-muted-foreground">{t('product.available')}</p>
                  <p className="font-semibold">{available_count} {t('product.units')}</p>
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Social Proof */}
        {socialProof && (
          <Card className="bg-card/30">
            <CardContent className="p-4 flex justify-between items-center">
              <div className="flex items-center gap-2">
                <div className="flex items-center gap-1 text-yellow-500">
                  <Star className="h-5 w-5 fill-current" />
                  <span className="font-bold text-lg">{socialProof.rating}</span>
                </div>
                <span className="text-sm text-muted-foreground">
                  ({socialProof.review_count} {t('product.reviews')})
                </span>
              </div>
              
              {socialProof.sales_count > 0 && (
                <div className="flex items-center gap-1.5 text-sm font-medium">
                  <Package className="h-4 w-4 text-muted-foreground" />
                  <span>{socialProof.sales_count}+ {t('product.sold')}</span>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Instructions */}
        {instructions && (
          <div className="space-y-3">
            <h3 className="font-semibold flex items-center gap-2">
              <FileText className="h-4 w-4 text-primary" />
              {t('product.instructions')}
            </h3>
            <div className="bg-secondary/30 rounded-xl p-4 text-sm text-muted-foreground whitespace-pre-wrap border border-border/50">
              {instructions}
            </div>
          </div>
        )}

        {/* Reviews List */}
        {socialProof?.recent_reviews?.length > 0 && (
          <div className="space-y-4 pt-4">
            <h3 className="font-semibold text-lg">{t('product.recentReviews')}</h3>
            <div className="space-y-4">
              {socialProof.recent_reviews.map((review, index) => (
                <div key={index} className="space-y-2">
                  <div className="flex justify-between items-start">
                    <span className="font-medium">{review.author}</span>
                    <span className="text-xs text-muted-foreground">
                      {formatDate(review.date)}
                    </span>
                  </div>
                  <StarRating rating={review.rating} size="sm" />
                  {review.text && (
                    <p className="text-sm text-muted-foreground">{review.text}</p>
                  )}
                  {index < socialProof.recent_reviews.length - 1 && (
                    <Separator className="mt-4" />
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
      
      {/* Floating Action Button - above navigation (nav is h-16 = 64px + safe area) */}
      <div className="fixed bottom-[calc(4rem+1rem+env(safe-area-inset-bottom))] left-4 right-4 z-40">
        <Button
          onClick={handleBuy}
          disabled={!isInStock && !can_fulfill_on_demand}
          className="w-full h-14 text-lg font-semibold shadow-2xl shadow-primary/30 bg-gradient-to-r from-primary to-emerald-500 hover:from-primary/90 hover:to-emerald-500/90"
          size="lg"
        >
          {isInStock ? (
            <>
              {t('product.buyNow')}
              <span className="ml-2">→</span>
            </>
          ) : can_fulfill_on_demand ? (
            t('product.preorder')
          ) : (
            t('product.notifyMe')
          )}
        </Button>
      </div>
    </div>
  )
}
