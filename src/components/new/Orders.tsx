
import React, { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useVirtualizer } from '@tanstack/react-virtual';
import { ArrowLeft, Box, Star, MessageSquare, X, Send, Package, Terminal } from 'lucide-react';
import { logger } from '../../utils/logger';
import { useClipboard } from '../../hooks/useClipboard';
import { useTimeoutState } from '../../hooks/useTimeoutState';
import OrderCard, { type OrderData } from './OrderCard';
import type { RefundContext } from './OrderCard';

// Re-export types for backward compatibility
export type { OrderData } from './OrderCard';
export type { OrderItemData } from './OrderItem';
export type { RefundContext } from './OrderCard';

interface OrdersProps {
  orders?: OrderData[];
  onBack: () => void;
  onOpenSupport?: (context?: RefundContext) => void;
  onSubmitReview?: (orderId: string, rating: number, text?: string) => Promise<void>;
}

const Orders: React.FC<OrdersProps> = ({ orders: propOrders, onBack, onOpenSupport, onSubmitReview }) => {
  // Use provided orders - NO MOCK fallback
  const ordersData = propOrders || [];
  const [activeTab, setActiveTab] = useState<'all' | 'active' | 'log'>('all');
  const [copiedId, setCopiedId] = useTimeoutState<number | string | null>(null);
  const [revealedKeys, setRevealedKeys] = useState<(number | string)[]>([]);
  const parentRef = useRef<HTMLDivElement>(null);
  
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

  const { copy: copyToClipboard } = useClipboard();
  
  const handleCopy = useCallback(async (text: string, id: number | string) => {
    const success = await copyToClipboard(text);
    if (success) {
      setCopiedId(id);
    }
  }, [copyToClipboard, setCopiedId]);

  const toggleReveal = useCallback((id: number | string) => {
      setRevealedKeys(prev => {
          if (prev.includes(id)) {
              return prev.filter(k => k !== id);
          } else {
              return [...prev, id];
          }
      });
  }, []);

  const openReviewModal = useCallback((itemId: number | string, itemName: string, orderId: string) => {
      setRating(5);
      setReviewText('');
      setReviewModal({ isOpen: true, itemId, itemName, orderId });
  }, []);

  const submitReview = useCallback(async () => {
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
        logger.error('Failed to submit review', error instanceof Error ? error : new Error(String(error)));
      } finally {
        setIsSubmitting(false);
      }
  }, [reviewModal.itemId, reviewModal.orderId, rating, reviewText, onSubmitReview, ordersState]);

  const filteredOrders = ordersState.filter(order => {
    if (activeTab === 'all') return true;
    // Active: orders in progress - uses adapted status 'processing'
    if (activeTab === 'active') return order.status === 'processing';
    // Archived: completed (paid) or refunded - finished orders
    if (activeTab === 'log') return order.status === 'paid' || order.status === 'refunded';
    return true;
  });

  // Virtualizer for orders list
  const virtualizer = useVirtualizer({
    count: filteredOrders.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 300, // Estimated order card height (varies by items count)
    overscan: 3, // Render 3 extra items outside viewport
  });

  // Empty state when no orders
  if (ordersState.length === 0) {
    return (
      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="min-h-screen text-white pt-20 md:pt-24 pb-32 px-4 md:px-8 md:pl-28 relative"
      >
        <div className="max-w-6xl mx-auto">
          <button onClick={onBack} className="flex items-center gap-2 text-[10px] font-mono text-gray-500 hover:text-pandora-cyan mb-8 transition-colors">
            <ArrowLeft size={12} /> RETURN_TO_BASE
          </button>
          <div className="flex flex-col items-center justify-center py-24 text-center">
            <Package size={64} className="text-gray-700 mb-6" />
            <h2 className="text-2xl font-bold text-white mb-2">NO ORDERS YET</h2>
            <p className="text-gray-500 font-mono text-sm max-w-md">
              Your order history is empty. Complete a purchase to see your transactions here.
            </p>
            <button 
              onClick={onBack}
              className="mt-8 px-6 py-3 bg-pandora-cyan/10 border border-pandora-cyan text-pandora-cyan font-mono text-sm uppercase hover:bg-pandora-cyan/20 transition-colors"
            >
              Browse Catalog
            </button>
          </div>
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div 
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
        className="min-h-screen text-white pt-20 md:pt-24 pb-32 px-4 md:px-8 md:pl-28 relative"
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

            {/* --- ORDERS LIST (Virtualized) --- */}
            <div 
                ref={parentRef}
                className="h-[70vh] overflow-auto"
                style={{ contain: 'strict' }}
            >
                <div
                    style={{
                        height: `${virtualizer.getTotalSize()}px`,
                        width: '100%',
                        position: 'relative',
                    }}
                >
                    {virtualizer.getVirtualItems().map((virtualRow) => {
                        const order = filteredOrders[virtualRow.index];
                        return (
                            <div
                                key={virtualRow.key}
                                style={{
                                    position: 'absolute',
                                    top: 0,
                                    left: 0,
                                    width: '100%',
                                    height: `${virtualRow.size}px`,
                                    transform: `translateY(${virtualRow.start}px)`,
                                }}
                                className="mb-8"
                            >
                                <OrderCard
                                  key={order.id}
                                  order={order}
                                  revealedKeys={revealedKeys}
                                  copiedId={copiedId}
                                  onToggleReveal={toggleReveal}
                                  onCopy={handleCopy}
                                  onOpenReview={openReviewModal}
                                  onOpenSupport={onOpenSupport}
                                />
                            </div>
                        );
                    })}
                </div>
            </div>

            {/* Footer */}
            <div className="mt-16 border-t border-white/10 pt-8 text-center">
                 <div onClick={() => onOpenSupport?.()} className="inline-flex flex-col items-center gap-2 group cursor-pointer">
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
