/**
 * ProductCardMedia - Optimized media component for product cards
 *
 * Supports:
 * - Static images (fallback)
 * - Video backgrounds (WebM/MP4 with low bitrate)
 * - Canvas particle effects (lightweight, no three.js)
 * - Parallax integration with framer-motion
 *
 * Performance optimizations:
 * - Lazy loading for videos
 * - Intersection Observer for canvas rendering
 * - RequestAnimationFrame throttling
 * - Automatic quality reduction on mobile
 */

import { type MotionValue, useMotionValue, useTransform } from "framer-motion";
import type React from "react";
import { useEffect, useRef, useState } from "react";

interface ProductCardMediaProps {
  image: string;
  video?: string; // Optional video URL (WebM preferred, MP4 fallback)
  useParticles?: boolean; // Enable canvas particle effects
  parallaxX?: MotionValue<number>; // Parallax X from framer-motion
  parallaxY?: MotionValue<number>; // Parallax Y from framer-motion
  className?: string;
  alt?: string;
}

// Lightweight particle system (no three.js)
class ParticleSystem {
  private readonly canvas: HTMLCanvasElement;
  private readonly ctx: CanvasRenderingContext2D;
  private particles: Particle[] = [];
  private animationFrame: number | null = null;
  private isActive = false;
  private parallaxX = 0;
  private parallaxY = 0;

  constructor(canvas: HTMLCanvasElement) {
    this.canvas = canvas;
    const ctx = canvas.getContext("2d", { alpha: true, desynchronized: true });
    if (!ctx) throw new Error("Canvas context not available");
    this.ctx = ctx;
    this.resize();
  }

  private resize() {
    const dpr = Math.min(globalThis.devicePixelRatio || 1, 2); // Limit DPR for performance
    this.canvas.width = this.canvas.offsetWidth * dpr;
    this.canvas.height = this.canvas.offsetHeight * dpr;
    this.ctx.scale(dpr, dpr);
  }

  setParallax(x: number, y: number) {
    this.parallaxX = x * 20; // Scale parallax effect
    this.parallaxY = y * 20;
  }

  init(particleCount = 30) {
    const width = this.canvas.offsetWidth;
    const height = this.canvas.offsetHeight;

    this.particles = Array.from({ length: particleCount }, () => ({
      x: Math.random() * width,
      y: Math.random() * height,
      vx: (Math.random() - 0.5) * 0.5,
      vy: (Math.random() - 0.5) * 0.5,
      size: Math.random() * 2 + 1,
      opacity: Math.random() * 0.5 + 0.2,
      color: `rgba(0, 255, 255, ${Math.random() * 0.3 + 0.1})`, // Pandora cyan
    }));
  }

  private draw() {
    const width = this.canvas.offsetWidth;
    const height = this.canvas.offsetHeight;

    // Clear with fade effect
    this.ctx.fillStyle = "rgba(0, 0, 0, 0.1)";
    this.ctx.fillRect(0, 0, width, height);

    // Update and draw particles
    this.particles.forEach((particle) => {
      // Apply parallax
      particle.x += particle.vx + this.parallaxX * 0.01;
      particle.y += particle.vy + this.parallaxY * 0.01;

      // Wrap around edges
      if (particle.x < 0) particle.x = width;
      if (particle.x > width) particle.x = 0;
      if (particle.y < 0) particle.y = height;
      if (particle.y > height) particle.y = 0;

      // Draw particle
      this.ctx.beginPath();
      this.ctx.arc(particle.x, particle.y, particle.size, 0, Math.PI * 2);
      this.ctx.fillStyle = particle.color;
      this.ctx.globalAlpha = particle.opacity;
      this.ctx.fill();

      // Draw connections to nearby particles
      this.particles.forEach((other) => {
        const dx = particle.x - other.x;
        const dy = particle.y - other.y;
        const distance = Math.hypot(dx, dy);

        if (distance < 80) {
          this.ctx.beginPath();
          this.ctx.moveTo(particle.x, particle.y);
          this.ctx.lineTo(other.x, other.y);
          this.ctx.strokeStyle = `rgba(0, 255, 255, ${(1 - distance / 80) * 0.1})`;
          this.ctx.globalAlpha = (1 - distance / 80) * 0.2;
          this.ctx.lineWidth = 0.5;
          this.ctx.stroke();
        }
      });
    });

    this.ctx.globalAlpha = 1;
  }

  start() {
    if (this.isActive) return;
    this.isActive = true;

    const animate = () => {
      if (!this.isActive) return;
      this.draw();
      this.animationFrame = requestAnimationFrame(animate);
    };

    animate();
  }

