"""Mesure la qualité des transcriptions par rapport aux scénarios (référence), entièrement par code.

Indicateurs, par appel et par méthode :
  - mots retrouvés et taux d'erreur mot à mot (WER), interjections exclues, nombres chiffre par chiffre ;
  - attribution du locuteur : part des mots, puis des répliques, attribués au bon locuteur ;
  - preuves de la notation de référence : retrouvées mot pour mot, approchées ou absentes, et bon locuteur ;
  - numéros masqués : même nombre de [numéro masqué], aucun numéro de téléphone en clair ;
  - [inaudible] et mots inventés (présents dans la transcription, absents du scénario) ;
  - horodatage : ordre croissant et bornes cohérentes avec la durée de l'audio.
Usage : python scripts/evaluer_transcription.py --methodes whisper-small gemini-3.8-flash --appels 03 10 --nom pilote
"""
import argparse
import difflib
import json
import re
import sys
import unicodedata
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
SCENARIOS = ROOT / "scenarios"
TRANSCRIPTIONS = ROOT / "transcriptions"
NOTATION = ROOT / "cadrage" / "calibre-notation-reference.md"
SORTIE = ROOT / "evaluations" / "transcription"
REFERENCE_TEMPS = SORTIE / "reference-temps"
INTERJECTIONS = {"hmm", "hm", "mm", "mmh", "mhm", "hum", "mmhmm", "euh", "heu"}
MASQUE, INAUDIBLE = "§masque", "§inaudible"


def jetons(texte):
    """Mots normalisés : minuscules, sans accents ni ponctuation, nombres chiffre par chiffre, sans interjections."""
    texte = texte.replace("[numéro masqué]", f" {MASQUE} ").replace("[inaudible]", f" {INAUDIBLE} ")
    texte = "".join(c for c in unicodedata.normalize("NFD", texte.lower()) if not unicodedata.combining(c))
    return [m for m in re.findall(r"§[a-z]+|[a-z]+|\d", texte) if m not in INTERJECTIONS]


NOMBRES = {"zero": "0", "un": "1", "une": "1", "deux": "2", "trois": "3", "quatre": "4", "cinq": "5", "six": "6",
           "sept": "7", "huit": "8", "neuf": "9", "dix": "10", "onze": "11", "douze": "12", "treize": "13",
           "quatorze": "14", "quinze": "15", "seize": "16"}


def jetons_preuve(texte):
    """Pour la recherche des preuves : mêmes jetons, avec « € » = « euros » et les nombres écrits en lettres
    convertis en chiffres, des deux côtés (une preuve ne doit pas échouer sur la seule forme d'un nombre)."""
    texte = texte.replace("€", " euros ")
    return [c for m in jetons(texte) for c in (NOMBRES.get(m, m) if not m.isdigit() else m)]


def reference(appel):
    corps = (SCENARIOS / f"appel-{appel}.md").read_text(encoding="utf-8").split("## Transcription de référence")[1]
    reps = [("conseiller" if m.group(1) == "Conseiller" else "client", m.group(2))
            for m in re.finditer(r"^\*\*(Conseiller|Client|Cliente) :\*\* (.+)$", corps, flags=re.M)]
    return reps


def preuves(appel):
    """Preuves citées dans la notation de référence pour cet appel (morceaux séparés par « … »)."""
    texte = NOTATION.read_text(encoding="utf-8").split("## 4.")[1].split("## 5.")[0]
    for ligne in texte.splitlines():
        if re.match(rf"- \*\*S{int(appel)}\*\*", ligne) and "reuves" in ligne:
            return [m.strip(" .,") for p in re.findall(r"« ([^»]+) »", ligne.split("reuves", 1)[1])
                    for m in p.split("…") if len(m.strip(" .,")) > 8]
    return []


def wer(ref, hyp):
    """Taux d'erreur mot à mot (substitutions + suppressions + insertions) / mots de la référence."""
    precedente = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, 1):
        courante = [i] + [0] * len(hyp)
        for j, h in enumerate(hyp, 1):
            courante[j] = min(precedente[j] + 1, courante[j - 1] + 1, precedente[j - 1] + (r != h))
        precedente = courante
    return precedente[-1] / max(1, len(ref))


