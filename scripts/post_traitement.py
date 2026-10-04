"""Traitement du son d'un appel généré, sans aucune requête à l'API.

1. Transcription locale (faster-whisper) avec l'horodatage de chaque mot, alignée sur le script de production.
2. Contrôle de fidélité : passages du script absents de l'audio, ou passages en trop.
3. Ambiance de centre d'appels, grésillements aux moments où le client fait répéter, effet de ligne téléphonique.
4. Numéros de téléphone masqués par un bip.

Entrée : audio/brut/appel-XX.wav (voix brute, locale, non versionnée).
Sortie : audio/appels/appel-XX.wav, et le contrôle de fidélité dans audio/appels/appel-XX.json.
Usage : python scripts/post_traitement.py --appel 03 [--snr 20]
"""
import argparse
import difflib
import json
import re
import sys
import unicodedata
from pathlib import Path

import numpy as np
import yaml
from scipy.signal import butter, resample_poly, sosfiltfilt

sys.path.insert(0, str(Path(__file__).parent))
from effet_telephone import appliquer_effet, ecrire_wav, lire_wav  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PRODUCTION = ROOT / "audio" / "production"
BRUT = ROOT / "audio" / "brut"
APPELS = ROOT / "audio" / "appels"
AMBIANCE = PRODUCTION / "ambiance-plateau.wav"


# --- Alignement texte / audio --------------------------------------------------------------

def jetons(texte):
    """Mots normalisés (minuscules, sans accents ni ponctuation) avec leur position dans le texte."""
    sans_accents = "".join(c for c in unicodedata.normalize("NFD", texte.lower()) if unicodedata.category(c) != "Mn")
    return [(m.group(), m.start(), m.end()) for m in re.finditer(r"[a-z]+|\d+", sans_accents)]


def reference(script):
    """Jetons du script avec, pour chacun, le numéro de réplique et les marques masque / brouillage."""
    sortie = []
    for r in script["repliques"]:
        texte = re.sub(r"<[^>]+> ", "", r["texte"])
        zones = [("masque", m) for m in r.get("masquer", [])]
        if r.get("brouiller"):
            zones.append(("brouille", r["brouiller"]))
        marques = []
        for genre, extrait in zones:
            debut = texte.index(extrait)
            marques.append((genre, extrait, debut, debut + len(extrait)))
        for mot, a, b in jetons(texte):
            marque = next(((g, e) for g, e, d, f in marques if a >= d and b <= f), None)
            sortie.append({"mot": mot, "replique": r["n"], "marque": marque})
    return sortie


def transcrire(signal, taux):
    from faster_whisper import WhisperModel
    modele = WhisperModel("small", device="cpu", compute_type="int8")
    audio = resample_poly(signal, 16000, taux).astype(np.float32)
    segments, _ = modele.transcribe(audio, language="fr", word_timestamps=True)
    mots = []
    for seg in segments:
        for w in seg.words:
            for mot, _, _ in jetons(w.word):
                mots.append({"mot": mot, "debut": w.start, "fin": w.end, "brut": w.word.strip()})
    return mots


def aligner(ref, hyp):
    sm = difflib.SequenceMatcher(None, [r["mot"] for r in ref], [h["mot"] for h in hyp], autojunk=False)
    correspondance = {}
    for a, b, n in sm.get_matching_blocks():
        for k in range(n):
            correspondance[a + k] = b + k
    return sm, correspondance


def zone_temps(indices, correspondance, hyp, nb_ref):
    """Début et fin d'un groupe de jetons du script ; à défaut, l'intervalle entre ses voisins alignés."""
    alignes = [correspondance[i] for i in indices if i in correspondance]
    if alignes:
        return hyp[min(alignes)]["debut"], hyp[max(alignes)]["fin"]
    avant = next((correspondance[i] for i in range(min(indices) - 1, -1, -1) if i in correspondance), None)
    apres = next((correspondance[i] for i in range(max(indices) + 1, nb_ref) if i in correspondance), None)
    return (hyp[avant]["fin"] if avant is not None else 0.0), (hyp[apres]["debut"] if apres is not None else hyp[-1]["fin"])


def chercher_chiffres(cible, hyp, apres=0.0):
    """Repère une suite de chiffres dans la transcription, même découpée autrement (« 06 39 » ou « 0639 »)."""
    for j, h in enumerate(hyp):
        if h["debut"] < apres or not h["mot"].isdigit():
            continue
        cumul, k = "", j
        while k < len(hyp) and hyp[k]["mot"].isdigit() and len(cumul) < len(cible):
            cumul += hyp[k]["mot"]
            k += 1
        if cumul.startswith(cible):
            return hyp[j]["debut"], hyp[k - 1]["fin"]
    return None


def zones(ref, hyp, correspondance):
    groupes = {}
    for i, r in enumerate(ref):
        if r["marque"]:
            groupes.setdefault((r["replique"],) + r["marque"], []).append(i)
    masques, brouilles = [], []
    for (rep, genre, extrait), indices in groupes.items():
        debut, fin = zone_temps(indices, correspondance, hyp, len(ref))
        if genre == "masque":
            trouve = chercher_chiffres(re.sub(r"\D", "", extrait), hyp, apres=max(0.0, debut - 5))
            if trouve:
                debut, fin = trouve
            masques.append((max(0.0, debut - 0.08), fin + 0.12))
        else:
            brouilles.append((debut, fin))
    return sorted(masques), sorted(brouilles)


