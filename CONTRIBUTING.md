# Contribuer

Merci de vouloir enrichir le répertoire ! Il y a trois façons de contribuer, de la plus simple à la plus technique.

## 1. Proposer une newsletter sans toucher au code

Remplissez le [formulaire d'ajout](../../issues/new?template=ajout-newsletter.yml). La fiche est créée automatiquement à partir de vos réponses, puis proposée en relecture. Un commentaire sur votre issue vous indique le résultat en moins d'une minute. S'il y a une erreur, modifiez simplement votre issue : la vérification se relance.

## 2. Ajouter une fiche directement depuis GitHub (sans installer quoi que ce soit)

Il vous faut seulement un compte GitHub.

1. Ouvrez le dossier [`newsletters/`](newsletters/) et cliquez sur **Add file → Create new file**.
2. GitHub indique que vous devez créer une copie du projet (un *fork*) pour proposer des modifications. Cliquez sur **Fork this repository**. L'éditeur s'ouvre ensuite dans votre copie.
3. Dans le champ du nom, tapez `<slug>.yml` : nom de la newsletter en minuscules, sans accents, mots séparés par des tirets (ex. `la-veille-du-dev.yml`). Vérifiez que le chemin affiché commence bien par `newsletters/`.
4. Copiez le contenu de [`_modele.yml`](newsletters/_modele.yml) dans l'éditeur et remplissez-le.
5. Cliquez sur **Commit changes…**, gardez ou modifiez le message, puis cliquez sur **Propose changes**.
6. GitHub affiche une page de comparaison de vos changements. Cliquez sur **Create pull request**, puis encore une fois sur **Create pull request** pour valider. Tant que vous n'avez pas fait cette étape, votre proposition n'est pas envoyée.

Une vérification automatique s'exécute ensuite sur votre pull request. Si elle échoue (croix rouge ❌), cliquez sur **Details** pour voir ce qu'il faut corriger. Pour corriger, ouvrez l'onglet **Files changed** de la pull request, puis **⋯ → Edit file** : vos modifications s'ajoutent directement à la même pull request.

## 3. En local

Prérequis : `git` et Python 3.

1. **Forkez le projet** : en haut de la page du dépôt, cliquez sur **Fork**, puis sur **Create fork**. Vous obtenez votre propre copie : `github.com/<votre-compte>/newsletters-tech-fr-a-la-french`.

2. **Clonez votre fork** et créez une branche :

   ```bash
   git clone https://github.com/<votre-compte>/newsletters-tech-fr-a-la-french.git
   cd newsletters-tech-fr-a-la-french
   git switch -c ajout-ma-newsletter
   ```

   Si vous avez configuré une clé SSH sur GitHub, vous pouvez utiliser `git@github.com:<votre-compte>/newsletters-tech-fr-a-la-french.git` à la place.

3. **Créez et validez la fiche** :

   ```bash
   cp newsletters/_modele.yml newsletters/ma-newsletter.yml
   # éditez la fiche, puis :
   python3 -m pip install pyyaml
   python3 scripts/build.py validate
   ```

4. **Envoyez-la sur votre fork** :

   ```bash
   git add newsletters/ma-newsletter.yml
   git commit -m "ajout: Ma Newsletter"
   git push -u origin ajout-ma-newsletter
   ```

5. **Ouvrez la pull request** : sur la page de votre fork, GitHub affiche un bandeau **Compare & pull request**. Cliquez dessus, puis sur **Create pull request**.

Pour une contribution suivante, mettez d'abord votre fork à jour : bouton **Sync fork** sur sa page GitHub, puis `git switch main && git pull` en local, avant de créer une nouvelle branche.

Ne modifiez pas la liste dans le `README.md` : elle est régénérée automatiquement après chaque fusion.

## Format d'une fiche

| Champ | Obligatoire | Description |
| --- | --- | --- |
| `nom` | oui | Nom de la newsletter |
| `url` | oui | Page d'inscription ou d'accueil, en `https://` |
| `description` | oui | Une phrase, 200 caractères max |
| `thematiques` | oui | 1 à 3 valeurs parmi [`thematiques.yml`](thematiques.yml). La première détermine la section du README |
| `frequence` | oui | `quotidienne`, `hebdomadaire`, `bimensuelle`, `mensuelle` ou `irreguliere` |
| `auteur` | non | Auteur·rice ou organisation |
| `gratuite` | non | `false` si l'accès est payant (par défaut on suppose qu'elle est gratuite) |
| `flux` | non | URL du flux RSS ou Atom, en `https://`. Inutile si le flux est détecté automatiquement (voir ci-dessous) |

## Critères d'inclusion

Une newsletter est acceptée si :

- elle est **rédigée en français** ;
- elle traite **principalement de tech** (au sens large : dev, data, produit, business de la tech…) ;
- elle est **active** : au moins une édition dans les 6 derniers mois (vérifié automatiquement, voir ci-dessous) ;
- elle est **éditoriale** : pas une simple newsletter promotionnelle d'un produit.

Vous pouvez proposer votre propre newsletter, c'est même encouragé.

## Vérification de l'activité

L'activité de chaque newsletter est vérifiée automatiquement à partir de son flux RSS ou Atom. Le flux est cherché sur la page de la newsletter et aux adresses habituelles des plateformes (Substack, Ghost, WordPress, Kessel…). Pour Beehiiv, ce sont les dates de la page d'archive qui sont utilisées.

- **À l'ajout via le formulaire** : une newsletter dont la dernière édition détectée date de plus de 6 mois est refusée. Si aucune date n'est trouvée, la fiche est quand même proposée, et l'activité est vérifiée à la main lors de la relecture.
- **Chaque mois** : les fiches sans nouvelle édition depuis plus de 6 mois sont retirées, via une pull request relue avant fusion.

Si la date détectée est fausse (le flux trouvé est celui d'un blog et non de la newsletter, par exemple), renseignez le bon flux dans le champ `flux` de la fiche. Les newsletters sans flux public, comme celles publiées sur LinkedIn, ne sont jamais retirées automatiquement.

Pour voir ce que détecte le script en local : `python3 scripts/activite.py rapport`.

## Corriger ou retirer une fiche

- Info erronée ou lien mort : [signalez-le](../../issues/new?template=signaler-probleme.yml) ou modifiez directement le fichier concerné.
- Newsletter arrêtée : ouvrez une pull request qui supprime sa fiche.
- Nouvelle thématique : proposez-la dans une pull request qui modifie `thematiques.yml`.

## Licence des contributions

En proposant une contribution, vous acceptez qu'elle soit publiée sous la licence du projet : [CC BY 4.0](LICENSE) pour les données, [MIT](LICENSE-CODE) pour le code.

## Code de conduite

En participant, vous vous engagez à respecter le [code de conduite](CODE_OF_CONDUCT.md).
