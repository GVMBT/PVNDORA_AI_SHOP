/**
 * AppLayout Component
 *
 * Provides the main visual layout including:
 * - Background gradient
 * - Grid overlay
 * - Mouse spotlight effect
 * - Grain/scanline overlay
 */

import { motion, useMotionTemplate, useMotionValue } from "framer-motion";
import type React from "react";
import { memo, useEffect } from "react";

interface AppLayoutProps {
  readonly children: React.ReactNode;
}

function AppLayoutComponent({ children }: AppLayoutProps) {
  // Spotlight mouse tracking
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);

  const spotlightBackground = useMotionTemplate`
    radial-gradient(
      600px circle at ${mouseX}px ${mouseY}px,
      rgba(0, 255, 255, 0.07),
      transparent 80%
    )
  `;

  useEffect(() => {
    const handleMouseMove = ({ clientX, clientY }: MouseEvent) => {
      mouseX.set(clientX);
      mouseY.set(clientY);
    };
    globalThis.addEventListener("mousemove", handleMouseMove);
    return () => globalThis.removeEventListener("mousemove", handleMouseMove);
  }, [mouseX, mouseY]);

  return (
    <div className="relative min-h-screen overflow-x-hidden text-white selection:bg-pandora-cyan selection:text-black">
      {/* === UNIFIED FIXED BACKGROUND LAYER === */}
      <div className="fixed inset-0 z-[-2] bg-[radial-gradient(circle_at_50%_0%,_#0e3a3a_0%,_#050505_90%)]" />

      {/* === GLOBAL BACKGROUND GRID (Fixed Layer) === */}
      <div
        className="pointer-events-none fixed inset-0 z-[-1] opacity-[0.03]"
        style={{
          backgroundImage:
            "linear-gradient(#00FFFF 1px, transparent 1px), linear-gradient(90deg, #00FFFF 1px, transparent 1px)",
          backgroundSize: "40px 40px",
          backgroundPosition: "center top",
        }}
      />

      {/* GLOBAL SPOTLIGHT EFFECT */}
      <motion.div
        className="pointer-events-none fixed inset-0 z-0 mix-blend-plus-lighter transition-opacity duration-300"
        style={{ background: spotlightBackground }}
      />

      {/* Main content */}
      {children}

      {/* Subtle Grain/Scanline Effect */}
      <div
        className="pointer-events-none fixed inset-0 z-[100] opacity-[0.02] brightness-100 contrast-150"
        style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")`,
        }}
      />
    </div>
  );
}

export const AppLayout = memo(AppLayoutComponent);
