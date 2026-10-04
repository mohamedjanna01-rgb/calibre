# Évaluation de la transcription – pilote

| Appel | Méthode | Mots retrouvés | WER | Mots au bon locuteur | Répliques bien attribuées | Preuves exactes | Preuves au bon locuteur | Masques (scén./transc.) | [inaudible] | Mots inventés /100 | Horodatage | Écart médian | Répliques à moins d'1 s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 03 | gemini-3.8-flash | 95.5 % | 5.5 % | 100.0 % | 100.0 % | 3/3 | 3/3 | 1/1 | 2 | 2.7 | INCOHÉRENT | 39.86 s | 25.0 % |
| 03 | hybride | 95.5 % | 5.5 % | 100.0 % | 100.0 % | 3/3 | 3/3 | 1/1 | 2 | 2.7 | cohérent | 0.23 s | 92.9 % |
| 03 | gemini-3.5-transcribe | 97.7 % | 2.3 % | 100.0 % | 100.0 % | 3/3 | 3/3 | 1/0 | 0 | 1.1 | cohérent | 0.18 s | 92.0 % |
| 03 | whisper-medium | 95.5 % | 5.2 % | 74.0 % | 70.8 % | 3/3 | 3/3 | 1/1 | 2 | 2.7 | cohérent | 0.16 s | 95.0 % |
| 03 | whisper-small | 87.3 % | 13.6 % | 72.4 % | 56.0 % | 2/3 | 2/3 | 1/1 | 24 | 6.6 | cohérent | 0.08 s | 92.9 % |
| 10 | gemini-3.5-transcribe | 94.9 % | 5.1 % | 100.0 % | 100.0 % | 4/4 | 4/4 | 0/0 | 0 | 1.4 | cohérent | 0.16 s | 100.0 % |
| 10 | whisper-medium | 94.4 % | 8.9 % | 74.8 % | 55.0 % | 4/4 | 4/4 | 0/0 | 1 | 8.9 | cohérent | 0.04 s | 100.0 % |
| 10 | whisper-small | 86.0 % | 15.0 % | 78.3 % | 65.0 % | 3/4 | 3/4 | 0/0 | 6 | 8.9 | cohérent | 0.04 s | 100.0 % |

## Preuves non retrouvées telles quelles

- Appel 03 / whisper-small : « Calmez-vous, Monsieur Martin » (absente)
- Appel 10 / whisper-small : « Tous les parents le prennent » (absente)
