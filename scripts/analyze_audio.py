"""
Audio Spectrum Analysis Script
Analyzes FLAC/WAV file and extracts parameters for procedural generation.
"""

import json
import os
import sys

import numpy as np

try:
    import librosa
except ImportError:
    print("Installing required packages...")
    os.system(f"{sys.executable} -m pip install librosa soundfile numpy -q")
    import librosa


def analyze_audio(file_path: str) -> dict:
    """
    Analyze audio file and extract spectral features.

    Returns:
        Dictionary with analysis results for procedural generation
    """
    print(f"Loading audio file: {file_path}")

    # Load audio file
    y, sr = librosa.load(file_path, sr=None, duration=60)  # Analyze first 60 seconds

    print(f"Sample rate: {sr} Hz")
    print(f"Duration: {len(y) / sr:.2f} seconds")
    print(f"Shape: {y.shape}")

    # Extract spectral features
    print("\nAnalyzing spectral features...")

    # 1. Fundamental frequencies (dominant pitches)
    pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
    pitch_mean = np.mean(pitches[pitches > 0])
    pitch_std = np.std(pitches[pitches > 0])

    # 2. Spectral centroid (brightness)
    spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
    centroid_mean = float(np.mean(spectral_centroids))
    centroid_std = float(np.std(spectral_centroids))

    # 3. Spectral rolloff (high frequency cutoff)
    rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)[0]
    rolloff_mean = float(np.mean(rolloff))

    # 4. Zero crossing rate (texture/noise)
    zcr = librosa.feature.zero_crossing_rate(y)[0]
    zcr_mean = float(np.mean(zcr))

    # 5. Tempo/BPM
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
    tempo = float(tempo)

    # 6. Harmonic and percussive components
    y_harmonic, y_percussive = librosa.effects.hpss(y)
    harmonic_ratio = float(np.mean(np.abs(y_harmonic)) / (np.mean(np.abs(y)) + 1e-10))
    percussive_ratio = float(np.mean(np.abs(y_percussive)) / (np.mean(np.abs(y)) + 1e-10))

    # 7. Spectral bandwidth
    bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr)[0]
    bandwidth_mean = float(np.mean(bandwidth))

    # 8. MFCC (Mel-frequency cepstral coefficients) - timbre
    mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
    mfcc_mean = [float(np.mean(m)) for m in mfccs]

    # 9. RMS Energy (loudness envelope)
    rms = librosa.feature.rms(y=y)[0]
    rms_mean = float(np.mean(rms))
    rms_std = float(np.std(rms))

    # 10. Chroma (pitch class)
    chroma = librosa.feature.chroma_stft(y=y, sr=sr)
    chroma_mean = [float(np.mean(c)) for c in chroma]

    # 11. Find dominant frequencies in different bands
    # Low (0-200Hz), Mid (200-2000Hz), High (2000Hz+)
    stft = librosa.stft(y)
    magnitude = np.abs(stft)
    freqs = librosa.fft_frequencies(sr=sr)

    low_band = magnitude[(freqs >= 0) & (freqs < 200)]
    mid_band = magnitude[(freqs >= 200) & (freqs < 2000)]
    high_band = magnitude[(freqs >= 2000) & (freqs < sr / 2)]

    # Find peak frequencies in each band
    low_peak_idx = np.argmax(np.mean(low_band, axis=1)) if len(low_band) > 0 else 0
    mid_peak_idx = np.argmax(np.mean(mid_band, axis=1)) if len(mid_band) > 0 else 0
    high_peak_idx = np.argmax(np.mean(high_band, axis=1)) if len(high_band) > 0 else 0

    low_freqs = freqs[(freqs >= 0) & (freqs < 200)]
    mid_freqs = freqs[(freqs >= 200) & (freqs < 2000)]
    high_freqs = freqs[(freqs >= 2000) & (freqs < sr / 2)]

    low_peak_freq = float(low_freqs[low_peak_idx]) if len(low_freqs) > low_peak_idx else 55.0
    mid_peak_freq = float(mid_freqs[mid_peak_idx]) if len(mid_freqs) > mid_peak_idx else 440.0
    high_peak_freq = float(high_freqs[high_peak_idx]) if len(high_freqs) > high_peak_idx else 2000.0

    # 12. Detect if it's ambient/drone vs rhythmic
    is_ambient = zcr_mean < 0.1 and rms_std < 0.05
    is_rhythmic = percussive_ratio > 0.3

    results = {
        "sample_rate": int(sr),
        "duration": float(len(y) / sr),
        "tempo_bpm": tempo,
        "is_ambient": bool(is_ambient),
        "is_rhythmic": bool(is_rhythmic),
        # Frequency analysis
        "fundamental_freq": float(pitch_mean) if not np.isnan(pitch_mean) else 55.0,
        "fundamental_std": float(pitch_std) if not np.isnan(pitch_std) else 0.0,
        # Spectral characteristics
        "spectral_centroid": centroid_mean,
        "spectral_centroid_std": centroid_std,
        "spectral_rolloff": rolloff_mean,
        "spectral_bandwidth": bandwidth_mean,
        # Energy
        "rms_energy": rms_mean,
        "rms_energy_std": rms_std,
        # Texture
        "zero_crossing_rate": zcr_mean,
        "harmonic_ratio": harmonic_ratio,
        "percussive_ratio": percussive_ratio,
        # Dominant frequencies by band
        "low_band_peak_freq": low_peak_freq,
        "mid_band_peak_freq": mid_peak_freq,
        "high_band_peak_freq": high_peak_freq,
        # Timbre (MFCC)
        "mfcc": mfcc_mean[:5],  # First 5 coefficients
        # Chroma (pitch classes)
        "chroma": chroma_mean,
    }

    return results


