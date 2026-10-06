"""Résultat officiel d'un appel noté en deux passes.

- Éliminatoires : un éliminatoire est retenu dès qu'une des deux passes le trouve (avec la citation de cette passe).
- Items, preuves, mises en garde, remarques et coaching : ceux de la passe 1 ; la passe 2 sert aux éliminatoires
  et à mesurer la variabilité.
La note, le niveau, les alertes et l'action sont recalculés par le code (scripts/noter.py, calculer).

Usage : python scripts/combiner_passes.py notations/<passe1> notations/<passe2> notations/<officiel>
"""
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import noter  # noqa: E402

if __name__ == "__main__":
    p1, p2, sortie = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    sortie.mkdir(parents=True, exist_ok=True)
    for f1 in sorted(p1.glob("appel-*.json")):
        d1 = json.loads(f1.read_text(encoding="utf-8"))
        f2 = p2 / f1.name
        d2 = json.loads(f2.read_text(encoding="utf-8")) if f2.exists() else None
        appel = d1["appel"]
        noter.SOURCE = d1.get("source_transcription", "hybride")
        reponse = copy.deepcopy(d1["reponse_ia"])
        deja = {e["numero"] for e in reponse["eliminatoires"]}
        ajoutes = []
        for e in (d2["reponse_ia"]["eliminatoires"] if d2 else []):
            if e["numero"] not in deja:
                reponse["eliminatoires"].append(dict(e, trouve_par="passe 2"))
                deja.add(e["numero"])
                ajoutes.append(e["numero"])
        type_appel, grille = noter.fiche(appel)
        calcul = noter.calculer(reponse, grille, noter.transcription(appel))
        donnees = dict(d1, reponse_ia=reponse, calcul=calcul,
                       combinaison={"passe1": str(f1), "passe2": str(f2) if d2 else None,
                                    "eliminatoires_ajoutes_par_passe2": ajoutes})
        (sortie / f1.name).write_text(json.dumps(donnees, ensure_ascii=False, indent=2), encoding="utf-8")
        (sortie / f1.with_suffix(".md").name).write_text(noter.rapport(appel, d1["modele"], type_appel, grille, reponse, calcul), encoding="utf-8")
        print(f"appel-{appel} : {calcul['note_pct']} % · {calcul['niveau']} · {calcul['action']}"
              f"{' · éliminatoires ajoutés par la passe 2 : ' + str(ajoutes) if ajoutes else ''}")
