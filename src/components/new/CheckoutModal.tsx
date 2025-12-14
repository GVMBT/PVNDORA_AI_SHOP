
import React, { useState, useEffect, memo, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, CheckCircle, Server } from 'lucide-react';
import { formatPrice } from '../../utils/currency';
import { logger } from '../../utils/logger';
import CartSummary from './CartSummary';
import PaymentMethodSelector from './PaymentMethodSelector';
import PaymentProcessing from './PaymentProcessing';
import type { CartItem } from '../../types/component';
import type { APICreateOrderResponse } from '../../types/api';

export type PaymentMethod = 'crystalpay' | 'internal';

interface CheckoutModalProps {
  cart: CartItem[];
  userBalance?: number;
  currency?: string; // Currency code from API
  onClose: () => void;
  onRemoveItem: (id: string | number) => void;
  onPay?: (method: PaymentMethod) => Promise<APICreateOrderResponse | null>;
  onSuccess: () => void;
  loading?: boolean;
  error?: string | null;
}

const CheckoutModal: React.FC<CheckoutModalProps> = ({ 
  cart, 
  userBalance = 0,
  currency = 'USD',
  onClose, 
  onRemoveItem, 
  onPay,
  onSuccess,
  loading: externalLoading = false,
  error: externalError = null,
}) => {
  const [step, setStep] = useState<'cart' | 'payment' | 'processing' | 'success'>('cart');
  const [selectedPayment, setSelectedPayment] = useState<PaymentMethod>('crystalpay');
  const [logs, setLogs] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  // Updated Total Logic to include Quantity - memoized for performance
  const total = useMemo(() => {
    try {
      if (cart && Array.isArray(cart)) {
        return cart.reduce((acc, item) => {
          const price = item?.price || 0;
          const quantity = item?.quantity || 1;
          return acc + (price * quantity);
        }, 0);
      }
    } catch (err) {
      // Silently fail
    }
    return 0;
  }, [cart]);

  // --- HACKING SIMULATION LOGIC ---
  const simulateLogs = (method: PaymentMethod) => {
    const commonLogs = ["> INITIALIZING_SECURE_CHANNEL", "> HANDSHAKE_PROTOCOL_V4"];
    
    const crystalLogs = [
      "> RESOLVING_CRYSTAL_NODE...",
      "> GENERATING_INVOICE_ID",
      "> ESTABLISHING_BRIDGE_CONNECTION",
      "> WAITING_FOR_EXTERNAL_SIGNAL...",
      "> PAYMENT_GATEWAY: READY"
    ];

    const internalLogs = [
      "> CHECKING_LOCAL_WALLET_INTEGRITY...",
      `> BALANCE_CHECK: ${userBalance} >= ${total} [OK]`,
      "> FREEZING_ASSETS...",
      "> INTERNAL_TRANSFER_EXECUTED",
      "> LEDGER_UPDATED_SUCCESSFULLY"
    ];

    let currentLogs = [...commonLogs];
    let targetLogs = crystalLogs;
    if (method === 'internal') targetLogs = internalLogs;

    setLogs(currentLogs);

    // Sequence the logs adding
    targetLogs.forEach((log, index) => {
      setTimeout(() => {
        setLogs(prev => [...prev.slice(-4), log]); // Keep only last 5 logs visible
      }, 500 + (index * 600));
    });
  };

  const handlePay = async () => {
    if (selectedPayment === 'internal' && total > userBalance) {
        setError("INSUFFICIENT_FUNDS_ON_INTERNAL_BALANCE");
        return;
    }
    
    setError(null);
    setStep('processing');
    simulateLogs(selectedPayment);

    // If external onPay is provided, use it
    if (onPay) {
      try {
        const result = await onPay(selectedPayment);
        // For external payment (CrystalPay), redirect happens in handlePay, result is null
        // For internal payment (balance), result contains order info, show success
        if (result && selectedPayment === 'internal') {
          // Short delay to show the animation for balance payment
          setTimeout(() => {
            setStep('success');
          }, 2000);
        }
        // If result is null, external redirect happened - modal will be closed by handlePay
      } catch (err: unknown) {
        const errorMessage = err instanceof Error ? err.message : 'PAYMENT_FAILED';
        setError(errorMessage);
        setStep('payment');
      }
    } else {
      // Fallback to mock behavior (demo mode)
      setTimeout(() => {
        setStep('success');
      }, 4500);
    }
  };

  const closeSuccess = () => {
      onSuccess();
      onClose();
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center px-4">
        {/* Backdrop */}
        <motion.div 
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            onClick={onClose}
            className="absolute inset-0 bg-black/80 backdrop-blur-sm"
        />

        {/* Modal Window */}
        <motion.div 
            initial={{ scale: 0.9, opacity: 0, y: 20 }}
            animate={{ scale: 1, opacity: 1, y: 0 }}
            exit={{ scale: 0.9, opacity: 0, y: 20 }}
            onClick={(e) => e.stopPropagation()}
            className="relative w-full max-w-2xl bg-[#080808] border border-white/20 shadow-[0_0_50px_rgba(0,0,0,0.8)] overflow-hidden flex flex-col max-h-[90vh]"
        >
            {/* Header */}
            <div className="flex items-center justify-between p-6 border-b border-white/10 bg-[#0a0a0a] relative z-20">
                <h2 className="text-xl font-display font-bold text-white flex items-center gap-2">
                    <span className="w-1.5 h-6 bg-pandora-cyan block" />
                    SYSTEM_CHECKOUT // V.2.1
                </h2>
                <button onClick={onClose} className="text-gray-500 hover:text-white transition-colors">
                    <X size={24} />
                </button>
            </div>

            {/* Content Body */}
            <div className="flex-1 overflow-y-auto p-6 relative z-10">
                
                <AnimatePresence mode="wait">
                    
                    {/* === STEP 1: CART REVIEW === */}
                    {step === 'cart' && (
                      <CartSummary
                        cart={cart}
                        total={total}
                        currency={currency}
                        onRemoveItem={onRemoveItem}
                        onProceed={() => setStep('payment')}
                      />
                    )}

                    {/* === STEP 2: PAYMENT METHOD SELECTION === */}
                    {step === 'payment' && (
                      <PaymentMethodSelector
                        selectedPayment={selectedPayment}
                        total={total}
                        userBalance={userBalance}
                        currency={currency}
                        error={error || externalError || null}
                        onSelectPayment={setSelectedPayment}
                        onPay={handlePay}
                      />
                    )}

                    {/* === STEP 3: PROCESSING === */}
                    {step === 'processing' && (
                      <PaymentProcessing logs={logs} selectedPayment={selectedPayment} />
                    )}

                    {/* === STEP 4: SUCCESS === */}
                    {step === 'success' && (
                        <motion.div 
                            key="success"
                            initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }}
                            className="flex flex-col items-center justify-center py-8 text-center"
                        >
                            <div className="relative mb-6">
                                <div className="absolute inset-0 bg-pandora-cyan blur-xl opacity-20" />
                                <CheckCircle size={64} className="text-pandora-cyan relative z-10" />
                            </div>
                            
                            <h3 className="text-2xl font-display font-bold text-white mb-2">ORDER CONFIRMED</h3>
                            <p className="text-gray-400 font-mono text-sm mb-6 max-w-xs mx-auto">
                                Payment processed successfully. Your order is being prepared for delivery.
                            </p>
                            
                            <div className="w-full bg-[#0e0e0e] border border-white/10 p-4 mb-6 text-left space-y-3">
                                <div className="flex items-center gap-3">
                                    <div className="w-8 h-8 rounded-full bg-green-500/10 border border-green-500/30 flex items-center justify-center">
                                        <CheckCircle size={14} className="text-green-500" />
                                    </div>
                                    <div>
                                        <div className="text-[10px] text-gray-500 font-mono">PAYMENT_STATUS</div>
                                        <div className="text-xs text-green-500 font-bold">CONFIRMED</div>
                                    </div>
                                </div>
                                <div className="flex items-center gap-3">
                                    <div className="w-8 h-8 rounded-full bg-pandora-cyan/10 border border-pandora-cyan/30 flex items-center justify-center">
                                        <Server size={14} className="text-pandora-cyan" />
                                    </div>
                                    <div>
                                        <div className="text-[10px] text-gray-500 font-mono">DELIVERY_CHANNEL</div>
                                        <div className="text-xs text-pandora-cyan font-bold">TELEGRAM BOT + ORDERS PAGE</div>
                                    </div>
                                </div>
                            </div>
                            
                            <p className="text-[10px] text-gray-500 font-mono mb-6 max-w-xs">
                                Instant items are delivered immediately. Preorder items will be delivered within 24-72 hours.
                            </p>

                            <button 
                                onClick={closeSuccess}
                                className="px-8 py-3 bg-pandora-cyan text-black hover:bg-white transition-colors text-xs font-bold uppercase tracking-widest"
                            >
                                VIEW ORDERS
                            </button>
                        </motion.div>
                    )}

                </AnimatePresence>
            </div>
        </motion.div>
    </div>
  );
};

export default memo(CheckoutModal);
