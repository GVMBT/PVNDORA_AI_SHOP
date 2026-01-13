/**
 * PaymentCountdown Component
 *
 * Displays countdown timer for pending order payment deadline.
 */

import { AlertTriangle, Clock } from "lucide-react";
import React, { useEffect, useState } from "react";

interface PaymentCountdownProps {
  deadline: string;
}

export function PaymentCountdown({ deadline }: PaymentCountdownProps) {
  const [timeLeft, setTimeLeft] = useState<string>("");
  const [isExpired, setIsExpired] = useState(false);

  useEffect(() => {
    const updateTimer = () => {
      try {
        // Parse ISO string (expires_at from API)
        // Format: "2025-12-15T16:53:41.123456+00:00" or "2025-12-15T16:53:41Z"
        const deadlineDate = new Date(deadline);

        // Validate date
        if (isNaN(deadlineDate.getTime())) {
          console.error("PaymentCountdown: Invalid date", deadline);
          setTimeLeft("--:--");
          return;
        }

        const now = new Date();
        const diff = deadlineDate.getTime() - now.getTime();

        if (diff <= 0) {
          setIsExpired(true);
          setTimeLeft("EXPIRED");
          return;
        }

        const totalSeconds = Math.floor(diff / 1000);
        const minutes = Math.floor(totalSeconds / 60);
        const seconds = totalSeconds % 60;

        if (minutes > 0) {
          setTimeLeft(`${minutes}m ${seconds}s`);
        } else {
          setTimeLeft(`${seconds}s`);
        }
      } catch (e) {
        console.error("PaymentCountdown error:", e, "deadline:", deadline);
        setTimeLeft("--:--");
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
