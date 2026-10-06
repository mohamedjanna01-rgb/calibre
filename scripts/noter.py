"""Notation d'un appel par l'IA, à partir de sa transcription hybride.

L'IA reçoit : la consigne (prompts/notation/consigne.md), la fiche d'identité (type d'appel et grille),
la transcription horodatée, et un référentiel assemblé UNIQUEMENT à partir des sources autorisées :
grilles et règles du cadrage (sections 2 à 4), règles 1 à 13 de la notation de référence (section 1),
exemples de notation du qualiticien, documentation de Kalyo. Jamais les scénarios, ni les tableaux de
la notation de référence, ni les scripts de production : un contrôle par code le vérifie avant tout envoi.

L'IA note les items, cite les preuves, repère les éliminatoires, les fautes de mise en garde et les
remarques de conformité, et rédige le coaching. Le code calcule ensuite la note, le niveau, les alertes
et l'action, et vérifie que chaque citation existe mot pour mot dans la transcription.

Sortie : notations/<modèle>/appel-XX.json et appel-XX.md
Usage :
    python scripts/noter.py --appels 03 --simulation        # assemble et contrôle la consigne, sans requête
    python scripts/noter.py --appels 01 02 03 04 05 [--modele gemini-3.8-flash]
"""
import argparse
import difflib
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from compteur import Compteur  # noqa: E402
from evaluer_transcription import jetons  # noqa: E402
from transcrire import API, BRUT, requete  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CADRAGE = ROOT / "cadrage" / "calibre-cadrage.md"
NOTATION_REF = ROOT / "cadrage" / "calibre-notation-reference.md"
EXEMPLES = ROOT / "cadrage" / "calibre-exemples-notation.md"
CONSIGNE = ROOT / "prompts" / "notation" / "consigne.md"
TRANSCRIPTIONS = ROOT / "transcriptions"
SOURCE = "hybride"  # méthode de transcription notée (modifiable avec --source)
SORTIE = ROOT / "notations"

STATUTS = ["oui", "non", "na"]
SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "items": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {
            "numero": {"type": "INTEGER"},
            "statut": {"type": "STRING", "enum": STATUTS},
            "justification": {"type": "STRING"},
            "preuves": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {
                "citation": {"type": "STRING"}, "debut_s": {"type": "NUMBER"}}, "required": ["citation", "debut_s"]}},
        }, "required": ["numero", "statut", "justification", "preuves"]}},
        "eliminatoires": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {
            "numero": {"type": "INTEGER"}, "motif": {"type": "STRING"},  # 1, 2 ou 3 : vérifié par le code
            "citation": {"type": "STRING"}, "debut_s": {"type": "NUMBER"}}, "required": ["numero", "motif", "citation", "debut_s"]}},
        "fautes_mise_en_garde": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {
            "type": {"type": "STRING", "enum": ["resiliation_retardee", "resiliation_refusee", "panne_ignoree"]},
            "citation": {"type": "STRING"}, "debut_s": {"type": "NUMBER"}}, "required": ["type", "citation", "debut_s"]}},
        "remarques_conformite": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {
            "regle": {"type": "STRING"}, "ecart": {"type": "STRING"},
            "citation": {"type": "STRING"}, "debut_s": {"type": "NUMBER"}}, "required": ["regle", "ecart", "citation", "debut_s"]}},
        "coaching": {"type": "OBJECT", "properties": {
            "points_forts": {"type": "ARRAY", "items": {"type": "STRING"}},
            "axes_progres": {"type": "ARRAY", "items": {"type": "STRING"}},
            "conseil_principal": {"type": "STRING"}}, "required": ["points_forts", "axes_progres", "conseil_principal"]},
    },
    "required": ["items", "eliminatoires", "fautes_mise_en_garde", "remarques_conformite", "coaching"],
}


# --- Référentiel autorisé et contrôle des fuites -------------------------------------------------------------

def section(texte, debut, fin):
    return texte.split(debut, 1)[1].split(fin, 1)[0]


