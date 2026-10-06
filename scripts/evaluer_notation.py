"""Calibration : compare la notation de l'IA à la notation de référence du qualiticien, entièrement par code.

Par appel : accord item par item (oui / non / non applicable), note, niveau, action, éliminatoires,
mises en garde, et preuves de référence reprises par l'IA. Puis un résumé global.
Usage : python scripts/evaluer_notation.py --modele gemini-3.8-flash --appels 01 02 03 04 05 --nom pilote
"""
import argparse
import difflib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from evaluer_transcription import jetons_preuve as jetons, preuves  # noqa: E402  (nombres et « € » normalisés)

ROOT = Path(__file__).resolve().parent.parent
NOTATION_REF = ROOT / "cadrage" / "calibre-notation-reference.md"
NOTATIONS = ROOT / "notations"
SORTIE = ROOT / "evaluations" / "notation"
CODES = {"O": "oui", "N": "non", "–": "na"}


def reference():
    """Tableaux de la notation de référence : items, note, niveau, alertes et action, par appel."""
    texte = NOTATION_REF.read_text(encoding="utf-8")
    ref = {}
    for ligne in texte.splitlines():
        m = re.match(r"^\| S(\d+) [^|]+\|(.+)\|$", ligne)
        if not m:
            continue
        cellules = [c.strip() for c in m.group(2).split("|")]
        nb_items = 16 if len(cellules) == 20 else 14
        items = {i + 1: CODES[c] for i, c in enumerate(cellules[:nb_items])}
        note = int(re.search(r"\d+", cellules[nb_items + 1]).group())
        niveau = cellules[nb_items + 2].replace("*", "").strip()
        alertes = cellules[nb_items + 3]
        elim = set()
        if "souscription sans accord" in alertes:
            elim.add(3)
        if re.search(r"mensonge|fausse condition|faux délai", alertes):
            elim.add(2)
        if "données bancaires" in alertes:
            elim.add(1)
        mises = set()
        for cle, mot in (("resiliation_retardee", "résiliation retardée"), ("resiliation_refusee", "résiliation refusée"),
                         ("panne_ignoree", "panne ignorée")):
            if mot in alertes:
                mises.add(cle)
        if niveau == "Insuffisant":
            mises.add("insuffisant")
        action = next(a for a in ("Avertissement", "Mise en garde", "Valorisation", "Rien à signaler", "Coaching ciblé") if a in alertes)
        ref[f"{int(m.group(1)):02d}"] = {"items": items, "note_pct": note, "niveau": niveau, "eliminatoires": elim,
                                         "mises_en_garde": mises, "action": action}
    return ref


def citee(preuve, citations):
    """La preuve de référence est-elle reprise dans au moins une citation de l'IA ?"""
    pj = jetons(preuve)
    for c in citations:
        cj = jetons(c)
        if any(cj[k:k + len(pj)] == pj for k in range(len(cj) - len(pj) + 1)):
            return True
        if len(cj) >= len(pj) * 0.6 and difflib.SequenceMatcher(None, pj, cj).ratio() >= 0.85:
            return True
    return False


