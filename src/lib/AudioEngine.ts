/**
 * PVNDORA Audio Engine
 *
 * Hybrid audio system: uses preloaded .ogg files with procedural fallback.
 * Optimized for low latency with AudioBuffer caching.
 *
 * Audio Worker is NOT needed for short SFX (<1s) - AudioBuffer is sufficient.
 * For background music, use BackgroundMusic component (HTMLAudioElement).
 */

import { logger } from "../utils/logger";

type OscillatorType = "sine" | "square" | "sawtooth" | "triangle";

interface ToneConfig {
  freq: number;
  type: OscillatorType;
  duration: number;
  volume?: number;
  delay?: number;
}

// Sound file mapping
const SOUND_FILES: Record<string, string> = {
  click: "/click-project.ogg",
  uiShort: "/ui-short.ogg", // open/close modals, navigation
  uiLong: "/ui-long.ogg", // product card open
  decrypt: "/Dossier.ogg",
  // success: '/success.ogg', // Missing file
  // error: '/error.ogg', // Missing file
  // warning: '/warning.ogg', // Missing file
  // notification: '/notification.ogg', // Missing file
  // addToCart: '/add-to-cart.ogg', // Missing file
  // transaction: '/transaction.ogg', // Missing file
};

class AudioEngineClass {
  private ctx: AudioContext | null = null;
  private masterGain: GainNode | null = null;
  private enabled: boolean = true;
  private initialized: boolean = false;

  // AudioBuffer cache for instant playback
  private soundCache: Map<string, AudioBuffer> = new Map();
  private loadingPromises: Map<string, Promise<AudioBuffer | null>> = new Map();

  // Throttle for frequent sounds (hover, click) to prevent CPU overload
  private lastSoundTime: Map<string, number> = new Map();
  private readonly THROTTLE_MS = 50; // Minimum 50ms between same sound type

  /**
   * Initialize AudioContext (must be called after user interaction)
   */
  init(): void {
    if (this.ctx) return;

    try {
      const AudioContextClass = globalThis.AudioContext || globalThis.webkitAudioContext;
      if (!AudioContextClass) {
        logger.warn("[AudioEngine] Web Audio API not supported");
        return;
      }

      this.ctx = new AudioContextClass();
      this.masterGain = this.ctx.createGain();
      this.masterGain.gain.value = 0.5;
      this.masterGain.connect(this.ctx.destination);
      this.initialized = true;

      logger.debug("[AudioEngine] Initialized");

      // Preload critical sounds
      this.preloadSounds();
    } catch (e) {
      logger.warn("[AudioEngine] Failed to initialize", e);
    }
  }

  /**
   * Resume AudioContext if suspended (required by browsers)
   */
  async resume(): Promise<void> {
    if (this.ctx && this.ctx.state === "suspended") {
      await this.ctx.resume();
    }
  }

  /**
   * Enable/disable all sounds
   */
  setEnabled(enabled: boolean): void {
    this.enabled = enabled;
  }

  /**
   * Set master volume (0-1)
   */
  setVolume(volume: number): void {
    if (this.masterGain) {
      this.masterGain.gain.value = Math.max(0, Math.min(1, volume));
    }
  }

  /**
   * Preload critical sounds for instant playback
   */
  private async preloadSounds(): Promise<void> {
    if (!this.ctx) return;

    const criticalSounds = ["click", "uiShort", "uiLong", "success", "error", "notification"];

    // Load in parallel
    await Promise.allSettled(criticalSounds.map((key) => this.loadSound(key)));

    logger.debug(`[AudioEngine] Preloaded ${this.soundCache.size} sound(s)`);
  }

  /**
   * Load and cache a sound file
   */
  private async loadSound(key: string): Promise<AudioBuffer | null> {
    if (!this.ctx) return null;

    // Return cached if available
    if (this.soundCache.has(key)) {
      return this.soundCache.get(key)!;
    }

    // Return existing promise if loading
    if (this.loadingPromises.has(key)) {
      return this.loadingPromises.get(key)!;
    }

    // Start loading
    const filePath = SOUND_FILES[key];
    if (!filePath) {
      logger.warn(`[AudioEngine] No file mapping for sound: ${key}`);
      return null;
    }

    const loadPromise = (async () => {
      try {
        const response = await fetch(filePath);
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const arrayBuffer = await response.arrayBuffer();
        const audioBuffer = await this.ctx!.decodeAudioData(arrayBuffer);

        // Cache the buffer
        this.soundCache.set(key, audioBuffer);
        this.loadingPromises.delete(key);

        logger.debug(`[AudioEngine] Loaded: ${key}`);
        return audioBuffer;
      } catch (error) {
        logger.warn(`[AudioEngine] Failed to load ${key}`, error);
        this.loadingPromises.delete(key);
        return null;
      }
    })();

    this.loadingPromises.set(key, loadPromise);
    return loadPromise;
  }

