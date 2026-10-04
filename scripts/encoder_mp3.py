"""Encode les appels finaux en MP3 mono 32 kbit/s pour le dépôt et la démo en ligne.

Les WAV restent en local (non versionnés) : la transcription travaille à partir des WAV.
Le son est ré-échantillonné à 16 kHz (MPEG-2, lu par tous les navigateurs) ; à 8 kHz, le MP3
utiliserait une extension non standard (MPEG-2.5) que certains lecteurs ne décodent pas.
Usage : python scripts/encoder_mp3.py [03 10 ...]   (sans argument : tous les appels)
"""
import sys
from pathlib import Path

import lameenc
import numpy as np
from scipy.signal import resample_poly

sys.path.insert(0, str(Path(__file__).parent))
from effet_telephone import lire_wav  # noqa: E402

APPELS = Path(__file__).resolve().parent.parent / "audio" / "appels"
TAUX_MP3 = 16000
DEBIT_KBPS = 32


def encoder(wav, mp3):
    signal, taux = lire_wav(wav)
    signal = resample_poly(signal, TAUX_MP3, taux)
    pcm = (np.clip(signal, -1, 1) * 32767).astype("<i2").tobytes()
    enc = lameenc.Encoder()
    enc.set_bit_rate(DEBIT_KBPS)
    enc.set_in_sample_rate(TAUX_MP3)
    enc.set_channels(1)
    enc.set_quality(2)
    mp3.write_bytes(enc.encode(pcm) + enc.flush())


if __name__ == "__main__":
    numeros = sys.argv[1:] or [p.stem.split("-")[1] for p in sorted(APPELS.glob("appel-*.wav"))]
    total_wav = total_mp3 = 0
    for n in numeros:
        wav, mp3 = APPELS / f"appel-{int(n):02d}.wav", APPELS / f"appel-{int(n):02d}.mp3"
        encoder(wav, mp3)
        total_wav += wav.stat().st_size
        total_mp3 += mp3.stat().st_size
        print(f"{mp3.name} : {mp3.stat().st_size / 1e6:.2f} Mo")
    print(f"Total : {total_wav / 1e6:.1f} Mo en WAV -> {total_mp3 / 1e6:.1f} Mo en MP3")
