"""Compteur local des requêtes Gemini, pour rester dans les limites gratuites.

Chaque requête est enregistrée AVANT son envoi : une requête en échec compte aussi.
Le quota quotidien suit la remise à zéro de Google : minuit heure du Pacifique (9 h à Paris).
"""
import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
FICHIER = ROOT / "audio" / ".compteur-requetes.json"
PACIFIQUE = ZoneInfo("America/Los_Angeles")

# (requêtes par jour, requêtes par minute) de l'offre gratuite, par modèle
LIMITES = {
    "gemini-3.8-flash-tts": (10, 3),
    "gemini-3.8-flash-lite-tts": (10, 3),
    "gemini-3.1-flash-tts-preview": (10, 3),
    "gemini-2.5-flash-preview-tts": (10, 3),
    "gemini-3.8-flash": (20, 5),
    "gemini-3.5-transcribe": (30, 3),
    "gemini-3.5-flash-lite": (40, 10),  # plafond quotidien non relevé : valeur prudente (15 par minute selon AI Studio)
    "gemma-4-26b-a4b-it": (100, 10),  # plafond quotidien non relevé : valeur prudente (30 par minute selon AI Studio)
}


class Compteur:
    def __init__(self, chemin=FICHIER):
        self.chemin = chemin
        self.historique = json.loads(chemin.read_text(encoding="utf-8")) if chemin.exists() else {}

    def _du_jour(self, modele):
        """Requêtes envoyées depuis la dernière remise à zéro de Google."""
        aujourdhui = datetime.now(PACIFIQUE).date()
        return [t for t in self.historique.get(modele, []) if datetime.fromtimestamp(t, PACIFIQUE).date() == aujourdhui]

    def restantes(self, modele):
        return LIMITES[modele][0] - len(self._du_jour(modele))

    def reserver(self, modele):
        par_jour, par_minute = LIMITES[modele]
        if len(self._du_jour(modele)) >= par_jour:
            demain = datetime.now(PACIFIQUE).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            sys.exit(f"Refusé : {par_jour} requêtes déjà envoyées aujourd'hui pour {modele}. "
                     f"Remise à zéro le {demain.astimezone().strftime('%d/%m à %H:%M')}.")
        minute = [t for t in self.historique.get(modele, []) if time.time() - t < 60]
        if len(minute) >= par_minute:
            attente = 60 - (time.time() - min(minute)) + 1
            print(f"Limite de {par_minute} requêtes par minute atteinte pour {modele} : attente de {attente:.0f} s.", flush=True)
            time.sleep(attente)
        self.historique.setdefault(modele, []).append(time.time())
        # Deux jours d'historique suffisent pour les deux limites
        self.historique[modele] = [t for t in self.historique[modele] if time.time() - t < 2 * 86400]
        self.chemin.parent.mkdir(parents=True, exist_ok=True)
        self.chemin.write_text(json.dumps(self.historique, indent=2), encoding="utf-8")

    def afficher(self):
        for m, (par_jour, _) in LIMITES.items():
            print(f"{m:32s} {self.restantes(m):2d} / {par_jour} requêtes restantes aujourd'hui (heure du Pacifique)")
