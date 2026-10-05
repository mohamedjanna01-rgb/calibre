"""Transcription d'un appel en répliques horodatées, séparées entre conseiller et client.

Trois méthodes, comparées sur les mêmes enregistrements (audio/appels/appel-XX.wav) :
  gemini-3.8-flash      modèle généraliste : consigne + réponse JSON structurée (1 requête par appel)
  gemini-3.5-flash-lite même consigne et même format, modèle plus léger et moins sollicité
  gemini-3.5-transcribe modèle spécialisé : séparation des voix et horodatage mot par mot (1 requête par appel)
  whisper-small         transcription locale, séparation des voix par la hauteur et le timbre (aucune requête)
  whisper-medium        idem avec le modèle local « medium », plus précis et plus lent

Les modèles ne reçoivent que l'audio et une consigne générique : jamais les scénarios ni les scripts de production.
Garde-fous : compteur de requêtes, réponse sauvegardée avant tout traitement, arrêt au premier refus.

Sortie : transcriptions/<méthode>/appel-XX.json et appel-XX.md
Usage :
    python scripts/transcrire.py --methode whisper-small --appels 03 10
    python scripts/transcrire.py --methode gemini-3.8-flash --appels 03 10 [--simulation]
"""
import argparse
import base64
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

import numpy as np
from scipy.cluster.vq import kmeans2
from scipy.fft import dct
from scipy.signal import resample_poly

sys.path.insert(0, str(Path(__file__).parent))
from compteur import Compteur  # noqa: E402
from effet_telephone import lire_wav  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
APPELS = ROOT / "audio" / "appels"
SORTIE = ROOT / "transcriptions"
BRUT = ROOT / "audio" / "brut"
API = "https://generativelanguage.googleapis.com"
METHODES = ("gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-3.5-transcribe", "whisper-small", "whisper-medium")
INAUDIBLE, MASQUE = "[inaudible]", "[numéro masqué]"

CONSIGNE = f"""Transcris mot pour mot cet enregistrement d'appel téléphonique, en français, entre un conseiller de l'opérateur Kalyo Télécom et un client.

Règles :
- Transcription strictement fidèle : garde les hésitations (euh), les répétitions, les faux départs et les phrases inachevées. Ne corrige rien, ne reformule rien, n'ajoute rien.
- Une entrée par prise de parole, dans l'ordre. Le locuteur est « conseiller » (la personne qui représente Kalyo Télécom) ou « client ».
- Début et fin de chaque prise de parole, en secondes depuis le début de l'enregistrement.
- Un passage incompréhensible s'écrit {INAUDIBLE}. Ne devine jamais un mot que tu n'entends pas clairement.
- Un bip qui masque une information s'écrit {MASQUE}.
- Les nombres s'écrivent en chiffres."""

SCHEMA = {
    "type": "OBJECT",
    "properties": {"repliques": {"type": "ARRAY", "items": {
        "type": "OBJECT",
        "properties": {
            "locuteur": {"type": "STRING", "enum": ["conseiller", "client"]},
            "debut": {"type": "NUMBER"},
            "fin": {"type": "NUMBER"},
            "texte": {"type": "STRING"},
        },
        "required": ["locuteur", "debut", "fin", "texte"],
    }}},
    "required": ["repliques"],
}


# --- Outils communs ------------------------------------------------------------------------

def requete(url, corps=None, cle=None, entetes=None, donnees=None, methode="POST", modele=None):
    """Envoie une requête. Pour une requête à un modèle (modele renseigné) : en cas d'erreur 503
    (surcharge passagère de Google), une seule nouvelle tentative après une minute, comptée dans le quota.
    Tout autre refus, dont un refus lié au quota (429), arrête immédiatement."""
    entetes = dict(entetes or {})
    if cle:
        entetes["x-goog-api-key"] = cle
    if corps is not None:
        donnees = json.dumps(corps).encode("utf-8")
        entetes["Content-Type"] = "application/json"
    for tentative in (1, 2):
        req = urllib.request.Request(url, data=donnees, method=methode, headers=entetes)
        try:
            with urllib.request.urlopen(req, timeout=900) as rep:
                return rep.headers, rep.read()
        except urllib.error.HTTPError as e:
            message = e.read().decode("utf-8", "replace")[:800]
            if e.code == 503 and modele and tentative == 1:
                print(f"Erreur 503 (surcharge de Google) : nouvelle tentative dans 60 s, comptée dans le quota.", flush=True)
                time.sleep(60)
                Compteur().reserver(modele)
                continue
            sys.exit(f"ARRÊT – échec HTTP {e.code} (requête comptée, pas de nouvel essai) : {message}")