def sans_scenarios(texte):
    """Retire toute mention des scénarios d'examen (lignes ou parenthèses qui y renvoient)."""
    texte = re.sub(r"\s*\((?:voir le |cf\. )?scénario \d+\)", "", texte, flags=re.I)
    return "\n".join(l for l in texte.splitlines() if not re.search(r"scénario", l, flags=re.I))


def grilles():
    """Items de chaque grille : numéro, libellé, et si « non applicable » est permis."""
    cadrage = CADRAGE.read_text(encoding="utf-8")
    resultat = {}
    for nom, debut, fin in (("Grille 1", "## 2. Grille 1", "## 3."), ("Grille 2", "## 3. Grille 2", "\n---\n")):
        items = {}
        for m in re.finditer(r"^\| (\d+) \| (.+) \|$", section(cadrage, debut, fin), flags=re.M):
            items[int(m.group(1))] = {"libelle": m.group(2), "na_permis": bool(re.search(r"\*\(si ", m.group(2)))}
        resultat[nom] = items
    return resultat


# Référentiel réduit (modèles limités en tokens par minute) : seulement les documents essentiels selon le type d'appel
DOCS_REDUITS = {"Appel entrant": ("01", "15"), "Télévente sortante": ("01", "16")}


def alleger(doc):
    """Référentiel réduit : retire de DOC-01 les parties sans rapport avec la notation d'un appel
    (pénalités de non-restitution du matériel, glossaire)."""
    texte = doc.read_text(encoding="utf-8")
    if doc.name.startswith("01"):
        texte = re.sub(r"## 4\. Équipements et pénalités.*?(?=## 5\.)", "", texte, flags=re.S)
        texte = re.sub(r"## 7\. Glossaire.*?(?=## Documents liés)", "", texte, flags=re.S)
    return texte


def referentiel(type_appel=None, reduit=False):
    cadrage = CADRAGE.read_text(encoding="utf-8")
    docs = sorted((ROOT / "docs").glob("*.md"))
    if reduit:
        docs = [d for d in docs if d.name[:2] in DOCS_REDUITS[type_appel]]
    parties = [
        "# Grilles et règles de notation\n" + sans_scenarios(section(cadrage, "## 2. Grille 1", "## 5.")),
        "# Règles précisées par le qualiticien\n" + sans_scenarios(section(NOTATION_REF.read_text(encoding="utf-8"), "## 1.", "## 2.")),
        "# Exemples de notation du qualiticien\n" + sans_scenarios(EXEMPLES.read_text(encoding="utf-8").split("\n", 1)[1]),
        "# Documentation interne de Kalyo Télécom\n" + "\n\n".join(alleger(p) if reduit else p.read_text(encoding="utf-8") for p in docs),
    ]
    return "\n\n".join(parties)


def tuiles(texte, n=8):
    mots = jetons(texte)
    return {" ".join(mots[i:i + n]) for i in range(len(mots) - n + 1)}


def controler_fuites(texte_envoye_hors_transcription):
    """Aucune suite de 8 mots provenant des sources interdites (scénarios, tableaux de la notation de référence,
    scripts de production) ne doit apparaître dans la consigne ou le référentiel, sauf si elle figure aussi dans une
    source autorisée (par exemple une phrase type reprise dans la documentation)."""
    interdit = CADRAGE.read_text(encoding="utf-8").split("## 6.", 1)[1].split("## 7.", 1)[0]
    interdit += NOTATION_REF.read_text(encoding="utf-8").split("## 2.", 1)[1]
    interdit += "".join(p.read_text(encoding="utf-8") for p in (ROOT / "scenarios").glob("*.md"))
    interdit += "".join(p.read_text(encoding="utf-8") for p in (ROOT / "audio" / "production").glob("*.yaml"))
    autorise = referentiel_autorise_brut()
    suspects = (tuiles(interdit) - tuiles(autorise)) & tuiles(texte_envoye_hors_transcription)
    if suspects:
        sys.exit(f"ARRÊT – contenu interdit détecté dans la consigne : {sorted(suspects)[:5]}")
    if re.search(r"scénario|titre_interne", texte_envoye_hors_transcription, flags=re.I):
        sys.exit("ARRÊT – mention des scénarios d'examen dans la consigne.")


