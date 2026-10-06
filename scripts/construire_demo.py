"""Construit les données de la démo (ui/donnees.js) : aucune requête, tout est déjà calculé.

Pour chaque appel : fiche, forme d'onde, transcription officielle horodatée (hybride locale + lexique),
notation officielle (deux passes combinées), notation de référence du qualiticien, alertes datées.
Plus un historique FICTIF de mises en garde pour la vue d'équipe (règle des 3 mises en garde en 30 jours).
Usage : python scripts/construire_demo.py
"""
import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from effet_telephone import lire_wav  # noqa: E402
from evaluer_notation import reference  # noqa: E402
from noter import fiche, grilles  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
NOTATION = ROOT / "notations" / "gemma-4-26b-a4b-it-reduit-hybride-locale-lexique-officielle"
TRANSCRIPTION = ROOT / "transcriptions" / "hybride-locale-lexique"
SORTIE = ROOT / "ui" / "donnees.js"
LIBELLES_MG = {"resiliation_retardee": "Résiliation retardée", "resiliation_refusee": "Résiliation refusée",
               "panne_ignoree": "Panne ignorée en télévente", "insuffisant": "Appel insuffisant (moins de 60 %)"}
ELIMINATOIRES = {1: "Données bancaires ou sensibles demandées", 2: "Mensonge ou fausse promesse qui engage l'entreprise",
                 3: "Souscription sans accord clair du client"}


def propre(texte):
    """Affichage seulement : recolle les apostrophes, tirets et décimales séparés par la transcription locale
    (« j 'ai » -> « j'ai », « Calmez -vous » -> « Calmez-vous », « 6 ,99 » -> « 6,99 ») ; aucun mot n'est changé."""
    texte = re.sub(r"\s+'", "'", texte or "")
    texte = re.sub(r"(\w)\s+-(?=[A-Za-zÀ-ÿ])", r"\1-", texte)
    return re.sub(r"(\d)\s+,(\d)", r"\1,\2", texte)


def libelle(texte):
    """« **Accueil** : présentation… *(si applicable)* » -> (« Accueil », « présentation… »)."""
    texte = re.sub(r"\s*\*\(.*?\)\*", "", texte)
    m = re.match(r"\*\*(.+?)\*\*\s*:?\s*(.*)", texte)
    return (m.group(1), m.group(2)) if m else (texte, "")


def forme_onde(appel, points=700):
    signal, _ = lire_wav(ROOT / "audio" / "appels" / f"appel-{appel}.wav")
    blocs = np.array_split(np.abs(signal), points)
    pics = np.array([b.max() if len(b) else 0 for b in blocs])
    return [round(float(v), 3) for v in pics / (pics.max() + 1e-9)]


def alertes(items_grille, reponse, calcul):
    """Alertes datées : réussite (item oui), faute (item non), mise en garde, éliminatoire."""
    liste = []
    for i in reponse["items"]:
        preuves = [p for p in i["preuves"] if p.get("debut_verifie_s") is not None]
        if i["statut"] == "na" or not preuves:
            continue
        nom, _ = libelle(items_grille[i["numero"]]["libelle"])
        liste.append({"t": preuves[0]["debut_verifie_s"], "type": "reussite" if i["statut"] == "oui" else "faute",
                      "titre": f"Item {i['numero']} · {nom}", "texte": propre(preuves[0]["citation"])})
    for f in reponse["fautes_mise_en_garde"]:
        if f.get("debut_verifie_s") is not None and f["type"] in calcul["mises_en_garde"]:
            liste.append({"t": f["debut_verifie_s"], "type": "mise_en_garde",
                          "titre": f"Mise en garde · {LIBELLES_MG.get(f['type'], f['type'])}", "texte": propre(f["citation"])})
    for e in reponse["eliminatoires"]:
        if e.get("debut_verifie_s") is not None:
            liste.append({"t": e["debut_verifie_s"], "type": "eliminatoire",
                          "titre": f"Éliminatoire {e['numero']} · {ELIMINATOIRES.get(e['numero'], '')}", "texte": propre(e["citation"])})
    return sorted(liste, key=lambda a: a["t"])


