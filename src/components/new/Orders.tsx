
import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowLeft, Copy, Check, Clock, AlertTriangle, Package, Terminal, Activity, Box, Star, MessageSquare, X, Send, Eye, EyeOff } from 'lucide-react';

// Type for order item data (matches OrderItem from types/component)
interface OrderItemData {
  id: string | number;
  name: string;
  type: 'instant' | 'preorder';
  status: 'delivered' | 'waiting' | 'cancelled';
  credentials?: string | null;
  expiry?: string | null;
  hasReview: boolean;
  estimatedDelivery?: string | null;
  progress?: number | null;
  deadline?: string | null;
  reason?: string | null;
}

// Type for order data (matches Order from types/component)
interface OrderData {
  id: string;
  date: string;
  total: number;
  status: 'paid' | 'processing' | 'refunded';
  items: OrderItemData[];
}

interface OrdersProps {
  orders?: OrderData[];
  onBack: () => void;
  onOpenSupport?: () => void;
  onSubmitReview?: (orderId: string, rating: number, text?: string) => Promise<void>;
}

// --- UTILITY: DECRYPT EFFECT ---
const DecryptText: React.FC<{ text: string, revealed: boolean }> = ({ text, revealed }) => {
    const [display, setDisplay] = useState(text.replace(/./g, '*'));
    
    useEffect(() => {
        if (!revealed) {
            setDisplay(text.replace(/./g, '•'));
            return;
        }

        let iterations = 0;
        const interval = setInterval(() => {
            setDisplay(text.split('').map((char, index) => {
                if (index < iterations) return char;
                return "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*".charAt(Math.floor(Math.random() * 40));
            }).join(''));
            
            if (iterations >= text.length) clearInterval(interval);
            iterations += 1/3; 
        }, 30);
        return () => clearInterval(interval);
    }, [revealed, text]);

    return <span className="font-mono">{display}</span>;
}

// --- MOCK ORDERS DATA ---
const MOCK_ORDERS = [
  {
    id: "CB8-C8D-C5",
    date: "2025-12-08 // 14:32:01",
    total: 1156,
    status: "paid",
    items: [
      {
        id: 1,
        name: "CURSOR_IDE_PRO_7D",
        type: "instant",
        status: "delivered",
        credentials: "cursor_user3:cursor_pass3",
        expiry: "2025-12-15",
        hasReview: false // User hasn't reviewed yet
      },
      {
        id: 2,
        name: "MIDJOURNEY_V6_SHARED",
        type: "instant",
        status: "delivered",
        credentials: "mj_user_x:discord_pass_123",
        hasReview: true // Already reviewed
      }
    ]
  },
  {
    id: "2C1-A0A-25",
    date: "2025-12-07 // 09:15:00",
    total: 4238,
    status: "processing",
    items: [
      {
        id: 3,
        name: "GEMINI_PRO_1Y_SUB",
        type: "preorder",
        status: "waiting",
        estimatedDelivery: "24H",
        progress: 65,
        deadline: "2025-12-09 // 14:00",
        hasReview: false
      }
    ]
  },
  {
    id: "FF9-E2B-11",
    date: "2025-12-01 // 18:45:22",
    total: 250,
    status: "refunded",
    items: [
      {
        id: 4,
        name: "JASPER_AI_TRIAL",
        type: "instant",
        status: "cancelled",
        reason: "ERR_STOCK_EMPTY :: AUTO_REFUND_EXECUTED",
        hasReview: false
      }
    ]
  }
];