def sauvegarder_reponse(appel, methode, reponse):
    f = BRUT / f"transcription-{appel}.{methode}.reponse.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(reponse, ensure_ascii=False), encoding="utf-8")
    return f


def normaliser(mot):
    return re.sub(r"[^a-z]", "", "".join(c for c in unicodedata.normalize("NFD", mot.lower()) if not unicodedata.combining(c)))


def roles(repliques, type_appel):
    """Rôles des étiquettes de voix (spk_1, spk_2…), décidés par code :
    le conseiller est la voix qui dit « Télécom » (« Kalyo Télécom ») en premier.
    À défaut : appel entrant = le conseiller parle en premier ; télévente = le client décroche en premier."""
    for r in repliques:
        if any(normaliser(m) in ("telecom", "kalyo") for m in r["texte"].split()):
            conseiller = r["locuteur"]
            break
    else:
        premier = repliques[0]["locuteur"]
        autres = [r["locuteur"] for r in repliques if r["locuteur"] != premier]
        conseiller = premier if type_appel.startswith("Appel entrant") or not autres else autres[0]
    return {r["locuteur"]: ("conseiller" if r["locuteur"] == conseiller else "client") for r in repliques}


def type_appel(appel):
    sc = (ROOT / "scenarios" / f"appel-{appel}.md").read_text(encoding="utf-8")
    return re.search(r"^\s*type: (.+)$", sc, flags=re.M).group(1).strip()  # fiche d'identité uniquement


# --- A. Gemini 3.8 Flash ------------------------------------------------------------------------

def gemini_flash(appel, wav, cle, simulation, modele="gemini-3.8-flash"):
    corps = {
        "contents": [{"parts": [
            {"inlineData": {"mimeType": "audio/wav", "data": "<audio>" if simulation else base64.b64encode(wav.read_bytes()).decode()}},
            {"text": CONSIGNE},
        ]}],
        "generationConfig": {"responseMimeType": "application/json", "responseSchema": SCHEMA},
    }
    if simulation:
        return corps
    Compteur().reserver(modele)
    _, octets = requete(f"{API}/v1beta/models/{modele}:generateContent", corps, cle, modele=modele)
    reponse = json.loads(octets)
    sauvegarde = sauvegarder_reponse(appel, modele, reponse)
    texte = "".join(p.get("text", "") for p in reponse["candidates"][0]["content"]["parts"] if not p.get("thought"))
    repliques = json.loads(texte)["repliques"]
    return repliques, sauvegarde, reponse.get("usageMetadata")


# --- B. Gemini 3.5 Transcribe ----------------------------------------------------------------------

def deposer_fichier(wav, cle):
    """Dépôt du fichier audio par l'API Files (ce n'est pas une requête au modèle)."""
    taille = wav.stat().st_size
    entetes, _ = requete(f"{API}/upload/v1beta/files", {"file": {"display_name": wav.stem}}, cle, {
        "X-Goog-Upload-Protocol": "resumable", "X-Goog-Upload-Command": "start",
        "X-Goog-Upload-Header-Content-Length": str(taille), "X-Goog-Upload-Header-Content-Type": "audio/wav"})
    _, octets = requete(entetes["x-goog-upload-url"], None, None, {
        "Content-Length": str(taille), "X-Goog-Upload-Offset": "0", "X-Goog-Upload-Command": "upload, finalize"},
        donnees=wav.read_bytes())
    fichier = json.loads(octets)["file"]
    for _ in range(30):  # attente du traitement du fichier
        if fichier.get("state", "ACTIVE") == "ACTIVE":
            return fichier
        time.sleep(2)
        _, octets = requete(f"{API}/v1beta/{fichier['name']}", cle=cle, methode="GET")
        fichier = json.loads(octets)
    sys.exit(f"ARRÊT – fichier audio jamais prêt : {fichier}")


def secondes(valeur):
    return float(str(valeur).rstrip("s"))


