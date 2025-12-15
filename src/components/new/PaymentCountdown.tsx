/**
 * PaymentCountdown Component
 * 
 * Displays countdown timer for pending order payment deadline.
 */

import React, { useState, useEffect } from 'react';
import { Clock, AlertTriangle } from 'lucide-react';

interface PaymentCountdownProps {
  deadline: string;
}

export function PaymentCountdown({ deadline }: PaymentCountdownProps) {
  const [timeLeft, setTimeLeft] = useState<string>('');
  const [isExpired, setIsExpired] = useState(false);

  useEffect(() => {
    const updateTimer = () => {
      try {
        // Parse deadline (format: "DD.MM.YY, HH:MM:SS (UTC+3)" or ISO string)
        let deadlineDate: Date;
        if (deadline.includes('UTC') || deadline.includes('GMT')) {
          // Parse formatted date string - extract just the date/time part
          const dateStr = deadline.replace(/ \(.*\)$/, '').replace(',', '');
          deadlineDate = new Date(dateStr);
        } else {
          deadlineDate = new Date(deadline);
        }

        const now = new Date();
        const diff = deadlineDate.getTime() - now.getTime();

        if (diff <= 0) {
          setIsExpired(true);
          setTimeLeft('EXPIRED');
          return;
        }

        const minutes = Math.floor(diff / 60000);
        const seconds = Math.floor((diff % 60000) / 1000);
        
        if (minutes > 0) {
          setTimeLeft(`${minutes}m ${seconds}s`);
        } else {
          setTimeLeft(`${seconds}s`);
        }
      } catch (e) {
        setTimeLeft('--:--');
      }
    };

    updateTimer();
    const interval = setInterval(updateTimer, 1000);

    return () => clearInterval(interval);
  }, [deadline]);

  if (isExpired) {
    return (
      <div className="text-[9px] font-mono text-red-400 flex items-center gap-1">
        <AlertTriangle size={10} />
        PAYMENT_TIMEOUT — Order will be cancelled
      </div>
    );
  }

  return (
    <div className="text-[9px] font-mono text-orange-400 flex items-center gap-1">
      <Clock size={10} />
      TIME_LEFT: {timeLeft}
    </div>
  );
}

