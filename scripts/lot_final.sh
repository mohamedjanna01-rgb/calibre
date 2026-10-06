#!/usr/bin/env bash
# Transcription hybride locale des appels restants, puis notation Gemma des 13 appels sur cette transcription.
# Un seul processus ; 75 s entre deux requêtes (Gemma : 16 000 tokens d'entrée par minute) ;
# une seule nouvelle tentative pour chaque échec, à la fin. Détail complet (erreurs comprises) : audio/brut/lot-detail.log
cd "$(dirname "$0")/.." || exit 1
export PYTHONIOENCODING=utf-8
PY=.venv/Scripts/python
echec_t=(); echec_n=()
for n in $1; do
  $PY scripts/hybride_locale.py "$n" >> audio/brut/lot-detail.log 2>&1; tail -1 audio/brut/lot-detail.log
  [ -f "transcriptions/hybride-locale/appel-$n.json" ] || echec_t+=("$n")
  sleep 75
done
for n in "${echec_t[@]}"; do
  echo "nouvelle tentative : transcription de l'appel $n"
  $PY scripts/hybride_locale.py "$n" >> audio/brut/lot-detail.log 2>&1; tail -1 audio/brut/lot-detail.log; sleep 75
done
DOSSIER=notations/gemma-4-26b-a4b-it-reduit-${SOURCE:-hybride-locale}${PASSE:+-passe$PASSE}
for n in $2; do
  [ -f "transcriptions/${SOURCE:-hybride-locale}/appel-$n.json" ] || { echo "appel $n : pas de transcription, notation impossible"; continue; }
  $PY scripts/noter.py --appels "$n" --modele gemma-4-26b-a4b-it --reduit --source "${SOURCE:-hybride-locale}" ${PASSE:+--passe $PASSE} >> audio/brut/lot-detail.log 2>&1; tail -1 audio/brut/lot-detail.log
  [ -f "$DOSSIER/appel-$n.json" ] || echec_n+=("$n")
  sleep 75
done
for n in "${echec_n[@]}"; do
  echo "nouvelle tentative : notation de l'appel $n"
  $PY scripts/noter.py --appels "$n" --modele gemma-4-26b-a4b-it --reduit --source "${SOURCE:-hybride-locale}" ${PASSE:+--passe $PASSE} >> audio/brut/lot-detail.log 2>&1; tail -1 audio/brut/lot-detail.log; sleep 75
done
echo "=== FIN $(date +%H:%M:%S)"
