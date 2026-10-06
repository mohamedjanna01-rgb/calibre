# Limites connues de Calibre

## Interruptions non détectées sur des enregistrements mono

Calibre ne repère pas qu'un conseiller coupe la parole au client quand l'appel est enregistré en **mono**, c'est-à-dire les deux voix sur une seule piste. La transcription locale fait se toucher les mots de deux locuteurs successifs, si bien que les silences ne disent rien. Elle peut même compléter une phrase interrompue avec des mots jamais prononcés. Une interruption reste donc invisible pour la notation. L'item « Écoute active » peut alors être noté « oui » à tort.

Sur des enregistrements en **stéréo**, avec le conseiller et le client chacun sur leur canal, la plupart des centres d'appels enregistrent ainsi. Les chevauchements de voix se mesurent alors directement, et une interruption peut être signalée à la notation.

## Autres limites constatées

- **Appels de démonstration générés par synthèse vocale.** Un appel est généré par une seule requête qui fait alterner les deux voix : la voix ne superpose jamais deux personnes, et une coupure est simulée par une phrase qui s'arrête net.
- **Erreurs d'écoute de la transcription locale.** Quelques mots sont mal transcrits. Certaines preuves ne sont alors retrouvées que de façon approchée, et une citation peut ne pas correspondre exactement au texte prononcé. Le contrôle des citations signale ces cas.
- **Noms des clients.** Le lexique des noms propres ne contient que des termes de la documentation de Kalyo, jamais de noms de clients. Une orthographe variable d'un nom n'est pas pénalisée par la notation.
- **Référentiel réduit pour la notation.** L'offre gratuite du modèle de notation limite l'entrée à 16 000 tokens par minute. L'IA reçoit donc les grilles, les règles, les exemples et seulement les documents essentiels selon le type d'appel. Ses remarques de conformité sont moins complètes qu'avec toute la documentation.
- **Variabilité.** Deux notations du même appel peuvent différer sur quelques items. Chaque appel est noté deux fois, et un éliminatoire est retenu dès qu'une des deux passes le trouve.
- **Offres gratuites.** Les quotas et les erreurs de surcharge des services utilisés allongent les traitements. Le code compte chaque requête, n'en refait qu'une seule après une surcharge, et s'arrête sur un refus lié au quota.
