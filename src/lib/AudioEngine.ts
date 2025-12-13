/**
 * PVNDORA Audio Engine
 * 
 * Procedural audio system:
 * - Procedural sound generation (Web Audio API) for SFX
 * - Procedural ambient music (Web Audio API) - based on sound.flac analysis
 * 
 * Creates immersive cyberpunk atmosphere with synthesized sounds.
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
  private musicGain: GainNode | null = null; // Separate gain for background music
  private enabled: boolean = true;
  private initialized: boolean = false;
  
  // Procedural ambient music
  private musicVolume: number = 0.3; // Default music volume (0-1)
  private musicEnabled: boolean = true;
  private ambientOscillators: OscillatorNode[] = [];
  private ambientSources: (OscillatorNode | ConstantSourceNode)[] = []; // Store all source nodes (oscillators + constant sources)
  private ambientNodes: AudioNode[] = []; // Store all audio nodes (delays, gains, filters) for cleanup
  private ambientPlaying: boolean = false;

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
      
      // Separate gain node for background music
      this.musicGain = this.ctx.createGain();
      this.musicGain.gain.value = this.musicVolume;
      this.musicGain.connect(this.ctx.destination);
      
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

  // ============================================
  // PROCEDURAL MUSIC METHODS
  // ============================================

  /**
   * Set music volume (0-1, separate from SFX volume)
   */
  setMusicVolume(volume: number): void {
    this.musicVolume = Math.max(0, Math.min(1, volume));
    if (this.musicGain) {
      this.musicGain.gain.value = this.musicVolume;
    }
  }

  /**
   * Enable/disable background music
   */
  setMusicEnabled(enabled: boolean): void {
    this.musicEnabled = enabled;
    if (!enabled) {
      this.stopAmbientMusic();
    }
  }

  /**
   * Enhanced procedural music based on analysis of sound.flac
   * Features:
   * - Reverb (DelayNode + Feedback)
   * - Harmonic overtones for richer timbre
   * - Dynamic volume modulation (based on RMS energy variations)
   * - Advanced filtering (spectral centroid, rolloff, bandwidth)
   * - More accurate frequency mapping from analysis
   */
  startAmbientMusicFromAnalysis(): void {
    if (!this.ctx || !this.musicGain || !this.musicEnabled || this.ambientPlaying) return;

    this.ambientPlaying = true;
    const now = this.ctx.currentTime;

    // Create shared reverb (DelayNode-based reverb for all layers)
    const reverbDelay = this.ctx.createDelay(2.0);
    const reverbGain = this.ctx.createGain();
    const reverbFilter = this.ctx.createBiquadFilter();
    
    reverbDelay.delayTime.setValueAtTime(0.3, now); // 300ms delay
    reverbGain.gain.setValueAtTime(0.25, now); // 25% feedback
    reverbFilter.type = 'lowpass';
    reverbFilter.frequency.setValueAtTime(3000, now); // Dampen high frequencies
    reverbFilter.Q.setValueAtTime(1, now);
    
    // Reverb feedback loop
    reverbDelay.connect(reverbFilter);
    reverbFilter.connect(reverbGain);
    reverbGain.connect(reverbDelay); // Feedback
    reverbGain.connect(this.musicGain); // Output
    
    // Store reverb nodes for cleanup
    this.ambientNodes.push(reverbDelay, reverbGain, reverbFilter);

    // ============================================
    // LOW FREQUENCY DRONE (43.07 Hz from analysis)
    // ============================================
    const lowFreq = 43.07;
    const lowBaseGain = 0.142 * this.musicVolume;
    
    // Fundamental (sine wave - pure tone)
    const drone1 = this.ctx.createOscillator();
    const drone1Gain = this.ctx.createGain();
    const drone1Filter = this.ctx.createBiquadFilter();
    
    drone1.type = 'sine';
    drone1.frequency.setValueAtTime(lowFreq, now);
    drone1Filter.type = 'lowpass';
    drone1Filter.frequency.setValueAtTime(75.0, now);
    drone1Filter.Q.setValueAtTime(1, now);
    
    // Dynamic volume modulation (based on RMS energy std: 0.057)
    // Use ConstantSourceNode for DC offset + LFO for modulation
    const lowVolumeConstant = this.ctx.createConstantSource();
    const lowVolumeLFO = this.ctx.createOscillator();
    const lowVolumeLFOGain = this.ctx.createGain();
    const lowVolumeSum = this.ctx.createGain();
    
    lowVolumeConstant.offset.setValueAtTime(lowBaseGain, now);
    lowVolumeLFO.type = 'sine';
    lowVolumeLFO.frequency.setValueAtTime(0.08, now); // Very slow (12.5s cycle)
    lowVolumeLFOGain.gain.setValueAtTime(0.03, now); // 3% variation
    
    lowVolumeConstant.connect(lowVolumeSum);
    lowVolumeLFO.connect(lowVolumeLFOGain);
    lowVolumeLFOGain.connect(lowVolumeSum);
    lowVolumeSum.connect(drone1Gain.gain);
    
    lowVolumeConstant.start(now);
    lowVolumeLFO.start(now);
    this.ambientOscillators.push(lowVolumeLFO);
    this.ambientSources.push(lowVolumeConstant, lowVolumeLFO);
    this.ambientNodes.push(lowVolumeLFOGain, lowVolumeSum);
    
    // Set base gain
    drone1Gain.gain.setValueAtTime(1, now); // Will be modulated by lowVolumeSum
    
    drone1.connect(drone1Filter);
    drone1Filter.connect(drone1Gain);
    drone1Gain.connect(reverbDelay); // Through reverb
    drone1Gain.connect(this.musicGain); // Direct output
    
    drone1.start(now);
    this.ambientOscillators.push(drone1);

    // First harmonic (2x = 86.14 Hz) - adds warmth
    const drone1Harmonic = this.ctx.createOscillator();
    const drone1HarmonicGain = this.ctx.createGain();
    const drone1HarmonicFilter = this.ctx.createBiquadFilter();
    
    drone1Harmonic.type = 'sine';
    drone1Harmonic.frequency.setValueAtTime(lowFreq * 2, now);
    drone1HarmonicFilter.type = 'lowpass';
    drone1HarmonicFilter.frequency.setValueAtTime(150, now);
    drone1HarmonicFilter.Q.setValueAtTime(1, now);
    drone1HarmonicGain.gain.setValueAtTime(lowBaseGain * 0.15, now); // 15% of fundamental
    
    drone1Harmonic.connect(drone1HarmonicFilter);
    drone1HarmonicFilter.connect(drone1HarmonicGain);
    drone1HarmonicGain.connect(reverbDelay);
    drone1HarmonicGain.connect(this.musicGain);
    
    drone1Harmonic.start(now);
    this.ambientOscillators.push(drone1Harmonic);

    // ============================================
    // MID FREQUENCY LAYER (258.4 Hz from analysis)
    // ============================================
    const midFreq = 258.4;
    const midBaseGain = 0.090 * this.musicVolume;
    const spectralBandwidth = 954.76; // From analysis
    
    // Fundamental (triangle wave - richer harmonics)
    const drone2 = this.ctx.createOscillator();
    const drone2Gain = this.ctx.createGain();
    const drone2Filter = this.ctx.createBiquadFilter();
    
    drone2.type = 'triangle';
    drone2.frequency.setValueAtTime(midFreq, now);
    drone2Filter.type = 'bandpass';
    drone2Filter.frequency.setValueAtTime(midFreq, now);
    drone2Filter.Q.setValueAtTime(spectralBandwidth / 500, now); // Q based on bandwidth (1.91)
    
    // Dynamic volume modulation
    const midVolumeConstant = this.ctx.createConstantSource();
    const midVolumeLFO = this.ctx.createOscillator();
    const midVolumeLFOGain = this.ctx.createGain();
    const midVolumeSum = this.ctx.createGain();
    
    midVolumeConstant.offset.setValueAtTime(midBaseGain, now);
    midVolumeLFO.type = 'sine';
    midVolumeLFO.frequency.setValueAtTime(0.12, now); // Slightly faster (8.3s cycle)
    midVolumeLFOGain.gain.setValueAtTime(0.04, now); // 4% variation
    
    midVolumeConstant.connect(midVolumeSum);
    midVolumeLFO.connect(midVolumeLFOGain);
    midVolumeLFOGain.connect(midVolumeSum);
    midVolumeSum.connect(drone2Gain.gain);
    
    midVolumeConstant.start(now);
    midVolumeLFO.start(now);
    this.ambientOscillators.push(midVolumeLFO);
    this.ambientSources.push(midVolumeConstant, midVolumeLFO);
    this.ambientNodes.push(midVolumeLFOGain, midVolumeSum);
    
    // Set base gain
    drone2Gain.gain.setValueAtTime(1, now); // Will be modulated by midVolumeSum
    
    drone2.connect(drone2Filter);
    drone2Filter.connect(drone2Gain);
    drone2Gain.connect(reverbDelay);
    drone2Gain.connect(this.musicGain);
    
    drone2.start(now);
    this.ambientOscillators.push(drone2);

    // Second harmonic (2x = 516.8 Hz) - adds presence
    const drone2Harmonic = this.ctx.createOscillator();
    const drone2HarmonicGain = this.ctx.createGain();
    const drone2HarmonicFilter = this.ctx.createBiquadFilter();
    
    drone2Harmonic.type = 'triangle';
    drone2Harmonic.frequency.setValueAtTime(midFreq * 2, now);
    drone2HarmonicFilter.type = 'bandpass';
    drone2HarmonicFilter.frequency.setValueAtTime(midFreq * 2, now);
    drone2HarmonicFilter.Q.setValueAtTime(2, now);
    drone2HarmonicGain.gain.setValueAtTime(midBaseGain * 0.2, now); // 20% of fundamental
    
    drone2Harmonic.connect(drone2HarmonicFilter);
    drone2HarmonicFilter.connect(drone2HarmonicGain);
    drone2HarmonicGain.connect(reverbDelay);
    drone2HarmonicGain.connect(this.musicGain);
    
    drone2Harmonic.start(now);
    this.ambientOscillators.push(drone2Harmonic);

    // ============================================
    // HIGH FREQUENCY TEXTURE (based on spectral rolloff: 250 Hz, but analysis shows 22028 Hz peak)
    // Use more realistic 8000-12000 Hz range for Web Audio API
    // ============================================
    const highFreq = 8000.0; // Base frequency
    const highBaseGain = 0.005 * this.musicVolume;
    const spectralCentroid = 209.49; // From analysis (Hz)
    const spectralRolloff = 250.09; // From analysis (Hz)
    
    // Main texture oscillator (square wave for rich harmonics)
    const texture = this.ctx.createOscillator();
    const textureGain = this.ctx.createGain();
    const textureFilter = this.ctx.createBiquadFilter();
    
    texture.type = 'square';
    texture.frequency.setValueAtTime(highFreq, now);
    textureFilter.type = 'bandpass';
    textureFilter.frequency.setValueAtTime(highFreq, now);
    textureFilter.Q.setValueAtTime(2, now);
    
    // Complex LFO for texture variation (multiple LFOs for richer modulation)
    const lfo1 = this.ctx.createOscillator();
    const lfo1Gain = this.ctx.createGain();
    lfo1.type = 'sine';
    lfo1.frequency.setValueAtTime(0.05, now); // Slow (20s cycle)
    lfo1Gain.gain.setValueAtTime(200, now); // Frequency modulation
    lfo1.connect(lfo1Gain);
    lfo1Gain.connect(texture.frequency);
    lfo1.start(now);
    this.ambientOscillators.push(lfo1);
    
    // Second LFO for amplitude modulation (tremolo effect)
    const textureVolumeConstant = this.ctx.createConstantSource();
    const lfo2 = this.ctx.createOscillator();
    const lfo2Gain = this.ctx.createGain();
    const textureVolumeSum = this.ctx.createGain();
    
    textureVolumeConstant.offset.setValueAtTime(highBaseGain, now);
    lfo2.type = 'sine';
    lfo2.frequency.setValueAtTime(0.15, now); // Faster (6.7s cycle)
    lfo2Gain.gain.setValueAtTime(highBaseGain * 0.3, now); // 30% amplitude variation
    
    textureVolumeConstant.connect(textureVolumeSum);
    lfo2.connect(lfo2Gain);
    lfo2Gain.connect(textureVolumeSum);
    textureVolumeSum.connect(textureGain.gain);
    
    textureVolumeConstant.start(now);
    lfo2.start(now);
    this.ambientOscillators.push(lfo2);
    this.ambientSources.push(textureVolumeConstant, lfo2);
    this.ambientNodes.push(lfo2Gain, textureVolumeSum);
    
    // Set base gain
    textureGain.gain.setValueAtTime(1, now); // Will be modulated by textureVolumeSum
    
    texture.connect(textureFilter);
    textureFilter.connect(textureGain);
    textureGain.connect(reverbDelay);
    textureGain.connect(this.musicGain);
    
    texture.start(now);
    this.ambientOscillators.push(texture);

    // Additional high-frequency layer (octave above, 16000 Hz) - very subtle
    const texture2 = this.ctx.createOscillator();
    const texture2Gain = this.ctx.createGain();
    const texture2Filter = this.ctx.createBiquadFilter();
    
    texture2.type = 'sawtooth'; // Different waveform for texture variation
    texture2.frequency.setValueAtTime(highFreq * 2, now);
    texture2Filter.type = 'highpass'; // Only high frequencies
    texture2Filter.frequency.setValueAtTime(12000, now);
    texture2Filter.Q.setValueAtTime(1, now);
    texture2Gain.gain.setValueAtTime(highBaseGain * 0.3, now); // 30% of main texture
    
    texture2.connect(texture2Filter);
    texture2Filter.connect(texture2Gain);
    texture2Gain.connect(reverbDelay);
    texture2Gain.connect(this.musicGain);
    
    texture2.start(now);
    this.ambientOscillators.push(texture2);

    console.log('[AudioEngine] Enhanced procedural music started (with reverb, harmonics, dynamic modulation)');
  }

  /**
   * Stop procedural ambient music
   */
  stopAmbientMusic(): void {
    if (!this.ambientPlaying) return;

    // Stop all source nodes (oscillators and constant sources)
    this.ambientSources.forEach(source => {
      try {
        if (source.stop) source.stop();
      } catch (e) {
        // Source might already be stopped
      }
    });
    
    // Disconnect all nodes
    this.ambientNodes.forEach(node => {
      try {
        node.disconnect();
      } catch (e) {
        // Node might already be disconnected
      }
    });
    
    this.ambientOscillators = [];
    this.ambientSources = [];
    this.ambientNodes = [];
    this.ambientPlaying = false;
    console.log('[AudioEngine] Ambient music stopped');
  }
}

// Singleton instance
export const AudioEngine = new AudioEngineClass();
export default AudioEngine;