def historique_fictif(appels):
    """Mises en garde FICTIVES antérieures, pour illustrer la règle des 3 mises en garde en 30 jours."""
    par_matricule = {a["fiche"]["matricule"]: a for a in appels}
    def avant(matricule, jours):
        return (date.fromisoformat(par_matricule[matricule]["fiche"]["date"]) - timedelta(days=jours)).isoformat()
    return [
        # Appel 4 : deux mises en garde récentes + celle de l'appel = 3 en 30 jours -> avertissement proposé
        {"matricule": "KAL-21349", "date": avant("KAL-21349", 9), "motif": "Appel insuffisant (moins de 60 %)"},
        {"matricule": "KAL-21349", "date": avant("KAL-21349", 21), "motif": "Appel insuffisant (moins de 60 %)"},
        # Appel 5 : une mise en garde récente + celle de l'appel = 2 en 30 jours -> à surveiller
        {"matricule": "KAL-21702", "date": avant("KAL-21702", 14), "motif": "Résiliation retardée"},
        # Appel 11 : deux mises en garde anciennes (plus de 30 jours) -> ne comptent pas
        {"matricule": "KAL-31507", "date": avant("KAL-31507", 45), "motif": "Panne ignorée en télévente"},
        {"matricule": "KAL-31507", "date": avant("KAL-31507", 62), "motif": "Appel insuffisant (moins de 60 %)"},
        # Appel 10 : une mise en garde récente + celle de l'appel = 2 en 30 jours
        {"matricule": "KAL-31135", "date": avant("KAL-31135", 6), "motif": "Appel insuffisant (moins de 60 %)"},
    ]


def main():
    ref = reference()
    toutes_grilles = grilles()
    appels = []
    for n in range(1, 14):
        appel = f"{n:02d}"
        sc = (ROOT / "scenarios" / f"appel-{appel}.md").read_text(encoding="utf-8")
        champ = lambda c: re.search(rf"^\s*{c}: (.+?)(?:\s+#.*)?$", sc, flags=re.M).group(1).strip().strip('"')  # noqa: E731
        titre = re.search(r'titre_interne: "Scénario \d+ – (.+?)"', sc).group(1)
        type_appel, grille = fiche(appel)
        cle_grille = "Grille 1" if grille.startswith("Grille 1") else "Grille 2"
        items_grille = toutes_grilles[cle_grille]
        notation = json.loads((NOTATION / f"appel-{appel}.json").read_text(encoding="utf-8"))
        rep, calcul = notation["reponse_ia"], notation["calcul"]
        transcription = json.loads((TRANSCRIPTION / f"appel-{appel}.json").read_text(encoding="utf-8"))
        r = ref[appel]
        appels.append({
            "id": appel, "titre": titre,
            "fiche": {"matricule": champ("matricule"), "date": champ("date"), "heure": champ("heure"),
                      "type": type_appel, "grille": grille},
            "audio": f"../audio/appels/appel-{appel}.mp3",
            "duree": transcription["duree_audio_s"],
            "onde": forme_onde(appel),
            "repliques": [{"l": x["locuteur"], "d": x["debut"], "f": x["fin"], "t": propre(x["texte"])} for x in transcription["repliques"]],
            "items": [{"n": num, "nom": libelle(it["libelle"])[0], "detail": libelle(it["libelle"])[1]} for num, it in items_grille.items()],
            "ia": {"items": {str(i["numero"]): {"s": i["statut"], "j": i["justification"],
                                                "p": [{"c": propre(p["citation"]), "t": p.get("debut_verifie_s"), "v": p.get("verification")} for p in i["preuves"]]}
                             for i in rep["items"]},
                   "eliminatoires": [{"n": e["numero"], "nom": ELIMINATOIRES.get(e["numero"], ""), "motif": e["motif"],
                                      "c": propre(e["citation"]), "t": e.get("debut_verifie_s")} for e in rep["eliminatoires"]],
                   "mises_en_garde": [LIBELLES_MG.get(m, m) for m in calcul["mises_en_garde"]],
                   "fautes": [{"type": LIBELLES_MG.get(f["type"], f["type"]), "c": propre(f["citation"]), "t": f.get("debut_verifie_s")}
                              for f in rep["fautes_mise_en_garde"]],
                   "remarques": [{"regle": x["regle"], "ecart": x["ecart"], "c": propre(x["citation"]), "t": x.get("debut_verifie_s")}
                                 for x in rep["remarques_conformite"]],
                   "coaching": rep["coaching"], "calcul": calcul},
            "reference": {"items": {str(k): v for k, v in r["items"].items()}, "note": r["note_pct"], "niveau": r["niveau"],
                          "action": r["action"], "eliminatoires": sorted(r["eliminatoires"]),
                          "mises_en_garde": [LIBELLES_MG.get(m, m) for m in sorted(r["mises_en_garde"])]},
            "alertes": alertes(items_grille, rep, calcul),
        })
    donnees = {"appels": appels, "historique_fictif": historique_fictif(appels)}
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    SORTIE.write_text("// Données de démonstration, générées par scripts/construire_demo.py. Entreprise, appels et conseillers fictifs.\n"
                      "window.CALIBRE = " + json.dumps(donnees, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")
    print(f"{SORTIE.relative_to(ROOT)} : {len(appels)} appels, {SORTIE.stat().st_size / 1e6:.2f} Mo,"
          f" {sum(len(a['alertes']) for a in appels)} alertes")


if __name__ == "__main__":
    main()
