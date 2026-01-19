/**
 * PaymentProcessing Component
 *
 * Displays payment processing animation with logs.
 */

import { motion } from "framer-motion";
import { Cpu } from "lucide-react";
import type React from "react";
import { memo } from "react";
import type { PaymentMethod } from "./CheckoutModal";

interface PaymentProcessingProps {
  logs: string[];
  selectedPayment: PaymentMethod;
}

const PaymentProcessing: React.FC<PaymentProcessingProps> = ({ logs, selectedPayment }) => {
  const isInternal = selectedPayment === "internal";

  return (
    <motion.div
      animate={{ opacity: 1 }}
      className="flex min-h-[300px] flex-col items-center justify-center py-8"
      exit={{ opacity: 0 }}
      initial={{ opacity: 0 }}
      key="processing"
    >
      {/* Central Spinner / Loader */}
      <div className="relative mb-8">
        <div
          className={`h-20 w-20 animate-spin rounded-full border-4 border-t-transparent ${
            isInternal
              ? "border-green-500/30 border-t-green-500"
              : "border-purple-500/30 border-t-purple-500"
          }`}
        />
        <div className="absolute inset-0 flex items-center justify-center">
          <Cpu
            className={`animate-pulse ${isInternal ? "text-green-500" : "text-purple-500"}`}
            size={24}
          />
        </div>
      </div>

      {/* Progress Bar */}
      <div className="relative mb-6 h-1 w-64 overflow-hidden rounded-full bg-gray-800">
        <motion.div
          animate={{ width: "100%" }}
          className={`relative h-full ${
            isInternal
              ? "bg-green-500 shadow-[0_0_10px_#00FF00]"
              : "bg-purple-500 shadow-[0_0_10px_#a855f7]"
          }`}
          initial={{ width: "0%" }}
          transition={{ duration: 4.5, ease: "linear" }}
        >
          <div className="absolute top-0 right-0 h-full w-20 bg-gradient-to-l from-white/50 to-transparent" />
        </motion.div>
      </div>

      {/* Terminal Logs */}
      <div className="flex h-32 w-full max-w-sm flex-col justify-end overflow-hidden border border-white/10 bg-black/50 p-4 font-mono text-[10px]">
        {logs.map((log) => (
          <motion.div
            animate={{ opacity: 1, x: 0 }}
            className={`mb-1 ${log.includes("ERROR") ? "text-red-500" : "text-gray-400"}`}
            initial={{ opacity: 0, x: -10 }}
            key={log}
          >
            <span className={isInternal ? "text-green-500" : "text-purple-500"}>
              {log.split(":")[0]}
            </span>
            {log.includes(":") && <span className="text-gray-300">:{log.split(":")[1]}</span>}
          </motion.div>
        ))}
        <div className="mt-1 h-4 w-2 animate-pulse bg-gray-500" />
      </div>
    </motion.div>
  );
};

export default memo(PaymentProcessing);
