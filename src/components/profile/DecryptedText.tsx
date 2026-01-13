/**
 * DecryptedText Component
 *
 * Animated text reveal effect with decryption animation.
 */

import React, { useState, useEffect, useRef } from "react";
import { randomChar } from "../../utils/random";

const CHARS = "ABCDEF0123456789!@#$%^&*()_+-=[]{}|;':\",./<>?";

interface DecryptedTextProps {
  text: string | number;
  speed?: number;
  className?: string;
  reveal?: boolean;
}

const DecryptedText: React.FC<DecryptedTextProps> = ({
  text,
  speed = 30,
  className = "",
  reveal = true,
}) => {
  const [displayText, setDisplayText] = useState("");
  const [isFinished, setIsFinished] = useState(false);
  const textStr = String(text);
  const elementRef = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (!reveal) return;

    // Use IntersectionObserver to pause animation when not visible (save CPU)
    let isVisible = true;
    let observer: IntersectionObserver | null = null;

    if (elementRef.current) {
      observer = new IntersectionObserver(
        (entries) => {
          isVisible = entries[0].isIntersecting;
        },
        { threshold: 0.1 }
      );
      observer.observe(elementRef.current);
    }

    let iteration = 0;
    let rafId: number | null = null;
    let lastTime = performance.now();
    const targetInterval = Math.max(speed, 16); // min 16ms (60fps)

    const animate = (currentTime: number) => {
      if (!isVisible || isFinished) {
        rafId = requestAnimationFrame(animate);
        return;
      }

      const delta = currentTime - lastTime;
      if (delta >= targetInterval) {
        setDisplayText(
          textStr
            .split("")
            .map((letter, index) => {
              if (index < iteration) {
                return textStr[index];
              }
              return randomChar(CHARS);
            })
            .join("")
        );

        if (iteration >= textStr.length) {
          setIsFinished(true);
          if (observer) observer.disconnect();
          return;
        }
        iteration += 1 / 2; // Speed of decryption
        lastTime = currentTime;
      }

      rafId = requestAnimationFrame(animate);
    };

    rafId = requestAnimationFrame(animate);

    return () => {
      if (rafId) cancelAnimationFrame(rafId);
      if (observer) observer.disconnect();
    };
  }, [textStr, speed, reveal, isFinished]);

  return (
    <span ref={elementRef} className={className}>
      {displayText || (reveal ? "" : textStr)}
    </span>
  );
};

export default DecryptedText;
