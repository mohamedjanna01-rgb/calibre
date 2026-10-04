"""Fabrique l'ambiance de plateau (audio/production/ambiance-plateau.wav), une seule fois.

Brouhaha de conversations rendu inintelligible (voix d'essais lues à l'envers et superposées),
souffle de fond et frappes de clavier. Usage : python scripts/ambiance.py audio/essais/*.wav
"""
import sys
from pathlib import Path

import numpy as np
from scipy.signal import butter, sosfiltfilt

sys.path.insert(0, str(Path(__file__).parent))
from effet_telephone import ecrire_wav, lire_wav  # noqa: E402

TAUX = 8000
DUREE = 90  # secondes, bouclées avec un fondu enchaîné
SORTIE = Path(__file__).resolve().parent.parent / "audio" / "production" / "ambiance-plateau.wav"


def bruit_rose(n, rng):
    spectre = np.fft.rfft(rng.normal(size=n))
    f = np.fft.rfftfreq(n)
    f[0] = f[1]
    return np.fft.irfft(spectre / np.sqrt(f), n)


def fabriquer(sources, graine=7):
    rng = np.random.default_rng(graine)
    n = DUREE * TAUX
    matiere = np.concatenate([lire_wav(s)[0][::-1] for s in sources])  # voix à l'envers
    brouhaha = np.zeros(n)
    for _ in range(7):  # sept conversations lointaines
        debut = rng.integers(0, len(matiere) - n)
        brouhaha += matiere[debut:debut + n] * 10 ** (rng.uniform(-14, -4) / 20)
    brouhaha = sosfiltfilt(butter(4, 2600, fs=TAUX, output="sos"), brouhaha)  # éloignement
    brouhaha /= np.sqrt(np.mean(brouhaha ** 2))

    souffle = bruit_rose(n, rng)
    souffle /= np.sqrt(np.mean(souffle ** 2))

    clavier = np.zeros(n)
    t = 0.0
    while t < DUREE - 1:
        t += rng.exponential(1.2)
        for _ in range(rng.integers(3, 9)):  # petites rafales de frappe
            i = int(t * TAUX)
            if i + 40 >= n:
                break
            clavier[i:i + 40] += rng.normal(size=40) * np.exp(-np.arange(40) / 8)
            t += rng.uniform(0.08, 0.2)
    clavier = sosfiltfilt(butter(2, 1800, btype="high", fs=TAUX, output="sos"), clavier)
    clavier /= np.max(np.abs(clavier)) + 1e-9

    ambiance = brouhaha + 0.25 * souffle + 0.35 * clavier
    return ambiance / np.sqrt(np.mean(ambiance ** 2)) * 0.1


if __name__ == "__main__":
    sources = [Path(p) for p in sys.argv[1:]]
    if not sources:
        sys.exit(__doc__)
    ecrire_wav(SORTIE, fabriquer(sources), TAUX)
    print(f"{SORTIE.name} : {DUREE} s à partir de {len(sources)} sources")