  /**
   * Play a sound file from cache or load it
   */
  private async playSoundFile(key: string, volume: number = 1.0): Promise<void> {
    if (!this.ctx || !this.masterGain || !this.enabled) return;

    const buffer = await this.loadSound(key);
    if (!buffer) {
      // Fallback to procedural generation
      logger.warn(`[AudioEngine] File not available, using procedural fallback for: ${key}`);
      // Throw error to trigger catch block in caller (which activates procedural fallback)
      throw new Error(`Sound file not found: ${key}`);
    }

    const source = this.ctx.createBufferSource();
    const gain = this.ctx.createGain();

    source.buffer = buffer;
    gain.gain.value = volume;

    source.connect(gain);
    gain.connect(this.masterGain);

    source.start(0);
  }

  /**
   * Check if sound should be throttled (prevents CPU overload from rapid sounds)
   */
  private shouldThrottle(soundKey?: string): boolean {
    if (!soundKey) return false;
    const now = Date.now();
    const lastTime = this.lastSoundTime.get(soundKey) || 0;
    if (now - lastTime < this.THROTTLE_MS) {
      return true; // Too soon, skip
    }
    this.lastSoundTime.set(soundKey, now);
    return false;
  }

  /**
   * Play a single tone (procedural fallback)
   */
  private playTone(config: ToneConfig, soundKey?: string): void {
    if (!this.ctx || !this.masterGain || !this.enabled) return;
    // Throttle frequent sounds to prevent CPU overload
    if (this.shouldThrottle(soundKey)) return;

    const { freq, type, duration, volume = 0.05, delay = 0 } = config;
    const now = this.ctx.currentTime + delay;

    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();

    osc.type = type;
    osc.frequency.setValueAtTime(freq, now);

    gain.gain.setValueAtTime(0, now);
    gain.gain.linearRampToValueAtTime(volume, now + 0.01);
    gain.gain.exponentialRampToValueAtTime(0.001, now + duration);

    osc.connect(gain);
    gain.connect(this.masterGain);

    osc.start(now);
    osc.stop(now + duration);
  }

  /**
   * Play white noise burst (procedural)
   */
  private playNoise(duration: number, volume: number = 0.02, delay: number = 0): void {
    if (!this.ctx || !this.masterGain || !this.enabled) return;

    const now = this.ctx.currentTime + delay;
    const bufferSize = Math.floor(this.ctx.sampleRate * duration);
    const buffer = this.ctx.createBuffer(1, bufferSize, this.ctx.sampleRate);
    const data = buffer.getChannelData(0);

    for (let i = 0; i < bufferSize; i++) {
      data[i] = Math.random() * 2 - 1;
    }

    const noise = this.ctx.createBufferSource();
    const filter = this.ctx.createBiquadFilter();
    const gain = this.ctx.createGain();

    noise.buffer = buffer;
    filter.type = "highpass";
    filter.frequency.value = 1000;

    gain.gain.setValueAtTime(volume, now);
    gain.gain.exponentialRampToValueAtTime(0.001, now + duration);

    noise.connect(filter);
    filter.connect(gain);
    gain.connect(this.masterGain);

    noise.start(now);
  }

  /**
   * Play frequency sweep (procedural)
   */
  private playSweep(
    startFreq: number,
    endFreq: number,
    duration: number,
    type: OscillatorType = "sine",
    volume: number = 0.03
  ): void {
    if (!this.ctx || !this.masterGain || !this.enabled) return;

    const now = this.ctx.currentTime;
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();

    osc.type = type;
    osc.frequency.setValueAtTime(startFreq, now);
    osc.frequency.exponentialRampToValueAtTime(endFreq, now + duration);

    gain.gain.setValueAtTime(volume, now);
    gain.gain.exponentialRampToValueAtTime(0.001, now + duration);

    osc.connect(gain);
    gain.connect(this.masterGain);

    osc.start(now);
    osc.stop(now + duration);
  }