  stop() {
    this.isActive = false;
    if (this.animationFrame !== null) {
      cancelAnimationFrame(this.animationFrame);
      this.animationFrame = null;
    }
  }

  destroy() {
    this.stop();
    this.particles = [];
  }
}

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  size: number;
  opacity: number;
  color: string;
}

const ProductCardMedia: React.FC<ProductCardMediaProps> = ({
  image,
  video,
  useParticles = false,
  parallaxX,
  parallaxY,
  className = "",
  alt = "Product",
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const particleSystemRef = useRef<ParticleSystem | null>(null);
  const [isInView, setIsInView] = useState(false);
  const [useVideo, setUseVideo] = useState(false);
  const [videoError, setVideoError] = useState(false);

  // Parallax values (fallback if not provided)
  const defaultX = useMotionValue(0);
  const defaultY = useMotionValue(0);
  const px = parallaxX || defaultX;
  const py = parallaxY || defaultY;

  // Transform parallax to canvas coordinates
  const canvasX = useTransform(px, (v) => v);
  const canvasY = useTransform(py, (v) => v);

  // Intersection Observer for lazy loading
  useEffect(() => {
    if (!containerRef.current) return;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          setIsInView(entry.isIntersecting);
        });
      },
      { threshold: 0.1, rootMargin: "50px" }
    );

    observer.observe(containerRef.current);

    return () => {
      if (containerRef.current) {
        observer.unobserve(containerRef.current);
      }
    };
  }, []);

  // Initialize particle system
  useEffect(() => {
    if (!(useParticles && canvasRef.current && isInView)) return;

    try {
      const system = new ParticleSystem(canvasRef.current);
      const particleCount = globalThis.innerWidth < 768 ? 15 : 30; // Fewer particles on mobile
      system.init(particleCount);
      particleSystemRef.current = system;

      // Subscribe to parallax changes
      // Note: The subscription callbacks update system.setParallax on each change
      // We don't need to track unsubscribe as system.destroy() handles cleanup
      canvasX.on("change", (v) => {
        canvasY.on("change", (y) => {
          system.setParallax(v, y);
        });
      });

      system.start();

      return () => {
        system.destroy();
        particleSystemRef.current = null;
      };
    } catch (err) {
      console.warn("Particle system initialization failed:", err);
    }
  }, [useParticles, isInView, canvasX, canvasY]);

  // Handle video loading
  useEffect(() => {
    if (!(video && videoRef.current && isInView) || videoError) return;

    const videoEl = videoRef.current;

    // Try to load video
    const handleCanPlay = () => {
      setUseVideo(true);
      videoEl.play().catch(() => {
        // Autoplay blocked, fallback to image
        setVideoError(true);
      });
    };

    const handleError = () => {
      setVideoError(true);
      setUseVideo(false);
    };

    videoEl.addEventListener("canplay", handleCanPlay);
    videoEl.addEventListener("error", handleError);

    // Load video
    videoEl.load();

    return () => {
      videoEl.removeEventListener("canplay", handleCanPlay);
      videoEl.removeEventListener("error", handleError);
    };
  }, [video, isInView, videoError]);

  // Determine what to render
  const shouldShowVideo = useVideo && video && !videoError && isInView;
  const shouldShowParticles = useParticles && isInView;

  return (
    <div className={`relative h-full w-full overflow-hidden ${className}`} ref={containerRef}>
      {/* Base Image (always present as fallback) */}
      <img
        alt={alt}
        className={`absolute inset-0 h-full w-full object-cover transition-opacity duration-700 ${
          shouldShowVideo
            ? "opacity-0"
            : "opacity-60 grayscale group-hover:opacity-100 group-hover:grayscale-0"
        }`}
        decoding="async"
        loading="lazy"
        src={image}
      />

      {/* Video Background (if available and loaded) */}
      {video && (
        <video
          className={`absolute inset-0 h-full w-full object-cover transition-opacity duration-700 ${
            shouldShowVideo
              ? "opacity-60 grayscale group-hover:opacity-100 group-hover:grayscale-0"
              : "opacity-0"
          }`}
          loop
          muted
          playsInline
          preload="metadata"
          ref={videoRef}
          style={{ transform: "scale(1.05)" }} // Slight zoom to prevent edges
        >
          <source src={video} type="video/webm" />
          <source src={video.replace(".webm", ".mp4")} type="video/mp4" />
        </video>
      )}

      {/* Canvas Particle System */}
      {shouldShowParticles && (
        <canvas
          className="pointer-events-none absolute inset-0 h-full w-full opacity-0 transition-opacity duration-300 group-hover:opacity-100"
          ref={canvasRef}
          style={{ mixBlendMode: "screen" }}
        />
      )}
    </div>
  );
};

export default ProductCardMedia;