def referentiel_autorise_brut():
    return (CADRAGE.read_text(encoding="utf-8").split("## 6.", 1)[0] + EXEMPLES.read_text(encoding="utf-8")
            + "".join(p.read_text(encoding="utf-8") for p in (ROOT / "docs").glob("*.md")))


def fiche(appel):
    texte = (ROOT / "scenarios" / f"appel-{appel}.md").read_text(encoding="utf-8")
    type_appel = re.search(r"^\s*type: (.+)$", texte, flags=re.M).group(1).strip()
    grille = re.search(r"^\s*grille: (.+)$", texte, flags=re.M).group(1).strip()
    return type_appel, grille


def transcription(appel):
    donnees = json.loads((TRANSCRIPTIONS / SOURCE / f"appel-{appel}.json").read_text(encoding="utf-8"))
    return donnees["repliques"]


def construire(appel, modele, reduit=False):
    type_appel, grille = fiche(appel)
    reps = transcription(appel)
    consigne = CONSIGNE.read_text(encoding="utf-8")
    ref = referentiel(type_appel, reduit)
    controler_fuites(consigne + ref)
    lignes = [f"[{r['debut']:.1f} s] {r['locuteur'].capitalize()} : {r['texte']}" for r in reps]
    utilisateur = (f"# Référentiel\n\n{ref}\n\n# Fiche d'identité de l'appel\n\nType d'appel : {type_appel}\nGrille à utiliser : {grille}\n\n"
                   f"# Transcription\n\n" + "\n".join(lignes))
    corps = {
        "systemInstruction": {"parts": [{"text": consigne}]},
        "contents": [{"role": "user", "parts": [{"text": utilisateur}]}],
        "generationConfig": {"responseMimeType": "application/json", "responseSchema": SCHEMA},
    }
    if modele.startswith("gemma"):
        # Gemma ne prend pas en charge la réponse JSON structurée : même consigne, format demandé en texte
        del corps["generationConfig"]
        corps["contents"][0]["parts"][0]["text"] += (
            "\n\n# Format de réponse\n\nRéponds uniquement par un objet JSON valide, sans aucun texte autour, "
            "conforme à ce schéma :\n" + json.dumps(SCHEMA, ensure_ascii=False, separators=(",", ":")))
    return corps, type_appel, grille


# --- Calculs et vérifications par code --------------------------------------------------------------------------

def verifier_citation(citation, reps):
    """Statut de la citation dans la transcription (exacte, approchée, introuvable) et horodatage de la réplique
    où elle commence. La recherche porte sur toute la transcription (une citation peut couvrir deux répliques) ;
    les repères de temps recopiés par l'IA (« [87.7 s] ») sont ignorés."""
    cj = jetons(re.sub(r"\[\d+(?:[.,]\d+)?\s*s\]", " ", citation))
    if not cj:
        return "vide", None
    tous = [(m, r["debut"]) for r in reps for m in jetons(r["texte"])]
    mots = [m for m, _ in tous]
    for k in range(len(mots) - len(cj) + 1):
        if mots[k:k + len(cj)] == cj:
            return "exacte", tous[k][1]
    meilleur = (0, None)
    for k in range(max(1, len(mots) - len(cj) + 1)):
        ratio = difflib.SequenceMatcher(None, cj, mots[k:k + len(cj)]).ratio()
        if ratio > meilleur[0]:
            meilleur = (ratio, tous[k][1] if tous else None)
    return ("approchée", meilleur[1]) if meilleur[0] >= 0.85 else ("introuvable", None)


