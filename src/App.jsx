import React, { useState, useEffect } from 'react'
import { useSearchParams } from './hooks/useSearchParams'
import { useTelegram } from './hooks/useTelegram'
import { useLocale } from './hooks/useLocale'
import { AnimatePresence, motion } from 'framer-motion'

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
import LoginPage from './pages/LoginPage'

// Components
import Navigation from './components/Navigation'
import LoadingScreen from './components/LoadingScreen'
import DesktopLayout from './components/DesktopLayout'
import { useAdmin } from './hooks/useAdmin'

// Check if running outside Telegram
const isWebMode = () => {
  return !window.Telegram?.WebApp?.initData
}

// Check if desktop viewport
const isDesktop = () => {
  return window.innerWidth >= 1024
}

export default function App() {
  const { initData, user, isReady } = useTelegram()
  const { t, locale, isRTL } = useLocale()
  const { isAdmin, checking } = useAdmin()
  const params = useSearchParams()
  
  const [currentPage, setCurrentPage] = useState('catalog')
  const [productId, setProductId] = useState(null)
  const [initialQuantity, setInitialQuantity] = useState(1)
  const [webUser, setWebUser] = useState(null)
  const [showLoginModal, setShowLoginModal] = useState(false)
  
  // Check for existing web session
  useEffect(() => {
    if (isWebMode()) {
      const savedUser = localStorage.getItem('pvndora_user')
      const sessionToken = localStorage.getItem('pvndora_session')
      
      if (savedUser && sessionToken) {
        // Verify session is still valid
        fetch('/api/webapp/auth/verify-session', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_token: sessionToken })
        })
          .then(res => res.ok ? res.json() : Promise.reject())
          .then(data => {
            if (data.valid) {
              setWebUser(JSON.parse(savedUser))
              setCurrentPage('admin') // Web users go straight to admin
            }
          })
          .catch(() => {
            // Clear invalid session
            localStorage.removeItem('pvndora_user')
            localStorage.removeItem('pvndora_session')
          })
      }
    }
  }, [])
  
  // Parse startapp parameter for deep linking
  useEffect(() => {
    const startapp = params.get('startapp') || params.get('tgWebAppStartParam')
    
    // Debug logging
    console.log('DEBUG: App.jsx - startapp param:', startapp)
    
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
  
  // Web mode without auth: allow browsing but show login for protected actions
  // Only block completely if trying to access admin
  if (isWebMode() && !webUser && currentPage.startsWith('admin')) {
    return (
      <LoginPage 
        onLogin={(userData, token) => {
          setWebUser(userData)
        }}
      />
    )
  }
  
  // Show loading while Telegram SDK initializes or checking admin status
  if (!isWebMode() && (!isReady || checking)) {
    return <LoadingScreen />
  }
  
  const navigateTo = (page, id = null) => {
    if (window.Telegram?.WebApp?.HapticFeedback) {
      window.Telegram.WebApp.HapticFeedback.impactOccurred('light')
    }
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
  
  // Handle login callback
  const handleWebLogin = (userData, token) => {
    setWebUser(userData)
    setShowLoginModal(false)
    // Redirect to admin if admin, otherwise to catalog
    if (userData.is_admin) {
      setCurrentPage('admin')
    } else {
      setCurrentPage('catalog')
    }
  }
  
  // Desktop layout for web users on large screens
  if (isWebMode() && isDesktop()) {
    // Show login modal if requested
    if (showLoginModal) {
      return (
        <LoginPage 
          onLogin={handleWebLogin}
        />
      )
    }
    
    return (
      <DesktopLayout
        currentPage={currentPage}
        onNavigate={navigateTo}
        isAdmin={webUser?.is_admin || isAdmin}
        user={webUser}
        onLogin={() => setShowLoginModal(true)}
      >
        <AnimatePresence mode="wait">
          <motion.div
            key={currentPage}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
          >
            {renderPage()}
          </motion.div>
        </AnimatePresence>
      </DesktopLayout>
    )
  }
  
  // Mobile layout (Telegram Mini App or mobile web)
  return (
    <div 
      className="min-h-screen bg-background text-foreground overflow-x-hidden"
      dir={isRTL ? 'rtl' : 'ltr'}
    >
      {/* Ambient Background */}
      <div className="fixed inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-primary/5 via-background to-background pointer-events-none z-0" />
      
      <main className="relative z-10 pb-24 safe-area-bottom min-h-screen">
        <AnimatePresence mode="wait">
          <motion.div
            key={currentPage}
            initial={{ opacity: 0, y: 10, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.98 }}
            transition={{ duration: 0.25, ease: [0.32, 0.72, 0, 1] }}
          >
            {renderPage()}
          </motion.div>
        </AnimatePresence>
      </main>
      
      <Navigation 
        currentPage={currentPage}
        onNavigate={navigateTo}
        isAdmin={isAdmin}
      />
    </div>
  )
}