def evaluer(appel, modele, ref):
    ia = json.loads((NOTATIONS / modele / f"appel-{appel}.json").read_text(encoding="utf-8"))
    r, rep, calc = ref[appel], ia["reponse_ia"], ia["calcul"]
    items_ia = {i["numero"]: i["statut"] for i in rep["items"]}
    desaccords = [{"item": n, "reference": v, "ia": items_ia.get(n)} for n, v in r["items"].items() if items_ia.get(n) != v]
    citations = ([p["citation"] for i in rep["items"] for p in i["preuves"]] + [e["citation"] for e in rep["eliminatoires"]]
                 + [f["citation"] for f in rep["fautes_mise_en_garde"]])
    pr = preuves(appel)
    # Une mise en garde absorbée par un éliminatoire ne compte pas (règle 8) : on ne compare les mises en garde
    # que si aucun des deux côtés ne conclut à un éliminatoire.
    comparer_mises = not r["eliminatoires"] and not calc["eliminatoires"]
    return {
        "appel": appel, "modele": modele,
        "items_accord": f"{len(r['items']) - len(desaccords)}/{len(r['items'])}",
        "items_accord_pct": round(100 * (len(r["items"]) - len(desaccords)) / len(r["items"]), 1),
        "desaccords": desaccords,
        "note": {"reference": r["note_pct"], "ia": calc["note_pct"]},
        "niveau": {"reference": r["niveau"], "ia": calc["niveau"], "accord": r["niveau"] == calc["niveau"]},
        "action": {"reference": r["action"], "ia": calc["action"], "accord": r["action"] == calc["action"]},
        "eliminatoires": {"reference": sorted(r["eliminatoires"]), "ia": calc["eliminatoires"],
                          "accord": sorted(r["eliminatoires"]) == calc["eliminatoires"]},
        "mises_en_garde": {"reference": sorted(r["mises_en_garde"]), "ia": calc["mises_en_garde"],
                           "accord": (sorted(r["mises_en_garde"]) == calc["mises_en_garde"]) if comparer_mises else None},
        "preuves_reprises": f"{sum(citee(p, citations) for p in pr)}/{len(pr)}",
        "preuves_manquantes": [p for p in pr if not citee(p, citations)],
        "citations_introuvables": sum(1 for a in calc["anomalies"] if a.startswith("citation introuvable")),
        "anomalies": calc["anomalies"],
    }


def tableau(resultats):
    l = ["| Appel | Items en accord | Note (réf. / IA) | Niveau (réf. / IA) | Action (réf. / IA) | Éliminatoires (réf. / IA) | Mises en garde | Preuves reprises | Citations introuvables |",
         "|---|---|---|---|---|---|---|---|---|"]
    ok = lambda b: "✓" if b else ("–" if b is None else "✗")  # noqa: E731
    for r in resultats:
        l.append(f"| {r['appel']} | {r['items_accord']} | {r['note']['reference']} % / {r['note']['ia']} % | "
                 f"{r['niveau']['reference']} / {r['niveau']['ia']} {ok(r['niveau']['accord'])} | "
                 f"{r['action']['reference']} / {r['action']['ia']} {ok(r['action']['accord'])} | "
                 f"{r['eliminatoires']['reference'] or '–'} / {r['eliminatoires']['ia'] or '–'} {ok(r['eliminatoires']['accord'])} | "
                 f"{ok(r['mises_en_garde']['accord'])} | {r['preuves_reprises']} | {r['citations_introuvables']} |")
    items = sum(int(r["items_accord"].split("/")[0]) for r in resultats)
    total = sum(int(r["items_accord"].split("/")[1]) for r in resultats)
    l += ["", f"**Global : {items}/{total} items en accord ({round(100 * items / max(1, total), 1)} %), "
              f"niveau {sum(r['niveau']['accord'] for r in resultats)}/{len(resultats)}, "
              f"action {sum(r['action']['accord'] for r in resultats)}/{len(resultats)}, "
              f"éliminatoires {sum(r['eliminatoires']['accord'] for r in resultats)}/{len(resultats)}.**"]
    for r in resultats:
        for d in r["desaccords"]:
            l.append(f"- Appel {r['appel']}, item {d['item']} : référence {d['reference']}, IA {d['ia']}")
        for p in r["preuves_manquantes"]:
            l.append(f"- Appel {r['appel']} : preuve de référence non reprise : « {p} »")
    return "\n".join(l)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--modele", default="gemini-3.8-flash")
    p.add_argument("--appels", nargs="+", required=True)
    p.add_argument("--nom", default="calibration")
    a = p.parse_args()
    ref = reference()
    resultats = [evaluer(f"{int(n):02d}", a.modele, ref) for n in a.appels]
    SORTIE.mkdir(parents=True, exist_ok=True)
    (SORTIE / f"{a.nom}.json").write_text(json.dumps(resultats, ensure_ascii=False, indent=2), encoding="utf-8")
    md = tableau(resultats)
    (SORTIE / f"{a.nom}.md").write_text(f"# Calibration de la notation – {a.nom} ({a.modele})\n\n{md}\n", encoding="utf-8")
    print(md)
