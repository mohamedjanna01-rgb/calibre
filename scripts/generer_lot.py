"""Génère plusieurs appels l'un après l'autre, en contrôlant chacun avant de passer au suivant.

- Un seul modèle par appel complet : la répartition (audio/production/repartition.yaml) est mise à jour
  avant chaque génération.
- Arrêt immédiat si une requête échoue ou est refusée (par Google ou par le compteur).
- Appel incomplet (passage absent, réplique d'au moins trois mots introuvable, moins de 90 % des mots retrouvés) :
  avec --repli, cet appel et les suivants passent sur le modèle de secours ; sinon, arrêt.

Usage :
    python scripts/generer_lot.py --appels 02 04 05 --modele gemini-2.5-flash-preview-tts --repli gemini-3.1-flash-tts-preview
"""
import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPARTITION = ROOT / "audio" / "production" / "repartition.yaml"
APPELS = ROOT / "audio" / "appels"
SEUIL = 90.0


def attribuer(appel, modele):
    texte = REPARTITION.read_text(encoding="utf-8")
    texte = re.sub(rf"^  appel-{appel}:.*$", f"  appel-{appel}: {modele}", texte, flags=re.M)
    REPARTITION.write_text(texte, encoding="utf-8")


def incomplet(appel):
    c = json.loads((APPELS / f"appel-{appel}.json").read_text(encoding="utf-8"))["controle"]
    raisons = []
    if c["mots_du_script_retrouves_pct"] < SEUIL:
        raisons.append(f"{c['mots_du_script_retrouves_pct']} % des mots retrouvés")
    # Une réplique très courte (« Bonjour. ») peut échapper à la transcription locale : seules
    # les répliques d'au moins trois mots introuvables comptent comme manquantes.
    longues = c.get("repliques_longues_non_retrouvees", c["repliques_non_retrouvees"])
    if longues:
        raisons.append(f"répliques introuvables {longues}")
    if c["passages_absents"]:
        raisons.append(f"passages absents dans les répliques {[p['replique'] for p in c['passages_absents']]}")
    return raisons


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--appels", nargs="+", required=True)
    p.add_argument("--modele", required=True)
    p.add_argument("--repli", help="modèle de secours si un appel est incomplet")
    a = p.parse_args()

    modele = a.modele
    file = [f"{int(n):02d}" for n in a.appels]
    while file:
        appel = file[0]
        attribuer(appel, modele)
        print(f"=== appel {appel} ({modele}) {datetime.now():%H:%M:%S}", flush=True)
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "generer_audio.py"), "--appel", appel, "--modele", modele])
        if r.returncode != 0:
            print(f"ARRÊT : la requête de l'appel {appel} a échoué ou a été refusée.", flush=True)
            sys.exit(1)
        raisons = incomplet(appel)
        if not raisons:
            print(f"appel {appel} complet", flush=True)
            file.pop(0)
            continue
        print(f"INCOMPLET appel {appel} ({modele}) : {' ; '.join(raisons)}", flush=True)
        if a.repli and modele != a.repli:
            modele = a.repli
            print(f"BASCULE : appel {appel} et suivants sur {modele}", flush=True)
            continue
        print("ARRÊT : appel incomplet, pas d'autre modèle de secours.", flush=True)
        sys.exit(2)
    print(f"=== FIN {datetime.now():%H:%M:%S}", flush=True)


if __name__ == "__main__":
    main()
