"""Transcription Gemini 3.8 Flash en mode « batch » : les requêtes sont mises en file d'attente chez Google,
ce qui évite les erreurs 503 de surcharge. Même consigne et même format que la transcription directe.

Chaque requête du lot est comptée dans le quota (par prudence) ; l'identifiant du lot est sauvegardé
avant tout traitement (audio/brut/batch-*.json), et les réponses le sont avant d'être interprétées.

Usage :
    python scripts/transcrire_batch.py soumettre 08 09 10        # envoie le lot, affiche son identifiant
    python scripts/transcrire_batch.py etat batches/xxxx          # état du lot
    python scripts/transcrire_batch.py recuperer batches/xxxx     # écrit les transcriptions si le lot est terminé
"""
import base64
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from compteur import Compteur  # noqa: E402
from effet_telephone import lire_wav  # noqa: E402
from transcrire import API, APPELS, BRUT, CONSIGNE, SCHEMA, ecrire, requete  # noqa: E402

MODELE = "gemini-3.8-flash"


def soumettre(appels, cle):
    requetes = []
    for appel in appels:
        audio = base64.b64encode((APPELS / f"appel-{appel}.wav").read_bytes()).decode()
        requetes.append({"request": {
            "contents": [{"parts": [{"inlineData": {"mimeType": "audio/wav", "data": audio}}, {"text": CONSIGNE}]}],
            "generationConfig": {"responseMimeType": "application/json", "responseSchema": SCHEMA},
        }, "metadata": {"key": f"appel-{appel}"}})
    compteur = Compteur()
    for _ in appels:
        compteur.reserver(MODELE)
    corps = {"batch": {"display_name": f"calibre-transcription-{'-'.join(appels)}",
                       "input_config": {"requests": {"requests": requetes}}}}
    _, octets = requete(f"{API}/v1beta/models/{MODELE}:batchGenerateContent", corps, cle)
    lot = json.loads(octets)
    nom = lot.get("name") or lot.get("metadata", {}).get("name")
    BRUT.mkdir(parents=True, exist_ok=True)
    (BRUT / f"batch-{nom.split('/')[-1]}.json").write_text(
        json.dumps({"nom": nom, "appels": appels, "date": datetime.now().isoformat(timespec="seconds"), "reponse": lot},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    return nom


def etat(nom, cle):
    _, octets = requete(f"{API}/v1beta/{nom}", cle=cle, methode="GET")
    return json.loads(octets)


def recuperer(nom, cle):
    lot = etat(nom, cle)
    (BRUT / f"batch-{nom.split('/')[-1]}.resultat.json").write_text(json.dumps(lot, ensure_ascii=False), encoding="utf-8")
    statut = lot.get("metadata", {}).get("state") or lot.get("state")
    if not lot.get("done") and "SUCCEEDED" not in str(statut):
        return statut, []
    reponses = (lot.get("response") or lot.get("metadata", {}).get("output") or {})
    reponses = reponses.get("inlinedResponses", {}).get("inlinedResponses", []) or reponses.get("inlinedResponses", [])
    ecrits = []
    for r in reponses:
        appel = r.get("metadata", {}).get("key", "").replace("appel-", "")
        if "error" in r or "response" not in r:
            print(f"appel-{appel} : erreur dans le lot : {json.dumps(r.get('error'), ensure_ascii=False)[:300]}")
            continue
        texte = "".join(p.get("text", "") for p in r["response"]["candidates"][0]["content"]["parts"] if not p.get("thought"))
        signal, taux = lire_wav(APPELS / f"appel-{appel}.wav")
        ecrire(appel, MODELE, json.loads(texte)["repliques"], len(signal) / taux, r["response"].get("usageMetadata"))
        ecrits.append(appel)
    return statut, ecrits


if __name__ == "__main__":
    cle = os.environ.get("GEMINI_API_KEY") or sys.exit("Variable d'environnement GEMINI_API_KEY absente.")
    action, args = sys.argv[1], sys.argv[2:]
    if action == "soumettre":
        print(soumettre([f"{int(n):02d}" for n in args], cle))
    elif action == "etat":
        lot = etat(args[0], cle)
        print(lot.get("metadata", {}).get("state") or lot.get("state"), "| terminé :", lot.get("done", False))
    elif action == "recuperer":
        statut, ecrits = recuperer(args[0], cle)
        print(statut, "| transcriptions écrites :", ecrits)
