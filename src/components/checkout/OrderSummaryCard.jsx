import React from 'react'
import { Card, CardContent } from '../ui/card'
import { Button } from '../ui/button'
import { Separator } from '../ui/separator'
import { Minus, Plus, X } from 'lucide-react'

/**
 * Order summary block: renders either cart items or single product with quantity controls.
 */
export function OrderSummaryCard({
  isCartMode,
  cart,
  product,
  quantity,
  currency,
  formatPrice,
  t,
  onRemoveItem,
  onChangeQuantity,
  onChangeSingleQuantity,
}) {
  if (isCartMode && (!cart || !cart.items || cart.items.length === 0)) {
    return null
  }

  return (
    <Card className="border-0 bg-card/40 backdrop-blur-xl shadow-lg ring-1 ring-white/10 overflow-hidden">
      <CardContent className="p-0">
        {isCartMode ? (
          <div className="divide-y divide-white/5">
            {cart.items.map((item, index) => (
              <div key={index} className="p-4 space-y-2">
                <div className="flex justify-between items-center">
                  <div>
                    <p className="font-bold text-foreground">{item.product_name}</p>
                    <p className="text-xs text-muted-foreground mt-1">
                      {item.instant_quantity > 0 ? `${item.instant_quantity} instant` : null}
                      {item.prepaid_quantity > 0 ? `${item.instant_quantity > 0 ? ' • ' : ''}${item.prepaid_quantity} prepaid` : null}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <p className="font-mono font-bold">{formatPrice(item.total_price, item.currency || currency)}</p>
                    <Button variant="ghost" size="icon" className="h-8 w-8 rounded-md" onClick={() => onRemoveItem(item.product_id)}>
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
                <div className="flex items-center justify-end gap-3">
                  <div className="flex items-center gap-3 bg-background rounded-lg p-1 shadow-sm">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 rounded-md hover:bg-secondary"
                      onClick={() => onChangeQuantity(item.product_id, Math.max(0, item.quantity - 1))}
                    >
                      <Minus className="h-4 w-4" />
                    </Button>
                    <span className="font-mono font-bold w-6 text-center">{item.quantity}</span>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 rounded-md hover:bg-secondary"
                      onClick={() => onChangeQuantity(item.product_id, item.quantity + 1)}
                    >
                      <Plus className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="p-5 space-y-4">
            <div className="flex justify-between items-start">
              <h2 className="text-xl font-bold leading-tight pr-4">{product?.name}</h2>
              <p className="font-mono text-primary font-bold text-lg whitespace-nowrap">
                {formatPrice(product?.final_price || product?.price, currency)}
              </p>
            </div>

            <Separator className="bg-white/5" />

            <div className="flex items-center justify-between bg-secondary/30 p-2 rounded-xl">
              <span className="text-sm font-medium pl-2">{t('checkout.quantity')}</span>
              <div className="flex items-center gap-3 bg-background rounded-lg p-1 shadow-sm">
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 rounded-md hover:bg-secondary"
                  onClick={() => onChangeSingleQuantity(Math.max(1, quantity - 1))}
                >
                  <Minus className="h-4 w-4" />
                </Button>
                <span className="font-mono font-bold w-6 text-center">{quantity}</span>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 rounded-md hover:bg-secondary"
                  onClick={() => onChangeSingleQuantity(quantity + 1)}
                >
                  <Plus className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export default OrderSummaryCard
