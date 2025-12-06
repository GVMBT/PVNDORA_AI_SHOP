import React from 'react'
import { ShoppingBag, ShieldCheck } from 'lucide-react'
import { motion as Motion } from 'framer-motion'

import { Skeleton } from '../components/ui/skeleton'
import { HeaderBar } from '../components/ui/header-bar'
import OrderSummaryCard from '../components/checkout/OrderSummaryCard'
import PromoBlock from '../components/checkout/PromoBlock'
import TotalSummary from '../components/checkout/TotalSummary'
import { useCheckoutFlow } from '../hooks/useCheckoutFlow'

export default function CheckoutPage({ productId, initialQuantity = 1, onBack, onSuccess }) {
  const {
    product,
    cart,
    promoCode,
    setPromoCode,
    promoResult,
    quantity,
    setQuantity,
    error,
    isCartMode,
    productLoading,
    promoLoading,
    cartLoading,
    currency,
    total,
    subtotal,
    discount,
    handlePromoCheck,
    handleRemovePromo,
    handleCartQuantity,
    handleCartRemove,
    formatPrice,
    t,
    paymentMethod,
    setPaymentMethod,
    availableMethods,
  } = useCheckoutFlow({ productId, initialQuantity, onBack, onSuccess })

  if (productLoading || cartLoading) {
    return (
      <div className="p-6 space-y-6">
        <Skeleton className="h-20 w-full rounded-2xl" />
        <Skeleton className="h-40 w-full rounded-2xl" />
        <Skeleton className="h-32 w-full rounded-2xl" />
      </div>
    )
  }

  if (error || (!product && !cart)) {
    return (
      <div className="flex flex-col items-center justify-center h-[80vh] p-6 text-center space-y-6">
        <div className="p-6 rounded-full bg-destructive/10 text-destructive">
          <ShoppingBag className="h-12 w-12" />
        </div>
        <h3 className="text-xl font-bold">
          {error || (isCartMode ? (t('checkout.cartEmpty') || 'Cart is empty') : t('product.notFound'))}
        </h3>
        <button onClick={onBack} className="rounded-full px-8 border border-input bg-background hover:bg-secondary transition-colors py-2 text-sm font-medium">
          {t('common.back')}
        </button>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background pb-24 relative">
      <div className="absolute inset-0 bg-gradient-to-b from-primary/5 to-background pointer-events-none" />

      <HeaderBar title={t('checkout.title')} onBack={onBack} className="z-20" />

      <div className="p-4 space-y-6 relative z-10">
        <Motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
          <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wider pl-1">
            {t('checkout.summary')}
          </h3>
          <OrderSummaryCard
            isCartMode={isCartMode}
            cart={cart}
            product={product}
            quantity={quantity}
            currency={currency}
            formatPrice={formatPrice}
            t={t}
            onRemoveItem={handleCartRemove}
            onChangeQuantity={handleCartQuantity}
            onChangeSingleQuantity={setQuantity}
          />
        </Motion.div>

        <PromoBlock
          promoCode={promoCode}
          setPromoCode={setPromoCode}
          promoResult={promoResult}
          cart={cart}
          isCartMode={isCartMode}
          promoLoading={promoLoading}
          onApply={handlePromoCheck}
          onRemove={handleRemovePromo}
          t={t}
        />

        <Motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
          <TotalSummary
            subtotal={subtotal}
            discount={discount}
            total={total}
            currency={currency}
            formatPrice={formatPrice}
            t={t}
          />
        </Motion.div>

        <div className="space-y-3">
          <h4 className="text-sm font-semibold px-1">{t('checkout.paymentMethod') || 'Способ оплаты'}</h4>
          <div className="grid grid-cols-2 gap-2">
            {(availableMethods?.length ? availableMethods : ['card', 'sbp', 'qr', 'crypto']).map((m) => (
              <button
                key={m}
                onClick={() => setPaymentMethod(m)}
                className={`rounded-xl border px-3 py-2 text-sm font-semibold transition-all ${
                  paymentMethod === m
                    ? 'border-primary bg-primary/10 text-primary'
                    : 'border-border bg-card/40 text-foreground/80'
                }`}
              >
                {m.toUpperCase()}
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center justify-center gap-2 text-xs text-muted-foreground opacity-70">
          <ShieldCheck className="h-3 w-3" />
          <span>{t('checkout.paymentInfo')}</span>
        </div>
      </div>
    </div>
  )
}
