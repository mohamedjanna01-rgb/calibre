"""Transcription « hybride locale » : mots et temps de la transcription locale (whisper-medium), locuteurs attribués
par Gemma à partir du seul texte.

1. Les mots locaux (déjà nettoyés : [numéro masqué] sur les bips, [inaudible] pour les mots peu sûrs) sont découpés
   en segments courts (fin de phrase ou pause), numérotés et horodatés.
2. Gemma reçoit ces segments, la fiche d'identité (type d'appel) et une consigne générique. Il attribue chaque segment
   au conseiller ou au client, et découpe un segment si les deux y parlent à la suite, sans changer un seul mot.
   Il ne reçoit jamais les scénarios, ni la notation de référence, ni les scripts de production.
3. Le code vérifie que le texte n'a pas été modifié : sinon, le segment garde son texte d'origine, entier, avec le
   locuteur de sa plus longue partie. Les temps des parties viennent des mots locaux.

Sortie : transcriptions/hybride-locale/appel-XX.json et appel-XX.md
Usage : python scripts/hybride_locale.py 01 02 03 [--simulation]
"""
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from compteur import Compteur  # noqa: E402
from effet_telephone import lire_wav  # noqa: E402
from evaluer_transcription import jetons  # noqa: E402
from transcrire import API, APPELS, BRUT, MASQUE, ecrire, mots_nettoyes, requete, type_appel  # noqa: E402

MODELE = "gemma-4-26b-a4b-it"
METHODE = "hybride-locale"

CONSIGNE = """Tu reçois la transcription automatique d'un appel téléphonique entre un conseiller de l'opérateur Kalyo Télécom et un client. La transcription est découpée en segments numérotés, avec leur heure de début, mais sans indication de qui parle.

Ta seule tâche : indiquer, pour chaque segment, qui parle : « conseiller » (la personne qui représente Kalyo Télécom : elle se présente au nom de l'opérateur, vérifie l'identité, explique, propose des offres) ou « client ».

Règles :
- Traite tous les segments, dans l'ordre, sans en oublier aucun.
- Si un segment contient deux personnes qui parlent à la suite (par exemple une question puis sa réponse), découpe-le en parties consécutives, chacune avec son locuteur. Recopie le texte de chaque partie exactement, sans changer, ajouter ou retirer un seul mot : mises bout à bout, les parties doivent redonner le segment entier.
- Ne corrige jamais la transcription, même si un mot semble mal transcrit.
- Appuie-toi sur le sens de la conversation : qui pose les questions d'identification, qui répond, qui propose, qui accepte ou refuse.

Réponds uniquement par un objet JSON valide, sans aucun texte autour, de la forme :
{"segments": [{"id": "S1", "parties": [{"locuteur": "conseiller", "texte": "..."}]}, ...]}"""


def segments(appel):
    """Segments courts : coupure après une fin de phrase (. ? !) ou avant une pause d'au moins 0,25 s."""
    mots = mots_nettoyes(appel, APPELS / f"appel-{appel}.wav", "medium")
    segs, courant = [], []
    for k, m in enumerate(mots):
        courant.append(m)
        suivant = mots[k + 1] if k + 1 < len(mots) else None
        fin_phrase = re.search(r"[.?!…]$", m["texte"]) or m["texte"] == MASQUE
        pause = suivant is not None and suivant["debut"] - m["fin"] >= 0.25
        if fin_phrase or pause or suivant is None:
            segs.append({"id": f"S{len(segs) + 1}", "mots": courant})
            courant = []
    for s in segs:
        s["texte"] = " ".join(m["texte"] for m in s["mots"])
        s["debut"] = s["mots"][0]["debut"]
    return segs


def construire(appel, segs):
    lignes = [f"{s['id']} [{s['debut']:.1f} s] {s['texte']}" for s in segs]
    return {
        "systemInstruction": {"parts": [{"text": CONSIGNE}]},
        "contents": [{"role": "user", "parts": [{"text": f"Type d'appel : {type_appel(appel)}\n\nSegments :\n" + "\n".join(lignes)}]}],
    }