def calculer(reponse, grille_nom, reps):
    items_grille = grilles()["Grille 1" if grille_nom.startswith("Grille 1") else "Grille 2"]
    anomalies = []
    items = {i["numero"]: i for i in reponse["items"]}
    if sorted(items) != sorted(items_grille):
        anomalies.append(f"items attendus {sorted(items_grille)}, reçus {sorted(items)}")
    for n, i in items.items():
        if i["statut"] == "na" and n in items_grille and not items_grille[n]["na_permis"]:
            anomalies.append(f"item {n} noté non applicable alors qu'il est toujours applicable")
    for e in reponse["eliminatoires"]:
        if e["numero"] not in (1, 2, 3):
            anomalies.append(f"éliminatoire inconnu : {e['numero']}")
    reponse["eliminatoires"] = [e for e in reponse["eliminatoires"] if e["numero"] in (1, 2, 3)]
    oui = sum(1 for i in items.values() if i["statut"] == "oui")
    applicables = sum(1 for i in items.values() if i["statut"] in ("oui", "non"))
    note = int(100 * oui / applicables + 0.5) if applicables else 0
    niveau = ("Excellent" if note >= 90 else "Conforme" if note >= 75 else "À améliorer" if note >= 60 else "Insuffisant")
    mises_en_garde = sorted({f["type"] for f in reponse["fautes_mise_en_garde"]} | ({"insuffisant"} if niveau == "Insuffisant" else set()))
    if reponse["eliminatoires"]:
        niveau_final, action = "Non conforme", "Avertissement"
    else:
        niveau_final = niveau
        action = ("Mise en garde" if mises_en_garde else
                  {"Excellent": "Valorisation", "Conforme": "Rien à signaler", "À améliorer": "Coaching ciblé"}[niveau])
    # Vérification de toutes les citations, horodatage recalculé à partir de la transcription
    for groupe in ([p for i in reponse["items"] for p in i["preuves"]], reponse["eliminatoires"],
                   reponse["fautes_mise_en_garde"], reponse["remarques_conformite"]):
        for c in groupe:
            c["verification"], c["debut_verifie_s"] = verifier_citation(c["citation"], reps)
            if c["verification"] == "introuvable":
                anomalies.append(f"citation introuvable dans la transcription : « {c['citation'][:80]} »")
    return {"oui": oui, "applicables": applicables, "note_pct": note, "niveau_note": niveau, "niveau": niveau_final,
            "eliminatoires": sorted({e["numero"] for e in reponse["eliminatoires"]}), "mises_en_garde": mises_en_garde,
            "action": action, "anomalies": anomalies}


# --- Rapport ----------------------------------------------------------------------------------------------------

