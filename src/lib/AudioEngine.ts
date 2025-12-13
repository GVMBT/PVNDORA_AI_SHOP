/**
 * PVNDORA Audio Engine
 * 
 * Procedural sound generation using Web Audio API.
 * Creates immersive cyberpunk atmosphere with synthesized SFX.
 * 
 * NO mp3 files - all sounds are generated in real-time.
 */

type OscillatorType = 'sine' | 'square' | 'sawtooth' | 'triangle';

interface ToneConfig {
  freq: number;
  type: OscillatorType;
  duration: number;
  volume?: number;
  delay?: number;
}

class AudioEngineClass {
  private ctx: AudioContext | null = null;
  private masterGain: GainNode | null = null;
  private enabled: boolean = true;
  private initialized: boolean = false;

  /**
   * Initialize AudioContext (must be called after user interaction)
   */
  init(): void {
    if (this.ctx) return;
    
    try {
      const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
      if (!AudioContextClass) {
        console.warn('[AudioEngine] Web Audio API not supported');
        return;
      }
      
      this.ctx = new AudioContextClass();
      this.masterGain = this.ctx.createGain();
      this.masterGain.gain.value = 0.5;
      this.masterGain.connect(this.ctx.destination);
      this.initialized = true;
      
      console.log('[AudioEngine] Initialized');
    } catch (e) {
      console.warn('[AudioEngine] Failed to initialize:', e);
    }
  }

