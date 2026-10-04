---
id: DOC-02
titre: Diagnostic à distance – Internet fibre et box
domaine: Technique
public: Conseillers N1 – Particuliers
version: 1.0
date_maj: 2026-09-30
statut: FICTIF – projet de démonstration, aucune donnée réelle
---

# Diagnostic à distance – Internet fibre et box

> Objet : diagnostiquer à distance une coupure totale, des coupures répétées ou une lenteur de la connexion fibre, et décider s'il faut redémarrer la box, la réinitialiser, l'échanger, ouvrir un ticket N2 ou planifier un technicien.

Concerne les box Nova 5, Nova 6 et Nova 7 (fibre). La Box 4G Maison (Nova Air) suit le diagnostic mobile de DOC-04, section 3 (vérifications de l'appareil).

## 1. Vérifications obligatoires avant tout diagnostic

**[FIB-01]** Avant de poser la moindre question technique, le conseiller vérifie dans Orbite, dans cet ordre :
1. **Bandeau INC** : si un incident collectif touche l'adresse, **pas de diagnostic, pas d'échange de box, pas de rendez-vous technicien**. Voir section 8.
2. **Suspension pour impayé** : si la ligne est suspendue, le problème n'est pas technique. Voir DOC-07, section 3.
3. **Commande ou déménagement en cours** : une box en cours d'activation (délai de 3 à 10 jours après un déménagement, voir DOC-10) n'est pas en panne.
4. **Tickets ouverts** : si un ticket est déjà ouvert pour le même problème, on le reprend au lieu d'en créer un nouveau.

**[FIB-02]** Le conseiller demande ensuite quelle box est concernée si le compte en a plusieurs (identifiant box BX-xxxxxx, voir DOC-11).

## 2. Code couleur du voyant des box Nova

Toutes les box Nova fibre (5, 6 et 7) utilisent le même code couleur sur le voyant en façade.

| Voyant | Signification | Action |
|---|---|---|
| Blanc fixe | Box connectée, internet fonctionnel | Le problème vient du Wi-Fi ou de l'appareil → Arbre C |
| Blanc clignotant | Démarrage en cours (jusqu'à 5 minutes) | Faire patienter 5 minutes |
| Orange fixe | Pas de signal fibre | Arbre A, étape « orange fixe » |
| Orange clignotant | Signal fibre présent mais connexion au réseau Kalyo refusée | Arbre A, étape « orange clignotant » |
| Rouge fixe | Défaut matériel de la box | Arbre A, étape « rouge fixe » |
| Éteint | Pas d'alimentation électrique | Arbre A, étape « éteint » |

## 3. Lecture de Sonde

**[FIB-03]** Puissance optique reçue par la box (mesurée par Sonde) :
- **entre -8 et -25 dBm** : normale ;
- **entre -25 et -27 dBm** : limite, des coupures sont possibles ;
- **inférieure à -27 dBm ou « LOS »** (perte de signal) : aucun signal exploitable.

**[FIB-04]** Si Sonde affiche la box « hors ligne », aucune action à distance n'est possible (ni redémarrage, ni réinitialisation). Le client doit agir lui-même sur la box.

## 4. Gestes de base (à faire faire au client)

**[FIB-05] Redémarrage de la box** : débrancher le câble d'alimentation de la box, attendre 30 secondes, le rebrancher, puis attendre 5 minutes que le voyant passe au blanc fixe. Si la box est en ligne dans Sonde, le conseiller peut aussi lancer le redémarrage à distance.

**[FIB-06] Réinitialisation usine** : à distance avec Sonde (box en ligne) ou en appuyant 15 secondes sur le bouton « Reset » au dos de la box avec la pointe d'un trombone. Durée : environ 10 minutes. **Prévenir le client avant** : le nom et le mot de passe Wi-Fi personnalisés ainsi que les réglages avancés sont effacés. La box revient au nom et à la clé Wi-Fi inscrits sur l'étiquette sous la box.

## 5. Arbre A – Plus d'internet du tout

Point de départ : le client n'a plus internet sur aucun appareil. Demander la couleur du voyant de la box.

**Voyant éteint**
1. Vérifier que la box est branchée sur une prise murale qui fonctionne (tester avec une lampe) plutôt que sur une multiprise, et que le bouton marche/arrêt est sur ON.
2. Toujours éteint → **échange standard de la box** (section 9).

**Voyant rouge fixe**
1. Redémarrage [FIB-05].
2. Toujours rouge → réinitialisation usine [FIB-06].
3. Toujours rouge → **échange standard de la box**.

**Voyant orange fixe (pas de signal fibre)**
1. Faire vérifier le câble fibre entre la prise murale (PTO) et la box : bien enfoncé des deux côtés (un « clic » se fait entendre), pas plié, pas écrasé par un meuble, pas de capuchon de protection oublié.
2. Redémarrage [FIB-05].
3. Contrôler la puissance optique dans Sonde (les dernières valeurs remontées restent visibles même box hors ligne) :
   - **LOS ou inférieure à -27 dBm** alors que le câble est en bon état → problème de prise ou de réseau → **rendez-vous technicien** (DOC-05).
   - Câble abîmé ou cassé → envoi d'un câble fibre de remplacement (gratuit, 3 à 5 jours ouvrés). Si la PTO elle-même est arrachée ou endommagée → **rendez-vous technicien**.
   - **Puissance normale** mais voyant toujours orange fixe → la box ne lit pas le signal → **échange standard de la box**.

**Voyant orange clignotant (connexion refusée)**
1. Lancer « Resynchronisation profil » dans Sonde, puis redémarrage [FIB-05].
2. Toujours orange clignotant → **ticket N2 « Authentification »** (rappel sous 48 heures ouvrées). **Pas de technicien** : le problème n'est pas physique.

**Voyant blanc fixe mais pas d'internet**
1. Faire tester un appareil branché en câble Ethernet directement sur la box.
2. Ça fonctionne en câble → problème de Wi-Fi → Arbre C.
3. Ça ne fonctionne pas en câble non plus → redémarrage [FIB-05], puis ticket N2 « Service ».

## 6. Arbre B – La connexion coupe régulièrement

**[FIB-07]** Consulter dans Sonde l'historique des désynchronisations sur 7 jours.

1. **5 désynchronisations ou plus sur 7 jours** :
   - avec une puissance optique limite (-25 à -27 dBm) ou très variable → faire vérifier les courbures et l'état du câble fibre. Câble en bon état → **rendez-vous technicien** (DOC-05). Câble abîmé → envoi d'un câble de remplacement, puis nouveau contrôle sous 7 jours ;
   - avec une puissance normale et des redémarrages de la box au même moment → surchauffe possible : la box doit être à l'air libre, pas dans un meuble fermé ni posée sur un autre appareil. Si le problème continue après 48 heures dans un endroit ventilé → **échange standard de la box**.
2. **Aucune désynchronisation dans Sonde**, mais le client dit que « ça coupe » → la connexion fibre est stable, les coupures viennent du Wi-Fi ou des appareils → Arbre C.

## 7. Arbre C – Lenteur et Wi-Fi

1. **Test en câble Ethernet** : faire lancer le test de débit de l'application Kalyo & Moi (menu « Ma box > Tester mon débit ») sur un ordinateur branché en câble sur la box.
   - **[FIB-08]** Débit en câble **supérieur ou égal à 300 Mb/s** → la ligne est conforme ; le problème vient du Wi-Fi ou de l'appareil (étape 2).
   - Débit en câble inférieur à 300 Mb/s → vérifier que le câble Ethernet n'est pas abîmé et que l'ordinateur accepte 1 Gb/s. Si c'est toujours lent → **ticket N2 « Débit »** (analyse sous 48 heures ouvrées).
2. **Améliorer le Wi-Fi** :
   - rapprocher l'appareil de la box, éviter les murs porteurs, les miroirs et les aquariums entre les deux ;
   - la box ne doit pas être dans un meuble fermé ni au sol derrière la télévision ;
   - lancer « Optimisation Wi-Fi » dans Sonde (changement automatique de canal) ;
   - près de la box, utiliser le réseau Wi-Fi 5 GHz (plus rapide) ; loin de la box, le 2,4 GHz (porte plus loin) ;
   - regarder dans Sonde le nombre d'appareils connectés : au-delà de 30, les performances peuvent baisser.
3. Si le logement est grand ou à étages et que le signal est faible dans certaines pièces → proposer le **Répéteur Wi-Fi Kalyo** (3 €/mois, voir DOC-01).

**[FIB-09]** Le débit indiqué dans les offres est un **maximum théorique**, en câble. En Wi-Fi, le débit réel est toujours inférieur. Aucun débit précis ne doit être garanti au client.

## 8. Incident collectif

**[FIB-10]** Si le bandeau INC est affiché :
1. Informer le client qu'un incident touche sa zone. Donner l'heure prévisionnelle de rétablissement (HPR) si elle existe, en précisant qu'il s'agit d'une estimation.
2. Rattacher le client à l'incident dans Orbite (bouton « Associer à INC ») : il recevra un SMS au rétablissement.
3. Aucun diagnostic, aucun échange de box, aucun rendez-vous technicien pendant un incident collectif.
4. L'indemnisation d'un incident collectif de plus de 72 heures est **automatique** : le conseiller ne la saisit pas lui-même, pour éviter un double remboursement (voir DOC-08).
5. Solution de dépannage si l'HPR dépasse 72 heures : voir DOC-08, section 4.

## 9. Échange standard de la box

**[FIB-11]** L'échange est possible uniquement après un diagnostic concluant :
- voyant éteint alors que la prise électrique fonctionne ;
- voyant rouge fixe malgré une réinitialisation ;
- voyant orange fixe avec une puissance optique normale ;
- redémarrages répétés de la box malgré un emplacement ventilé.

**[FIB-12]** Conditions de l'échange :
- **gratuit**, livraison express en 24 à 48 heures ouvrées ;
- l'ancienne box est à renvoyer sous **15 jours** avec l'étiquette prépayée fournie dans le colis, sinon la pénalité de non-restitution est facturée (DOC-01, [CAT-14]) ;
- **1 seul échange par période de 6 mois sans validation**. Pour un 2e échange dans les 6 mois, il faut la validation du N2 : des pannes répétées cachent souvent un problème de câble ou d'installation électrique.

## 10. Téléphone fixe en panne (internet fonctionne)

**[FIB-13]**
1. Vérifier que le téléphone est branché sur la prise « Tél 1 » de la box.
2. Vérifier dans Orbite que la ligne fixe est bien active sur le contrat.
3. Redémarrer la box [FIB-05] et tester avec un autre téléphone si possible.
4. Toujours en panne → ticket N2 « Téléphonie » (rappel sous 48 heures ouvrées).

## 11. Formulations recommandées

- « Je vais vous guider pas à pas, cela prend quelques minutes. Pouvez-vous me dire de quelle couleur est le petit voyant à l'avant de votre box ? »
- « Avant de redémarrer la box, je vous préviens : internet sera coupé environ 5 minutes. »
- En cas d'incident : « Je vois qu'un incident touche actuellement votre quartier. Nos équipes sont déjà mobilisées et le rétablissement est estimé à [HPR]. Je vous inscris pour recevoir un SMS dès que c'est rétabli. »

## 12. Vigilance – ce qu'il ne faut pas promettre

- Ne jamais garantir un débit précis, en particulier en Wi-Fi [FIB-09].
- Ne pas promettre un technicien avant d'avoir suivi l'arbre complet et vérifié les critères de DOC-05.
- Ne pas annoncer une heure de rétablissement ferme pendant un incident : l'HPR est une estimation.
- Ne pas faire réinitialiser la box sans avoir prévenu que les réglages Wi-Fi personnalisés seront perdus.
- Ne pas lancer un 2e échange de box dans les 6 mois sans validation du N2.

## 13. Escalade

| Situation | Destination | Mode |
|---|---|---|
| Voyant orange clignotant persistant | Support Technique N2 | Ticket « Authentification » |
| Débit en câble inférieur à 300 Mb/s | Support Technique N2 | Ticket « Débit » |
| 2e échange de box en moins de 6 mois | Support Technique N2 | Validation préalable |
| Signal absent ou PTO endommagée | Technicien | Plan'Inter (DOC-05) |
| Panne de plus de 5 jours ou 3e appel | Voir DOC-08 | — |

## Documents liés

DOC-01 (équipements et pénalités), DOC-05 (intervention technicien), DOC-08 (pannes longues), DOC-14 (escalade).
