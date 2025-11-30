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
import AdminPage from './pages/AdminPage'
import AdminProductsPage from './pages/AdminProductsPage'
import AdminStockPage from './pages/AdminStockPage'
import AdminOrdersPage from './pages/AdminOrdersPage'
import AdminTicketsPage from './pages/AdminTicketsPage'
import AdminAnalyticsPage from './pages/AdminAnalyticsPage'
import AdminFAQPage from './pages/AdminFAQPage'

// Components
import Navigation from './components/Navigation'
import LoadingScreen from './components/LoadingScreen'
import { useAdmin } from './hooks/useAdmin'

export default function App() {
  const { initData, user, isReady } = useTelegram()
  const { t, locale, isRTL } = useLocale()
  const { isAdmin, checking } = useAdmin()
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
        // Cart-based checkout
        setCurrentPage('checkout')
        setProductId(null)
      } else if (startapp === 'catalog') {
        setCurrentPage('catalog')
      } else if (startapp === 'admin') {
        setCurrentPage('admin')
      } else if (startapp.startsWith('admin_')) {
        setCurrentPage(startapp)
      }
    }
  }, [params])
  
  // Show loading while Telegram SDK initializes or checking admin status
  if (!isReady || checking) {
    return <LoadingScreen />
  }
  
  const navigateTo = (page, id = null) => {
    setCurrentPage(page)
    if (id) setProductId(id)
    window.scrollTo(0, 0)
  }
  
  const renderPage = () => {
    // Admin pages
    if (currentPage === 'admin') {
      return <AdminPage onNavigate={navigateTo} />
    }
    if (currentPage === 'admin_products') {
      return <AdminProductsPage onBack={() => navigateTo('admin')} />
    }
    if (currentPage === 'admin_stock') {
      return <AdminStockPage onBack={() => navigateTo('admin')} />
    }
    if (currentPage === 'admin_orders') {
      return <AdminOrdersPage onBack={() => navigateTo('admin')} />
    }
    if (currentPage === 'admin_tickets') {
      return <AdminTicketsPage onBack={() => navigateTo('admin')} />
    }
    if (currentPage === 'admin_analytics') {
      return <AdminAnalyticsPage onBack={() => navigateTo('admin')} />
    }
    if (currentPage === 'admin_faq') {
      return <AdminFAQPage onBack={() => navigateTo('admin')} />
    }

    // User pages
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
        isAdmin={isAdmin}
      />
    </div>
  )
}