def gemini_transcribe(appel, wav, cle, simulation):
    corps = {
        "model": "gemini-3.5-transcribe",
        "input": [{"type": "audio", "uri": "<uri du fichier déposé>", "mime_type": "audio/wav"}],
        "generation_config": {"transcription_config": {"mode": {
            "type": "verbatim", "diarization_mode": "speaker", "timestamp_granularities": ["word"]}}},
    }
    if simulation:
        return corps
    fichier = deposer_fichier(wav, cle)
    corps["input"][0]["uri"] = fichier["uri"]
    try:
        Compteur().reserver("gemini-3.5-transcribe")
        _, octets = requete(f"{API}/v1beta/interactions", corps, cle, modele="gemini-3.5-transcribe")
    finally:
        requete(f"{API}/v1beta/{fichier['name']}", cle=cle, methode="DELETE")  # le fichier déposé est supprimé
    reponse = json.loads(octets)
    sauvegarde = sauvegarder_reponse(appel, "gemini-3.5-transcribe", reponse)
    mots, pile = [], [reponse]
    while pile:  # annotations « word_info », où qu'elles soient dans la réponse
        x = pile.pop(0)
        if isinstance(x, dict):
            if x.get("type") == "word_info":
                mots.append(x)
            pile.extend(x.values())
        elif isinstance(x, list):
            pile.extend(x)
    if not mots:
        sys.exit(f"ARRÊT – aucune annotation mot par mot dans la réponse (sauvegardée dans {sauvegarde.name}).")
    mots.sort(key=lambda m: secondes(m["start_offset"]))
    # Mots horodatés conservés : le traitement ci-dessous peut être refait sans nouvelle requête
    (SORTIE / "gemini-3.5-transcribe").mkdir(parents=True, exist_ok=True)
    (SORTIE / "gemini-3.5-transcribe" / f"appel-{appel}.mots.json").write_text(
        json.dumps(mots, ensure_ascii=False, indent=1), encoding="utf-8")
    return repliques_depuis_mots(appel, wav, mots), sauvegarde, reponse.get("usage")


def repliques_depuis_mots(appel, wav, mots):
    """Répliques à partir des mots horodatés de Gemini 3.5 Transcribe.
    Le modèle ne signale pas les bips : ils sont repérés dans le son (tonalité à 1 kHz) et remplacent
    les mots qui tombent dedans par [numéro masqué]."""
    signal, taux = lire_wav(wav)
    for a, b in bips(signal, taux):
        milieu = lambda m: (secondes(m["start_offset"]) + secondes(m["end_offset"])) / 2  # noqa: E731
        dedans = [m for m in mots if a - 0.1 <= milieu(m) <= b + 0.1]
        mots = [m for m in mots if m not in dedans]
        # Le modèle n'écrit souvent rien pendant un bip : le masque est attribué au locuteur qui parlait juste avant
        avant = [m for m in mots if secondes(m["end_offset"]) <= a + 0.1]
        locuteur = dedans[0].get("speaker") if dedans else (avant[-1].get("speaker") if avant else mots[0].get("speaker"))
        mots.append({"text": MASQUE, "speaker": locuteur, "start_offset": f"{a}s", "end_offset": f"{b}s"})
    mots.sort(key=lambda m: secondes(m["start_offset"]))
    repliques = []
    for m in mots:  # une réplique = suite de mots du même locuteur
        if repliques and repliques[-1]["locuteur"] == m.get("speaker"):
            repliques[-1]["texte"] += " " + m["text"]
            repliques[-1]["fin"] = secondes(m["end_offset"])
        else:
            repliques.append({"locuteur": m.get("speaker"), "debut": secondes(m["start_offset"]),
                              "fin": secondes(m["end_offset"]), "texte": m["text"]})
    correspondance = roles(repliques, type_appel(appel))
    for r in repliques:
        r["locuteur"] = correspondance[r["locuteur"]]
    return repliques


# --- C. Transcription locale ----------------------------------------------------------------------

