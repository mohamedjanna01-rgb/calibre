# Évaluation de la transcription – pilote

| Appel | Méthode | Mots retrouvés | WER | Mots au bon locuteur | Répliques bien attribuées | Preuves exactes | Preuves au bon locuteur | Masques (scén./transc.) | [inaudible] | Mots inventés /100 | Horodatage |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 03 | gemini-3.8-flash | 95.5 % | 5.5 % | 100.0 % | 100.0 % | 3/3 | 3/3 | 1/1 | 2 | 2.7 | INCOHÉRENT |
| 03 | whisper-small | 87.3 % | 13.6 % | 72.4 % | 56.0 % | 2/3 | 2/3 | 1/1 | 24 | 6.6 | cohérent |
| 03 | whisper-medium | 93.9 % | 6.6 % | 73.8 % | 70.8 % | 2/3 | 2/3 | 1/1 | 11 | 2.0 | cohérent |
| 10 | whisper-small | 86.0 % | 15.0 % | 78.3 % | 65.0 % | 3/4 | 3/4 | 0/0 | 6 | 8.9 | cohérent |
| 10 | whisper-medium | 93.0 % | 10.3 % | 75.4 % | 55.0 % | 4/4 | 4/4 | 0/0 | 3 | 8.4 | cohérent |

## Preuves non retrouvées telles quelles

- Appel 03 / whisper-small : « Calmez-vous, Monsieur Martin » (absente)
- Appel 03 / whisper-medium : « Calmez-vous, Monsieur Martin » (absente)
- Appel 10 / whisper-small : « Tous les parents le prennent » (absente)