def controle(sm, ref, hyp, minimum=5):
    """Passages du script absents de l'audio et passages entendus qui ne sont pas dans le script."""
    absents, en_trop = [], []
    for op, a1, a2, b1, b2 in sm.get_opcodes():
        if op in ("delete", "replace") and a2 - a1 >= minimum:
            absents.append({"replique": ref[a1]["replique"], "texte": " ".join(r["mot"] for r in ref[a1:a2])})
        if op in ("insert", "replace") and b2 - b1 >= minimum:
            en_trop.append({"vers_s": round(hyp[b1]["debut"], 1), "texte": " ".join(h["brut"] for h in hyp[b1:b2])})
    alignes = {a + k for a, _, n in sm.get_matching_blocks() for k in range(n)}
    # Répliques dont aucun mot n'a été retrouvé (utile pour les répliques courtes : « Bonjour. », « D'accord. »)
    par_replique = {}
    for i, r in enumerate(ref):
        par_replique.setdefault(r["replique"], []).append(i in alignes)
    muettes = [n for n, vus in par_replique.items() if not any(vus)]
    return {"mots_du_script_retrouves_pct": round(100 * len(alignes) / max(1, len(ref)), 1),
            "repliques_non_retrouvees": muettes, "passages_absents": absents, "passages_en_trop": en_trop}


# --- Son -------------------------------------------------------------------------------------

def ambiance(longueur, taux):
    fond, t = lire_wav(AMBIANCE)
    fond = resample_poly(fond, taux, t)
    fondu = int(taux)
    sortie = fond.copy()
    while len(sortie) < longueur:  # boucle avec fondu enchaîné
        rampe = np.linspace(0, 1, fondu)
        sortie[-fondu:] = sortie[-fondu:] * (1 - rampe) + fond[:fondu] * rampe
        sortie = np.concatenate([sortie, fond[fondu:]])
    return sortie[:longueur]


def niveau_parole(signal, taux):
    trames = signal[: len(signal) // (taux // 50) * (taux // 50)].reshape(-1, taux // 50)
    energie = np.sqrt(np.mean(trames ** 2, axis=1))
    return np.sqrt(np.mean(energie[energie > 0.2 * energie.max()] ** 2))


def hacher(signal, taux, debut, fin, rng):
    """Paroles hachées et grésillements entre debut et fin (en secondes)."""
    a, b = int(debut * taux), int(fin * taux)
    trame, rampe = int(0.04 * taux), int(0.004 * taux)
    coupure = np.concatenate([np.linspace(1, 0, rampe), np.zeros(trame - 2 * rampe), np.linspace(0, 1, rampe)])
    for i in range(a, b - trame, trame):
        if rng.random() < 0.35:  # parole hachée : trame coupée, avec de courts fondus
            signal[i:i + trame] *= coupure
    crepitements = np.zeros(b - a)
    impulsions = rng.random(b - a) < 80 / taux
    crepitements[impulsions] = rng.normal(0, 1, impulsions.sum())
    crepitements = sosfiltfilt(butter(2, [700, 3200], btype="bandpass", fs=taux, output="sos"), crepitements)
    niveau = niveau_parole(signal, taux)
    signal[a:b] += crepitements / (np.max(np.abs(crepitements)) + 1e-9) * niveau * 1.2
    signal[a:b] = np.round(signal[a:b] * 24) / 24  # quantification grossière
    return signal


def biper(signal, taux, debut, fin):
    a, b = int(debut * taux), min(int(fin * taux), len(signal))
    t = np.arange(b - a) / taux
    bip = 0.3 * np.sin(2 * np.pi * 1000 * t)
    rampe = int(0.01 * taux)
    bip[:rampe] *= np.linspace(0, 1, rampe)
    bip[-rampe:] *= np.linspace(1, 0, rampe)
    signal[a:b] = bip
    return signal


def traiter(appel, snr_db=20, graine=0):
    script = yaml.safe_load((PRODUCTION / f"appel-{appel}.yaml").read_text(encoding="utf-8"))
    signal, taux = lire_wav(BRUT / f"appel-{appel}.wav")

    ref = reference(script)
    hyp = transcrire(signal, taux)
    sm, correspondance = aligner(ref, hyp)
    masques, brouilles = zones(ref, hyp, correspondance)
    rapport = controle(sm, ref, hyp)

    rng = np.random.default_rng(graine)
    fond = ambiance(len(signal), taux)
    signal = signal + fond / np.sqrt(np.mean(fond ** 2)) * niveau_parole(signal, taux) * 10 ** (-snr_db / 20)
    for debut, fin in brouilles:
        signal = hacher(signal, taux, debut, fin, rng)
    tel, taux_tel = appliquer_effet(signal, taux, graine=graine)
    for debut, fin in masques:
        tel = biper(tel, taux_tel, debut, fin)

    APPELS.mkdir(parents=True, exist_ok=True)
    ecrire_wav(APPELS / f"appel-{appel}.wav", tel, taux_tel)
    rapport.update({"bips_s": [[round(a, 2), round(b, 2)] for a, b in masques],
                    "grésillements_s": [[round(a, 2), round(b, 2)] for a, b in brouilles],
                    "snr_ambiance_db": snr_db})
    return rapport


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--appel", required=True)
    p.add_argument("--snr", type=float, default=20, help="écart en dB entre la parole et l'ambiance")
    a = p.parse_args()
    appel = f"{int(a.appel):02d}"
    rapport = traiter(appel, a.snr)
    infos_f = APPELS / f"appel-{appel}.json"
    infos = json.loads(infos_f.read_text(encoding="utf-8")) if infos_f.exists() else {"appel": appel}
    infos["controle"] = rapport
    infos_f.write_text(json.dumps(infos, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(rapport, ensure_ascii=False, indent=2))
