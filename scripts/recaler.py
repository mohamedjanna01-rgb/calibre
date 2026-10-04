"""Méthode hybride : texte et locuteurs de Gemini 3.8 Flash, temps de la transcription locale.

L'horodatage renvoyé par Gemini 3.8 Flash dérive (il peut dépasser la durée de l'appel). Chaque réplique
est recalée sur les mots horodatés de la transcription locale (whisper-medium) : on aligne les deux textes,
et la réplique prend le temps du premier et du dernier de ses mots retrouvés (interpolé sinon).
Aucune requête : la transcription Gemini déjà obtenue est réutilisée.

Sortie : transcriptions/hybride/appel-XX.json et appel-XX.md
Usage : python scripts/recaler.py 03 10
"""
import difflib
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from evaluer_transcription import jetons  # noqa: E402
from transcrire import ecrire, mots_whisper  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "transcriptions" / "gemini-3.8-flash"


def recaler(appel):
    gemini = json.loads((SOURCE / f"appel-{appel}.json").read_text(encoding="utf-8"))
    locaux = mots_whisper(appel, ROOT / "audio" / "appels" / f"appel-{appel}.wav", "medium")
    hyp = [(m, w["debut"], w["fin"]) for w in locaux for m in jetons(w["texte"])]
    g = [(m, k) for k, r in enumerate(gemini["repliques"]) for m in jetons(r["texte"]) if not m.startswith("§")]
    sm = difflib.SequenceMatcher(None, [m for m, _ in g], [m for m, _, _ in hyp], autojunk=False)
    debuts, fins = [None] * len(g), [None] * len(g)
    for a, b, n in sm.get_matching_blocks():
        for k in range(n):
            debuts[a + k], fins[a + k] = hyp[b + k][1], hyp[b + k][2]
    connus = [i for i, t in enumerate(debuts) if t is not None]
    debuts = np.interp(range(len(g)), connus, [debuts[i] for i in connus])
    fins = np.interp(range(len(g)), connus, [fins[i] for i in connus])
    repliques = []
    for k, r in enumerate(gemini["repliques"]):
        idx = [i for i, (_, kk) in enumerate(g) if kk == k]
        if idx:
            debut, fin = float(debuts[idx[0]]), float(fins[idx[-1]])
        else:  # réplique sans mot (par exemple un bip seul) : juste après la précédente
            debut = fin = repliques[-1]["fin"] if repliques else 0.0
        repliques.append({"locuteur": r["locuteur"], "debut": debut, "fin": max(fin, debut), "texte": r["texte"]})
    ecrire(appel, "hybride", repliques, gemini["duree_audio_s"], {"source_texte": "gemini-3.8-flash",
                                                                   "source_temps": "whisper-medium",
                                                                   "mots_alignes_pct": round(100 * len(connus) / len(g), 1)})
    return round(100 * len(connus) / len(g), 1)


if __name__ == "__main__":
    for n in sys.argv[1:]:
        appel = f"{int(n):02d}"
        if not (SOURCE / f"appel-{appel}.json").exists():
            print(f"appel-{appel} : pas de transcription Gemini 3.8 Flash, rien à recaler")
            continue
        print(f"appel-{appel} : recalé, {recaler(appel)} % des mots Gemini alignés sur les temps locaux")