def evaluer(appel, methode):
    donnees = json.loads((TRANSCRIPTIONS / methode / f"appel-{appel}.json").read_text(encoding="utf-8"))
    hyp_reps = donnees["repliques"]

    ref = [(mot, loc, i) for i, (loc, texte) in enumerate(reference(appel)) for mot in jetons(texte)]
    hyp_tous = [(mot, r["locuteur"], k) for k, r in enumerate(hyp_reps) for mot in jetons(r["texte"])]
    nb_inaudible = sum(1 for m, _, _ in hyp_tous if m == INAUDIBLE)
    hyp = [h for h in hyp_tous if h[0] != INAUDIBLE]
    ref_mots, hyp_mots = [m for m, _, _ in ref], [m for m, _, _ in hyp]

    sm = difflib.SequenceMatcher(None, ref_mots, hyp_mots, autojunk=False)
    paires = [(a + k, b + k) for a, b, n in sm.get_matching_blocks() for k in range(n)]
    retrouves = {i for i, _ in paires}
    bons_locuteurs = sum(1 for i, j in paires if ref[i][1] == hyp[j][1])

    # Réplique bien attribuée : la majorité de ses mots retrouvés a le bon locuteur
    votes = {}
    for i, j in paires:
        votes.setdefault(ref[i][2], []).append(ref[i][1] == hyp[j][1])
    repliques_ok = sum(1 for v in votes.values() if sum(v) > len(v) / 2)

    # Preuves : recherchées dans toute la transcription (nombres et « € » normalisés), puis attribution du locuteur
    ref_p = [(m, loc) for loc, texte in reference(appel) for m in jetons_preuve(texte) if m not in (INAUDIBLE,)]
    hyp_p = [(m, r["locuteur"]) for r in hyp_reps for m in jetons_preuve(r["texte"]) if m != INAUDIBLE]
    hyp_pm, ref_pm = [m for m, _ in hyp_p], [m for m, _ in ref_p]
    resultats_preuves = []
    for p in preuves(appel):
        pj = jetons_preuve(p)
        trouve, statut = None, "absente"
        for k in range(len(hyp_pm) - len(pj) + 1):
            if hyp_pm[k:k + len(pj)] == pj:
                trouve, statut = k, "exacte"
                break
        if trouve is None:
            meilleur = max(((difflib.SequenceMatcher(None, pj, hyp_pm[k:k + len(pj)]).ratio(), k)
                            for k in range(max(1, len(hyp_pm) - len(pj) + 1))), default=(0, None))
            if meilleur[0] >= 0.85:
                trouve, statut = meilleur[1], "approchée"
        locuteur_ok = None
        # Locuteur attendu : celui de la réplique du scénario qui contient la preuve
        debut_ref = next((i for i in range(len(ref_pm) - len(pj) + 1) if ref_pm[i:i + len(pj)] == pj), None)
        if trouve is not None and debut_ref is not None:
            locs = [loc for _, loc in hyp_p[trouve:trouve + len(pj)]]
            locuteur_ok = max(set(locs), key=locs.count) == ref_p[debut_ref][1]
        resultats_preuves.append({"preuve": p, "statut": statut, "bon_locuteur": locuteur_ok})

    # Horodatage, si une référence de temps existe : écart entre le début de chaque réplique transcrite
    # et le temps de référence de son premier mot retrouvé dans le scénario
    ecarts = []
    fichier_temps = REFERENCE_TEMPS / f"appel-{appel}.json"
    if fichier_temps.exists():
        temps_ref = [m["debut"] for m in json.loads(fichier_temps.read_text(encoding="utf-8"))["mots"]]
        assert len(temps_ref) == len(ref), "référence de temps périmée : à reconstruire"
        vers_ref = {j: i for i, j in paires}
        deja = set()
        for j, (_, _, k) in enumerate(hyp):
            if k not in deja and j in vers_ref:
                deja.add(k)
                ecarts.append(abs(hyp_reps[k]["debut"] - temps_ref[vers_ref[j]]))

    fuites = re.findall(r"0\s?6\s?39\s?98", " ".join(r["texte"] for r in hyp_reps))
    ordre_ok = all(a["debut"] <= b["debut"] for a, b in zip(hyp_reps, hyp_reps[1:]))
    bornes_ok = all(0 <= r["debut"] <= r["fin"] <= donnees["duree_audio_s"] + 1 for r in hyp_reps)
    return {
        "appel": appel, "methode": methode,
        "mots_retrouves_pct": round(100 * len(retrouves) / max(1, len(ref)), 1),
        "wer_pct": round(100 * wer(ref_mots, hyp_mots), 1),
        "mots_bon_locuteur_pct": round(100 * bons_locuteurs / max(1, len(paires)), 1),
        "repliques_bien_attribuees_pct": round(100 * repliques_ok / max(1, len(votes)), 1),
        "repliques": {"scenario": len(reference(appel)), "transcription": len(hyp_reps)},
        "preuves": resultats_preuves,
        "masques": {"scenario": ref_mots.count(MASQUE), "transcription": hyp_mots.count(MASQUE), "fuites": len(fuites)},
        "inaudible": nb_inaudible,
        "mots_inventes_pour_100": round(100 * (len(hyp_mots) - len(paires)) / max(1, len(ref)), 1),
        "horodatage_coherent": ordre_ok and bornes_ok,
        "ecart_debut_median_s": round(float(np.median(ecarts)), 2) if ecarts else None,
        "repliques_a_moins_1s_pct": round(100 * sum(e <= 1 for e in ecarts) / len(ecarts), 1) if ecarts else None,
    }


