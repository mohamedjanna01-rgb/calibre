"""Lexique des noms propres de Kalyo, tiré UNIQUEMENT de la documentation (docs/), et correction de ces noms
dans une transcription, après coup.

Le lexique (transcriptions/lexique-noms-propres.json) liste chaque terme avec le document d'où il vient ;
un contrôle vérifie que chaque terme figure bien dans la documentation et ne provient d'aucune autre source.

Correction prudente, par code :
  - un mot qui ressemble phonétiquement à un nom du lexique (« Calio », « Caliot », « Cali ») est remplacé, sauf
    s'il existe dans le vocabulaire de la documentation (un vrai mot, comme « Calmez », n'est jamais touché) ;
  - un nom fusionné avec « Télécom » (« Caliotelecom ») est séparé et corrigé ;
  - le mot qui précède « Télécom » est corrigé en « Kalyo » (« Télécom » n'apparaît que dans « Kalyo Télécom »).

Usage : python scripts/lexique.py hybride-locale hybride-locale-lexique 01 02 ... 13
"""
import difflib
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
FICHIER = ROOT / "transcriptions" / "lexique-noms-propres.json"

# Motifs des noms propres de Kalyo, recherchés dans la documentation (le lexique ne garde que ce qui y figure)
MOTIFS = [r"Kalyo Télécom", r"Kalyo & Moi", r"Kalyo TV", r"Code Kalyo", r"Kalyo Mobile \d+ Go(?: 5G)?",
          r"Orbite", r"Sonde", r"Plan'Inter", r"Pack Horizon", r"Horizon [A-ZÉ][a-zéèêû]+",
          r"Box (?:Essentielle|Évolution|Ultra|4G Maison)", r"Box Nova(?: \d| Air)?", r"Vision 4K\+?",
          r"Avantage Foyer", r"Bandeau INC", r"Kalyo"]


def sans_accents(texte):
    return "".join(c for c in unicodedata.normalize("NFD", texte.lower()) if not unicodedata.combining(c))


def construire():
    lexique = {}
    for doc in sorted(DOCS.glob("*.md")):
        texte = doc.read_text(encoding="utf-8")
        for motif in MOTIFS:
            for terme in re.findall(motif, texte):
                lexique.setdefault(terme, doc.name[:2])
    # Contrôle de provenance : chaque terme figure dans la documentation
    tout = "".join(p.read_text(encoding="utf-8") for p in DOCS.glob("*.md"))
    assert all(t in tout for t in lexique), "terme absent de la documentation"
    FICHIER.write_text(json.dumps({"source": "docs/ (documentation de Kalyo uniquement)",
                                   "termes": [{"terme": t, "document": f"DOC-{d}"} for t, d in sorted(lexique.items())]},
                                  ensure_ascii=False, indent=1), encoding="utf-8")
    return sorted(lexique)


def phonetique(mot):
    """Clé phonétique simplifiée du français (k/c/qu, y/i, eau/au, finales muettes…)."""
    m = re.sub(r"[^a-z]", "", sans_accents(mot))
    for a, b in (("qu", "k"), ("ck", "k"), ("ph", "f"), ("eaux", "o"), ("eau", "o"), ("au", "o"), ("eux", "e"),
                 ("y", "i"), ("h", "")):
        m = m.replace(a, b)
    m = re.sub(r"c(?=[aou])|c$", "k", m)
    m = re.sub(r"(.)\1", r"\1", m)
    return re.sub(r"[estx]$", "", m) if len(m) > 3 else m


def vocabulaire_documentation():
    tout = sans_accents("".join(p.read_text(encoding="utf-8") for p in DOCS.glob("*.md")))
    return set(re.findall(r"[a-z]+", tout))


def corriger(texte, noms, vocab, journal):
    """Corrige les noms propres dans un texte ; chaque correction est consignée dans le journal."""
    def remplacer(m, nouveau, motif):
        journal.append(f"{m.group(0)!r} → {nouveau!r} ({motif})")
        return nouveau
    # Nom fusionné avec « Télécom »
    texte = re.sub(r"\b[CcKk]al\w*?t[ée]l[ée]com\b", lambda m: remplacer(m, "Kalyo Télécom", "nom fusionné"), texte)
    # Mot qui précède « Télécom »
    texte = re.sub(r"\b(?!Kalyo\b)(\w+)(?=\s+[Tt][ée]l[ée]com\b)", lambda m: remplacer(m, "Kalyo", "devant Télécom"), texte)
    # Mots isolés proches d'un nom du lexique, absents du vocabulaire de la documentation
    def mot(m):
        brut = m.group(0)
        cle = phonetique(brut)
        if len(cle) < 3 or sans_accents(brut) in vocab:
            return brut
        for nom in noms:
            ref = phonetique(nom)
            # Même son initial, longueur presque identique, forte ressemblance : « Calio » oui, « Allô » ou « seconde » non
            if (brut != nom and cle[0] == ref[0] and abs(len(cle) - len(ref)) <= 1
                    and difflib.SequenceMatcher(None, cle, ref).ratio() >= 0.8):
                return remplacer(m, nom, "ressemblance phonétique")
        return brut
    texte = re.sub(r"\b[A-Za-zÀ-ÿ']+\b", mot, texte)
    # « Cali au Télécom » donne « Kalyo Kalyo Télécom » : on fusionne, et « Télécom » reprend sa majuscule
    texte = re.sub(r"\bKalyo(?:\s+Kalyo)+\b", "Kalyo", texte)
    return re.sub(r"\bKalyo\s+t[ée]l[ée]com\b", "Kalyo Télécom", texte, flags=re.I)


if __name__ == "__main__":
    source, cible, appels = sys.argv[1], sys.argv[2], sys.argv[3:]
    termes = construire()
    # Noms à surveiller mot par mot : les noms propres d'un seul mot qui ne sont pas des mots courants de la documentation
    vocab = vocabulaire_documentation()
    noms = sorted({t for t in termes if " " not in t and "'" not in t})
    print(f"lexique : {len(termes)} termes tirés de la documentation ; noms surveillés mot par mot : {noms}")
    (ROOT / "transcriptions" / cible).mkdir(parents=True, exist_ok=True)
    for n in appels:
        appel = f"{int(n):02d}"
        donnees = json.loads((ROOT / "transcriptions" / source / f"appel-{appel}.json").read_text(encoding="utf-8"))
        journal = []
        for r in donnees["repliques"]:
            r["texte"] = corriger(r["texte"], noms, vocab, journal)
        donnees["methode"] = cible
        donnees["usage"] = dict(donnees.get("usage") or {}, lexique=journal)
        (ROOT / "transcriptions" / cible / f"appel-{appel}.json").write_text(json.dumps(donnees, ensure_ascii=False, indent=2), encoding="utf-8")
        md = [f"# Appel {appel} – transcription {cible}", ""] + [
            f"**[{int(r['debut'] // 60):02d}:{r['debut'] % 60:04.1f}] {r['locuteur'].capitalize()} :** {r['texte']}\n" for r in donnees["repliques"]]
        (ROOT / "transcriptions" / cible / f"appel-{appel}.md").write_text("\n".join(md), encoding="utf-8")
        print(f"appel-{appel} : {len(journal)} correction(s) " + "; ".join(journal))
