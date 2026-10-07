#!/usr/bin/env python3
"""
audio_generator.py
Procedural 16-bit PCM 44.1kHz WAV Audio Asset Generator for Assetto Corsa GT Licenses.

Generates:
  - countdown_beep.wav: 880Hz electronic countdown beep
  - countdown_go.wav: 1760Hz high-pitched GO beep
  - fail_buzzer.wav: Low dissonant fail buzzer (110Hz + 116Hz)
  - pass_fanfare.wav: Major triad pass fanfare (C-E-G-C)
  - gold_fanfare.wav: Ascending triumphant fanfare (C-E-G-B-C)
"""

import math
import os
import struct
import wave
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SAMPLE_RATE = 44100


def create_wave(filename: Path, samples: list[float]):
    filename.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(filename), "w") as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(SAMPLE_RATE)

        raw_bytes = bytearray()
        for s in samples:
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
        env = math.exp(-t * 25.0)
        val = math.sin(2 * math.pi * freq * t) * env * 0.7
        samples.append(val)
    create_wave(filepath, samples)


def generate_countdown_go(filepath: Path):
    """Higher pitched 1760Hz double-frequency chime with longer sustain (400ms)."""
    duration = 0.4
    freq1 = 1760.0
    freq2 = 880.0
    num_samples = int(duration * SAMPLE_RATE)
    samples = []
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        env = math.exp(-t * 8.0)
        val = (math.sin(2 * math.pi * freq1 * t) * 0.5 + math.sin(2 * math.pi * freq2 * t) * 0.3) * env * 0.8
        samples.append(val)
    create_wave(filepath, samples)


def generate_fail_buzzer(filepath: Path):
    """Dissonant low buzzer combining 110Hz and 116Hz to produce harsh acoustic beat frequency."""
    duration = 0.6
    f1 = 110.0
    f2 = 116.5
    f3 = 220.0
    num_samples = int(duration * SAMPLE_RATE)
    samples = []
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        env = 1.0 - (t / duration) ** 2
        saw1 = 2.0 * (t * f1 - math.floor(t * f1 + 0.5))
        saw2 = 2.0 * (t * f2 - math.floor(t * f2 + 0.5))
        sq = 1.0 if math.sin(2 * math.pi * f3 * t) > 0 else -1.0
        val = (saw1 * 0.35 + saw2 * 0.35 + sq * 0.15) * env * 0.7
        samples.append(val)
    create_wave(filepath, samples)


def generate_pass_fanfare(filepath: Path):
    """Short cheerful brass fanfare (C5 -> E5 -> G5 -> C6)."""
    duration = 1.2
    notes = [
        (0.00, 0.18, 523.25),  # C5
        (0.18, 0.18, 659.25),  # E5
        (0.36, 0.18, 783.99),  # G5
        (0.54, 0.60, 1046.50), # C6
    ]
    num_samples = int(duration * SAMPLE_RATE)
    samples = [0.0] * num_samples
    for start_t, note_dur, freq in notes:
        start_idx = int(start_t * SAMPLE_RATE)
        end_idx = min(num_samples, int((start_t + note_dur) * SAMPLE_RATE))
        for i in range(start_idx, end_idx):
            t = (i - start_idx) / SAMPLE_RATE
            env = math.exp(-t * (4.0 / note_dur))
            val = (math.sin(2 * math.pi * freq * t) * 0.6 + math.sin(4 * math.pi * freq * t) * 0.25) * env * 0.35
            samples[i] += val
    create_wave(filepath, samples)


def generate_gold_fanfare(filepath: Path):
    """Triumphant Gran Turismo-style gold victory fanfare."""
    duration = 2.0
    arpeggio = [
        (0.00, 0.12, 523.25),  # C5
        (0.12, 0.12, 659.25),  # E5
        (0.24, 0.12, 783.99),  # G5
        (0.36, 0.12, 987.77),  # B5
        (0.48, 0.90, 1046.50), # C6
    ]
    harmonies = [
        (0.48, 0.90, 523.25),  # C5
        (0.48, 0.90, 659.25),  # E5
        (0.48, 0.90, 783.99),  # G5
    ]
    num_samples = int(duration * SAMPLE_RATE)
    samples = [0.0] * num_samples

    for start_t, note_dur, freq in arpeggio + harmonies:
        start_idx = int(start_t * SAMPLE_RATE)
        end_idx = min(num_samples, int((start_t + note_dur) * SAMPLE_RATE))
        for i in range(start_idx, end_idx):
            t = (i - start_idx) / SAMPLE_RATE
            env = math.exp(-t * (3.5 / note_dur))
            val = (math.sin(2 * math.pi * freq * t) * 0.5 + math.sin(4 * math.pi * freq * t) * 0.2) * env * 0.28
            samples[i] += val

    create_wave(filepath, samples)


def main():
    base_dir = REPO_ROOT / "assets" / "audio"
    generate_countdown_beep(base_dir / "countdown_beep.wav")
    generate_countdown_go(base_dir / "countdown_go.wav")
    generate_fail_buzzer(base_dir / "fail_buzzer.wav")
    generate_pass_fanfare(base_dir / "pass_fanfare.wav")
    generate_gold_fanfare(base_dir / "gold_fanfare.wav")
    print("All audio assets generated successfully!")


if __name__ == "__main__":
    main()

