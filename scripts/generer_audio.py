"""Génère un appel complet en une seule requête de synthèse vocale, avec deux voix.

Un appel est toujours produit en entier par un seul modèle : une requête, un modèle, un fichier.
Aucune nouvelle tentative automatique : une requête envoyée est comptée, même en cas d'échec.

Usage :
    python scripts/generer_audio.py --appel 03 --modele gemini-3.8-flash-tts --sortie audio/essais
    python scripts/generer_audio.py --appel 03 --modele gemini-3.8-flash-tts --simulation   # n'envoie rien
    python scripts/generer_audio.py --etat                                                  # requêtes restantes

La clé est lue dans la variable d'environnement GEMINI_API_KEY.
"""
import argparse
import base64
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
import wave
from datetime import datetime
from pathlib import Path

import numpy as np
import yaml

sys.path.insert(0, str(Path(__file__).parent))
from effet_telephone import appliquer_effet, lire_wav, ecrire_wav  # noqa: E402
from post_traitement import traiter  # noqa: E402
from compteur import Compteur  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PRODUCTION = ROOT / "audio" / "production"
COMPTEUR = ROOT / "audio" / ".compteur-requetes.json"
API = "https://generativelanguage.googleapis.com/v1beta"

# Modèles autorisés et route de l'API correspondante
MODELES = {
    "gemini-3.8-flash-tts": "interactions",
    "gemini-3.8-flash-lite-tts": "interactions",
    "gemini-3.1-flash-tts-preview": "generate",
    "gemini-2.5-flash-preview-tts": "generate",
}
LOCUTEURS = {"conseiller": "Conseiller", "client": "Client"}
BALISES_FR = {"sigh": "soupir", "chuckle": "petit rire", "short pause": "courte pause", "long pause": "longue pause",
              "cough": "toussote"}
FIN_DE_PHRASE = re.compile(r"([.!?…])\s+(?=[A-ZÀ-ÖØ-Þ«])")
RYTHME = "Rythme naturel et posé de conversation téléphonique"
REPARTITION = PRODUCTION / "repartition.yaml"
SORTIE_FINALE = "audio/appels"


def decrire(personne):
    """Description du locuteur, répétée à chaque réplique pour stabiliser la voix."""
    profil = personne["profil"]
    femme = profil.startswith("femme")
    genre = "voix féminine" if femme else "voix masculine"
    if genre not in profil:
        profil = f"{profil}, {genre}"
    return f"{'Locutrice' if femme else 'Locuteur'} : {profil}"


# --- Construction de la requête -------------------------------------------------------

def charger(appel):
    script = yaml.safe_load((PRODUCTION / f"appel-{appel}.yaml").read_text(encoding="utf-8"))
    prononciation = yaml.safe_load((PRODUCTION / "prononciation.yaml").read_text(encoding="utf-8"))["remplacements"]
    return script, prononciation


def preparer_repliques(script, prononciation):
    """Texte à prononcer et consigne de ton de chaque réplique, en une seule requête."""
    sortie = []
    for i, r in enumerate(script["repliques"]):
        texte = r["texte"]
        for ecrit, dit in prononciation.items():
            texte = texte.replace(ecrit, dit)
        # Pauses naturelles entre les phrases d'une même réplique
        texte = FIN_DE_PHRASE.sub(r"\1 <short pause> ", texte)
        # Courte pause entre les répliques, longue si le script le demande, aucune si on coupe la parole
        if i and not r.get("chevauchement_ms"):
            texte = ("<long pause> " if r.get("pause_avant_ms", 400) >= 1500 else "<short pause> ") + texte
        ton = r["ton"]
        if r.get("chevauchement_ms"):
            ton += " ; enchaîne immédiatement, sans blanc, en coupant la parole"
        if r.get("coupee"):
            ton += " ; la phrase est coupée net : la voix s'arrête brusquement"
        sortie.append({"locuteur": LOCUTEURS[r["locuteur"]], "texte": texte, "ton": ton})
    return sortie


def corps_interactions(modele, script, repliques):
    casting = script["casting"]
    contenu = []
    for r in repliques:
        qui = decrire(casting[r["locuteur"].lower()])
        contenu.append({
            "type": "text",
            "text": r["texte"],
            "annotations": [{"type": "speech_metadata", "speaker": r["locuteur"],
                             "style": f"{qui}. {RYTHME}. Ton : {r['ton']}."}],
        })
    return {
        "model": modele,
        "input": [{"type": "user_input", "content": contenu}],
        "response_format": {"type": "audio"},
        "generation_config": {"speech_config": {
            "mode": "conversational",
            "speakers": [{"speaker": LOCUTEURS[k], "voice": v["voix"]} for k, v in casting.items()],
        }},
    }