  // ============================================
  // PUBLIC SFX METHODS
  // ============================================

  /**
   * Light hover sound (procedural - too short for file)
   */
  hover(): void {
    this.playTone({ freq: 800, type: "sine", duration: 0.03, volume: 0.008 });
  }

  /**
   * Button click
   */
  click(): void {
    this.playSoundFile("click", 0.5).catch(() => {
      // Fallback to procedural
      this.playTone({ freq: 1200, type: "square", duration: 0.05, volume: 0.015 }, "click");
      this.playNoise(0.03, 0.01);
    });
  }

  /**
   * Success notification
   */
  success(): void {
    this.playSoundFile("success", 0.6).catch(() => {
      // Fallback to procedural
      this.playTone({ freq: 440, type: "sine", duration: 0.15, volume: 0.04, delay: 0 });
      this.playTone({ freq: 554, type: "sine", duration: 0.15, volume: 0.04, delay: 0.08 });
      this.playTone({ freq: 659, type: "sine", duration: 0.25, volume: 0.05, delay: 0.16 });
    });
  }

  /**
   * Error notification
   */
  error(): void {
    this.playSoundFile("error", 0.6).catch(() => {
      // Fallback to procedural
      this.playTone({ freq: 150, type: "sawtooth", duration: 0.3, volume: 0.04 });
      this.playTone({ freq: 120, type: "sawtooth", duration: 0.4, volume: 0.03, delay: 0.1 });
    });
  }

  /**
   * Warning notification
   */
  warning(): void {
    this.playSoundFile("warning", 0.6).catch(() => {
      // Fallback to procedural
      this.playTone({ freq: 880, type: "triangle", duration: 0.15, volume: 0.03 });
      this.playTone({ freq: 880, type: "triangle", duration: 0.15, volume: 0.03, delay: 0.2 });
    });
  }

  /**
   * Modal/menu open (ui-short.ogg)
   */
  open(): void {
    this.playSoundFile("uiShort", 0.5).catch(() => {
      // Fallback to procedural
      this.playSweep(150, 400, 0.15, "sine", 0.03);
    });
  }

  /**
   * Modal/menu close (ui-short.ogg)
   */
  close(): void {
    this.playSoundFile("uiShort", 0.5).catch(() => {
      // Fallback to procedural
      this.playSweep(400, 150, 0.1, "sine", 0.02);
    });
  }

  /**
   * Product card open (ui-long.ogg)
   */
  productOpen(): void {
    this.playSoundFile("uiLong", 0.5).catch(() => {
      // Fallback to procedural
      this.playSweep(150, 400, 0.2, "sine", 0.03);
    });
  }

  /**
   * System boot sequence sound (procedural - complex sequence)
   */
  boot(): void {
    // Power-up sweep
    this.playSweep(50, 200, 0.5, "sawtooth", 0.02);

    // Digital chirps
    this.playTone({ freq: 2400, type: "square", duration: 0.02, volume: 0.02, delay: 0.3 });
    this.playTone({ freq: 3200, type: "square", duration: 0.02, volume: 0.02, delay: 0.35 });
    this.playTone({ freq: 2800, type: "square", duration: 0.02, volume: 0.02, delay: 0.4 });

    // Confirmation tone
    this.playTone({ freq: 880, type: "sine", duration: 0.3, volume: 0.03, delay: 0.6 });
  }

  /**
   * Single typing character (procedural - random)
   */
  type(): void {
    // Use inline calculation for audio frequency variation
    const freq = 2000 + Math.random() * 1000;
    this.playTone({ freq, type: "square", duration: 0.01, volume: 0.005 });
  }

  /**
   * Notification ping (HUD log entry)
   */
  notification(): void {
    this.playSoundFile("notification", 0.5).catch(() => {
      // Fallback to procedural
      this.playTone({ freq: 1800, type: "sine", duration: 0.08, volume: 0.025 });
      this.playTone({ freq: 2400, type: "sine", duration: 0.1, volume: 0.02, delay: 0.05 });
    });
  }

  /**
   * Scan/search sound (procedural - dynamic)
   */
  scan(): void {
    this.playSweep(800, 2000, 0.2, "sine", 0.02);
    this.playNoise(0.1, 0.01, 0.1);
  }

