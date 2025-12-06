import { useState, useEffect, useCallback, useMemo } from 'react'

import { useProducts, useOrders, usePromo, useCart } from './useApi'
import { useLocale } from './useLocale'
import { useTelegram } from './useTelegram'

/**
 * Инкапсулирует логику страницы Checkout: загрузка товара/корзины,
 * промокоды, пересчёт тоталов, оформление заказа и взаимодействие
 * с Telegram UI (back/main buttons, haptics, alerts).
 */
export function useCheckoutFlow({ productId, initialQuantity = 1, onBack, onSuccess }) {
  const { getProduct, loading: productLoading } = useProducts()
  const { createOrderFromCart, getPaymentMethods } = useOrders()
  const { checkPromo, loading: promoLoading } = usePromo()
  const { getCart, addToCart, updateCartItem, removeCartItem, applyCartPromo, removeCartPromo, loading: cartLoading } = useCart()
  const { t, formatPrice } = useLocale()
  const { setBackButton, setMainButton, hapticFeedback, showAlert } = useTelegram()

  const [product, setProduct] = useState(null)
  const [cart, setCart] = useState(null)
  const [promoCode, setPromoCode] = useState('')
  const [promoResult, setPromoResult] = useState(null)
  const [quantity, setQuantity] = useState(initialQuantity)
  const [error, setError] = useState(null)
  const [paymentMethod, setPaymentMethod] = useState('card')
  const [availableMethods, setAvailableMethods] = useState([])
  const isCartMode = !productId

  const loadProduct = useCallback(async () => {
    try {
      const data = await getProduct(productId)
      setProduct(data.product)
    } catch (err) {
      setError(err.message)
    }
  }, [getProduct, productId])

  const loadCart = useCallback(async () => {
    try {
      const data = await getCart()
      if (data && data.items && Array.isArray(data.items) && data.items.length > 0) {
        setCart(data)
        if (data.promo_code) {
          setPromoCode(data.promo_code)
        }
      } else {
        setError(t('checkout.cartEmpty') || 'Cart is empty')
      }
    } catch (err) {
      setError(err.message)
    }
  }, [getCart, t])

  const calculateTotal = useCallback(() => {
    if (isCartMode) {
      if (!cart || !cart.items || !Array.isArray(cart.items) || cart.items.length === 0) return 0

      let total = cart.total || cart.subtotal || 0

      if (promoResult?.is_valid && promoResult.discount_percent) {
        total = total * (1 - promoResult.discount_percent / 100)
      }

      return total
    }

    if (!product) return 0

    const price = product.final_price || product.price
    let total = price * quantity

    if (promoResult?.is_valid) {
      if (promoResult.discount_percent) {
        total = total * (1 - promoResult.discount_percent / 100)
      } else if (promoResult.discount_amount) {
        total = Math.max(0, total - promoResult.discount_amount)
      }
    }

    return total
  }, [isCartMode, cart, promoResult, product, quantity])

  const handlePromoCheck = useCallback(async () => {
    if (!promoCode.trim()) return

    try {
      if (isCartMode) {
        const updated = await applyCartPromo(promoCode)
        setCart(updated)
        setPromoResult({ is_valid: true, discount_percent: updated.promo_discount_percent || 0 })
        hapticFeedback('notification', 'success')
      } else {
        const result = await checkPromo(promoCode)
        setPromoResult(result)

        if (result.is_valid) {
          hapticFeedback('notification', 'success')
        } else {
          hapticFeedback('notification', 'error')
        }
      }
    } catch (err) {
      setPromoResult({ is_valid: false, error: err.message })
      hapticFeedback('notification', 'error')
      await showAlert(err.message)
    }
  }, [applyCartPromo, checkPromo, hapticFeedback, isCartMode, promoCode, showAlert])

  const handleRemovePromo = useCallback(async () => {
    if (!isCartMode) {
      setPromoResult(null)
      setPromoCode('')
      return
    }
    try {
      const updated = await removeCartPromo()
      setCart(updated)
      setPromoResult(null)
      setPromoCode('')
      hapticFeedback('notification', 'success')
    } catch (err) {
      await showAlert(err.message)
    }
  }, [hapticFeedback, isCartMode, removeCartPromo, showAlert])

  const handleCartQuantity = useCallback(async (pid, newQuantity) => {
    try {
      hapticFeedback('selection')
      const updated = await updateCartItem(pid, newQuantity)
      setCart(updated)
    } catch (err) {
      await showAlert(err.message)
    }
  }, [hapticFeedback, showAlert, updateCartItem])

  const handleCartRemove = useCallback(async (pid) => {
    try {
      hapticFeedback('selection')
      const updated = await removeCartItem(pid)
      setCart(updated)
    } catch (err) {
      await showAlert(err.message)
    }
  }, [hapticFeedback, removeCartItem, showAlert])

  const handleCheckout = useCallback(async () => {
    try {
      hapticFeedback('impact', 'medium')
      setMainButton({ isLoading: true })

      // Всегда идём через корзину: если в режиме товара, сначала положим в корзину
      if (!isCartMode && productId) {
        await addToCart(productId, quantity)
      }

      if (promoResult?.is_valid && promoCode) {
        await applyCartPromo(promoCode)
      }

      const result = await createOrderFromCart(
        promoResult?.is_valid ? promoCode : null,
        paymentMethod
      )

      hapticFeedback('notification', 'success')

      if (result.payment_url) {
        if (window.Telegram?.WebApp?.openLink) {
          window.Telegram.WebApp.openLink(result.payment_url)
        } else {
          window.open(result.payment_url, '_blank')
        }
        setTimeout(() => {
          if (window.Telegram?.WebApp?.close) {
            window.Telegram.WebApp.close()
          }
        }, 500)
      } else {
        await showAlert(t('checkout.orderCreated'))
        onSuccess()
      }

    } catch (err) {
      hapticFeedback('notification', 'error')
      await showAlert(err.message)
    } finally {
      setMainButton({ isLoading: false })
    }
  }, [
    addToCart,
    applyCartPromo,
    createOrderFromCart,
    hapticFeedback,
    isCartMode,
    onSuccess,
    productId,
    promoCode,
    promoResult,
    quantity,
    setMainButton,
    showAlert,
    t
  ])

  useEffect(() => {
    if (productId) {
      loadProduct()
    } else {
      loadCart()
    }
    // load payment methods
    getPaymentMethods()
      .then((data) => {
        if (data && Array.isArray(data.systems)) {
          setAvailableMethods(data.systems.map((s) => s.system_group))
          setPaymentMethod(data.systems[0]?.system_group || 'card')
        } else {
          setAvailableMethods(['card', 'sbp', 'qr', 'crypto'])
        }
      })
      .catch(() => setAvailableMethods(['card', 'sbp', 'qr', 'crypto']))

    setBackButton({
      isVisible: true,
      onClick: onBack
    })

    return () => {
      setBackButton({ isVisible: false })
      setMainButton({ isVisible: false })
    }
  }, [productId, loadProduct, loadCart, onBack, setBackButton, setMainButton, getPaymentMethods])

  useEffect(() => {
    const total = calculateTotal()
    if (total > 0) {
      const currency = product?.currency || cart?.currency || 'USD'
      setMainButton({
        text: `${t('checkout.pay')} ${formatPrice(total, currency)}`,
        isVisible: true,
        onClick: handleCheckout
      })
    }
  }, [product, cart, calculateTotal, formatPrice, t, handleCheckout, setMainButton])

  const total = calculateTotal()
  const currency = product?.currency || cart?.currency || 'USD'

  const priceMeta = useMemo(() => {
    let subtotal = 0
    let discount = 0

    if (isCartMode && cart) {
      subtotal = cart.subtotal || 0
      discount = subtotal - total
    } else if (!isCartMode && product) {
      const basePrice = (product.final_price || product.price) * quantity
      subtotal = basePrice
      discount = subtotal - total
    }

    return { subtotal, discount }
  }, [isCartMode, cart, product, quantity, total])

  return {
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
    subtotal: priceMeta.subtotal,
    discount: priceMeta.discount,
    handlePromoCheck,
    handleRemovePromo,
    handleCartQuantity,
    handleCartRemove,
    handleCheckout,
    calculateTotal,
    formatPrice,
    t,
    paymentMethod,
    setPaymentMethod,
    availableMethods,
  }
}

export default useCheckoutFlow
