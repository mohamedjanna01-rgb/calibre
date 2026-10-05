#!/usr/bin/env bash
# Pilote de notation : les deux modèles alternent dans un seul processus (un seul compteur à la fois).
cd "$(dirname "$0")/.." || exit 1
export PYTHONIOENCODING=utf-8
FLASH=1; GEMMA=1
for n in 01 02 03 04 05; do
  [ $FLASH = 1 ] && { .venv/Scripts/python scripts/noter.py --appels $n --modele gemini-3.8-flash || { FLASH=0; echo "ARRÊT gemini-3.8-flash : échec sur l'appel $n"; }; }
  [ $GEMMA = 1 ] && { .venv/Scripts/python scripts/noter.py --appels $n --modele gemma-4-26b-a4b-it || { GEMMA=0; echo "ARRÊT gemma : échec sur l'appel $n"; }; }
  sleep 90
done
echo "=== FIN $(date +%H:%M:%S)"
