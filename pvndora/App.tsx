
import React, { useState, useEffect, useCallback, useRef } from 'react';
import Navbar from './components/Navbar';
import Hero from './components/Hero';
import Catalog from './components/Catalog';
import Guarantees from './components/Guarantees';
import ProductDetail from './components/ProductDetail';
import CheckoutModal from './components/CheckoutModal';
import Orders from './components/Orders';
import Profile from './components/Profile';
import Leaderboard from './components/Leaderboard';
import Footer from './components/Footer';
import Legal from './components/Legal';
import AdminPanel from './components/AdminPanel';
import SupportChat from './components/SupportChat';
import CommandPalette from './components/CommandPalette';
import { AnimatePresence, motion, useMotionValue, useMotionTemplate } from 'framer-motion';
import { Terminal, CheckCircle, AlertTriangle, Info, Command } from 'lucide-react';

// --- AUDIO ENGINE (Web Audio API) ---
// Pure JS synthesizer to avoid external assets and ensure immediate feedback
class AudioEngine {
    ctx: AudioContext | null = null;
    
    init() {
        if (!this.ctx && typeof window !== 'undefined') {
            const AudioContext = window.AudioContext || (window as any).webkitAudioContext;
            this.ctx = new AudioContext();
        }
    }

    resume() {
        if (this.ctx && this.ctx.state === 'suspended') {
            this.ctx.resume();
        }
    }

    playTone(freq: number, type: OscillatorType, duration: number, vol: number = 0.05) {
        if (!this.ctx) return;
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();
        
        osc.type = type;
        osc.frequency.setValueAtTime(freq, this.ctx.currentTime);
        
        gain.gain.setValueAtTime(vol, this.ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + duration);
        
        osc.connect(gain);
        gain.connect(this.ctx.destination);
        
        osc.start();
        osc.stop(this.ctx.currentTime + duration);
    }

    playNoise(duration: number) {
        if (!this.ctx) return;
        const bufferSize = this.ctx.sampleRate * duration;
        const buffer = this.ctx.createBuffer(1, bufferSize, this.ctx.sampleRate);
        const data = buffer.getChannelData(0);
        for (let i = 0; i < bufferSize; i++) {
            data[i] = Math.random() * 2 - 1;
        }

        const noise = this.ctx.createBufferSource();
        noise.buffer = buffer;
        const gain = this.ctx.createGain();
        gain.gain.setValueAtTime(0.02, this.ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + duration);
        
        noise.connect(gain);
        gain.connect(this.ctx.destination);
        noise.start();
    }

    // --- SFX PRESETS ---
    hover() { this.playTone(800, 'sine', 0.03, 0.01); } // Very subtle blip
    click() { 
        this.playTone(1200, 'square', 0.05, 0.02); 
        this.playNoise(0.05); // Mechanical click
    }
    success() {
        if (!this.ctx) return;
        const now = this.ctx.currentTime;
        this.playTone(440, 'sine', 0.2); // A4
        setTimeout(() => this.playTone(554, 'sine', 0.2), 100); // C#5
        setTimeout(() => this.playTone(659, 'sine', 0.4), 200); // E5
    }
    error() {
        this.playTone(150, 'sawtooth', 0.3, 0.05); // Low buzz
    }
    open() {
        this.playTone(200, 'sine', 0.5, 0.02); // Swoosh
    }
}

const audio = new AudioEngine();

// --- TOAST TYPES ---
interface Toast {
  id: number;
  message: string;
  type: 'success' | 'error' | 'info';
}

// --- MOCK PRODUCT DATA FOR SEARCH ---
// In a real app, this would be imported or fetched
const PRODUCTS_DATA_REF = [
  { id: 1, name: 'Nano Banana Pro', category: 'Text' },
  { id: 2, name: 'Veo 3.1', category: 'Video' },
  { id: 3, name: 'Claude Max', category: 'Text' },
  { id: 4, name: 'GitHub Copilot', category: 'Code' },
  { id: 5, name: 'Runway Gen-2', category: 'Video' },
];

