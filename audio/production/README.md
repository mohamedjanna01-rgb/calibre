# Scripts de production audio

Un fichier par appel (`appel-01.yaml` à `appel-13.yaml`). Chaque fichier décrit comment générer les répliques et comment les assembler. Il ne doit **jamais être transmis à l'IA qui note** : les consignes de ton révèlent les fautes à détecter.

## Génération

- Modèle : `gemini-3.8-flash-tts`, avec **une requête par réplique**. Le style est donné par `speech_metadata.style`, qui combine le profil du personnage et le ton de la réplique.
- Sortie : WAV mono, 24 kHz, 16 bits. L'assemblage applique ensuite l'effet de ligne téléphonique : filtre de 300 à 3 400 Hz, son ramené à 8 kHz, codage G.711, léger bruit de ligne. L'audio final est en **mono**.
- La clé est lue dans la variable d'environnement locale `GEMINI_API_KEY`. Elle n'est jamais écrite dans un fichier.

## Format d'une réplique

| Champ | Rôle |
|---|---|
| `n` | Numéro de la réplique dans l'appel |
| `locuteur` | `conseiller` ou `client` |
| `texte` | Mots réellement prononcés. Les balises en anglais entre chevrons (`<sigh>`, `<chuckle>`, `<short pause>`, `<long pause>`) sont des effets de voix. Elles sont retirées de la référence de transcription. |
| `ton` | Consigne de ton pour cette réplique |
| `pause_avant_ms` | Silence avant la réplique. Valeur par défaut : 400 ms. |
| `chevauchement_ms` | La réplique démarre ce nombre de millisecondes **avant** la fin de la précédente : les deux voix se superposent. |
| `coupee` | La réplique est interrompue : elle est générée inachevée, puis s'éteint en fondu sous la réplique suivante. |

Le fichier [prononciation.yaml](prononciation.yaml) indique comment faire prononcer les adresses e-mail, les numéros de carte fictifs et les sigles. Le texte écrit reste la référence.

## Horodatage

L'assemblage écrit, pour chaque appel, un fichier `appel-XX.json` avec le début, la fin, le locuteur et le texte de chaque réplique, au millième de seconde, chevauchements compris. Ce fichier sert de référence pour évaluer la transcription.

## Casting

26 voix différentes, une par personnage, toutes différentes d'un appel à l'autre. Le genre et l'âge perçus sont à confirmer à l'écoute.

| Appel | Conseiller | Voix | Client | Voix |
|---|---|---|---|---|
| 01 | Yanis Benali, 30 ans | Achird | Claire Lefèvre, 41 ans | Autonoe |
| 02 | Sofia Haddad, 31 ans | Sulafat | Thomas Garnier, 47 ans | Iapetus |
| 03 | Inès Kaddouri, 26 ans | Pulcherrima | Julien Martin, 36 ans | Fenrir |
| 04 | Conseiller non nommé, 42 ans | Schedar | Nathalie Roux, 58 ans | Achernar |
| 05 | Karim Tazi, 35 ans | Umbriel | Antoine Petit, 38 ans | Zubenelgenubi |
| 06 | Mehdi Alaoui, 40 ans | Alnilam | Sandrine Benoît, 51 ans | Kore |
| 07 | Samir El Idrissi, 33 ans | Puck | Philippe Durand, 44 ans | Sadaltager |
| 08 | Leïla Amrani, 35 ans | Laomedeia | Isabelle Moreau, 56 ans | Erinome |
| 09 | Nabil Chraibi, 27 ans | Charon | Gérard Lambert, 68 ans | Algenib |
| 10 | Conseillère non nommée, 24 ans | Leda | Céline Fabre, 42 ans | Zephyr |
| 11 | Hamza Benjelloun, 29 ans | Sadachbia | Laurent Girard, 49 ans | Orus |
| 12 | Salma Idrissi, 32 ans | Despina | Monique Chevalier, 64 ans | Gacrux |
| 13 | Anas Lahlou, 31 ans | Algieba | Michel Rousseau, 50 ans | Rasalgethi |

Voix en réserve, pour remplacer une voix qui sonnerait mal en français : Aoede, Callirrhoe et Vindemiatrix (voix féminines), Enceladus (voix masculine).
