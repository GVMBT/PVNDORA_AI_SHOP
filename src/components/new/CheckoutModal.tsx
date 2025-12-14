
import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, CreditCard, Bitcoin, ShieldCheck, ChevronRight, Cpu, CheckCircle, Trash2, Globe, Lock, Server, Wallet, Zap } from 'lucide-react';
import { formatPrice } from '../../utils/currency';

export type PaymentMethod = 'crystalpay' | 'internal';

interface CheckoutModalProps {
  cart: any[];
  userBalance?: number;
  currency?: string; // Currency code from API
  onClose: () => void;
  onRemoveItem: (id: string | number) => void;
  onPay?: (method: PaymentMethod) => Promise<any>;
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

  // Updated Total Logic to include Quantity - with safety checks
  let total = 0;
  try {
    if (cart && Array.isArray(cart)) {
      total = cart.reduce((acc, item) => {
        const price = item?.price || 0;
        const quantity = item?.quantity || 1;
        return acc + (price * quantity);
      }, 0);
    }
  } catch (err) {
    total = 0;
  }

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
      } catch (err: any) {
        setError(err.message || 'PAYMENT_FAILED');
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
                        <motion.div 
                            key="cart"
                            initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }}
                        >
                            {cart.length === 0 ? (
                                <div className="text-center py-12">
                                    <div className="text-gray-600 font-mono mb-4">NO_MODULES_DETECTED</div>
                                    <button onClick={onClose} className="text-pandora-cyan font-bold hover:underline">RETURN TO CATALOG</button>
                                </div>
                            ) : (
                                <div className="space-y-4">
                                    {cart.map((item) => (
                                        <div key={item.id} className="flex items-center justify-between bg-white/5 border border-white/10 p-4 rounded-sm hover:border-pandora-cyan/30 transition-colors">
                                            <div className="flex items-center gap-4">
                                                <div className="w-12 h-12 bg-black border border-white/10 rounded-sm overflow-hidden relative">
                                                    <img src={item.image} className="w-full h-full object-cover grayscale" />
                                                    {/* Quantity Badge on Image */}
                                                    {(item.quantity || 1) > 1 && (
                                                        <div className="absolute top-0 right-0 bg-pandora-cyan text-black text-[9px] font-bold w-4 h-4 flex items-center justify-center">
                                                            {item.quantity}
                                                        </div>
                                                    )}
                                                </div>
                                                <div>
                                                    <div className="font-bold text-white text-sm">{item.name}</div>
                                                    <div className="text-[10px] text-gray-500 font-mono flex items-center gap-2">
                                                        {item.category} MODULE
                                                        {(item.quantity || 1) > 1 && (
                                                            <span className="text-white">x{item.quantity}</span>
                                                        )}
                                                    </div>
                                                </div>
                                            </div>
                                            <div className="flex items-center gap-6">
                                                <div className="text-right">
                                                    <div className="font-mono text-pandora-cyan">{formatPrice(item.price * (item.quantity || 1), item.currency || currency)}</div>
                                                    {(item.quantity || 1) > 1 && (
                                                        <div className="text-[9px] text-gray-500">{formatPrice(item.price, item.currency || currency)} ea</div>
                                                    )}
                                                </div>
                                                <button onClick={() => onRemoveItem(item.id)} className="text-gray-600 hover:text-red-500 transition-colors">
                                                    <Trash2 size={16} />
                                                </button>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}

                            {cart.length > 0 && (
                                <div className="mt-8 border-t border-white/10 pt-6">
                                    <div className="flex justify-between items-end mb-6">
                                        <span className="text-gray-500 font-mono text-xs">TOTAL_ESTIMATION</span>
                                        <span className="text-3xl font-display font-bold text-white">{formatPrice(total, currency)}</span>
                                    </div>
                                    <button 
                                        onClick={() => setStep('payment')}
                                        className="w-full bg-white text-black font-bold py-4 hover:bg-pandora-cyan transition-colors uppercase tracking-widest flex items-center justify-center gap-2 group"
                                    >
                                        PROCEED TO PAYMENT 
                                        <ChevronRight size={18} className="group-hover:translate-x-1 transition-transform" />
                                    </button>
                                </div>
                            )}
                        </motion.div>
                    )}

                    {/* === STEP 2: PAYMENT METHOD SELECTION === */}
                    {step === 'payment' && (
                        <motion.div 
                            key="payment"
                            initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }}
                        >
                            <div className="mb-8">
                                <h3 className="text-xs font-mono text-pandora-cyan mb-4 uppercase flex items-center gap-2">
                                    <Server size={12} />
                                    Select Payment Node
                                </h3>
                                
                                {(error || externalError) && (
                                    <div className="mb-4 p-3 bg-red-500/10 border border-red-500/30 text-red-400 text-xs font-mono flex items-center gap-2">
                                        <ShieldCheck size={14} /> {error || externalError}
                                    </div>
                                )}

                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                    
                                    {/* Option 1: Internal Balance */}
                                    <button 
                                        onClick={() => setSelectedPayment('internal')}
                                        className={`relative p-4 border flex flex-col items-center text-center gap-3 transition-all overflow-hidden group ${selectedPayment === 'internal' ? 'border-green-500 bg-green-500/5' : 'border-white/10 bg-white/5 hover:bg-white/10'}`}
                                    >
                                        <div className={`p-2 rounded-full ${selectedPayment === 'internal' ? 'bg-green-500 text-black' : 'bg-black text-gray-400'}`}>
                                            <Wallet size={20} />
                                        </div>
                                        <div>
                                            <div className="text-xs font-bold text-white uppercase mb-1">Internal</div>
                                            <div className="text-[10px] text-gray-500 font-mono">Balance: {formatPrice(userBalance, currency)}</div>
                                        </div>
                                        {selectedPayment === 'internal' && (
                                            <div className="absolute top-1 right-1">
                                                <div className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse" />
                                            </div>
                                        )}
                                    </button>

                                    {/* Option 2: CrystalPay (Redirect) */}
                                    <button 
                                        onClick={() => setSelectedPayment('crystalpay')}
                                        className={`relative p-4 border flex flex-col items-center text-center gap-3 transition-all overflow-hidden group ${selectedPayment === 'crystalpay' ? 'border-purple-500 bg-purple-500/5' : 'border-white/10 bg-white/5 hover:bg-white/10'}`}
                                    >
                                        <div className={`p-2 rounded-full ${selectedPayment === 'crystalpay' ? 'bg-purple-500 text-white' : 'bg-black text-gray-400'}`}>
                                            <Globe size={20} />
                                        </div>
                                        <div>
                                            <div className="text-xs font-bold text-white uppercase mb-1">Crypto/P2P</div>
                                            <div className="text-[10px] text-gray-500 font-mono">Gateway</div>
                                        </div>
                                        {selectedPayment === 'crystalpay' && (
                                            <div className="absolute top-1 right-1">
                                                <div className="w-1.5 h-1.5 bg-purple-500 rounded-full animate-pulse" />
                                            </div>
                                        )}
                                    </button>
                                </div>
                            </div>

                            {/* Dynamic Payment Interface */}
                            <div className="bg-[#0e0e0e] border border-white/10 p-6 rounded-sm mb-8 relative">
                                <div className="absolute top-0 left-0 w-2 h-2 border-t border-l border-white/20" />
                                <div className="absolute bottom-0 right-0 w-2 h-2 border-b border-r border-white/20" />

                                {selectedPayment === 'internal' && (
                                    <div className="flex flex-col items-center justify-center py-2">
                                        <div className="text-center mb-4">
                                            <div className="text-3xl font-display font-bold text-white mb-1">{total} ₽</div>
                                            <div className="text-xs font-mono text-gray-500">WILL BE DEBITED FROM ID: UID-8492-X</div>
                                        </div>
                                        <div className="flex items-center gap-2 text-xs font-mono text-green-500 bg-green-900/10 px-3 py-1 border border-green-500/30">
                                            <Zap size={12} /> INSTANT_PROCESSING_ENABLED
                                        </div>
                                    </div>
                                )}

                                {selectedPayment === 'crystalpay' && (
                                    <div className="text-center py-4">
                                        <div className="w-16 h-16 bg-purple-500/10 rounded-full flex items-center justify-center mx-auto mb-4 border border-purple-500/30 animate-pulse">
                                            <Bitcoin size={32} className="text-purple-400" />
                                        </div>
                                        <h4 className="text-white font-bold uppercase mb-2">External Gateway</h4>
                                        <p className="text-xs font-mono text-gray-400 leading-relaxed max-w-xs mx-auto">
                                            You will be redirected to the secure CrystalPay terminal to complete the transaction via Cryptocurrency or P2P.
                                        </p>
                                    </div>
                                )}
                            </div>

                            <button 
                                onClick={handlePay}
                                className={`
                                    w-full text-black font-bold py-4 hover:bg-white transition-all uppercase tracking-widest flex items-center justify-center gap-3 relative overflow-hidden
                                    ${selectedPayment === 'internal' ? 'bg-green-500' : 'bg-purple-500 text-white hover:text-purple-500'}
                                `}
                            >
                                <span className="relative z-10 flex items-center gap-2">
                                    <ShieldCheck size={18} />
                                    {selectedPayment === 'internal' ? `CONFIRM DEBIT (${formatPrice(total, currency)})` : `OPEN GATEWAY (${formatPrice(total, currency)})`}
                                </span>
                                {/* Hover Glitch */}
                                <div className="absolute inset-0 bg-white mix-blend-overlay opacity-0 hover:opacity-20 transition-opacity" />
                            </button>
                        </motion.div>
                    )}

                    {/* === STEP 3: PROCESSING (THE HACK) === */}
                    {step === 'processing' && (
                        <motion.div 
                            key="processing"
                            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                            className="flex flex-col items-center justify-center py-8 min-h-[300px]"
                        >
                            {/* Central Spinner / Loader */}
                            <div className="relative mb-8">
                                <div className={`w-20 h-20 border-4 border-t-transparent rounded-full animate-spin ${selectedPayment === 'internal' ? 'border-green-500/30 border-t-green-500' : 'border-purple-500/30 border-t-purple-500'}`} />
                                <div className="absolute inset-0 flex items-center justify-center">
                                    <Cpu size={24} className={`animate-pulse ${selectedPayment === 'internal' ? 'text-green-500' : 'text-purple-500'}`} />
                                </div>
                            </div>

                            {/* Progress Bar */}
                            <div className="w-64 h-1 bg-gray-800 rounded-full overflow-hidden mb-6 relative">
                                <motion.div 
                                    initial={{ width: "0%" }}
                                    animate={{ width: "100%" }}
                                    transition={{ duration: 4.5, ease: "linear" }}
                                    className={`h-full relative ${selectedPayment === 'internal' ? 'bg-green-500 shadow-[0_0_10px_#00FF00]' : 'bg-purple-500 shadow-[0_0_10px_#a855f7]'}`}
                                >
                                    <div className="absolute top-0 right-0 w-20 h-full bg-gradient-to-l from-white/50 to-transparent" />
                                </motion.div>
                            </div>

                            {/* Terminal Logs */}
                            <div className="w-full max-w-sm bg-black/50 border border-white/10 p-4 font-mono text-[10px] h-32 overflow-hidden flex flex-col justify-end">
                                {logs.map((log, i) => (
                                    <motion.div 
                                        key={i}
                                        initial={{ opacity: 0, x: -10 }}
                                        animate={{ opacity: 1, x: 0 }}
                                        className={`mb-1 ${log.includes('ERROR') ? 'text-red-500' : 'text-gray-400'}`}
                                    >
                                        <span className={selectedPayment === 'internal' ? 'text-green-500' : 'text-purple-500'}>{log.split(':')[0]}</span>
                                        {log.includes(':') && <span className="text-gray-300">:{log.split(':')[1]}</span>}
                                    </motion.div>
                                ))}
                                <div className="w-2 h-4 bg-gray-500 animate-pulse mt-1" />
                            </div>

                        </motion.div>
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

export default CheckoutModal;