def corps_generate(script, repliques, suite=False):
    casting = script["casting"]
    lignes = [
        ("Voici la suite de la même conversation téléphonique, avec les mêmes voix. " if suite else "")
        + "Synthétise cette conversation téléphonique en français de France, entre un conseiller "
        "de Kalyo Télécom (Conseiller) et son client (Client).",
        "Profils des voix :",
        f"- Conseiller : {decrire(casting['conseiller'])}",
        f"- Client : {decrire(casting['client'])}",
        f"{RYTHME}, avec de courtes pauses entre les phrases et entre les répliques.",
        "Les indications entre crochets sont des consignes de jeu : applique-les, ne les lis jamais à voix haute.",
        "",
    ]
    for r in repliques:
        # Les courtes pauses sont demandées une fois dans l'en-tête : les répéter entre crochets alourdit
        # la consigne, et les anciens modèles s'arrêtent alors avant la fin des appels longs.
        texte = re.sub(r"<short pause> ", "", r["texte"])
        texte = re.sub(r"<([^>]+)>", lambda m: f"[{BALISES_FR.get(m.group(1), m.group(1))}]", texte)
        genre = casting[r["locuteur"].lower()]["profil"].split(",")[0]
        lignes.append(f"{r['locuteur']}: [{genre} ; {r['ton']}] {texte}")
    return {
        "contents": [{"parts": [{"text": "\n".join(lignes)}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {"multiSpeakerVoiceConfig": {"speakerVoiceConfigs": [
                {"speaker": LOCUTEURS[k], "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": v["voix"]}}}
                for k, v in casting.items()
            ]}},
        },
    }


# --- Envoi et lecture de la réponse ------------------------------------------------------

def envoyer(url, corps, cle, modele):
    """Erreur 503 (surcharge passagère de Google) : une seule nouvelle tentative après une minute,
    comptée dans le quota. Tout autre refus, dont un refus lié au quota (429), arrête immédiatement."""
    for tentative in (1, 2):
        req = urllib.request.Request(url, data=json.dumps(corps).encode("utf-8"), method="POST",
                                     headers={"Content-Type": "application/json", "x-goog-api-key": cle})
        try:
            with urllib.request.urlopen(req, timeout=600) as rep:
                return json.loads(rep.read())
        except urllib.error.HTTPError as e:
            message = e.read().decode("utf-8", "replace")[:800]
            if e.code == 503 and tentative == 1:
                print("Erreur 503 (surcharge de Google) : nouvelle tentative dans 60 s, comptée dans le quota.", flush=True)
                time.sleep(60)
                Compteur().reserver(modele)
                continue
            sys.exit(f"Échec HTTP {e.code} (requête comptée, pas de nouvel essai) : {message}")


def extraire_audio(reponse):
    """Cherche le premier bloc audio en base64, quelle que soit la route utilisée."""
    pile = [reponse]
    while pile:
        x = pile.pop(0)
        if isinstance(x, dict):
            mime = x.get("mimeType") or x.get("mime_type") or ""
            if isinstance(x.get("data"), str) and len(x["data"]) > 1000 and ("audio" in mime or not mime):
                return base64.b64decode(x["data"]), mime
            pile.extend(x.values())
        elif isinstance(x, list):
            pile.extend(x)
    sys.exit(f"Aucun audio dans la réponse : {json.dumps(reponse)[:800]}")


