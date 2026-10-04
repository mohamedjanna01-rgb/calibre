---
id: DOC-05
titre: Critères et règles de planification d'une intervention technicien
domaine: Technique
public: Conseillers N1 – Particuliers
version: 1.1
date_maj: 2026-10-04
statut: FICTIF – projet de démonstration, aucune donnée réelle
---

# Critères et règles de planification d'une intervention technicien

> Objet : savoir quand un déplacement de technicien est justifié, comment le planifier dans Plan'Inter, ce qu'il coûte et ce qu'il faut annoncer au client.

Une intervention coûte cher et immobilise le client : un rendez-vous inutile est un échec du diagnostic. Le conseiller ne planifie un technicien que si les critères ci-dessous sont réunis.

## 1. Conditions préalables obligatoires

**[INT-01]** Avant tout rendez-vous, **les trois conditions suivantes** doivent être remplies :
1. l'arbre de diagnostic de DOC-02 a été suivi jusqu'au bout et **tracé dans Orbite** (étapes faites et résultats) ;
2. **aucun incident collectif** (bandeau INC) ne touche l'adresse ;
3. le client n'est pas suspendu pour impayé.

## 2. Critères qui justifient un technicien (au moins un)

**[INT-02]**

| Critère | Source de vérification |
|---|---|
| Aucun signal fibre (LOS) ou puissance optique inférieure à -27 dBm, alors que le câble fibre entre la prise et la box est en bon état | Sonde |
| 5 désynchronisations ou plus sur 7 jours avec une puissance limite (-25 à -27 dBm), câble en bon état | Sonde |
| Prise fibre murale (PTO) arrachée, cassée ou endommagée | Déclaration du client, idéalement avec une photo envoyée depuis Kalyo & Moi |
| Premier raccordement (éligibilité « Éligible – raccordable ») ou déménagement dans un logement jamais raccordé | Orbite, onglet Éligibilité (DOC-10) |
| Problème qui continue après un échange de box dans les 30 derniers jours | **Validation du N2 obligatoire** |

## 3. Situations où un technicien ne doit PAS être envoyé

**[INT-03]**
- Problème de Wi-Fi, de portée ou de débit sans fil (DOC-02, Arbre C).
- Panne de box ou de décodeur : on **échange** le matériel (DOC-02 et DOC-03).
- Télécommande.
- Réception mobile (DOC-04, [MOB-08]).
- Câblage Ethernet ou électrique interne au logement du client.
- Incident collectif en cours.
- Voyant orange clignotant (problème d'authentification : ticket N2).

## 4. Prise de rendez-vous dans Plan'Inter

**[INT-04]** Créneaux proposés du lundi au samedi : **8 h – 12 h**, **14 h – 18 h** ou **18 h – 20 h**. Le conseiller propose un créneau et le confirme avec le client.

**[INT-05]** Délais :
- **standard** : premier créneau disponible entre 2 et 5 jours ouvrés ;
- **prioritaire** (sous 48 heures ouvrées), **à demander au N2** : panne totale depuis plus de 5 jours (panne longue, DOC-08), client ayant déclaré une téléassistance médicale reliée à la box, ou 3e appel pour le même incident.

**[INT-06]** Le conseiller vérifie et note dans le rendez-vous :
- l'adresse exacte, le bâtiment, l'escalier, l'étage, la porte ;
- le code d'accès, le digicode ou le badge nécessaire pour entrer ;
- un numéro de téléphone joignable le jour J ;
- l'emplacement de la prise fibre (PTO) et de la box.

**[INT-13] Confirmation et rappel** : dès que le rendez-vous est enregistré dans Plan'Inter, le client reçoit un **SMS de confirmation** (date, créneau, adresse), puis un **SMS de rappel la veille** de l'intervention. Le conseiller l'annonce au client avant de conclure.

## 5. Frais d'intervention – annonce obligatoire

**[INT-07]** Avant de confirmer le rendez-vous, le conseiller **doit** annoncer les frais possibles au client et noter dans Orbite que l'information a été donnée :

| Situation constatée par le technicien | Frais facturés |
|---|---|
| Cause côté Kalyo (réseau, prise fibre, box, câble fourni par Kalyo) | **0 €** |
| Cause côté client (câble abîmé par le client, prise arrachée par le client, box déplacée ou modifiée, matériel du client) ou **aucune anomalie constatée côté Kalyo** | **49 € de frais de déplacement** |
| Rendez-vous non honoré par le client (absent, sans annulation au moins 24 heures avant) | **29 €** |

**[INT-08]** Le client peut **reporter ou annuler gratuitement** son rendez-vous jusqu'à 24 heures avant le créneau, par téléphone ou dans Kalyo & Moi.

**[INT-09]** Si le technicien ne vient pas sans avoir prévenu au moins 24 heures à l'avance, ou arrive en dehors du créneau sans avoir prévenu : **avoir automatique de 20 €** (compensation contractuelle, ce n'est pas un geste commercial) et nouveau rendez-vous en **priorité** (48 heures ouvrées).

## 6. Le jour de l'intervention

**[INT-10]**
- Une **personne majeure** doit être présente pendant toute l'intervention.
- La prise fibre, la box et, si besoin, les parties communes (local technique, palier) doivent être accessibles.
- Durée moyenne : 1 à 2 heures.

## 7. Après l'intervention

**[INT-11]** Le technicien renseigne un code de clôture visible dans Orbite :
- **« Résolu »** : rien à faire ;
- **« Non résolu – N2 »** : le Support Technique N2 reprend le dossier et rappelle le client sous 48 heures ouvrées ;
- **« Client absent »** : les frais de 29 € s'appliquent, sauf annulation faite dans les délais ;
- **« Cause client »** : les frais de 49 € s'appliquent.

**[INT-12]** Si le client **conteste des frais de 49 €** : le conseiller N1 ne peut pas les annuler seul. Il transfère au **superviseur** (voir DOC-13, gestes commerciaux). Les frais de 29 € pour absence peuvent être annulés **une fois par période de 12 mois** par le conseiller N1, si le client donne un motif sérieux (DOC-13).

## 8. Formulations recommandées

- « D'après les tests, le problème se situe au niveau de la prise ou du réseau. Je vais donc vous proposer le passage d'un technicien. »
- « Je dois vous informer d'un point important : si le technicien constate que la panne vient d'un équipement ou d'une manipulation de votre côté, ou s'il ne constate aucune anomalie de notre côté, des frais de déplacement de 49 € seront facturés. Si la panne vient de chez nous, c'est gratuit. »
- « Vous pouvez déplacer ce rendez-vous gratuitement jusqu'à 24 heures avant, dans l'application Kalyo & Moi. »

## 9. Vigilance – ce qu'il ne faut pas promettre

- Ne jamais promettre qu'une intervention sera gratuite avant le passage du technicien.
- Ne pas promettre une heure d'arrivée précise : seul le créneau est garanti.
- Ne pas promettre un rendez-vous prioritaire sans l'accord du N2.
- Ne pas annuler seul des frais de 49 €.

## 10. Escalade

| Situation | Destination | Mode |
|---|---|---|
| Demande de rendez-vous prioritaire | Support Technique N2 | Transfert chaud ou ticket |
| Nouveau rendez-vous après un échange de box récent | Support Technique N2 | Validation préalable |
| Contestation des frais de 49 € | Superviseur | Transfert chaud |
| Clôture « Non résolu – N2 » | Support Technique N2 | Reprise automatique |

## Documents liés

DOC-02 (diagnostic internet), DOC-08 (pannes longues), DOC-10 (éligibilité et déménagement), DOC-13 (gestes), DOC-14 (escalade).