  /**
   * Item added to cart
   */
  addToCart(): void {
    this.playSoundFile("addToCart", 0.6).catch(() => {
      // Fallback to procedural
      this.playTone({ freq: 660, type: "sine", duration: 0.1, volume: 0.03 });
      this.playTone({ freq: 880, type: "sine", duration: 0.15, volume: 0.03, delay: 0.08 });
      this.playNoise(0.05, 0.01);
    });
  }

  /**
   * Transaction/purchase complete
   */
  transaction(): void {
    this.playSoundFile("transaction", 0.6).catch(() => {
      // Fallback to procedural
      [440, 554, 659, 880].forEach((freq, i) => {
        this.playTone({ freq, type: "sine", duration: 0.12, volume: 0.03, delay: i * 0.1 });
      });
      // Final chord
      this.playTone({ freq: 440, type: "triangle", duration: 0.5, volume: 0.02, delay: 0.4 });
      this.playTone({ freq: 659, type: "triangle", duration: 0.5, volume: 0.02, delay: 0.4 });
      this.playTone({ freq: 880, type: "triangle", duration: 0.5, volume: 0.02, delay: 0.4 });
    });
  }

  /**
   * Connection established (procedural - complex)
   */
  connect(): void {
    this.playNoise(0.05, 0.02);
    this.playSweep(200, 600, 0.15, "sine", 0.03);
    this.playTone({ freq: 800, type: "sine", duration: 0.2, volume: 0.03, delay: 0.15 });
  }

  /**
   * Connection lost / disconnected (procedural)
   */
  disconnect(): void {
    this.playSweep(600, 100, 0.3, "sawtooth", 0.03);
    this.playNoise(0.2, 0.02, 0.1);
  }

  /**
   * Glitch effect (procedural - random)
   */
  glitch(): void {
    const glitchCount = 3 + Math.floor(Math.random() * 4);
    for (let i = 0; i < glitchCount; i++) {
      const freq = 100 + Math.random() * 2000;
      const delay = i * 0.03;
      this.playNoise(0.02, 0.03, delay);
      this.playTone({ freq, type: "square", duration: 0.02, volume: 0.02, delay });
    }
  }

  /**
   * Typewriter effect - for menu expansion, text reveal
   * Uses ui-short.ogg or procedural fallback
   */
  typewriter(charCount: number = 5): void {
    // For typewriter, we can use ui-short.ogg or procedural
    // Using procedural for variety
    for (let i = 0; i < charCount; i++) {
      const delay = i * 0.04;
      const freq = 1800 + Math.random() * 400;
      this.playTone({ freq, type: "square", duration: 0.015, volume: 0.012, delay });
      this.playNoise(0.008, 0.015, delay + 0.005);
    }
  }

  /**
   * Decrypt/Scramble effect - for data reveal, referral dossier
   */
  decrypt(): void {
    this.playSoundFile("decrypt", 0.6).catch(() => {
      // Fallback to procedural
      for (let i = 0; i < 12; i++) {
        const freq = 800 + Math.random() * 2400;
        const delay = i * 0.035;
        this.playTone({ freq, type: "square", duration: 0.02, volume: 0.015, delay });
      }
      this.playNoise(0.3, 0.015);
      this.playTone({ freq: 1200, type: "sine", duration: 0.08, volume: 0.02, delay: 0.4 });
      this.playTone({ freq: 1600, type: "sine", duration: 0.1, volume: 0.025, delay: 0.45 });
    });
  }

  /**
   * Panel slide open - for sidebar/drawer opening
   * Uses ui-short.ogg or procedural
   */
  panelOpen(): void {
    this.playSoundFile("uiShort", 0.4).catch(() => {
      // Fallback to procedural
      this.playSweep(100, 300, 0.12, "sine", 0.02);
      this.playTone({ freq: 400, type: "square", duration: 0.03, volume: 0.02, delay: 0.1 });
      this.playNoise(0.03, 0.015, 0.1);
    });
  }

  /**
   * Panel slide close - for sidebar/drawer closing
   * Uses ui-short.ogg or procedural
   */
  panelClose(): void {
    this.playSoundFile("uiShort", 0.4).catch(() => {
      // Fallback to procedural
      this.playSweep(300, 100, 0.1, "sine", 0.02);
      this.playTone({ freq: 200, type: "square", duration: 0.04, volume: 0.015 });
    });
  }
}

// Singleton instance
export const AudioEngine = new AudioEngineClass();
export default AudioEngine;