def pcm_vers_wav(octets, mime):
    """Les anciens modèles renvoient du PCM brut (L16, 24 kHz) : on ajoute l'en-tête WAV."""
    if octets[:4] == b"RIFF":
        return octets
    taux = int(re.search(r"rate=(\d+)", mime).group(1)) if "rate=" in mime else 24000
    tampon = io.BytesIO()
    with wave.open(tampon, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(taux)
        w.writeframes(octets)
    return tampon.getvalue()


def assembler(parties_wav, silence_s=0.45):
    """Met bout à bout les parties d'un appel généré en plusieurs requêtes, séparées par un court silence."""
    signaux, taux = [], None
    for octets in parties_wav:
        s, t = lire_wav(io.BytesIO(octets))
        assert taux in (None, t), "fréquences différentes entre les parties"
        taux = t
        signaux += [s, np.zeros(int(silence_s * t))]
    tampon = io.BytesIO()
    ecrire_wav(tampon, np.concatenate(signaux[:-1]), taux)  # sans le silence final
    return tampon.getvalue()


def finaliser(parties_wav, appel, sortie):
    """Conserve la voix brute en local (audio/brut/, non versionné), pour pouvoir refaire le traitement
    du son sans nouvelle requête, puis produit la version finale avec effet de ligne téléphonique."""
    brut = ROOT / "audio" / "brut" / f"appel-{appel}.wav"
    brut.parent.mkdir(parents=True, exist_ok=True)
    brut.write_bytes(parties_wav[0] if len(parties_wav) == 1 else assembler(parties_wav))
    if Path(sortie) == Path(SORTIE_FINALE):
        return traiter(appel)  # ambiance, grésillements, bips, contrôle de fidélité
    signal, taux = lire_wav(brut)
    tel, taux_tel = appliquer_effet(signal, taux)
    (ROOT / sortie).mkdir(parents=True, exist_ok=True)
    ecrire_wav(ROOT / sortie / f"appel-{appel}.wav", tel, taux_tel)
    return None


# --- Programme principal -------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--appel", help="numéro de l'appel, par exemple 03")
    p.add_argument("--modele", choices=MODELES)
    p.add_argument("--sortie", default=SORTIE_FINALE)
    p.add_argument("--simulation", action="store_true", help="affiche la requête sans l'envoyer")
    p.add_argument("--etat", action="store_true", help="affiche les requêtes restantes")
    a = p.parse_args()

    compteur = Compteur()
    if a.etat:
        compteur.afficher()
        return
    if not (a.appel and a.modele):
        p.error("--appel et --modele sont obligatoires")

    appel = f"{int(a.appel):02d}"
    # Un seul modèle par appel : les appels définitifs suivent la répartition validée
    if Path(a.sortie) == Path(SORTIE_FINALE):
        prevu = (yaml.safe_load(REPARTITION.read_text(encoding="utf-8")) or {}).get("appels", {}).get(f"appel-{appel}")
        if prevu != a.modele:
            sys.exit(f"Refusé : appel-{appel} est attribué à « {prevu} » dans {REPARTITION.name}, pas à {a.modele}.")
    script, prononciation = charger(appel)
    repliques = preparer_repliques(script, prononciation)
    route = MODELES[a.modele]

    # Appels longs : plusieurs requêtes, mêmes voix et même consigne, coupées aux répliques indiquées
    coupes = [0] + list(script.get("decoupe_apres", [])) + [len(repliques)]
    parties = [repliques[coupes[k]:coupes[k + 1]] for k in range(len(coupes) - 1)]
    if route == "interactions":
        url = f"{API}/interactions"
        corps_parties = [corps_interactions(a.modele, script, rep) for rep in parties]
    else:
        url = f"{API}/models/{a.modele}:generateContent"
        corps_parties = [corps_generate(script, rep, suite=k > 0) for k, rep in enumerate(parties)]

    if a.simulation:
        print(json.dumps(corps_parties[0] if len(corps_parties) == 1 else corps_parties, ensure_ascii=False, indent=2))
        return

    cle = os.environ.get("GEMINI_API_KEY")
    if not cle:
        sys.exit("Variable d'environnement GEMINI_API_KEY absente.")

    parties_wav, usages, mimes, sauvegardes, duree_requete = [], [], [], [], 0.0
    for k, corps in enumerate(corps_parties, 1):
        compteur.reserver(a.modele)
        debut = time.time()
        reponse = envoyer(url, corps, cle, a.modele)  # en cas d'échec : arrêt immédiat, les parties reçues restent sauvegardées
        duree_requete += time.time() - debut
        # Réponse sauvegardée telle quelle avant tout traitement : rien n'est perdu en cas d'erreur locale
        suffixe = f".partie{k}" if len(corps_parties) > 1 else ""
        sauvegarde = ROOT / "audio" / "brut" / f"appel-{appel}{suffixe}.{a.modele}.reponse.json"
        sauvegarde.parent.mkdir(parents=True, exist_ok=True)
        sauvegarde.write_text(json.dumps(reponse), encoding="utf-8")
        sauvegardes.append(sauvegarde)
        octets, mime = extraire_audio(reponse)
        parties_wav.append(pcm_vers_wav(octets, mime))
        mimes.append(mime)
        usages.append(reponse.get("usageMetadata") or reponse.get("usage"))
        if len(corps_parties) > 1:
            print(f"appel-{appel} : partie {k}/{len(corps_parties)} reçue", flush=True)
    controle = finaliser(parties_wav, appel, a.sortie)
    for s in sauvegardes:
        s.unlink()
    base = ROOT / a.sortie / f"appel-{appel}"
    signal, taux = lire_wav(base.with_suffix(".wav"))

    infos = {
        "appel": appel, "modele": a.modele, "route": route,
        "date": datetime.now().isoformat(timespec="seconds"),
        "repliques": len(repliques), "requetes": len(corps_parties), "decoupe_apres": script.get("decoupe_apres", []),
        "duree_audio_s": round(len(signal) / taux, 1),
        "duree_requete_s": round(duree_requete, 1), "format_recu": mimes[0] or "audio/wav",
        "usage": usages[0] if len(usages) == 1 else usages,
        "controle": controle,
    }
    base.with_suffix(".json").write_text(json.dumps(infos, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"appel-{appel} / {a.modele} : {infos['duree_audio_s']} s d'audio en {infos['duree_requete_s']} s "
          f"| reste {compteur.restantes(a.modele)} requêtes aujourd'hui")


if __name__ == "__main__":
    main()
