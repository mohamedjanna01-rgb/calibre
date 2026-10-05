# Évaluation de la transcription – bilan-intermediaire

| Appel | Méthode | Mots retrouvés | WER | Mots au bon locuteur | Répliques bien attribuées | Preuves exactes | Preuves au bon locuteur | Masques (scén./transc.) | [inaudible] | Mots inventés /100 | Horodatage | Écart médian | Répliques à moins d'1 s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 01 | hybride | 96.7 % | 3.3 % | 100.0 % | 100.0 % | 0/0 | 0/0 | 2/2 | 0 | 1.9 | cohérent | 0.24 s | 92.9 % |
| 01 | gemini-3.5-transcribe | 95.2 % | 4.8 % | 99.6 % | 97.5 % | 0/0 | 0/0 | 2/2 | 0 | 2.8 | cohérent | 0.21 s | 97.5 % |
| 01 | whisper-medium | 89.7 % | 11.2 % | 65.9 % | 73.7 % | 0/0 | 0/0 | 2/2 | 5 | 8.5 | cohérent | 0.19 s | 97.4 % |
| 02 | hybride | 99.8 % | 0.2 % | 100.0 % | 100.0 % | 0/0 | 0/0 | 1/1 | 0 | 0.2 | cohérent | 0.12 s | 95.7 % |
| 02 | gemini-3.5-transcribe | 98.0 % | 2.0 % | 99.8 % | 100.0 % | 0/0 | 0/0 | 1/1 | 0 | 1.8 | cohérent | 0.08 s | 100.0 % |
| 02 | whisper-medium | 98.0 % | 4.5 % | 59.8 % | 68.2 % | 0/0 | 0/0 | 1/1 | 2 | 4.5 | cohérent | 0.13 s | 100.0 % |
| 03 | hybride | 95.5 % | 5.5 % | 100.0 % | 100.0 % | 3/3 | 3/3 | 1/1 | 2 | 2.7 | cohérent | 0.23 s | 92.9 % |
| 03 | gemini-3.5-transcribe | 98.0 % | 2.3 % | 100.0 % | 100.0 % | 3/3 | 3/3 | 1/1 | 0 | 1.1 | cohérent | 0.18 s | 92.0 % |
| 03 | whisper-medium | 95.5 % | 5.2 % | 74.0 % | 70.8 % | 3/3 | 3/3 | 1/1 | 2 | 2.7 | cohérent | 0.16 s | 95.0 % |
| 04 | hybride | 97.1 % | 3.5 % | 100.0 % | 100.0 % | 3/3 | 3/3 | 1/1 | 0 | 2.3 | cohérent | 0.16 s | 94.7 % |
| 04 | gemini-3.5-transcribe | 97.1 % | 3.5 % | 100.0 % | 100.0 % | 3/3 | 3/3 | 1/1 | 0 | 2.9 | cohérent | 0.1 s | 94.7 % |
| 04 | whisper-medium | 95.3 % | 5.2 % | 70.7 % | 57.9 % | 3/3 | 3/3 | 1/1 | 0 | 3.5 | cohérent | 0.18 s | 100.0 % |
| 05 | hybride | 100.0 % | 0.0 % | 100.0 % | 100.0 % | 3/3 | 3/3 | 1/1 | 0 | 0.0 | cohérent | 0.12 s | 95.2 % |
| 05 | gemini-3.5-transcribe | 98.4 % | 2.3 % | 85.5 % | 85.7 % | 3/3 | 3/3 | 1/1 | 0 | 1.3 | cohérent | 0.1 s | 100.0 % |
| 05 | whisper-medium | 97.4 % | 2.6 % | 73.0 % | 52.4 % | 3/3 | 3/3 | 1/1 | 2 | 1.9 | cohérent | 1.04 s | 0.0 % |
| 06 | gemini-3.5-transcribe | 97.9 % | 3.4 % | 99.7 % | 100.0 % | 4/4 | 4/4 | 1/1 | 0 | 2.5 | cohérent | 0.26 s | 100.0 % |
| 06 | whisper-medium | 98.2 % | 3.4 % | 76.6 % | 85.7 % | 2/4 | 3/4 | 1/1 | 1 | 2.5 | cohérent | 0.29 s | 95.0 % |
| 07 | gemini-3.5-transcribe | 94.4 % | 5.9 % | 98.1 % | 92.7 % | 0/0 | 0/0 | 0/0 | 0 | 3.8 | cohérent | 0.18 s | 100.0 % |
| 07 | whisper-medium | 92.9 % | 8.0 % | 63.8 % | 46.3 % | 0/0 | 0/0 | 0/0 | 6 | 5.6 | cohérent | 0.14 s | 96.1 % |
| 08 | gemini-3.5-transcribe | 99.5 % | 0.8 % | 80.5 % | 47.6 % | 0/0 | 0/0 | 0/0 | 0 | 0.8 | cohérent | 0.1 s | 100.0 % |
| 08 | whisper-medium | 97.2 % | 3.1 % | 50.0 % | 57.1 % | 0/0 | 0/0 | 0/0 | 1 | 2.6 | cohérent | 0.12 s | 100.0 % |
| 09 | gemini-3.5-transcribe | 98.2 % | 3.7 % | 70.0 % | 61.9 % | 0/0 | 0/0 | 0/0 | 0 | 3.7 | cohérent | 0.08 s | 100.0 % |
| 09 | whisper-medium | 96.1 % | 6.1 % | 21.1 % | 47.6 % | 0/0 | 0/0 | 0/0 | 1 | 5.3 | cohérent | 0.1 s | 100.0 % |
| 10 | gemini-3.5-transcribe | 94.9 % | 5.1 % | 100.0 % | 100.0 % | 4/4 | 4/4 | 0/0 | 0 | 1.4 | cohérent | 0.16 s | 100.0 % |
| 10 | whisper-medium | 94.4 % | 8.9 % | 74.8 % | 55.0 % | 4/4 | 4/4 | 0/0 | 1 | 8.9 | cohérent | 0.04 s | 100.0 % |
| 11 | gemini-3.5-transcribe | 96.5 % | 3.5 % | 98.2 % | 91.3 % | 4/4 | 4/4 | 0/0 | 0 | 2.9 | cohérent | 0.08 s | 100.0 % |
| 11 | whisper-medium | 97.9 % | 2.1 % | 76.9 % | 58.3 % | 4/4 | 4/4 | 0/0 | 0 | 1.5 | cohérent | 0.1 s | 100.0 % |
| 12 | gemini-3.5-transcribe | 96.3 % | 4.4 % | 29.5 % | 44.8 % | 1/3 | 0/3 | 0/0 | 0 | 2.6 | cohérent | 0.18 s | 82.6 % |
| 12 | whisper-medium | 97.1 % | 4.4 % | 31.9 % | 44.8 % | 2/3 | 2/3 | 0/0 | 3 | 3.1 | cohérent | 0.18 s | 84.0 % |
| 13 | gemini-3.5-transcribe | 96.9 % | 4.1 % | 77.9 % | 51.5 % | 2/4 | 3/4 | 0/0 | 0 | 3.7 | cohérent | 0.36 s | 100.0 % |
| 13 | whisper-medium | 92.1 % | 8.6 % | 18.1 % | 35.5 % | 2/4 | 0/4 | 0/0 | 2 | 7.7 | cohérent | 0.19 s | 96.7 % |