def bips(signal, taux, trame_s=0.02):
    """Zones de bip : tonalité pure à 1 kHz détectée dans le son (pas les positions connues de la production)."""
    n = int(trame_s * taux)
    trames = signal[: len(signal) // n * n].reshape(-1, n)
    t = np.arange(n) / taux
    p1k = np.abs(trames @ np.exp(-2j * np.pi * 1000 * t)) ** 2 / n
    total = np.sum(trames ** 2, axis=1) / 2 + 1e-12
    est_bip = (p1k / total > 0.8) & (np.sqrt(np.mean(trames ** 2, axis=1)) > 0.05)
    zones, debut = [], None
    for i, b in enumerate(np.append(est_bip, False)):
        if b and debut is None:
            debut = i
        elif not b and debut is not None:
            if (i - debut) * trame_s >= 0.3:
                zones.append((debut * trame_s, i * trame_s))
            debut = None
    return zones


def caracteristiques(signal, taux, debut, fin):
    """Timbre (MFCC moyens) et hauteur (fréquence fondamentale médiane) d'un morceau de parole."""
    x = signal[int(debut * taux): int(fin * taux)]
    n, pas = int(0.025 * taux), int(0.01 * taux)
    if len(x) < n:
        x = np.pad(x, (0, n - len(x)))
    trames = np.lib.stride_tricks.sliding_window_view(x, n)[::pas] * np.hamming(n)
    spectre = np.abs(np.fft.rfft(trames, 256)) ** 2
    mel = lambda f: 2595 * np.log10(1 + f / 700)  # noqa: E731
    points = 700 * (10 ** (np.linspace(mel(250), mel(3500), 28) / 2595) - 1)
    bacs = np.floor(128 * points / (taux / 2)).astype(int).clip(0, 128)
    banc = np.zeros((26, 129))
    for i in range(26):
        a, b, c = bacs[i], bacs[i + 1], bacs[i + 2]
        banc[i, a:b] = np.linspace(0, 1, b - a, endpoint=False)
        banc[i, b:c] = np.linspace(1, 0, c - b, endpoint=False)
    mfcc = dct(np.log(spectre @ banc.T + 1e-10), norm="ortho", axis=1)[:, 1:13]
    hauteurs = []
    for tr in trames:
        ac = np.correlate(tr, tr, "full")[n - 1:]
        lo, hi = int(taux / 400), min(int(taux / 70), n - 1)
        if ac[0] > 0 and hi > lo:
            k = lo + np.argmax(ac[lo:hi])
            if ac[k] / ac[0] > 0.45:
                hauteurs.append(taux / k)
    f0 = np.median(hauteurs) if hauteurs else np.nan
    return np.concatenate([mfcc.mean(axis=0), [f0]])


SEUIL_INAUDIBLE = 0.1  # probabilité sous laquelle un mot est remplacé par [inaudible] (0,3 masquait des mots bien entendus)


def mots_whisper(appel, wav, taille):
    """Mots horodatés avec leur probabilité, conservés dans transcriptions/whisper-<taille>/appel-XX.mots.json :
    ils servent aussi de source de temps, et le seuil [inaudible] peut être ajusté sans retranscrire."""
    cache = SORTIE / f"whisper-{taille}" / f"appel-{appel}.mots.json"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    from faster_whisper import WhisperModel
    signal, taux = lire_wav(wav)
    audio = resample_poly(signal, 16000, taux).astype(np.float32)
    modele = WhisperModel(taille, device="cpu", compute_type="int8")
    segments, _ = modele.transcribe(audio, language="fr", word_timestamps=True)
    mots = [{"texte": w.word.strip(), "debut": round(w.start, 2), "fin": round(w.end, 2), "proba": round(w.probability, 3)}
            for s in segments for w in s.words]
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(mots, ensure_ascii=False, indent=1), encoding="utf-8")
    return mots


def mots_nettoyes(appel, wav, taille):
    """Mots locaux horodatés, avec [numéro masqué] sur les bips et [inaudible] à la place des mots peu sûrs."""
    signal, taux = lire_wav(wav)
    mots = mots_whisper(appel, wav, taille)
    # Bips : les mots qui tombent dedans sont remplacés par [numéro masqué]
    for a, b in bips(signal, taux):
        mots = [m for m in mots if not a - 0.1 <= (m["debut"] + m["fin"]) / 2 <= b + 0.1]
        mots.append({"texte": MASQUE, "debut": a, "fin": b, "proba": 1.0})
    mots.sort(key=lambda m: m["debut"])
    # Mots peu sûrs : regroupés en [inaudible], jamais devinés
    propres = []
    for m in mots:
        if m["proba"] < SEUIL_INAUDIBLE:
            if propres and propres[-1]["texte"] == INAUDIBLE:
                propres[-1]["fin"] = m["fin"]
                continue
            m = dict(m, texte=INAUDIBLE)
        propres.append(m)
    return propres


