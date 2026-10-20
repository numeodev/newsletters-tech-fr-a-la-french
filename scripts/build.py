#!/usr/bin/env python3
"""Valide les fiches de newsletters et génère la liste du README.

Usage :
    python scripts/build.py validate   # vérifie les fiches, code de sortie 1 si erreur
    python scripts/build.py generate   # valide puis réécrit la liste dans README.md
"""

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
NEWSLETTERS_DIR = ROOT / "newsletters"
THEMATIQUES_FILE = ROOT / "thematiques.yml"
README = ROOT / "README.md"

DEBUT = "<!-- LISTE:DEBUT -->"
FIN = "<!-- LISTE:FIN -->"

CHAMPS_OBLIGATOIRES = {"nom", "url", "description", "thematiques", "frequence"}
CHAMPS_FACULTATIFS = {"auteur", "gratuite", "flux"}
FREQUENCES = {"quotidienne", "hebdomadaire", "bimensuelle", "mensuelle", "irreguliere"}
SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
DESCRIPTION_MAX = 200


def charger_thematiques():
    return yaml.safe_load(THEMATIQUES_FILE.read_text(encoding="utf-8"))


def fichiers_fiches():
    return sorted(p for p in NEWSLETTERS_DIR.glob("*.y*ml") if not p.name.startswith("_"))


def valider_fiche(chemin, data, thematiques):
    erreurs = []
    nom_fichier = chemin.name

    if chemin.suffix != ".yml":
        erreurs.append("l'extension doit être .yml")
    if not SLUG_RE.match(chemin.stem):
        erreurs.append("le nom du fichier doit être en minuscules, sans accents, avec des tirets (ex. ma-newsletter.yml)")
    if not isinstance(data, dict):
        return [f"{nom_fichier} : le fichier doit contenir des champs clé: valeur"]

    manquants = CHAMPS_OBLIGATOIRES - data.keys()
    if manquants:
        erreurs.append(f"champs obligatoires manquants : {', '.join(sorted(manquants))}")
    inconnus = data.keys() - CHAMPS_OBLIGATOIRES - CHAMPS_FACULTATIFS
    if inconnus:
        erreurs.append(f"champs inconnus : {', '.join(sorted(inconnus))}")

    for champ in ("nom", "url", "description", "auteur", "flux"):
        if champ in data and (not isinstance(data[champ], str) or not data[champ].strip()):
            erreurs.append(f"`{champ}` doit être un texte non vide")

    for champ in ("url", "flux"):
        valeur = data.get(champ)
        if isinstance(valeur, str) and not valeur.strip().startswith("https://"):
            erreurs.append(f"`{champ}` doit commencer par https://")

    description = data.get("description")
    if isinstance(description, str) and len(description) > DESCRIPTION_MAX:
        erreurs.append(f"`description` dépasse {DESCRIPTION_MAX} caractères ({len(description)})")

    themes = data.get("thematiques")
    if themes is not None:
        if not isinstance(themes, list) or not 1 <= len(themes) <= 3:
            erreurs.append("`thematiques` doit être une liste de 1 à 3 valeurs")
        else:
            invalides = [t for t in themes if t not in thematiques]
            if invalides:
                erreurs.append(
                    f"thématiques inconnues : {', '.join(map(str, invalides))} "
                    f"(valeurs possibles : {', '.join(thematiques)})"
                )

    frequence = data.get("frequence")
    if frequence is not None and frequence not in FREQUENCES:
        erreurs.append(f"`frequence` doit valoir : {', '.join(sorted(FREQUENCES))}")

    if "gratuite" in data and not isinstance(data["gratuite"], bool):
        erreurs.append("`gratuite` doit valoir true ou false")

    return [f"{nom_fichier} : {e}" for e in erreurs]


def normaliser_url(url):
    return url.lower().rstrip("/").removeprefix("https://").removeprefix("www.")


def valider():
    thematiques = charger_thematiques()
    erreurs = []
    fiches = []
    urls_vues = {}

    for chemin in fichiers_fiches():
        try:
            data = yaml.safe_load(chemin.read_text(encoding="utf-8"))
        except yaml.YAMLError as e:
            erreurs.append(
                f"{chemin.name} : YAML invalide ({e})\n"
                "  Astuce : mettez la description entre guillemets si elle contient « : », "
                "et écrivez les thématiques dans une seule liste, ex. [dev, ia]"
            )
            continue
        erreurs_fiche = valider_fiche(chemin, data, thematiques)
        erreurs.extend(erreurs_fiche)
        if erreurs_fiche:
            continue

        cle = normaliser_url(data["url"])
        if cle in urls_vues:
            erreurs.append(f"{chemin.name} : même URL que {urls_vues[cle]} (doublon)")
        urls_vues[cle] = chemin.name
        fiches.append(data)

    return fiches, thematiques, erreurs


def generer_liste(fiches, thematiques):
    if not fiches:
        return "_Aucune newsletter pour l'instant : soyez la première personne à en ajouter une !_"

    par_theme = {}
    for fiche in fiches:
        par_theme.setdefault(fiche["thematiques"][0], []).append(fiche)

    lignes = []
    for theme, titre in thematiques.items():
        if theme not in par_theme:
            continue
        lignes += [f"### {titre}", ""]
        for f in sorted(par_theme[theme], key=lambda f: f["nom"].lower()):
            details = [f["frequence"]]
            if f.get("auteur"):
                details.append(f"par {f['auteur']}")
            if f.get("gratuite") is False:
                details.append("payante")
            lignes.append(f"- **[{f['nom']}]({f['url']})** : {f['description']} _({', '.join(details)})_")
        lignes.append("")

    total = len(fiches)
    lignes.append(f"_{total} newsletter{'s' if total > 1 else ''} référencée{'s' if total > 1 else ''}._")
    return "\n".join(lignes)


def ecrire_readme(liste):
    contenu = README.read_text(encoding="utf-8")
    if DEBUT not in contenu or FIN not in contenu:
        sys.exit(f"Marqueurs {DEBUT} / {FIN} introuvables dans README.md")
    avant, reste = contenu.split(DEBUT, 1)
    _, apres = reste.split(FIN, 1)
    README.write_text(f"{avant}{DEBUT}\n{liste}\n{FIN}{apres}", encoding="utf-8")


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("validate", "generate"):
        sys.exit(__doc__)

    fiches, thematiques, erreurs = valider()
    if erreurs:
        print("❌ Erreurs trouvées :\n")
        print("\n".join(f"- {e}" for e in erreurs))
        sys.exit(1)
    print(f"✅ {len(fiches)} fiche(s) valide(s)")

    if sys.argv[1] == "generate":
        ecrire_readme(generer_liste(fiches, thematiques))
        print("README.md mis à jour")


if __name__ == "__main__":
    main()