## Preuves non retrouvées telles quelles

- Appel 06 / whisper-medium : « Mon responsable vous dira la même chose » (absente)
- Appel 06 / whisper-medium : « Voilà, c'est activé, vous l'avez dès ce soir » (approchée)
- Appel 12 / gemini-3.5-transcribe : « je vous bloque le prix à 6,99 € par mois pendant un an » (approchée, mauvais locuteur)
- Appel 12 / gemini-3.5-transcribe : « cette remise n'est valable qu'aujourd'hui » (approchée, mauvais locuteur)
- Appel 12 / gemini-3.5-transcribe : « le système affiche toujours le tarif standard. Votre remise sera appliquée automatiquement » (exacte, mauvais locuteur)
- Appel 12 / whisper-medium : « je vous bloque le prix à 6,99 € par mois pendant un an » (approchée)
- Appel 12 / whisper-medium : « le système affiche toujours le tarif standard. Votre remise sera appliquée automatiquement » (exacte, mauvais locuteur)
- Appel 13 / gemini-3.5-transcribe : « les seize chiffres au recto » (absente)
- Appel 13 / gemini-3.5-transcribe : « les trois chiffres au dos, le cryptogramme » (approchée)
- Appel 13 / whisper-medium : « il doit être rattaché à une carte, sinon l'activation peut prendre plusieurs jours » (exacte, mauvais locuteur)
- Appel 13 / whisper-medium : « les seize chiffres au recto » (absente)
- Appel 13 / whisper-medium : « la date d'expiration » (absente)
- Appel 13 / whisper-medium : « les trois chiffres au dos, le cryptogramme » (exacte, mauvais locuteur)