function App() {
  const [selectedProduct, setSelectedProduct] = useState<any | null>(null);
  const [cart, setCart] = useState<any[]>([]);
  const [isCheckoutOpen, setIsCheckoutOpen] = useState(false);
  const [isSupportWidgetOpen, setIsSupportWidgetOpen] = useState(false);
  const [isCmdOpen, setIsCmdOpen] = useState(false);
  
  // Navigation State
  const [currentView, setCurrentView] = useState<'home' | 'orders' | 'profile' | 'leaderboard' | 'legal' | 'admin'>('home');
  const [legalDoc, setLegalDoc] = useState('terms');

  // Toast State
  const [toasts, setToasts] = useState<Toast[]>([]);

  // Initialize Audio on first interaction
  useEffect(() => {
      const initAudio = () => {
          audio.init();
          audio.resume();
          window.removeEventListener('click', initAudio);
          window.removeEventListener('keydown', initAudio);
      };
      window.addEventListener('click', initAudio);
      window.addEventListener('keydown', initAudio);
      
      // CMD+K Listener
      const handleKeyDown = (e: KeyboardEvent) => {
          if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
              e.preventDefault();
              setIsCmdOpen(prev => !prev);
              audio.open();
          }
      };
      window.addEventListener('keydown', handleKeyDown);
      return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // --- UNIFIED FEEDBACK HANDLER ---
  const handleFeedback = useCallback((type: 'light' | 'medium' | 'heavy' | 'success' | 'error' = 'light') => {
      // 1. Haptic
      if (typeof navigator !== 'undefined' && navigator.vibrate) {
          switch (type) {
              case 'light': navigator.vibrate(5); break;
              case 'medium': navigator.vibrate(15); break;
              case 'heavy': navigator.vibrate(30); break;
              case 'success': navigator.vibrate([10, 30, 10]); break;
              case 'error': navigator.vibrate([30, 50, 30, 50, 30]); break;
          }
      }

      // 2. Audio
      audio.resume(); // Ensure context is running
      switch (type) {
          case 'light': audio.hover(); break; // Subtle
          case 'medium': audio.click(); break; // Standard interaction
          case 'heavy': audio.open(); break; // Major interaction
          case 'success': audio.success(); break;
          case 'error': audio.error(); break;
      }
  }, []);

  // --- ACTIONS ---

  const showToast = useCallback((message: string, type: 'success' | 'error' | 'info' = 'info') => {
    const id = Date.now();
    setToasts(prev => [...prev, { id, message, type }]);
    
    if (type === 'success') handleFeedback('success');
    if (type === 'error') handleFeedback('error');
    if (type === 'info') handleFeedback('medium');

    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 3000);
  }, [handleFeedback]);

  const handleProductSelect = (product: any) => {
    handleFeedback('medium');
    setSelectedProduct(product);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleBackToCatalog = () => {
    handleFeedback('light');
    setSelectedProduct(null);
  };

  // UPDATED: Now handles Quantity
  const handleAddToCart = (product: any, quantity: number = 1) => {
    setCart(prevCart => {
      const existingItem = prevCart.find(p => p.id === product.id);
      if (existingItem) {
        // Update quantity if exists
        showToast(`QUANTITY INCREASED: +${quantity}`, 'success');
        return prevCart.map(p => 
          p.id === product.id ? { ...p, quantity: (p.quantity || 1) + quantity } : p
        );
      } else {
        // Add new item
        showToast(`MODULE [${product.name}] MOUNTED`, 'success');
        return [...prevCart, { ...product, quantity }];
      }
    });
  };

  const handleRemoveFromCart = (productId: number) => {
    handleFeedback('medium');
    setCart(cart.filter(item => item.id !== productId));
  };

  const handleOpenCart = () => {
    handleFeedback('medium');
    setIsCheckoutOpen(true);
  };

  const handleClearCart = () => {
    setCart([]);
    setIsCheckoutOpen(false);
    setCurrentView('orders');
    window.scrollTo({ top: 0, behavior: 'smooth' });
    showToast('TRANSACTION COMPLETE. ASSETS TRANSFERRED.', 'success');
  }

  // Navigation Handlers
  const navigate = (view: 'home' | 'orders' | 'profile' | 'leaderboard' | 'legal' | 'admin') => {
      handleFeedback('light');
      setSelectedProduct(null);
      setIsCheckoutOpen(false);
      setCurrentView(view);
      window.scrollTo({ top: 0, behavior: 'smooth' });
  };
  
  // For Command Palette
  const handleUniversalNavigate = (target: any) => {
      handleFeedback('medium');
      if (typeof target === 'string') {
          navigate(target as any);
      } else if (target.type === 'product') {
          // If we are navigating to a product, we need to be on home view but with product selected
          setCurrentView('home');
          setSelectedProduct(target.product);
      }
  };

  const handleNavigateLegal = (doc: string) => {
    handleFeedback('light');
    setLegalDoc(doc);
    setCurrentView('legal');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  // --- SPOTLIGHT LOGIC ---
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);

  useEffect(() => {
    const handleMouseMove = ({ clientX, clientY }: MouseEvent) => {
      mouseX.set(clientX);
      mouseY.set(clientY);
    };
    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  const getActiveTab = () => {
    if (currentView === 'profile') return 'profile';
    if (currentView === 'orders') return 'orders';
    if (currentView === 'leaderboard') return 'leaderboard';
    return 'catalog';
  };

  // Determine if we need to raise the support widget (for sticky mobile elements)
  // UPDATED: Removed check for selectedProduct because navbar is hidden on product detail, 
  // so widget only needs to clear the sticky footer which bottom-24 handles fine.
  // It only needs to raise for Leaderboard where Navbar + HUD are stacked.
  const shouldRaiseSupport = currentView === 'leaderboard';

  return (
    <div className="min-h-screen text-white overflow-x-hidden relative selection:bg-pandora-cyan selection:text-black">
      
      {/* === UNIFIED FIXED BACKGROUND LAYER === */}
      {/* This ensures seamless transition. Hero is bright at top, fades to dark. No steps. */}
      <div className="fixed inset-0 z-[-2] bg-[radial-gradient(circle_at_50%_0%,_#0e3a3a_0%,_#050505_90%)]" />
      
      {/* === 1. GLOBAL BACKGROUND GRID (Fixed Layer) === */}
      <div 
        className="fixed inset-0 pointer-events-none opacity-[0.03] z-[-1]" 
        style={{ 
            backgroundImage: 'linear-gradient(#00FFFF 1px, transparent 1px), linear-gradient(90deg, #00FFFF 1px, transparent 1px)', 
            backgroundSize: '40px 40px',
            backgroundPosition: 'center top'
        }} 
      />

      {/* GLOBAL SPOTLIGHT EFFECT */}
      <motion.div
        className="pointer-events-none fixed inset-0 z-0 transition-opacity duration-300 mix-blend-plus-lighter"
        style={{
          background: useMotionTemplate`
            radial-gradient(
              600px circle at ${mouseX}px ${mouseY}px,
              rgba(0, 255, 255, 0.07),
              transparent 80%
            )
          `,
        }}
      />
      
      {currentView !== 'admin' && (
          <Navbar 
            showMobile={!selectedProduct} 
            cartCount={cart.length} 
            onOpenCart={handleOpenCart}
            onNavigateHome={() => navigate('home')}
            onNavigateOrders={() => navigate('orders')}
            onNavigateProfile={() => navigate('profile')}
            onNavigateLeaderboard={() => navigate('leaderboard')}
            activeTab={getActiveTab()}
            onHaptic={() => handleFeedback('light')}
          />
      )}
      
      {/* Main Content (Transparent to show grid) */}
      <main className="w-full relative z-10">
        <AnimatePresence mode="wait">
          {currentView === 'admin' ? (
            <AdminPanel key="admin" onExit={() => navigate('profile')} />
          ) : currentView === 'profile' ? (
            <Profile key="profile" onBack={() => navigate('home')} onHaptic={handleFeedback} onAdminEnter={() => navigate('admin')} />
          ) : currentView === 'orders' ? (
             <Orders key="orders" onBack={() => navigate('home')} onOpenSupport={() => setIsSupportWidgetOpen(true)} />
          ) : currentView === 'leaderboard' ? (
             <Leaderboard key="leaderboard" onBack={() => navigate('home')} />
          ) : currentView === 'legal' ? (
             <Legal key="legal" doc={legalDoc} onBack={() => navigate('home')} />
          ) : selectedProduct ? (
            <ProductDetail 
              key="detail" 
              product={selectedProduct} 
              onBack={handleBackToCatalog} 
              onAddToCart={handleAddToCart}
              onProductSelect={handleProductSelect}
              isInCart={false} 
              onHaptic={handleFeedback}
            />
          ) : (
            <motion.div 
              key="home"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <Hero />
              <Catalog onSelectProduct={handleProductSelect} onHaptic={handleFeedback} />
              <Guarantees />
              <Footer onNavigate={handleNavigateLegal} onOpenSupport={() => setIsSupportWidgetOpen(true)} />
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      {/* --- COMMAND PALETTE --- */}
      <CommandPalette 
        isOpen={isCmdOpen} 
        onClose={() => setIsCmdOpen(false)} 
        onNavigate={handleUniversalNavigate}
        products={PRODUCTS_DATA_REF} 
      />

      {/* --- CHECKOUT MODAL --- */}
      <AnimatePresence>
        {isCheckoutOpen && (
          <CheckoutModal 
            cart={cart} 
            onClose={() => { handleFeedback('light'); setIsCheckoutOpen(false); }} 
            onRemoveItem={handleRemoveFromCart}
            onSuccess={handleClearCart}
          />
        )}
      </AnimatePresence>

      {/* --- PERSISTENT SUPPORT WIDGET --- */}
      {/* Passing raiseOnMobile to prevent overlap with sticky footers/HUDs */}
      <SupportChat 
        isOpen={isSupportWidgetOpen} 
        onToggle={(val) => setIsSupportWidgetOpen(val)} 
        onHaptic={() => handleFeedback('light')} 
        raiseOnMobile={shouldRaiseSupport}
      />

      {/* --- SYSTEM TOASTS --- */}
      <div className="fixed top-4 left-1/2 -translate-x-1/2 z-[100] flex flex-col gap-2 w-full max-w-sm px-4 pointer-events-none">
        <AnimatePresence>
            {toasts.map(toast => (
                <motion.div
                    key={toast.id}
                    initial={{ opacity: 0, y: -20, scale: 0.9 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: -20, scale: 0.9 }}
                    className={`
                        pointer-events-auto flex items-center gap-3 p-3 border font-mono text-xs shadow-[0_4px_20px_rgba(0,0,0,0.5)] backdrop-blur-md
                        ${toast.type === 'success' ? 'bg-[#0a0a0a] border-pandora-cyan text-pandora-cyan' : ''}
                        ${toast.type === 'error' ? 'bg-red-900/10 border-red-500 text-red-500' : ''}
                        ${toast.type === 'info' ? 'bg-blue-900/10 border-blue-500 text-blue-400' : ''}
                    `}
                >
                    {toast.type === 'success' && <CheckCircle size={16} />}
                    {toast.type === 'error' && <AlertTriangle size={16} />}
                    {toast.type === 'info' && <Terminal size={16} />}
                    <span className="uppercase tracking-wide font-bold">{toast.message}</span>
                </motion.div>
            ))}
        </AnimatePresence>
      </div>
      
      {/* Subtle Grain/Scanline Effect */}
      <div className="fixed inset-0 pointer-events-none z-[100] opacity-[0.02] bg-[url('https://grainy-gradients.vercel.app/noise.svg')] brightness-100 contrast-150" />
    </div>
  );
}

export default App;
