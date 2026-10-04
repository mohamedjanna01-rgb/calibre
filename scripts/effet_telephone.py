"""Effet de ligne téléphonique : bande 300-3 400 Hz, 8 kHz, codage G.711 (loi µ), léger bruit de ligne."""
import wave
from math import gcd

import numpy as np
from scipy.signal import butter, resample_poly, sosfiltfilt

TAUX_TELEPHONE = 8000


def lire_wav(chemin):
    """Renvoie un signal mono en flottants entre -1 et 1, et sa fréquence d'échantillonnage."""
    with wave.open(str(chemin), "rb") as w:
        taux, canaux = w.getframerate(), w.getnchannels()
        donnees = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float64) / 32768
    if canaux > 1:
        donnees = donnees.reshape(-1, canaux).mean(axis=1)
    return donnees, taux


def ecrire_wav(chemin, signal, taux):
    with wave.open(str(chemin), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(taux)
        w.writeframes((np.clip(signal, -1, 1) * 32767).astype("<i2").tobytes())


def loi_mu(signal, mu=255):
    """Codage puis décodage G.711 sur 8 bits : la perte de qualité d'une vraie ligne."""
    code = np.sign(signal) * np.log1p(mu * np.abs(signal)) / np.log1p(mu)
    code = np.round(code * 127) / 127
    return np.sign(code) * ((1 + mu) ** np.abs(code) - 1) / mu


def appliquer_effet(signal, taux, bruit_db=-50, graine=0):
    signal = sosfiltfilt(butter(6, [300, 3400], btype="bandpass", fs=taux, output="sos"), signal)
    k = gcd(TAUX_TELEPHONE, taux)
    signal = resample_poly(signal, TAUX_TELEPHONE // k, taux // k)
    signal = signal / (np.max(np.abs(signal)) + 1e-9) * 0.7
    bruit = np.random.default_rng(graine).normal(0, 10 ** (bruit_db / 20), len(signal))
    bruit = sosfiltfilt(butter(4, [300, 3400], btype="bandpass", fs=TAUX_TELEPHONE, output="sos"), bruit)
    return loi_mu(signal + bruit), TAUX_TELEPHONE
