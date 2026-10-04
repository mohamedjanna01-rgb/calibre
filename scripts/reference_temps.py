"""Référence approchée des temps de parole, pour évaluer l'horodatage des transcriptions.

La génération des appels ne fournit pas d'horodatage. On transcrit localement la voix brute (audio/brut/,
avant ambiance, bips et effet téléphonique) avec le modèle « small », puis on aligne ce texte sur le
scénario : chaque mot du scénario reçoit un temps (interpolé s'il n'est pas reconnu).
Modèle et audio sont différents de ceux du recalage de la méthode hybride (« medium » sur l'audio final),
mais c'est la même famille de modèles : la référence reste approchée.

Sortie : evaluations/transcription/reference-temps/appel-XX.json
Usage : python scripts/reference_temps.py 03 10
"""
import difflib
import json
import sys
from pathlib import Path

import numpy as np
from scipy.signal import resample_poly

sys.path.insert(0, str(Path(__file__).parent))
from effet_telephone import lire_wav  # noqa: E402
from evaluer_transcription import jetons, reference  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SORTIE = ROOT / "evaluations" / "transcription" / "reference-temps"


def construire(appel, modele):
    signal, taux = lire_wav(ROOT / "audio" / "brut" / f"appel-{appel}.wav")
    segments, _ = modele.transcribe(resample_poly(signal, 16000, taux).astype(np.float32), language="fr", word_timestamps=True)
    hyp = [(m, w.start) for s in segments for w in s.words for m in jetons(w.word)]
    ref = [(m, i) for i, (_, texte) in enumerate(reference(appel)) for m in jetons(texte)]
    sm = difflib.SequenceMatcher(None, [m for m, _ in ref], [m for m, _ in hyp], autojunk=False)
    temps = [None] * len(ref)
    for a, b, n in sm.get_matching_blocks():
        for k in range(n):
            temps[a + k] = hyp[b + k][1]
    connus = [i for i, t in enumerate(temps) if t is not None]
    temps = list(np.interp(range(len(ref)), connus, [temps[i] for i in connus]))
    return {"appel": appel, "mots_alignes_pct": round(100 * len(connus) / len(ref), 1),
            "mots": [{"mot": m, "replique": i + 1, "debut": round(t, 2)} for (m, i), t in zip(ref, temps)]}


if __name__ == "__main__":
    from faster_whisper import WhisperModel
    modele = WhisperModel("small", device="cpu", compute_type="int8")
    SORTIE.mkdir(parents=True, exist_ok=True)
    for n in sys.argv[1:]:
        appel = f"{int(n):02d}"
        donnees = construire(appel, modele)
        (SORTIE / f"appel-{appel}.json").write_text(json.dumps(donnees, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"appel-{appel} : référence de temps, {donnees['mots_alignes_pct']} % des mots alignés", flush=True)
