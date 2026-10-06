"""Variabilité de la notation : compare deux passes du même modèle, sur la même transcription et la même consigne.

Pour chaque appel noté dans les deux passes : items notés de la même façon, et niveau, action, éliminatoires
identiques ou non. Écrit evaluations/notation/<nom>.md.
Usage : python scripts/variabilite_notation.py notations/<passe1> notations/<passe2> --nom variabilite
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def charger(dossier):
    return {f.stem.split("-")[1]: json.loads(f.read_text(encoding="utf-8")) for f in sorted(Path(dossier).glob("appel-*.json"))}


if __name__ == "__main__":
    p1, p2 = charger(sys.argv[1]), charger(sys.argv[2])
    nom = sys.argv[sys.argv.index("--nom") + 1] if "--nom" in sys.argv else "variabilite"
    lignes = ["| Appel | Items identiques | Note (passe 1 / passe 2) | Niveau | Action | Éliminatoires |", "|---|---|---|---|---|---|"]
    total = identiques = niv = act = elim = 0
    communs = sorted(set(p1) & set(p2))
    ok = lambda b: "identique" if b else "différent"  # noqa: E731
    for a in communs:
        i1 = {i["numero"]: i["statut"] for i in p1[a]["reponse_ia"]["items"]}
        i2 = {i["numero"]: i["statut"] for i in p2[a]["reponse_ia"]["items"]}
        same = sum(1 for n in i1 if i1[n] == i2.get(n))
        c1, c2 = p1[a]["calcul"], p2[a]["calcul"]
        total += len(i1); identiques += same
        niv += c1["niveau"] == c2["niveau"]; act += c1["action"] == c2["action"]; elim += c1["eliminatoires"] == c2["eliminatoires"]
        lignes.append(f"| {a} | {same}/{len(i1)} | {c1['note_pct']} % / {c2['note_pct']} % | {ok(c1['niveau'] == c2['niveau'])} ({c1['niveau']} / {c2['niveau']}) | "
                      f"{ok(c1['action'] == c2['action'])} | {ok(c1['eliminatoires'] == c2['eliminatoires'])} ({c1['eliminatoires'] or '–'} / {c2['eliminatoires'] or '–'}) |")
    resume = (f"**{len(communs)} appels notés dans les deux passes : {identiques}/{total} items identiques "
              f"({round(100 * identiques / max(1, total), 1)} %), niveau identique {niv}/{len(communs)}, action {act}/{len(communs)}, "
              f"éliminatoires {elim}/{len(communs)}.**")
    sortie = ROOT / "evaluations" / "notation" / f"{nom}.md"
    sortie.write_text(f"# Variabilité de la notation entre deux passes\n\n{chr(10).join(lignes)}\n\n{resume}\n", encoding="utf-8")
    print("\n".join(lignes)); print(); print(resume)