def rapport(appel, modele, type_appel, grille, reponse, calcul):
    mm = lambda s: "" if s is None else f"{int(s // 60):02d}:{s % 60:04.1f}"  # noqa: E731
    libelles = grilles()["Grille 1" if grille.startswith("Grille 1") else "Grille 2"]
    l = [f"# Appel {appel} – rapport Calibre ({modele})", "",
         f"**{type_appel}** · {grille}", "",
         f"**Note : {calcul['oui']} / {calcul['applicables']} = {calcul['note_pct']} %** · **Niveau : {calcul['niveau']}** · "
         f"**Action proposée : {calcul['action']}**", "",
         "> Calibre recommande, le qualiticien décide.", "", "## Notation", "",
         "| N° | Item | Note | Justification | Preuves |", "|---|---|---|---|---|"]
    for i in sorted(reponse["items"], key=lambda x: x["numero"]):
        preuves = "<br>".join(f"[{mm(p.get('debut_verifie_s'))}] « {p['citation']} »" + ("" if p["verification"] == "exacte" else f" *({p['verification']})*")
                              for p in i["preuves"])
        lib = re.sub(r"\*\*|\*\(.*?\)\*", "", libelles.get(i["numero"], {}).get("libelle", "")).split(" : ")[0].strip()
        l.append(f"| {i['numero']} | {lib} | {i['statut'].upper() if i['statut'] != 'na' else '–'} | {i['justification']} | {preuves} |")
    l += ["", "## Éliminatoires", ""] + ([f"- **Éliminatoire {e['numero']}** : {e['motif']} — [{mm(e.get('debut_verifie_s'))}] « {e['citation']} »"
                                          for e in reponse["eliminatoires"]] or ["Aucun."])
    l += ["", "## Mises en garde", ""] + ([f"- {m.replace('_', ' ')}" for m in calcul["mises_en_garde"]] or ["Aucune."])
    l += ["", "## Remarques de conformité (sans effet sur la note)", ""] + (
        [f"- **{r['regle']}** : {r['ecart']} — [{mm(r.get('debut_verifie_s'))}] « {r['citation']} »" for r in reponse["remarques_conformite"]] or ["Aucune."])
    c = reponse["coaching"]
    l += ["", "## Coaching", "", "**Points forts**", ""] + [f"- {p}" for p in c["points_forts"]]
    l += ["", "**Axes de progrès**", ""] + [f"- {p}" for p in c["axes_progres"]]
    l += ["", f"**Conseil principal :** {c['conseil_principal']}"]
    if calcul["anomalies"]:
        l += ["", "## Anomalies détectées par le contrôle", ""] + [f"- {a}" for a in calcul["anomalies"]]
    return "\n".join(l) + "\n"


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--appels", nargs="+", required=True)
    p.add_argument("--modele", default="gemini-3.8-flash")
    p.add_argument("--simulation", action="store_true", help="assemble et contrôle la consigne, sans requête")
    p.add_argument("--reduit", action="store_true", help="référentiel réduit (documents essentiels seulement)")
    p.add_argument("--source", default="hybride", help="méthode de transcription à noter")
    p.add_argument("--passe", help="numéro de passe, pour mesurer la variabilité (dossier distinct)")
    a = p.parse_args()
    global SOURCE
    SOURCE = a.source
    cle = os.environ.get("GEMINI_API_KEY")
    for n in a.appels:
        appel = f"{int(n):02d}"
        corps, type_appel, grille = construire(appel, a.modele, a.reduit)
        if a.simulation:
            taille = len(corps["contents"][0]["parts"][0]["text"]) + len(corps["systemInstruction"]["parts"][0]["text"])
            print(f"appel-{appel} : consigne contrôlée (aucun contenu interdit), {taille} caractères, {type_appel}, {grille}")
            continue
        Compteur().reserver(a.modele)
        _, octets = requete(f"{API}/v1beta/models/{a.modele}:generateContent", corps, cle, modele=a.modele)
        brute = json.loads(octets)
        sauvegarde = BRUT / f"notation-{appel}.{a.modele}.reponse.json"
        sauvegarde.write_text(json.dumps(brute, ensure_ascii=False), encoding="utf-8")
        texte = "".join(x.get("text", "") for x in brute["candidates"][0]["content"]["parts"] if not x.get("thought"))
        reponse = json.loads(texte[texte.index("{"): texte.rindex("}") + 1])  # tolère un bloc ```json autour
        calcul = calculer(reponse, grille, transcription(appel))
        dossier = SORTIE / (a.modele + ("-reduit" if a.reduit else "") + ("" if SOURCE == "hybride" else f"-{SOURCE}")
                            + (f"-passe{a.passe}" if a.passe else ""))
        dossier.mkdir(parents=True, exist_ok=True)
        (dossier / f"appel-{appel}.json").write_text(json.dumps({
            "appel": appel, "modele": a.modele, "date": datetime.now().isoformat(timespec="seconds"),
            "source_transcription": SOURCE, "referentiel": "réduit" if a.reduit else "complet", "reponse_ia": reponse, "calcul": calcul,
            "usage": brute.get("usageMetadata")}, ensure_ascii=False, indent=2), encoding="utf-8")
        (dossier / f"appel-{appel}.md").write_text(rapport(appel, a.modele, type_appel, grille, reponse, calcul), encoding="utf-8")
        sauvegarde.unlink()
        print(f"appel-{appel} / {a.modele} : {calcul['note_pct']} % · {calcul['niveau']} · {calcul['action']}"
              f"{' · ' + str(len(calcul['anomalies'])) + ' anomalie(s)' if calcul['anomalies'] else ''}", flush=True)


if __name__ == "__main__":
    main()
