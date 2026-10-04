"""Page locale d'écoute des 13 appels, avec le contrôle de fidélité : audio/appels/ecoute.html (non versionnée)."""
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APPELS = ROOT / "audio" / "appels"
NOMS = {"gemini-3.8-flash-tts": "3.8 Flash", "gemini-2.5-flash-preview-tts": "2.5 Flash"}

lignes = []
for n in range(1, 14):
    sc = (ROOT / "scenarios" / f"appel-{n:02d}.md").read_text(encoding="utf-8")
    titre = re.search(r'titre_interne: "Scénario \d+ – (.+?)"', sc).group(1)
    typ = re.search(r"type: (.+)", sc).group(1)
    info_f = APPELS / f"appel-{n:02d}.json"
    if not info_f.exists():
        lignes.append(f'<tr><td class="num">{n:02d}</td><td><strong>{html.escape(titre)}</strong><small>{typ}</small></td>'
                      f'<td colspan="3" class="manque">Pas encore généré</td></tr>')
        continue
    info = json.loads(info_f.read_text(encoding="utf-8"))
    c = info.get("controle") or {}
    remarques = []
    if c.get("repliques_non_retrouvees"):
        remarques.append("Répliques non reconnues : " + ", ".join(map(str, c["repliques_non_retrouvees"])))
    for p in c.get("passages_absents", []):
        remarques.append(f"Absent (réplique {p['replique']}) : « {p['texte']} »")
    for p in c.get("passages_en_trop", []):
        remarques.append(f"En trop (vers {p['vers_s']} s) : « {p['texte']} »")
    pct = c.get("mots_du_script_retrouves_pct", "–")
    alerte = " alerte" if (isinstance(pct, float) and pct < 90) or c.get("passages_absents") or c.get("passages_en_trop") else ""
    lignes.append(
        f'<tr><td class="num">{n:02d}</td><td><strong>{html.escape(titre)}</strong><small>{typ} · {NOMS.get(info["modele"], info["modele"])} · {info["duree_audio_s"]} s</small></td>'
        f'<td><audio controls preload="none" src="appel-{n:02d}.mp3"></audio></td>'
        f'<td class="pct{alerte}">{pct} %</td>'
        f'<td class="rem">{"<br>".join(html.escape(r) for r in remarques) or "Aucune anomalie détectée"}</td></tr>')

page = f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Appels Calibre</title>
<style>
:root {{ --fond:#f7f6f3; --carte:#fff; --texte:#1d1d1f; --doux:#6b6b70; --bord:#e3e1dc; --alerte:#b3261e; }}
@media (prefers-color-scheme: dark) {{ :root {{ --fond:#151517; --carte:#1f1f22; --texte:#ececee; --doux:#9a9aa1; --bord:#33333a; --alerte:#f2b8b5; }} }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--fond); color:var(--texte); font:15px/1.5 system-ui,sans-serif; padding:24px 16px; }}
main {{ max-width:1150px; margin:0 auto; }}
h1 {{ font-size:22px; margin:0 0 4px; }} p.sous {{ color:var(--doux); margin:0 0 20px; }}
table {{ width:100%; border-collapse:collapse; background:var(--carte); border:1px solid var(--bord); }}
th,td {{ padding:10px 12px; border-bottom:1px solid var(--bord); text-align:left; vertical-align:middle; }}
th {{ font-size:13px; color:var(--doux); }}
td small {{ display:block; color:var(--doux); font-size:12px; }}
td.num {{ font-variant-numeric:tabular-nums; color:var(--doux); }}
td.pct {{ font-variant-numeric:tabular-nums; white-space:nowrap; }} td.alerte {{ color:var(--alerte); font-weight:600; }}
td.rem {{ font-size:13px; color:var(--doux); }} td.manque {{ color:var(--doux); font-style:italic; }}
audio {{ width:260px; max-width:100%; }}
@media (max-width:760px) {{ table,tbody,tr,td {{ display:block; }} thead {{ display:none; }} td {{ border:0; padding:4px 12px; }} tr {{ border-bottom:1px solid var(--bord); padding:8px 0; }} }}
</style></head><body><main>
<h1>Les 13 appels de Calibre</h1>
<p class="sous">Version téléphonique finale. Contrôle de fidélité : part des mots du script retrouvés par une transcription locale, avec les passages absents ou en trop.</p>
<table><thead><tr><th>#</th><th>Scénario</th><th>Écoute</th><th>Mots retrouvés</th><th>Contrôle</th></tr></thead>
<tbody>{"".join(lignes)}</tbody></table>
</main></body></html>
"""
(APPELS / "ecoute.html").write_text(page, encoding="utf-8")
print("ecoute.html :", sum(1 for l in lignes if "<audio" in l), "appels disponibles")
