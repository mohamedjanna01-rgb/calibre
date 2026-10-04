#!/usr/bin/env bash
# Transcription des appels avec les deux méthodes Gemini, dans un seul processus (un seul compteur à la fois).
# A (gemini-3.8-flash) : si un appel échoue encore après sa nouvelle tentative (503), A s'arrête pour le reste du lot.
# B (gemini-3.5-transcribe) : même règle, indépendamment de A.
# Attente de 90 s entre deux appels pour espacer les requêtes.
# Usage : bash scripts/transcrire_lot.sh "01 02 04" "01 02 03"
cd "$(dirname "$0")/.." || exit 1
export PYTHONIOENCODING=utf-8
PY=.venv/Scripts/python
A_APPELS=" $1 "
B_APPELS=" $2 "
A_ACTIF=1
B_ACTIF=1
for n in 01 02 03 04 05 06 07 08 09 10 11 12 13; do
  fait=0
  if [ $A_ACTIF = 1 ] && [[ "$A_APPELS" == *" $n "* ]]; then
    $PY scripts/transcrire.py --methode gemini-3.8-flash --appels "$n" || { A_ACTIF=0; echo "ARRÊT A : échec persistant sur l'appel $n, reprise plus tard"; }
    fait=1
  fi
  if [ $B_ACTIF = 1 ] && [[ "$B_APPELS" == *" $n "* ]]; then
    $PY scripts/transcrire.py --methode gemini-3.5-transcribe --appels "$n" || { B_ACTIF=0; echo "ARRÊT B : échec sur l'appel $n"; }
    fait=1
  fi
  [ $fait = 1 ] && sleep 90
done
echo "=== FIN $(date +%H:%M:%S)"
$PY scripts/generer_audio.py --etat | grep -E "gemini-3.8-flash |transcribe"