def generate_procedural_code(analysis: dict) -> str:
    """
    Generate TypeScript code for procedural music based on analysis.
    """

    # Map frequencies to Web Audio API oscillators
    low_freq = max(20, min(200, analysis["low_band_peak_freq"]))
    mid_freq = max(200, min(2000, analysis["mid_band_peak_freq"]))
    high_freq = max(2000, min(8000, analysis["high_band_peak_freq"]))

    # Determine oscillator types based on harmonic ratio
    if analysis["harmonic_ratio"] > 0.7:
        low_type = "sine"
        mid_type = "triangle"
    elif analysis["harmonic_ratio"] > 0.4:
        low_type = "triangle"
        mid_type = "sawtooth"
    else:
        low_type = "sawtooth"
        mid_type = "square"

    # Calculate volumes based on RMS energy
    base_volume = min(0.15, analysis["rms_energy"] * 2)
    low_vol = base_volume * (1 - analysis["percussive_ratio"])
    mid_vol = base_volume * 0.6
    high_vol = base_volume * 0.3 * analysis["spectral_centroid"] / 2000

    # LFO rate based on tempo
    lfo_rate = analysis["tempo_bpm"] / 60 / 4  # Quarter note subdivisions

    code = f"""
  /**
   * Procedural music based on analysis of: sound.flac
   * Generated from spectral analysis
   */
  startAmbientMusicFromAnalysis(): void {{
    if (!this.ctx || !this.musicGain || !this.musicEnabled || this.ambientPlaying) return;

    this.ambientPlaying = true;
    const now = this.ctx.currentTime;

    // Low frequency drone ({low_freq:.1f}Hz) - {low_type}
    const drone1 = this.ctx.createOscillator();
    const drone1Gain = this.ctx.createGain();
    const drone1Filter = this.ctx.createBiquadFilter();
    
    drone1.type = '{low_type}';
    drone1.frequency.setValueAtTime({low_freq:.1f}, now);
    drone1Filter.type = 'lowpass';
    drone1Filter.frequency.setValueAtTime({analysis["spectral_rolloff"] * 0.3:.1f}, now);
    drone1Filter.Q.setValueAtTime(1, now);
    
    drone1Gain.gain.setValueAtTime({low_vol:.3f} * this.musicVolume, now);
    
    drone1.connect(drone1Filter);
    drone1Filter.connect(drone1Gain);
    drone1Gain.connect(this.musicGain);
    
    drone1.start(now);
    this.ambientOscillators.push(drone1);

    // Mid frequency layer ({mid_freq:.1f}Hz) - {mid_type}
    const drone2 = this.ctx.createOscillator();
    const drone2Gain = this.ctx.createGain();
    const drone2Filter = this.ctx.createBiquadFilter();
    
    drone2.type = '{mid_type}';
    drone2.frequency.setValueAtTime({mid_freq:.1f}, now);
    drone2Filter.type = 'bandpass';
    drone2Filter.frequency.setValueAtTime({mid_freq:.1f}, now);
    drone2Filter.Q.setValueAtTime({analysis["spectral_bandwidth"] / 500:.2f}, now);
    
    drone2Gain.gain.setValueAtTime({mid_vol:.3f} * this.musicVolume, now);
    
    drone2.connect(drone2Filter);
    drone2Filter.connect(drone2Gain);
    drone2Gain.connect(this.musicGain);
    
    drone2.start(now);
    this.ambientOscillators.push(drone2);

    // High frequency texture ({high_freq:.1f}Hz)
    const texture = this.ctx.createOscillator();
    const textureGain = this.ctx.createGain();
    const textureFilter = this.ctx.createBiquadFilter();
    
    texture.type = 'square';
    texture.frequency.setValueAtTime({high_freq:.1f}, now);
    textureFilter.type = 'bandpass';
    textureFilter.frequency.setValueAtTime({high_freq:.1f}, now);
    textureFilter.Q.setValueAtTime(2, now);
    
    // LFO for texture variation (based on tempo: {analysis["tempo_bpm"]:.1f} BPM)
    const lfo = this.ctx.createOscillator();
    const lfoGain = this.ctx.createGain();
    lfo.type = 'sine';
    lfo.frequency.setValueAtTime({lfo_rate:.3f}, now);
    lfoGain.gain.setValueAtTime({analysis["fundamental_std"] * 2:.1f}, now);
    lfo.connect(lfoGain);
    lfoGain.connect(texture.frequency);
    lfo.start(now);
    this.ambientOscillators.push(lfo);
    
    textureGain.gain.setValueAtTime({high_vol:.3f} * this.musicVolume, now);
    
    texture.connect(textureFilter);
    textureFilter.connect(textureGain);
    textureGain.connect(this.musicGain);
    
    texture.start(now);
    this.ambientOscillators.push(texture);

    // Noise layer (if percussive ratio > 0.2)
    {f'''
    const noiseBuffer = this.ctx.createBuffer(1, this.ctx.sampleRate * 2, this.ctx.sampleRate);
    const noiseData = noiseBuffer.getChannelData(0);
    for (let i = 0; i < noiseData.length; i++) {{
      noiseData[i] = Math.random() * 2 - 1;
    }}
    
    const noiseSource = this.ctx.createBufferSource();
    const noiseGain = this.ctx.createGain();
    const noiseFilter = this.ctx.createBiquadFilter();
    
    noiseSource.buffer = noiseBuffer;
    noiseSource.loop = true;
    noiseFilter.type = 'highpass';
    noiseFilter.frequency.setValueAtTime({analysis["spectral_rolloff"] * 0.5:.1f}, now);
    noiseFilter.Q.setValueAtTime(1, now);
    
    noiseGain.gain.setValueAtTime({analysis["zero_crossing_rate"] * 0.5:.3f} * this.musicVolume, now);
    
    noiseSource.connect(noiseFilter);
    noiseFilter.connect(noiseGain);
    noiseGain.connect(this.musicGain);
    
    noiseSource.start(now);
    this.ambientOscillators.push(noiseSource as any);
    ''' if analysis["percussive_ratio"] > 0.2 else '    // Noise layer skipped (low percussive content)'}

    console.log('[AudioEngine] Procedural music started (from analysis)');
  }}
"""

    return code


