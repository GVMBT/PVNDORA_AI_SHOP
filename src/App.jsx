import React, { useState, useEffect } from 'react'
import { useSearchParams } from './hooks/useSearchParams'
import { useTelegram } from './hooks/useTelegram'
import { useLocale } from './hooks/useLocale'

// Pages
import CatalogPage from './pages/CatalogPage'
import ProductPage from './pages/ProductPage'
import OrdersPage from './pages/OrdersPage'
import LeaderboardPage from './pages/LeaderboardPage'
import ProfilePage from './pages/ProfilePage'
import FAQPage from './pages/FAQPage'
import CheckoutPage from './pages/CheckoutPage'
import AdminPage from './pages/AdminPage'
import AdminProductsPage from './pages/AdminProductsPage'
import AdminStockPage from './pages/AdminStockPage'
import AdminOrdersPage from './pages/AdminOrdersPage'
import AdminTicketsPage from './pages/AdminTicketsPage'
import AdminAnalyticsPage from './pages/AdminAnalyticsPage'
import AdminFAQPage from './pages/AdminFAQPage'
import AdminReferralPage from './pages/AdminReferralPage'
import ContactsPage from './pages/ContactsPage'
import RefundPolicyPage from './pages/RefundPolicyPage'
import PaymentInfoPage from './pages/PaymentInfoPage'
import TermsPage from './pages/TermsPage'
import PrivacyPage from './pages/PrivacyPage'

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
    
    // Debug logging
    console.log('DEBUG: App.jsx - startapp param:', startapp)
    console.log('DEBUG: App.jsx - all params:', Array.from(params.entries()))
    console.log('DEBUG: App.jsx - window.location.search:', window.location.search)
    console.log('DEBUG: App.jsx - window.location.hash:', window.location.hash)
    
    if (startapp) {
      if (startapp.startsWith('product_')) {
        const id = startapp.replace('product_', '').split('_ref_')[0]
        setProductId(id)
        setCurrentPage('product')
      } else if (startapp.startsWith('pay_')) {
        // Format: pay_{product_id}_qty_{quantity}
        const parts = startapp.replace('pay_', '')
        console.log('DEBUG: App.jsx - pay_ detected, parts:', parts)
        if (parts.includes('_qty_')) {
          const [id, qty] = parts.split('_qty_')
          console.log('DEBUG: App.jsx - parsed product_id:', id, 'quantity:', qty)
          setProductId(id)
          setInitialQuantity(parseInt(qty) || 1)
        } else {
          console.log('DEBUG: App.jsx - no _qty_ found, using parts as product_id:', parts)
          setProductId(parts)
          setInitialQuantity(1)
        }
        console.log('DEBUG: App.jsx - setting currentPage to checkout')
        setCurrentPage('checkout')
      } else if (startapp === 'orders') {
        setCurrentPage('orders')
      } else if (startapp === 'leaderboard') {
        setCurrentPage('leaderboard')
      } else if (startapp === 'faq') {
        setCurrentPage('faq')
      } else if (startapp === 'profile') {
        setCurrentPage('profile')
      } else if (startapp === 'contacts') {
        setCurrentPage('contacts')
      } else if (startapp === 'refund') {
        setCurrentPage('refund')
      } else if (startapp === 'payment') {
        setCurrentPage('payment')
      } else if (startapp === 'terms') {
        setCurrentPage('terms')
      } else if (startapp === 'privacy') {
        setCurrentPage('privacy')
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
    } else {
      console.log('DEBUG: App.jsx - no startapp found, staying on catalog')
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
    if (currentPage === 'admin_referral') {
      return <AdminReferralPage onBack={() => navigateTo('admin')} />
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
      case 'profile':
        return <ProfilePage onBack={() => navigateTo('catalog')} />
      case 'faq':
        return <FAQPage onBack={() => navigateTo('catalog')} onNavigate={navigateTo} />
      case 'contacts':
        return <ContactsPage onBack={() => navigateTo('catalog')} />
      case 'refund':
        return <RefundPolicyPage onBack={() => navigateTo('catalog')} />
      case 'payment':
        return <PaymentInfoPage onBack={() => navigateTo('catalog')} />
      case 'terms':
        return <TermsPage onBack={() => navigateTo('catalog')} />
      case 'privacy':
        return <PrivacyPage onBack={() => navigateTo('catalog')} />
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