def tableau(resultats):
    lignes = ["| Appel | Méthode | Mots retrouvés | WER | Mots au bon locuteur | Répliques bien attribuées | Preuves exactes | Preuves au bon locuteur | Masques (scén./transc.) | [inaudible] | Mots inventés /100 | Horodatage | Écart médian | Répliques à moins d'1 s |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in resultats:
        p = r["preuves"]
        exactes = sum(1 for x in p if x["statut"] == "exacte")
        bons = sum(1 for x in p if x["bon_locuteur"])
        lignes.append(f"| {r['appel']} | {r['methode']} | {r['mots_retrouves_pct']} % | {r['wer_pct']} % | "
                      f"{r['mots_bon_locuteur_pct']} % | {r['repliques_bien_attribuees_pct']} % | {exactes}/{len(p)} | {bons}/{len(p)} | "
                      f"{r['masques']['scenario']}/{r['masques']['transcription']}{' FUITE' if r['masques']['fuites'] else ''} | "
                      f"{r['inaudible']} | {r['mots_inventes_pour_100']} | {'cohérent' if r['horodatage_coherent'] else 'INCOHÉRENT'} | "
                      f"{'' if r['ecart_debut_median_s'] is None else str(r['ecart_debut_median_s']) + ' s'} | "
                      f"{'' if r['repliques_a_moins_1s_pct'] is None else str(r['repliques_a_moins_1s_pct']) + ' %'} |")
    return "\n".join(lignes)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--methodes", nargs="+", required=True)
    p.add_argument("--appels", nargs="+", required=True)
    p.add_argument("--nom", default="evaluation")
    a = p.parse_args()
    resultats = [evaluer(f"{int(n):02d}", m) for n in a.appels for m in a.methodes
                 if (TRANSCRIPTIONS / m / f"appel-{int(n):02d}.json").exists()]
    SORTIE.mkdir(parents=True, exist_ok=True)
    (SORTIE / f"{a.nom}.json").write_text(json.dumps(resultats, ensure_ascii=False, indent=2), encoding="utf-8")
    md = tableau(resultats)
    manquantes = [f"- Appel {r['appel']} / {r['methode']} : « {x['preuve']} » ({x['statut']}"
                  f"{', mauvais locuteur' if x['bon_locuteur'] is False else ''})"
                  for r in resultats for x in r["preuves"] if x["statut"] != "exacte" or x["bon_locuteur"] is False]
    (SORTIE / f"{a.nom}.md").write_text(f"# Évaluation de la transcription – {a.nom}\n\n{md}\n\n## Preuves non retrouvées telles quelles\n\n"
                                        + ("\n".join(manquantes) or "Aucune.") + "\n", encoding="utf-8")
    print(md)
    print("\n".join(manquantes) or "Toutes les preuves retrouvées mot pour mot, au bon locuteur.")