  /**
   * Resume AudioContext if suspended (required by browsers)
   */
  async resume(): Promise<void> {
    if (this.ctx && this.ctx.state === 'suspended') {
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
   * Play a single tone
   */
  private playTone(config: ToneConfig): void {
    if (!this.ctx || !this.masterGain || !this.enabled) return;
    
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
   * Play white noise burst
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
    filter.type = 'highpass';
    filter.frequency.value = 1000;

    gain.gain.setValueAtTime(volume, now);
    gain.gain.exponentialRampToValueAtTime(0.001, now + duration);

    noise.connect(filter);
    filter.connect(gain);
    gain.connect(this.masterGain);

    noise.start(now);
  }

  /**
   * Play frequency sweep
   */
  private playSweep(
    startFreq: number, 
    endFreq: number, 
    duration: number, 
    type: OscillatorType = 'sine',
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
   * Light hover sound
   */
  hover(): void {
    this.playTone({ freq: 800, type: 'sine', duration: 0.03, volume: 0.008 });
  }

  /**
   * Button click
   */
  click(): void {
    this.playTone({ freq: 1200, type: 'square', duration: 0.05, volume: 0.015 });
    this.playNoise(0.03, 0.01);
  }

  /**
   * Success notification (ascending arpeggio)
   */
  success(): void {
    this.playTone({ freq: 440, type: 'sine', duration: 0.15, volume: 0.04, delay: 0 });
    this.playTone({ freq: 554, type: 'sine', duration: 0.15, volume: 0.04, delay: 0.08 });
    this.playTone({ freq: 659, type: 'sine', duration: 0.25, volume: 0.05, delay: 0.16 });
  }

  /**
   * Error notification (low rumble)
   */
  error(): void {
    this.playTone({ freq: 150, type: 'sawtooth', duration: 0.3, volume: 0.04 });
    this.playTone({ freq: 120, type: 'sawtooth', duration: 0.4, volume: 0.03, delay: 0.1 });
  }

  /**
   * Warning notification
   */
  warning(): void {
    this.playTone({ freq: 880, type: 'triangle', duration: 0.15, volume: 0.03 });
    this.playTone({ freq: 880, type: 'triangle', duration: 0.15, volume: 0.03, delay: 0.2 });
  }

  /**
   * Modal/menu open
   */
  open(): void {
    this.playSweep(150, 400, 0.15, 'sine', 0.03);
  }

  /**
   * Modal/menu close
   */
  close(): void {
    this.playSweep(400, 150, 0.1, 'sine', 0.02);
  }

  /**
   * System boot sequence sound
   */
  boot(): void {
    // Power-up sweep
    this.playSweep(50, 200, 0.5, 'sawtooth', 0.02);
    
    // Digital chirps
    this.playTone({ freq: 2400, type: 'square', duration: 0.02, volume: 0.02, delay: 0.3 });
    this.playTone({ freq: 3200, type: 'square', duration: 0.02, volume: 0.02, delay: 0.35 });
    this.playTone({ freq: 2800, type: 'square', duration: 0.02, volume: 0.02, delay: 0.4 });
    
    // Confirmation tone
    this.playTone({ freq: 880, type: 'sine', duration: 0.3, volume: 0.03, delay: 0.6 });
  }

  /**
   * Single typing character
   */
  type(): void {
    const freq = 2000 + Math.random() * 1000;
    this.playTone({ freq, type: 'square', duration: 0.01, volume: 0.005 });
  }

  /**
   * Notification ping (HUD log entry)
   */
  notification(): void {
    this.playTone({ freq: 1800, type: 'sine', duration: 0.08, volume: 0.025 });
    this.playTone({ freq: 2400, type: 'sine', duration: 0.1, volume: 0.02, delay: 0.05 });
  }

  /**
   * Scan/search sound
   */
  scan(): void {
    this.playSweep(800, 2000, 0.2, 'sine', 0.02);
    this.playNoise(0.1, 0.01, 0.1);
  }

  /**
   * Item added to cart
   */
  addToCart(): void {
    this.playTone({ freq: 660, type: 'sine', duration: 0.1, volume: 0.03 });
    this.playTone({ freq: 880, type: 'sine', duration: 0.15, volume: 0.03, delay: 0.08 });
    this.playNoise(0.05, 0.01);
  }

  /**
   * Transaction/purchase complete
   */
  transaction(): void {
    // Ascending confirmation
    [440, 554, 659, 880].forEach((freq, i) => {
      this.playTone({ freq, type: 'sine', duration: 0.12, volume: 0.03, delay: i * 0.1 });
    });
    // Final chord
    this.playTone({ freq: 440, type: 'triangle', duration: 0.5, volume: 0.02, delay: 0.4 });
    this.playTone({ freq: 659, type: 'triangle', duration: 0.5, volume: 0.02, delay: 0.4 });
    this.playTone({ freq: 880, type: 'triangle', duration: 0.5, volume: 0.02, delay: 0.4 });
  }

  /**
   * Connection established
   */
  connect(): void {
    this.playNoise(0.05, 0.02);
    this.playSweep(200, 600, 0.15, 'sine', 0.03);
    this.playTone({ freq: 800, type: 'sine', duration: 0.2, volume: 0.03, delay: 0.15 });
  }

  /**
   * Connection lost / disconnected
   */
  disconnect(): void {
    this.playSweep(600, 100, 0.3, 'sawtooth', 0.03);
    this.playNoise(0.2, 0.02, 0.1);
  }

  /**
   * Glitch effect
   */
  glitch(): void {
    const glitchCount = 3 + Math.floor(Math.random() * 4);
    for (let i = 0; i < glitchCount; i++) {
      const freq = 100 + Math.random() * 2000;
      const delay = i * 0.03;
      this.playNoise(0.02, 0.03, delay);
      this.playTone({ freq, type: 'square', duration: 0.02, volume: 0.02, delay });
    }
  }

  /**
   * Typewriter effect - for menu expansion, text reveal
   * Creates a burst of mechanical key clicks
   */
  typewriter(charCount: number = 5): void {
    for (let i = 0; i < charCount; i++) {
      const delay = i * 0.04;
      // Mechanical click
      const freq = 1800 + Math.random() * 400;
      this.playTone({ freq, type: 'square', duration: 0.015, volume: 0.012, delay });
      // Clack impact
      this.playNoise(0.008, 0.015, delay + 0.005);
    }
  }

  /**
   * Decrypt/Scramble effect - for data reveal, referral dossier
   * Creates a digital scrambling sound followed by confirmation
   */
  decrypt(): void {
    // Scrambling phase - rapid random tones
    for (let i = 0; i < 12; i++) {
      const freq = 800 + Math.random() * 2400;
      const delay = i * 0.035;
      this.playTone({ freq, type: 'square', duration: 0.02, volume: 0.015, delay });
    }
    // Digital noise during scramble
    this.playNoise(0.3, 0.015);
    
    // Confirmation chirp at end
    this.playTone({ freq: 1200, type: 'sine', duration: 0.08, volume: 0.02, delay: 0.4 });
    this.playTone({ freq: 1600, type: 'sine', duration: 0.1, volume: 0.025, delay: 0.45 });
  }

  /**
   * Panel slide open - for sidebar/drawer opening
   */
  panelOpen(): void {
    // Whoosh sweep
    this.playSweep(100, 300, 0.12, 'sine', 0.02);
    // Mechanical latch
    this.playTone({ freq: 400, type: 'square', duration: 0.03, volume: 0.02, delay: 0.1 });
    this.playNoise(0.03, 0.015, 0.1);
  }

  /**
   * Panel slide close - for sidebar/drawer closing
   */
  panelClose(): void {
    // Reverse whoosh
    this.playSweep(300, 100, 0.1, 'sine', 0.02);
    // Soft thud
    this.playTone({ freq: 200, type: 'square', duration: 0.04, volume: 0.015 });
  }
}

// Singleton instance
export const AudioEngine = new AudioEngineClass();
export default AudioEngine;
