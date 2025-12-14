/**
 * PaymentResult Component
 * 
 * Terminal-style UI shown after payment redirect.
 * Polls order status and displays progress logs.
 * Works for both Mini App (startapp) and Browser (/payment/result) flows.
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Cpu, CheckCircle, XCircle, Clock, AlertTriangle, ArrowRight, RefreshCw } from 'lucide-react';

interface PaymentResultProps {
  orderId: string;
  isTopUp?: boolean;  // True if this is a balance top-up, not an order
  onComplete: () => void;
  onViewOrders: () => void;  // For topup, this navigates to profile
}

type PaymentStatus = 'checking' | 'paid' | 'delivered' | 'partial' | 'pending' | 'expired' | 'failed' | 'unknown';

interface OrderStatusResponse {
  status: string;
  payment_confirmed?: boolean;
  items_delivered?: number;
  items_total?: number;
}

const STATUS_MESSAGES: Record<PaymentStatus, { color: string; label: string; description: string }> = {
  checking: { color: 'purple', label: 'VERIFYING', description: 'Checking payment status...' },
  paid: { color: 'green', label: 'CONFIRMED', description: 'Payment confirmed! Preparing delivery...' },
  delivered: { color: 'cyan', label: 'COMPLETE', description: 'All items delivered to your account!' },
  partial: { color: 'yellow', label: 'PARTIAL', description: 'Some items delivered, others in queue.' },
  pending: { color: 'orange', label: 'PENDING', description: 'Waiting for payment confirmation...' },
  expired: { color: 'red', label: 'EXPIRED', description: 'Payment session expired.' },
  failed: { color: 'red', label: 'FAILED', description: 'Payment verification failed.' },
  unknown: { color: 'gray', label: 'UNKNOWN', description: 'Unable to determine status.' },
};

// Terminal log entry
interface LogEntry {
  timestamp: string;
  message: string;
  type: 'info' | 'success' | 'error' | 'warning';
}

// Constants for polling strategy
const MAX_POLL_ATTEMPTS = 15; // Maximum number of polling attempts
const INITIAL_POLL_DELAY = 1000; // Start with 1 second delay
const MAX_POLL_DELAY = 16000; // Maximum delay of 16 seconds between polls
const BACKOFF_MULTIPLIER = 2; // Exponential backoff multiplier

export function PaymentResult({ orderId, isTopUp = false, onComplete, onViewOrders }: PaymentResultProps) {
  const [status, setStatus] = useState<PaymentStatus>('checking');
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [progress, setProgress] = useState(0);
  const [pollCount, setPollCount] = useState(0);
  const [isComplete, setIsComplete] = useState(false);
  const consecutive404sRef = useRef(0); // Use ref to avoid triggering effect re-runs

  // Add log entry
  const addLog = useCallback((message: string, type: LogEntry['type'] = 'info') => {
    const timestamp = new Date().toLocaleTimeString('en-US', { 
      hour12: false, 
      hour: '2-digit', 
      minute: '2-digit', 
      second: '2-digit' 
    });
    setLogs(prev => [...prev.slice(-9), { timestamp, message, type }]);
  }, []);

  // Check order/topup status
  const checkStatus = useCallback(async () => {
    try {
      const tg = (window as any).Telegram?.WebApp;
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      
      // Add Telegram init data if available
      if (tg?.initData) {
        headers['X-Telegram-Init-Data'] = tg.initData;
      }
      
      // Add session token if available
      const sessionToken = localStorage.getItem('session_token');
      if (sessionToken) {
        headers['Authorization'] = `Bearer ${sessionToken}`;
      }

      // Use different endpoint for topup vs order
      const endpoint = isTopUp 
        ? `/api/webapp/profile/topup/${orderId}/status`
        : `/api/webapp/orders/${orderId}/status`;
      
      const response = await fetch(endpoint, { headers });
      
      // Handle 404 specifically - order might not exist yet or invalid ID
      if (response.status === 404) {
        const errorData = await response.json().catch(() => ({}));
        return { 
          status: 'unknown' as PaymentStatus, 
          error: new Error('ORDER_NOT_FOUND'),
          httpStatus: 404,
          errorDetail: errorData
        };
      }
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      
      const data: OrderStatusResponse = await response.json();
      
      // Map backend status to our status type
      const backendStatus = data.status?.toLowerCase() || 'unknown';
      let newStatus: PaymentStatus = 'unknown';
      
      if (['delivered', 'completed', 'ready'].includes(backendStatus)) {
        newStatus = 'delivered';
      } else if (['paid', 'processing'].includes(backendStatus)) {
        newStatus = 'paid';
      } else if (backendStatus === 'partial') {
        newStatus = 'partial';
      } else if (['pending', 'awaiting_payment'].includes(backendStatus)) {
        newStatus = 'pending';
      } else if (['expired', 'cancelled'].includes(backendStatus)) {
        newStatus = 'expired';
      } else if (['failed', 'refunded'].includes(backendStatus)) {
        newStatus = 'failed';
      } else if (backendStatus === 'prepaid') {
        newStatus = 'paid'; // Prepaid means payment confirmed, waiting for stock
      }
      
      return { status: newStatus, data };
    } catch (error: any) {
      console.error('Status check failed:', error);
      return { 
        status: 'unknown' as PaymentStatus, 
        error: error instanceof Error ? error : new Error(String(error)),
        httpStatus: error?.httpStatus
      };
    }
  }, [orderId, isTopUp]);

  // Polling effect with exponential backoff
  useEffect(() => {
    if (isComplete) return;

    const targetLabel = isTopUp ? 'Top-Up' : 'Order';
    addLog(`INIT: ${isTopUp ? 'Balance top-up' : 'Payment'} verification started`, 'info');
    addLog(`TARGET: ${targetLabel} ${orderId.slice(0, 8).toUpperCase()}`, 'info');

    let pollTimeout: NodeJS.Timeout | null = null;
    let progressInterval: NodeJS.Timeout;
    let currentAttempt = 0;
    let shouldStop = false;

    const calculateDelay = (attempt: number): number => {
      // Exponential backoff: 1s, 2s, 4s, 8s, 16s (max)
      const delay = Math.min(
        INITIAL_POLL_DELAY * Math.pow(BACKOFF_MULTIPLIER, attempt),
        MAX_POLL_DELAY
      );
      return delay;
    };

    const poll = async () => {
      if (shouldStop || isComplete) return;

      currentAttempt++;
      setPollCount(currentAttempt);

      // Check if we've exceeded max attempts
      if (currentAttempt > MAX_POLL_ATTEMPTS) {
        addLog(`TIMEOUT: Max verification attempts (${MAX_POLL_ATTEMPTS}) reached`, 'warning');
        addLog('INFO: Order may still be processing. Check your orders later.', 'info');
        setIsComplete(true);
        shouldStop = true;
        return;
      }

      addLog('SCAN: Querying payment gateway...', 'info');
      
      const result = await checkStatus();
      
      // Handle 404 specifically
      if (result.httpStatus === 404 || (result.error && result.error.message === 'ORDER_NOT_FOUND')) {
        consecutive404sRef.current += 1;
        const new404Count = consecutive404sRef.current;

        // If we get multiple consecutive 404s, order likely doesn't exist
        if (new404Count >= 3) {
          addLog('ERROR: Order not found in system', 'error');
          addLog('INFO: Please verify order ID or contact support', 'info');
          setStatus('failed');
          setIsComplete(true);
          shouldStop = true;
          return;
        }

        // First few 404s might be temporary (order not yet in DB after redirect)
        if (currentAttempt <= 3) {
          addLog('WAIT: Order record not yet available, retrying...', 'warning');
        } else {
          addLog('WARN: Order not found, but continuing verification...', 'warning');
        }
      } else {
        // Reset 404 counter on successful response
        if (consecutive404sRef.current > 0) {
          consecutive404sRef.current = 0;
        }

        // Handle successful response
        if (result.status !== 'unknown' || !result.error) {
          setStatus(result.status);
          
          switch (result.status) {
            case 'delivered':
              addLog('RECV: Payment confirmed by gateway', 'success');
              if (isTopUp) {
                addLog('EXEC: Balance credited successfully', 'success');
                addLog('DONE: Top-up complete!', 'success');
              } else {
                addLog('EXEC: Delivery pipeline complete', 'success');
                addLog('DONE: All assets transferred', 'success');
              }
              setProgress(100);
              setIsComplete(true);
              shouldStop = true;
              break;
            case 'paid':
            case 'partial':
              addLog('RECV: Payment confirmed', 'success');
              addLog(isTopUp ? 'PROC: Crediting balance...' : 'PROC: Delivery in progress...', 'info');
              setProgress(75);
              break;
            case 'pending':
              addLog('WAIT: Payment not yet received', 'warning');
              break;
            case 'expired':
            case 'failed':
              addLog(`FAIL: Payment ${result.status}`, 'error');
              setIsComplete(true);
              shouldStop = true;
              break;
            default:
              if (result.error) {
                addLog('WARN: Gateway response delayed, retrying...', 'warning');
              }
          }
        } else if (result.error) {
          // Generic error handling
          addLog('WARN: Gateway response delayed, retrying...', 'warning');
        }
      }

      // Schedule next poll if we should continue
      if (!shouldStop && !isComplete && currentAttempt < MAX_POLL_ATTEMPTS) {
        const delay = calculateDelay(currentAttempt - 1);
        const delaySeconds = (delay / 1000).toFixed(1);
        
        if (currentAttempt > 1) {
          addLog(`NEXT: Retry in ${delaySeconds}s (attempt ${currentAttempt}/${MAX_POLL_ATTEMPTS})`, 'info');
        }

        pollTimeout = setTimeout(() => {
          poll();
        }, delay);
      }
    };

    // Start first poll immediately
    poll();

    // Progress animation (cosmetic)
    progressInterval = setInterval(() => {
      if (!shouldStop && !isComplete) {
        setProgress(prev => {
          if (prev >= 90) return prev; // Cap at 90% until complete
          return prev + Math.random() * 5;
        });
      }
    }, 500);

    // Cleanup
    return () => {
      shouldStop = true;
      if (pollTimeout) {
        clearTimeout(pollTimeout);
      }
      clearInterval(progressInterval);
    };
  }, [orderId, addLog, checkStatus, isComplete]);

  const statusInfo = STATUS_MESSAGES[status];
  const isSuccess = status === 'delivered' || status === 'paid' || status === 'partial';
  const isFailed = status === 'expired' || status === 'failed' || (status === 'unknown' && isComplete && consecutive404sRef.current >= 3);

  return (
    <div className="min-h-screen bg-black flex items-center justify-center p-4">
      <motion.div 
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="w-full max-w-md"
      >
        {/* Header */}
        <div className="text-center mb-8">
          <div className="font-mono text-xs text-gray-500 mb-2">PVNDORA // PAYMENT GATEWAY</div>
          <div className="font-display text-2xl font-bold text-white tracking-wider">
            TRANSACTION_STATUS
          </div>
        </div>

        {/* Main Terminal Card */}
        <div className="bg-[#080808] border border-white/10 overflow-hidden">
          {/* Status Header */}
          <div className={`p-4 border-b border-white/10 bg-${statusInfo.color}-500/10`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                {status === 'checking' && (
                  <div className="relative">
                    <div className="w-10 h-10 border-2 border-purple-500/30 border-t-purple-500 rounded-full animate-spin" />
                    <Cpu size={16} className="absolute inset-0 m-auto text-purple-500" />
                  </div>
                )}
                {isSuccess && <CheckCircle size={24} className="text-green-500" />}
                {isFailed && <XCircle size={24} className="text-red-500" />}
                {status === 'pending' && <Clock size={24} className="text-orange-500 animate-pulse" />}
                {status === 'unknown' && <AlertTriangle size={24} className="text-gray-500" />}
                
                <div>
                  <div className={`font-mono text-sm font-bold text-${statusInfo.color}-500`}>
                    [ {statusInfo.label} ]
                  </div>
                  <div className="text-xs text-gray-400">{statusInfo.description}</div>
                </div>
              </div>
              
              <div className="font-mono text-xs text-gray-500">
                ID: {orderId.slice(0, 8).toUpperCase()}
              </div>
            </div>
          </div>

          {/* Progress Bar */}
          <div className="px-4 py-3 border-b border-white/5">
            <div className="flex justify-between text-[10px] font-mono text-gray-500 mb-1">
              <span>VERIFICATION_PROGRESS</span>
              <span>{Math.round(progress)}%</span>
            </div>
            <div className="h-1 bg-gray-800 rounded-full overflow-hidden">
              <motion.div 
                initial={{ width: 0 }}
                animate={{ width: `${progress}%` }}
                className={`h-full ${isSuccess ? 'bg-green-500' : isFailed ? 'bg-red-500' : 'bg-purple-500'}`}
                style={{ boxShadow: `0 0 10px ${isSuccess ? '#22c55e' : isFailed ? '#ef4444' : '#a855f7'}` }}
              />
            </div>
          </div>

          {/* Terminal Logs */}
          <div className="p-4 bg-black/50 h-48 overflow-hidden font-mono text-[10px] flex flex-col justify-end">
            <AnimatePresence mode="popLayout">
              {logs.map((log, i) => (
                <motion.div
                  key={`${log.timestamp}-${i}`}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0 }}
                  className="mb-1 flex gap-2"
                >
                  <span className="text-gray-600">{log.timestamp}</span>
                  <span className={
                    log.type === 'success' ? 'text-green-500' :
                    log.type === 'error' ? 'text-red-500' :
                    log.type === 'warning' ? 'text-orange-500' :
                    'text-gray-400'
                  }>
                    {log.message}
                  </span>
                </motion.div>
              ))}
            </AnimatePresence>
            <div className="w-2 h-4 bg-gray-600 animate-pulse mt-1" />
          </div>

          {/* Actions */}
          {isComplete && (
            <div className="p-4 border-t border-white/10 space-y-3">
              {isSuccess && (
                <button
                  onClick={onViewOrders}
                  className="w-full py-3 bg-pandora-cyan text-black font-bold text-sm flex items-center justify-center gap-2 hover:bg-pandora-cyan/90 transition-colors"
                >
                  {isTopUp ? 'VIEW_PROFILE' : 'VIEW_ORDERS'}
                  <ArrowRight size={16} />
                </button>
              )}
              
              {(isFailed || (status === 'unknown' && isComplete && consecutive404sRef.current >= 3)) && (
                <>
                  <button
                    onClick={() => window.location.reload()}
                    className="w-full py-3 bg-white/10 text-white font-bold text-sm flex items-center justify-center gap-2 hover:bg-white/20 transition-colors"
                  >
                    <RefreshCw size={16} />
                    RETRY
                  </button>
                  <button
                    onClick={onViewOrders}
                    className="w-full py-2 bg-transparent border border-white/20 text-gray-400 text-xs font-mono hover:border-white/40 transition-colors"
                  >
                    CHECK_ORDERS_MANUALLY
                  </button>
                </>
              )}
              
              <button
                onClick={onComplete}
                className="w-full py-2 bg-transparent border border-white/20 text-gray-400 text-xs font-mono hover:border-white/40 transition-colors"
              >
                RETURN_TO_CATALOG
              </button>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="text-center mt-4 font-mono text-[10px] text-gray-600">
          {!isComplete && (
            <span className="animate-pulse">
              LIVE CONNECTION • Poll #{pollCount}
            </span>
          )}
          {isComplete && (
            <span>CONNECTION_CLOSED</span>
          )}
        </div>
      </motion.div>
    </div>
  );
}

export default PaymentResult;