def whisper_local(appel, wav, cle, simulation, taille="small"):
    if simulation:
        return {"methode": f"whisper-{taille}", "requetes": 0}
    signal, taux = lire_wav(wav)
    propres = mots_nettoyes(appel, wav, taille)

    # Morceaux de parole séparés par des pauses, puis regroupés en deux voix
    morceaux = []
    for m in propres:
        if morceaux and m["debut"] - morceaux[-1]["fin"] < 0.25 and m["texte"] != MASQUE:
            morceaux[-1]["mots"].append(m)
            morceaux[-1]["fin"] = m["fin"]
        else:
            morceaux.append({"debut": m["debut"], "fin": m["fin"], "mots": [m]})
    traits = np.array([caracteristiques(signal, taux, c["debut"], c["fin"]) for c in morceaux])
    traits[:, -1] = np.where(np.isnan(traits[:, -1]), np.nanmedian(traits[:, -1]), traits[:, -1])
    traits = (traits - traits.mean(axis=0)) / (traits.std(axis=0) + 1e-9)
    traits[:, -1] *= 3  # la hauteur pèse plus que chaque coefficient de timbre
    meilleur = None
    for graine in range(10):
        centres, etiquettes = kmeans2(traits, 2, seed=graine, minit="++")
        inertie = sum(np.sum((traits[etiquettes == k] - centres[k]) ** 2) for k in (0, 1))
        if meilleur is None or inertie < meilleur[0]:
            meilleur = (inertie, etiquettes)
    repliques = []
    for c, e in zip(morceaux, meilleur[1]):
        texte = " ".join(m["texte"] for m in c["mots"])
        if c["mots"][0]["texte"] == MASQUE and repliques:  # un bip appartient à la réplique en cours
            repliques[-1]["texte"] += " " + texte
            repliques[-1]["fin"] = c["fin"]
        elif repliques and repliques[-1]["locuteur"] == f"spk_{e}":
            repliques[-1]["texte"] += " " + texte
            repliques[-1]["fin"] = c["fin"]
        else:
            repliques.append({"locuteur": f"spk_{e}", "debut": c["debut"], "fin": c["fin"], "texte": texte})
    correspondance = roles(repliques, type_appel(appel))
    for r in repliques:
        r["locuteur"] = correspondance[r["locuteur"]]
    return repliques, None, None


# --- Programme principal ---------------------------------------------------------------------------

def ecrire(appel, methode, repliques, duree, usage):
    dossier = SORTIE / methode
    dossier.mkdir(parents=True, exist_ok=True)
    for i, r in enumerate(repliques, 1):
        r["n"] = i
        r["debut"], r["fin"] = round(float(r["debut"]), 2), round(float(r["fin"]), 2)
        r["texte"] = re.sub(r"\s+", " ", r["texte"]).strip()
    donnees = {"appel": appel, "methode": methode, "date": datetime.now().isoformat(timespec="seconds"),
               "duree_audio_s": round(duree, 1), "usage": usage,
               "repliques": [{k: r[k] for k in ("n", "locuteur", "debut", "fin", "texte")} for r in repliques]}
    (dossier / f"appel-{appel}.json").write_text(json.dumps(donnees, ensure_ascii=False, indent=2), encoding="utf-8")
    lignes = [f"# Appel {appel} – transcription {methode}", ""]
    for r in donnees["repliques"]:
        mm = lambda s: f"{int(s // 60):02d}:{s % 60:04.1f}"  # noqa: E731
        lignes += [f"**[{mm(r['debut'])}] {r['locuteur'].capitalize()} :** {r['texte']}", ""]
    (dossier / f"appel-{appel}.md").write_text("\n".join(lignes), encoding="utf-8")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--methode", choices=METHODES, required=True)
    p.add_argument("--appels", nargs="+", required=True)
    p.add_argument("--simulation", action="store_true", help="affiche la requête sans l'envoyer")
    a = p.parse_args()
    fonction = {"gemini-3.8-flash": gemini_flash,
                "gemini-3.5-flash-lite": lambda *x: gemini_flash(*x, modele="gemini-3.5-flash-lite"),
                "gemini-3.5-transcribe": gemini_transcribe,
                "whisper-small": whisper_local,
                "whisper-medium": lambda *x: whisper_local(*x, taille="medium")}[a.methode]
    cle = os.environ.get("GEMINI_API_KEY")
    if a.methode.startswith("gemini") and not cle and not a.simulation:
        sys.exit("Variable d'environnement GEMINI_API_KEY absente.")
    for n in a.appels:
        appel = f"{int(n):02d}"
        wav = APPELS / f"appel-{appel}.wav"
        if a.simulation:
            print(json.dumps(fonction(appel, wav, cle, True), ensure_ascii=False, indent=2))
            continue
        debut = time.time()
        repliques, sauvegarde, usage = fonction(appel, wav, cle, False)
        signal, taux = lire_wav(wav)
        ecrire(appel, a.methode, repliques, len(signal) / taux, usage)
        if sauvegarde:
            sauvegarde.unlink()  # la transcription est écrite : la réponse brute n'est plus utile
        print(f"appel-{appel} / {a.methode} : {len(repliques)} répliques en {time.time() - debut:.0f} s", flush=True)


if __name__ == "__main__":
    main()
