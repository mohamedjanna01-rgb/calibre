#!/usr/bin/env bash
# Un seul processus (un seul compteur à la fois) : transcription A (Gemini 3.8 Flash) et notation Gemma en alternance.
# Transcription : une seule nouvelle tentative par appel en cas de 503 ; si le 503 persiste, appel suivant.
# Un refus lié au quota (compteur local ou erreur 429 de Google) arrête le modèle concerné.
# 70 s entre deux tours : Gemma est limité à 16 000 tokens d'entrée par minute.
# Usage : bash scripts/lot_transcription_notation.sh "06 07 08" "01 02 03"
cd "$(dirname "$0")/.." || exit 1
export PYTHONIOENCODING=utf-8
PY=.venv/Scripts/python
read -ra A <<< "$1"
read -ra N <<< "$2"
A_ACTIF=1; N_ACTIF=1; i=0; j=0
while { [ $A_ACTIF = 1 ] && [ $i -lt ${#A[@]} ]; } || { [ $N_ACTIF = 1 ] && [ $j -lt ${#N[@]} ]; }; do
  if [ $A_ACTIF = 1 ] && [ $i -lt ${#A[@]} ]; then
    n=${A[$i]}; i=$((i + 1))
    if [ -f "transcriptions/gemini-3.8-flash/appel-$n.json" ]; then
      echo "A : appel $n déjà transcrit, sauté"
    else
      sortie=$($PY scripts/transcrire.py --methode gemini-3.8-flash --appels "$n" 2>&1); echo "$sortie"
      if echo "$sortie" | grep -q "Refusé\|HTTP 429"; then A_ACTIF=0; echo "ARRÊT A : quota atteint"
      elif ! echo "$sortie" | grep -q "répliques en"; then echo "A : appel $n en échec (503 persistant), passage au suivant"; fi
    fi
  fi
  if [ $N_ACTIF = 1 ] && [ $j -lt ${#N[@]} ]; then
    n=${N[$j]}; j=$((j + 1))
    sortie=$($PY scripts/noter.py --appels "$n" --modele gemma-4-26b-a4b-it --reduit 2>&1); echo "$sortie"
    if echo "$sortie" | grep -q "Refusé\|HTTP 429"; then N_ACTIF=0; echo "ARRÊT Gemma : quota atteint"
    elif ! echo "$sortie" | grep -q " % · "; then echo "Gemma : notation de l'appel $n en échec, passage au suivant"; fi
  fi
  sleep 70
done
echo "=== FIN $(date +%H:%M:%S)"
$PY scripts/generer_audio.py --etat | grep -E "gemini-3.8-flash |gemma"
