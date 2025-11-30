import React, { useState, useEffect } from 'react'
import { useSearchParams } from './hooks/useSearchParams'
import { useTelegram } from './hooks/useTelegram'
import { useLocale } from './hooks/useLocale'

// Pages
import CatalogPage from './pages/CatalogPage'
import ProductPage from './pages/ProductPage'
import OrdersPage from './pages/OrdersPage'
import LeaderboardPage from './pages/LeaderboardPage'
import FAQPage from './pages/FAQPage'
import CheckoutPage from './pages/CheckoutPage'

// Components
import Navigation from './components/Navigation'
import LoadingScreen from './components/LoadingScreen'

export default function App() {
  const { initData, user, isReady } = useTelegram()
  const { t, locale, isRTL } = useLocale()
  const params = useSearchParams()
  
  const [currentPage, setCurrentPage] = useState('catalog')
  const [productId, setProductId] = useState(null)
  const [initialQuantity, setInitialQuantity] = useState(1)
  
  // Parse startapp parameter for deep linking
  useEffect(() => {
    const startapp = params.get('startapp') || params.get('tgWebAppStartParam')
    
    if (startapp) {
      if (startapp.startsWith('product_')) {
        const id = startapp.replace('product_', '').split('_ref_')[0]
        setProductId(id)
        setCurrentPage('product')
      } else if (startapp.startsWith('pay_')) {
        // Format: pay_{product_id}_qty_{quantity}
        const parts = startapp.replace('pay_', '')
        if (parts.includes('_qty_')) {
          const [id, qty] = parts.split('_qty_')
          setProductId(id)
          setInitialQuantity(parseInt(qty) || 1)
        } else {
          setProductId(parts)
          setInitialQuantity(1)
        }
        setCurrentPage('checkout')
      } else if (startapp === 'orders') {
        setCurrentPage('orders')
      } else if (startapp === 'leaderboard') {
        setCurrentPage('leaderboard')
      } else if (startapp === 'faq') {
        setCurrentPage('faq')
      } else if (startapp === 'checkout') {
        // Checkout without productId - redirect to catalog
        // (Cart-based checkout not implemented yet)
        setCurrentPage('catalog')
      } else if (startapp === 'catalog') {
        setCurrentPage('catalog')
      }
    }
  }, [params])
  
  // Show loading while Telegram SDK initializes
  if (!isReady) {
    return <LoadingScreen />
  }
  
  const navigateTo = (page, id = null) => {
    setCurrentPage(page)
    if (id) setProductId(id)
    window.scrollTo(0, 0)
  }
  
  const renderPage = () => {
    switch (currentPage) {
      case 'product':
        return (
          <ProductPage 
            productId={productId} 
            onBack={() => navigateTo('catalog')}
            onCheckout={() => navigateTo('checkout', productId)}
          />
        )
      case 'orders':
        return <OrdersPage onBack={() => navigateTo('catalog')} />
      case 'leaderboard':
        return <LeaderboardPage onBack={() => navigateTo('catalog')} />
      case 'faq':
        return <FAQPage onBack={() => navigateTo('catalog')} />
      case 'checkout':
        return (
          <CheckoutPage 
            productId={productId}
            initialQuantity={initialQuantity}
            onBack={() => productId ? navigateTo('product', productId) : navigateTo('catalog')}
            onSuccess={() => navigateTo('orders')}
          />
        )
      default:
        return (
          <CatalogPage 
            onProductClick={(id) => navigateTo('product', id)}
          />
        )
    }
  }
  
  return (
    <div 
      className="min-h-screen bg-gradient-animated"
      dir={isRTL ? 'rtl' : 'ltr'}
    >
      <main className="pb-20 safe-area-bottom">
        {renderPage()}
      </main>
      
      <Navigation 
        currentPage={currentPage}
        onNavigate={navigateTo}
      />
    </div>
  )
}


