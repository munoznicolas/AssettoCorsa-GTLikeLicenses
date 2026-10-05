"""
Asset Generator for GT-Like Licenses Mod
Generates clean 16-bit PCM WAV sound effects for:
- countdown_beep.wav
- countdown_go.wav
- fail_buzzer.wav
- pass_fanfare.wav
- gold_fanfare.wav
"""

import math
import struct
import wave
from pathlib import Path

SAMPLE_RATE = 44100

def create_wave(filename: Path, samples: list[float]):
    filename.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(filename), "w") as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(SAMPLE_RATE)
        
        raw_bytes = bytearray()
        for s in samples:
            # Clamp sample between -1.0 and 1.0
            clamped = max(-1.0, min(1.0, s))
            int_sample = int(clamped * 32767)
            raw_bytes.extend(struct.pack("<h", int_sample))
            
        wav_file.writeframes(raw_bytes)
    print(f"Generated: {filename} ({len(samples)} samples, {len(samples)/SAMPLE_RATE:.2f}s)")

def generate_countdown_beep(filepath: Path):
    """Clean 880Hz electronic beep with sharp attack and short decay (150ms)."""
    duration = 0.15
    freq = 880.0
    num_samples = int(duration * SAMPLE_RATE)
    samples = []
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        env = math.exp(-t * 18.0)
        s = math.sin(2 * math.pi * freq * t) * env * 0.75
        samples.append(s)
    create_wave(filepath, samples)

def generate_countdown_go(filepath: Path):
    """High-pitch 1760Hz double-harmonic chime (350ms)."""
    duration = 0.35
    freq1 = 1760.0
    freq2 = 3520.0
    num_samples = int(duration * SAMPLE_RATE)
    samples = []
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        env = math.exp(-t * 9.0)
        s = (math.sin(2 * math.pi * freq1 * t) * 0.7 + 
             math.sin(2 * math.pi * freq2 * t) * 0.3) * env * 0.8
        samples.append(s)
    create_wave(filepath, samples)

def generate_fail_buzzer(filepath: Path):
    """Iconic GT-style low harsh dual-tone buzz (650ms)."""
    duration = 0.65
    freq1 = 135.0
    freq2 = 180.0
    num_samples = int(duration * SAMPLE_RATE)
    samples = []
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        # Envelope: flat with slight fade at end
        env = min(1.0, t * 50.0) * max(0.0, 1.0 - (t / duration) ** 3)
        # Saturated square/sawtooth mix
        wave1 = 1.0 if (math.sin(2 * math.pi * freq1 * t) > 0) else -1.0
        wave2 = (2.0 * ((freq2 * t) % 1.0)) - 1.0
        s = (wave1 * 0.5 + wave2 * 0.5) * env * 0.6
        samples.append(s)
    create_wave(filepath, samples)

def generate_pass_fanfare(filepath: Path):
    """Harmonic ascending triad chord (C5 -> E5 -> G5 -> C6)."""
    duration = 1.2
    notes = [
        (0.00, 0.20, 523.25),  # C5
        (0.18, 0.20, 659.25),  # E5
        (0.36, 0.22, 783.99),  # G5
        (0.55, 0.65, 1046.50)  # C6 (held)
    ]
    num_samples = int(duration * SAMPLE_RATE)
    samples = [0.0] * num_samples
    
    for start_t, note_dur, freq in notes:
        start_idx = int(start_t * SAMPLE_RATE)
        end_idx = min(num_samples, int((start_t + note_dur) * SAMPLE_RATE))
        for i in range(start_idx, end_idx):
            t = (i - start_idx) / SAMPLE_RATE
            env = math.exp(-t * (4.0 / note_dur))
            val = (math.sin(2 * math.pi * freq * t) * 0.6 +
                   math.sin(4 * math.pi * freq * t) * 0.2) * env * 0.45
            samples[i] += val
            
    create_wave(filepath, samples)

def generate_gold_fanfare(filepath: Path):
    """Triumphant gold victory jingle (rapid arpeggio + triumphant sustained chord)."""
    duration = 2.0
    arpeggio = [
        (0.00, 0.12, 523.25),   # C5
        (0.10, 0.12, 659.25),   # E5
        (0.20, 0.12, 783.99),   # G5
        (0.30, 0.15, 1046.50),  # C6
        (0.42, 0.15, 1318.51),  # E6
        (0.55, 1.45, 1567.98),  # G6 (sustained harmony)
    ]
    harmonies = [
        (0.55, 1.45, 1046.50),  # C6
        (0.55, 1.45, 1318.51),  # E6
        (0.55, 1.45, 2093.00),  # C7 chime
    ]
    num_samples = int(duration * SAMPLE_RATE)
    samples = [0.0] * num_samples
    
    for start_t, note_dur, freq in arpeggio + harmonies:
        start_idx = int(start_t * SAMPLE_RATE)
        end_idx = min(num_samples, int((start_t + note_dur) * SAMPLE_RATE))
        for i in range(start_idx, end_idx):
            t = (i - start_idx) / SAMPLE_RATE
            env = math.exp(-t * (3.5 / note_dur))
            val = (math.sin(2 * math.pi * freq * t) * 0.5 +
                   math.sin(4 * math.pi * freq * t) * 0.2) * env * 0.28
            samples[i] += val
            
    create_wave(filepath, samples)

def main():
    base_dir = Path("d:/Repositories/AssettoCorsa-GTLikeLicenses/assets/audio")
    generate_countdown_beep(base_dir / "countdown_beep.wav")
    generate_countdown_go(base_dir / "countdown_go.wav")
    generate_fail_buzzer(base_dir / "fail_buzzer.wav")
    generate_pass_fanfare(base_dir / "pass_fanfare.wav")
    generate_gold_fanfare(base_dir / "gold_fanfare.wav")
    print("All audio assets generated successfully!")

if __name__ == "__main__":
    main()