if __name__ == "__main__":
    audio_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sound.flac")

    if not os.path.exists(audio_file):
        print(f"Error: File not found: {audio_file}")
        sys.exit(1)

    print("=" * 60)
    print("Audio Spectrum Analysis")
    print("=" * 60)

    try:
        analysis = analyze_audio(audio_file)

        print("\n" + "=" * 60)
        print("Analysis Results:")
        print("=" * 60)
        print(json.dumps(analysis, indent=2))

        # Generate procedural code
        procedural_code = generate_procedural_code(analysis)

        # Save results
        output_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "scripts", "audio_analysis"
        )
        os.makedirs(output_dir, exist_ok=True)

        # Save analysis JSON
        analysis_file = os.path.join(output_dir, "analysis.json")
        with open(analysis_file, "w", encoding="utf-8") as f:
            json.dump(analysis, f, indent=2)
        print(f"\nAnalysis saved to: {analysis_file}")

        # Save procedural code
        code_file = os.path.join(output_dir, "procedural_code.ts")
        with open(code_file, "w", encoding="utf-8") as f:
            f.write(procedural_code)
        print(f"Procedural code saved to: {code_file}")

        print("\n" + "=" * 60)
        print("Generated Procedural Code:")
        print("=" * 60)
        print(procedural_code)

    except Exception as e:
        print(f"\nError during analysis: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
