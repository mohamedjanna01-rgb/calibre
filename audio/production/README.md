# Scripts de production audio

Un fichier par appel (`appel-01.yaml` à `appel-13.yaml`). Chaque fichier décrit comment générer les répliques et comment les assembler. Il ne doit **jamais être transmis à l'IA qui note** : les consignes de ton révèlent les fautes à détecter.

## Génération

- **Une requête par appel complet**, avec les deux voix, produite par un **seul modèle**. Script : [scripts/generer_audio.py](../../scripts/generer_audio.py). La répartition des appels entre modèles est fixée dans [repartition.yaml](repartition.yaml) : le script refuse tout autre modèle.
- Modèles 3.8 (route `interactions`) : chaque réplique porte son locuteur et son style (`speech_metadata.style` = profil du personnage + ton de la réplique). Modèles 3.1 et 2.5 (route `generateContent`) : les consignes sont écrites entre crochets devant chaque réplique, avec l'ordre de ne pas les lire.
- Stabilité des voix : chaque consigne répète la description du locuteur (genre, âge, timbre) et demande un rythme naturel et posé de conversation téléphonique.
- Pauses et interruptions : une courte pause est ajoutée entre les phrases d'une même réplique et entre les répliques. Une pause longue devient `<long pause>`. Une réplique `coupee` est générée inachevée, et celle qui `chevauche` enchaîne sans pause, avec la consigne de couper la parole.
- Sortie : seule la version avec effet de ligne téléphonique est conservée, dans `audio/appels/` (WAV mono, 8 kHz). L'effet est appliqué par [scripts/effet_telephone.py](../../scripts/effet_telephone.py) : filtre de 300 à 3 400 Hz, son ramené à 8 kHz, codage G.711, léger bruit de ligne. L'audio final est en **mono**.
- Offre gratuite : un compteur local (`audio/.compteur-requetes.json`, non versionné) bloque tout dépassement de **10 requêtes par modèle sur 24 heures glissantes** et de **3 par minute**. Une requête en échec compte aussi, et il n'y a jamais de nouvel essai automatique. `--etat` affiche les requêtes restantes, `--simulation` montre la requête sans l'envoyer.
- La clé est lue dans la variable d'environnement locale `GEMINI_API_KEY`. Elle n'est jamais écrite dans un fichier.

## Format d'une réplique

| Champ | Rôle |
|---|---|
| `n` | Numéro de la réplique dans l'appel |
| `locuteur` | `conseiller` ou `client` |
| `texte` | Mots réellement prononcés. Les balises en anglais entre chevrons (`<sigh>`, `<chuckle>`, `<short pause>`, `<long pause>`) sont des effets de voix. Elles sont retirées de la référence de transcription. |
| `ton` | Consigne de ton pour cette réplique |
| `pause_avant_ms` | Silence avant la réplique. Valeur par défaut : 400 ms. |
| `chevauchement_ms` | La réplique coupe la parole à la précédente. En génération en une seule requête, cela devient une consigne d'enchaîner sans blanc (la valeur sert d'indication). |
| `coupee` | La réplique est interrompue : elle est générée inachevée, coupée net. |

Le fichier [prononciation.yaml](prononciation.yaml) indique comment faire prononcer les adresses e-mail, les numéros de carte fictifs et les sigles. Le texte écrit reste la référence.

## Évaluation de la transcription

La génération en une seule requête ne fournit pas d'horodatage. La transcription est évaluée **mot par mot** à partir du texte des scénarios ([scenarios/](../../scenarios/)), une fois les balises de voix retirées.

## Casting

26 voix différentes, une par personnage, toutes différentes d'un appel à l'autre. Le genre et l'âge perçus sont à confirmer à l'écoute.

| Appel | Conseiller | Voix | Client | Voix |
|---|---|---|---|---|
| 01 | Yanis Benali, 30 ans | Achird | Claire Lefèvre, 41 ans | Autonoe |
| 02 | Sofia Haddad, 31 ans | Sulafat | Thomas Garnier, 47 ans | Iapetus |
| 03 | Inès Kaddouri, 26 ans | Aoede | Julien Martin, 36 ans | Fenrir |
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

Tous les personnages parlent un français standard. Voix en réserve, pour remplacer une voix qui sonnerait mal en français : Pulcherrima, Callirrhoe et Vindemiatrix (voix féminines), Enceladus (voix masculine).