const Orders: React.FC<OrdersProps> = ({ orders: propOrders, onBack, onOpenSupport, onSubmitReview }) => {
  // Use provided orders or fallback to mock data
  const ordersData = propOrders || MOCK_ORDERS;
  const [activeTab, setActiveTab] = useState<'all' | 'active' | 'log'>('all');
  const [copiedId, setCopiedId] = useState<number | string | null>(null);
  const [revealedKeys, setRevealedKeys] = useState<(number | string)[]>([]);
  
  // Review State - use ordersData as initial state when provided
  const [ordersState, setOrdersState] = useState<OrderData[]>(ordersData as OrderData[]);
  const [reviewModal, setReviewModal] = useState<{isOpen: boolean, itemId: number | string | null, itemName: string, orderId: string | null}>({
      isOpen: false, itemId: null, itemName: '', orderId: null
  });
  const [rating, setRating] = useState(5);
  const [reviewText, setReviewText] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Sync with prop changes
  useEffect(() => {
    if (propOrders) {
      setOrdersState(propOrders);
    }
  }, [propOrders]);

  const handleCopy = (text: string, id: number | string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const toggleReveal = (id: number | string) => {
      if (revealedKeys.includes(id)) {
          setRevealedKeys(prev => prev.filter(k => k !== id));
      } else {
          setRevealedKeys(prev => [...prev, id]);
      }
  };

  const openReviewModal = (itemId: number | string, itemName: string, orderId: string) => {
      setRating(5);
      setReviewText('');
      setReviewModal({ isOpen: true, itemId, itemName, orderId });
  };

  const submitReview = async () => {
      if (!reviewModal.itemId || !reviewModal.orderId) return;

      setIsSubmitting(true);
      try {
        // If onSubmitReview prop is provided, use it (real API)
        if (onSubmitReview) {
          await onSubmitReview(reviewModal.orderId, rating, reviewText || undefined);
        }

        // Update local state to show "Reviewed" status
        const updatedOrders = ordersState.map(order => ({
            ...order,
            items: order.items.map(item => 
                item.id === reviewModal.itemId ? { ...item, hasReview: true } : item
            )
        }));

        setOrdersState(updatedOrders);
        setReviewModal({ isOpen: false, itemId: null, itemName: '', orderId: null });
      } catch (error) {
        console.error('Failed to submit review:', error);
      } finally {
        setIsSubmitting(false);
      }
  };

  const filteredOrders = ordersState.filter(order => {
    if (activeTab === 'all') return true;
    // Active: orders in progress or awaiting action
    const activeStatuses = ['pending', 'prepaid', 'fulfilling', 'ready', 'awaiting_payment', 'payment_pending', 'partial'];
    if (activeTab === 'active') return activeStatuses.includes(order.status); 
    // Archived: completed, delivered, refunded, cancelled, failed - finished orders
    const archivedStatuses = ['delivered', 'fulfilled', 'completed', 'cancelled', 'refunded', 'failed', 'expired', 'error'];
    if (activeTab === 'log') return archivedStatuses.includes(order.status); 
    return true;
  });

  return (
    <motion.div 
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="min-h-screen text-white pt-24 pb-32 px-4 md:px-8 md:pl-28 relative"
    >
        <div className="max-w-7xl mx-auto relative z-10">
            
            {/* === UNIFIED HEADER (Leaderboard Style) === */}
            <div className="mb-8 md:mb-16">
                <button onClick={onBack} className="flex items-center gap-2 text-[10px] font-mono text-gray-500 hover:text-pandora-cyan mb-4 transition-colors">
                    <ArrowLeft size={12} /> RETURN_TO_BASE
                </button>
                <h1 className="text-3xl sm:text-4xl md:text-6xl font-display font-black text-white uppercase tracking-tighter leading-[0.9] mb-4">
                    TRANSACTION <br/> <span className="text-transparent bg-clip-text bg-gradient-to-r from-pandora-cyan to-white/50">LOGS</span>
                </h1>
                <div className="flex items-center gap-2 text-[10px] font-mono text-pandora-cyan tracking-widest uppercase">
                     <Terminal size={12} />
                     <span>System_Logs // User_History</span>
                </div>
            </div>

            {/* --- TABS --- */}
            <div className="flex gap-8 mb-10 pl-2 overflow-x-auto">
                {[
                    { id: 'all', label: 'ALL_LOGS' }, 
                    { id: 'active', label: 'ACTIVE_NODES' }, 
                    { id: 'log', label: 'ARCHIVED' }
                ].map(tab => (
                    <button
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id as any)}
                        className="relative pb-2 text-sm font-mono font-bold tracking-wider uppercase transition-colors whitespace-nowrap"
                    >
                        <span className={activeTab === tab.id ? 'text-pandora-cyan' : 'text-gray-600 hover:text-gray-400'}>
                            {tab.label}
                        </span>
                        {activeTab === tab.id && (
                            <motion.div 
                                layoutId="activeOrderTab"
                                className="absolute bottom-0 left-0 w-full h-0.5 bg-pandora-cyan shadow-[0_0_10px_#00FFFF]" 
                            />
                        )}
                    </button>
                ))}
            </div>

            {/* --- ORDERS LIST --- */}
            <div className="space-y-8">
                {filteredOrders.map((order) => (
                    <div key={order.id} className="relative group">
                        
                        {/* Connecting Line */}
                        <div className="absolute -left-3 top-0 bottom-0 w-px bg-white/5 group-hover:bg-white/10 transition-colors" />

                        {/* Order Card */}
                        <div className="bg-[#080808] border border-white/10 hover:border-white/20 transition-all relative overflow-hidden">
                            
                            {/* Card Header */}
                            <div className="bg-white/5 p-3 flex justify-between items-center border-b border-white/5">
                                <div className="flex items-center gap-4">
                                    <span className="font-mono text-xs text-pandora-cyan tracking-wider">ID: {order.id}</span>
                                    <span className="hidden sm:inline text-[10px] font-mono text-gray-600 uppercase">// {order.date}</span>
                                </div>
                                <div className="flex items-center gap-3">
                                    {order.status === 'paid' && <span className="text-[10px] font-bold bg-green-500/20 text-green-400 px-2 py-0.5 border border-green-500/30">[ STATUS: OK ]</span>}
                                    {order.status === 'processing' && <span className="text-[10px] font-bold bg-orange-500/20 text-orange-400 px-2 py-0.5 border border-orange-500/30 animate-pulse">[ STATUS: PENDING ]</span>}
                                    {order.status === 'refunded' && <span className="text-[10px] font-bold bg-red-500/10 text-red-500 px-2 py-0.5 border border-red-500/20">[ STATUS: VOID ]</span>}
                                    <span className="font-display font-bold text-white">{order.total} ₽</span>
                                </div>
                            </div>

                            {/* Items Content */}
                            <div className="p-5 space-y-6">
                                {order.items.map((item) => (
                                    <div key={item.id} className="relative pl-4 border-l-2 border-white/10 group-hover:border-pandora-cyan/30 transition-colors">
                                        
                                        {/* Item Header */}
                                        <div className="flex justify-between items-start mb-3">
                                            <h3 className="font-bold text-white text-sm tracking-wide">{item.name}</h3>
                                            
                                            <div className="text-[10px] font-mono">
                                                {item.status === 'delivered' && <span className="text-green-500 flex items-center gap-1"><Check size={10} /> DELIVERED</span>}
                                                {item.status === 'waiting' && <span className="text-orange-400 flex items-center gap-1"><Clock size={10} /> QUEUED</span>}
                                                {item.status === 'cancelled' && <span className="text-red-500 flex items-center gap-1"><AlertTriangle size={10} /> KILLED</span>}
                                            </div>
                                        </div>

                                        {/* === DELIVERED: Credentials & Actions === */}
                                        {item.status === 'delivered' && (
                                            <div className="space-y-3">
                                                {/* Credentials Box */}
                                                {item.credentials && (
                                                    <div className="bg-black border border-white/10 border-dashed p-3 relative group/key">
                                                        <div className="text-[10px] text-gray-500 font-mono mb-2 flex justify-between items-center border-b border-white/5 pb-2">
                                                            <span>ACCESS_KEY_ENCRYPTED</span>
                                                            <div className="flex items-center gap-2">
                                                                <button onClick={() => toggleReveal(item.id)} className="text-gray-500 hover:text-white transition-colors">
                                                                    {revealedKeys.includes(item.id) ? <EyeOff size={12} /> : <Eye size={12} />}
                                                                </button>
                                                                {item.expiry && <span className="text-gray-600">EXP: {item.expiry}</span>}
                                                            </div>
                                                        </div>
                                                        
                                                        {/* Key Content */}
                                                        <div className="flex justify-between items-center mt-2">
                                                            <div className="font-mono text-sm text-pandora-cyan break-all tracking-wider">
                                                                <DecryptText text={item.credentials} revealed={revealedKeys.includes(item.id)} />
                                                            </div>
                                                            <button 
                                                                onClick={() => handleCopy(item.credentials!, item.id)}
                                                                className="ml-4 p-1.5 bg-white/5 hover:bg-pandora-cyan hover:text-black transition-colors rounded-sm shrink-0"
                                                                title="Copy to Clipboard"
                                                            >
                                                                {copiedId === item.id ? <Check size={14} /> : <Copy size={14} />}
                                                            </button>
                                                        </div>
                                                    </div>
                                                )}

                                                {/* Review Action (Only for delivered items) */}
                                                <div className="flex justify-end pt-2">
                                                    {item.hasReview ? (
                                                        <div className="flex items-center gap-2 text-[10px] font-mono text-gray-500 border border-white/5 px-3 py-1.5 rounded-sm select-none opacity-60">
                                                            <Check size={12} className="text-pandora-cyan" />
                                                            FEEDBACK_LOGGED
                                                        </div>
                                                    ) : (
                                                        <button 
                                                            onClick={() => openReviewModal(item.id, item.name, order.id)}
                                                            className="flex items-center gap-2 text-[10px] font-bold font-mono text-pandora-cyan border border-pandora-cyan/30 px-3 py-1.5 hover:bg-pandora-cyan hover:text-black transition-all"
                                                        >
                                                            <MessageSquare size={12} />
                                                            INITIALIZE_REVIEW
                                                        </button>
                                                    )}
                                                </div>
                                            </div>
                                        )}

                                        {/* === WAITING: Pre-order === */}
                                        {item.status === 'waiting' && (
                                            <div className="mt-2 bg-[#0c0c0c] border border-orange-500/20 p-3">
                                                <div className="flex justify-between text-[10px] font-mono text-orange-400 mb-1">
                                                    <span className="flex items-center gap-1"><Activity size={10} /> PROVISIONING_RESOURCE...</span>
                                                    <span>EST: {item.estimatedDelivery}</span>
                                                </div>
                                                
                                                {/* Fake Progress Bar */}
                                                <div className="w-full h-1 bg-gray-800 mt-2 mb-2 relative overflow-hidden">
                                                    <div 
                                                        className="absolute top-0 left-0 h-full bg-orange-500 shadow-[0_0_10px_orange]"
                                                        style={{ width: `${item.progress}%` }} 
                                                    />
                                                    <div className="absolute top-0 left-0 h-full w-full bg-gradient-to-r from-transparent via-white/30 to-transparent animate-pulse" />
                                                </div>

                                                <p className="text-[10px] text-gray-500 font-mono border-t border-white/5 pt-2 mt-2">
                                                    &gt; DEADLINE: {item.deadline}
                                                </p>
                                            </div>
                                        )}

                                        {/* === REFUNDED === */}
                                        {item.status === 'cancelled' && (
                                            <div className="mt-2 bg-red-900/5 border border-red-500/20 p-2 font-mono text-[10px] text-red-400">
                                                &gt; {item.reason}
                                            </div>
                                        )}

                                    </div>
                                ))}
                            </div>
                            
                            {/* Decorative Corner Overlays */}
                            <div className="absolute top-0 right-0 w-2 h-2 border-t border-r border-pandora-cyan opacity-50" />
                            <div className="absolute bottom-0 left-0 w-2 h-2 border-b border-l border-pandora-cyan opacity-50" />

                        </div>
                    </div>
                ))}
            </div>

            {/* Footer */}
            <div className="mt-16 border-t border-white/10 pt-8 text-center">
                 <div onClick={onOpenSupport} className="inline-flex flex-col items-center gap-2 group cursor-pointer">
                    <div className="w-10 h-10 bg-white/5 rounded-full flex items-center justify-center border border-white/10 group-hover:border-pandora-cyan group-hover:text-pandora-cyan transition-all">
                        <Box size={18} />
                    </div>
                    <span className="text-[10px] font-mono text-gray-500 group-hover:text-white transition-colors">INITIATE_SUPPORT_TICKET</span>
                 </div>
            </div>

        </div>

        {/* === REVIEW MODAL === */}
        <AnimatePresence>
            {reviewModal.isOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center px-4">
                    <motion.div 
                        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                        onClick={() => setReviewModal({...reviewModal, isOpen: false})}
                        className="absolute inset-0 bg-black/80 backdrop-blur-sm"
                    />
                    <motion.div 
                        initial={{ scale: 0.9, opacity: 0, y: 20 }}
                        animate={{ scale: 1, opacity: 1, y: 0 }}
                        exit={{ scale: 0.9, opacity: 0, y: 20 }}
                        className="relative w-full max-w-md bg-[#0a0a0a] border border-white/20 p-6 shadow-[0_0_50px_rgba(0,0,0,0.8)]"
                    >
                        <div className="flex justify-between items-start mb-6 border-b border-white/10 pb-4">
                            <div>
                                <h3 className="text-lg font-display font-bold text-white uppercase">Submit Evaluation</h3>
                                <p className="text-[10px] font-mono text-pandora-cyan mt-1">TARGET: {reviewModal.itemName}</p>
                            </div>
                            <button onClick={() => setReviewModal({...reviewModal, isOpen: false})} className="text-gray-500 hover:text-white">
                                <X size={20} />
                            </button>
                        </div>

                        {/* Rating */}
                        <div className="mb-6 flex flex-col items-center">
                            <span className="text-xs font-mono text-gray-500 mb-2 uppercase tracking-widest">Quality Assessment</span>
                            <div className="flex gap-2">
                                {[1, 2, 3, 4, 5].map((star) => (
                                    <button 
                                        key={star} 
                                        onClick={() => setRating(star)}
                                        className="hover:scale-110 transition-transform focus:outline-none"
                                    >
                                        <Star 
                                            size={24} 
                                            fill={star <= rating ? "#00FFFF" : "none"} 
                                            className={star <= rating ? "text-pandora-cyan drop-shadow-[0_0_5px_#00FFFF]" : "text-gray-700"} 
                                        />
                                    </button>
                                ))}
                            </div>
                        </div>

                        {/* Text Area */}
                        <div className="mb-6 relative group">
                            <textarea 
                                value={reviewText}
                                onChange={(e) => setReviewText(e.target.value)}
                                placeholder="Describe your experience with this module..."
                                className="w-full h-32 bg-black border border-white/20 p-3 text-sm text-white font-mono focus:border-pandora-cyan outline-none resize-none placeholder:text-gray-700"
                            />
                            <div className="absolute bottom-2 right-2 text-[10px] text-gray-600 font-mono">
                                {reviewText.length} CHARS
                            </div>
                        </div>

                        <button 
                            onClick={submitReview}
                            disabled={isSubmitting}
                            className="w-full bg-white/5 hover:bg-pandora-cyan border border-white/20 hover:border-pandora-cyan text-white hover:text-black font-bold py-3 uppercase tracking-widest transition-all flex items-center justify-center gap-2 group/btn disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {isSubmitting ? (
                              <>
                                <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
                                UPLOADING...
                              </>
                            ) : (
                              <>
                                <Send size={16} />
                                UPLOAD_PACKET
                              </>
                            )}
                        </button>

                        {/* Decorative Corners */}
                        <div className="absolute top-0 left-0 w-2 h-2 border-t border-l border-pandora-cyan" />
                        <div className="absolute bottom-0 right-0 w-2 h-2 border-b border-r border-pandora-cyan" />
                    </motion.div>
                </div>
            )}
        </AnimatePresence>

    </motion.div>
  );
};

export default Orders;
