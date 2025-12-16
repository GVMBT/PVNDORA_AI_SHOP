/**
 * PaymentProcessing Component
 * 
 * Displays payment processing animation with logs.
 */

import React, { memo } from 'react';
import { motion } from 'framer-motion';
import { Cpu } from 'lucide-react';
import type { PaymentMethod } from './CheckoutModal';

interface PaymentProcessingProps {
  logs: string[];
  selectedPayment: PaymentMethod;
}

const PaymentProcessing: React.FC<PaymentProcessingProps> = ({ logs, selectedPayment }) => {
  const isInternal = selectedPayment === 'internal';
  
  return (
    <motion.div 
      key="processing"
      initial={{ opacity: 0 }} 
      animate={{ opacity: 1 }} 
      exit={{ opacity: 0 }}
      className="flex flex-col items-center justify-center py-8 min-h-[300px]"
    >
      {/* Central Spinner / Loader */}
      <div className="relative mb-8">
        <div className={`w-20 h-20 border-4 border-t-transparent rounded-full animate-spin ${
          isInternal ? 'border-green-500/30 border-t-green-500' : 'border-purple-500/30 border-t-purple-500'
        }`} />
        <div className="absolute inset-0 flex items-center justify-center">
          <Cpu size={24} className={`animate-pulse ${isInternal ? 'text-green-500' : 'text-purple-500'}`} />
        </div>
      </div>

      {/* Progress Bar */}
      <div className="w-64 h-1 bg-gray-800 rounded-full overflow-hidden mb-6 relative">
        <motion.div 
          initial={{ width: "0%" }}
          animate={{ width: "100%" }}
          transition={{ duration: 4.5, ease: "linear" }}
          className={`h-full relative ${
            isInternal 
              ? 'bg-green-500 shadow-[0_0_10px_#00FF00]' 
              : 'bg-purple-500 shadow-[0_0_10px_#a855f7]'
          }`}
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
            <span className={isInternal ? 'text-green-500' : 'text-purple-500'}>
              {log.split(':')[0]}
            </span>
            {log.includes(':') && (
              <span className="text-gray-300">:{log.split(':')[1]}</span>
            )}
          </motion.div>
        ))}
        <div className="w-2 h-4 bg-gray-500 animate-pulse mt-1" />
      </div>
    </motion.div>
  );
};

export default memo(PaymentProcessing);