def attribuer(segs, reponse):
    """Répliques à partir de la réponse de Gemma, en vérifiant que le texte n'a pas été modifié."""
    par_id = {s["id"]: s for s in reponse.get("segments", [])}
    parties_finales, anomalies, dernier = [], [], "client"
    for s in segs:
        r = par_id.get(s["id"])
        mots = s["mots"]
        if not r or not r.get("parties"):
            anomalies.append(f"{s['id']} : segment non traité, locuteur précédent conservé")
            parties_finales.append((dernier, mots))
            continue
        parties = [p for p in r["parties"] if p.get("locuteur") in ("conseiller", "client")]
        if [j for p in parties for j in jetons(p["texte"])] != jetons(s["texte"]) or not parties:
            # Texte modifié : on garde le segment entier, avec le locuteur de la plus longue partie
            long = max(parties or [{"locuteur": dernier, "texte": ""}], key=lambda p: len(p["texte"]))
            anomalies.append(f"{s['id']} : texte modifié par le modèle, segment gardé entier ({long['locuteur']})")
            parties_finales.append((long["locuteur"], mots))
            dernier = long["locuteur"]
            continue
        # Découpage : on répartit les mots locaux selon le nombre de jetons de chaque partie
        k = 0
        for p in parties:
            n, morceau = len(jetons(p["texte"])), []
            while k < len(mots) and (len(jetons(" ".join(m["texte"] for m in morceau))) < n or not jetons(mots[k]["texte"])):
                morceau.append(mots[k])
                k += 1
            if morceau:
                parties_finales.append((p["locuteur"], morceau))
            dernier = p["locuteur"]
        if k < len(mots):
            parties_finales[-1] = (parties_finales[-1][0], parties_finales[-1][1] + mots[k:])
    repliques = []
    for loc, mots in parties_finales:
        texte = " ".join(m["texte"] for m in mots)
        if repliques and repliques[-1]["locuteur"] == loc:
            repliques[-1]["texte"] += " " + texte
            repliques[-1]["fin"] = mots[-1]["fin"]
        else:
            repliques.append({"locuteur": loc, "debut": mots[0]["debut"], "fin": mots[-1]["fin"], "texte": texte})
    return repliques, anomalies


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    simulation = "--simulation" in sys.argv
    cle = os.environ.get("GEMINI_API_KEY")
    for n in args:
        appel = f"{int(n):02d}"
        segs = segments(appel)
        corps = construire(appel, segs)
        if simulation:
            print(f"appel-{appel} : {len(segs)} segments, {len(corps['contents'][0]['parts'][0]['text'])} caractères")
            continue
        Compteur().reserver(MODELE)
        _, octets = requete(f"{API}/v1beta/models/{MODELE}:generateContent", corps, cle, modele=MODELE)
        brute = json.loads(octets)
        sauvegarde = BRUT / f"locuteurs-{appel}.{MODELE}.reponse.json"
        sauvegarde.write_text(json.dumps(brute, ensure_ascii=False), encoding="utf-8")
        texte = "".join(x.get("text", "") for x in brute["candidates"][0]["content"]["parts"] if not x.get("thought"))
        reponse = json.loads(texte[texte.index("{"): texte.rindex("}") + 1])
        repliques, anomalies = attribuer(segs, reponse)
        signal, taux = lire_wav(APPELS / f"appel-{appel}.wav")
        ecrire(appel, METHODE, repliques, len(signal) / taux,
               {"source_mots": "whisper-medium", "locuteurs": MODELE, "segments": len(segs), "anomalies": anomalies,
                "usage": brute.get("usageMetadata")})
        sauvegarde.unlink()
        print(f"appel-{appel} / {METHODE} : {len(segs)} segments, {len(repliques)} répliques, {len(anomalies)} anomalie(s)", flush=True)


if __name__ == "__main__":
    main()
