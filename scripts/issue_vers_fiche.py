#!/usr/bin/env python3
"""Crée une fiche dans newsletters/ à partir d'une issue « Proposer une newsletter ».

Lit le corps de l'issue dans le fichier désigné par ISSUE_BODY_FILE, écrit la fiche,
la valide avec build.py et écrit dans MESSAGE_FILE le commentaire à poster sur l'issue.
Vérifie aussi l'activité de la newsletter (dernière édition de moins de 6 mois).
Sorties GitHub Actions : `statut` (ok | erreur), `slug`, `nom`, `activite`.
"""

import os
import re
import sys
import unicodedata
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import activite  # noqa: E402
import build  # noqa: E402

SANS_REPONSE = "_No response_"


def lire_sections(corps):
    """Découpe le corps d'une issue form en {titre de section: contenu}."""
    sections = {}
    for bloc in re.split(r"^### ", corps.replace("\r\n", "\n"), flags=re.M)[1:]:
        titre, _, contenu = bloc.partition("\n")
        contenu = contenu.strip()
        sections[titre.strip()] = None if contenu in ("", SANS_REPONSE) else contenu
    return sections


def trouver(sections, debut):
    for titre, contenu in sections.items():
        if titre.startswith(debut):
            return contenu
    return None


def slugifier(texte):
    texte = re.sub(r"['’]", " ", texte)
    ascii_ = unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_.lower()).strip("-")


def construire_fiche(sections, thematiques):
    erreurs = []
    libelle_vers_id = {libelle: ident for ident, libelle in thematiques.items()}

    nom = trouver(sections, "Nom de la newsletter")
    url = trouver(sections, "URL")
    description = trouver(sections, "Description")
    themes_bruts = trouver(sections, "Thématiques") or ""
    frequence = trouver(sections, "Fréquence")
    auteur = trouver(sections, "Auteur")
    flux = trouver(sections, "Flux RSS")
    verifications = trouver(sections, "Vérifications") or ""

    themes = []
    for libelle in (t.strip() for t in themes_bruts.split(",") if t.strip()):
        if libelle in libelle_vers_id:
            themes.append(libelle_vers_id[libelle])
        else:
            erreurs.append(f"thématique inconnue : {libelle}")

    fiche = {
        "nom": nom,
        "url": url,
        "description": " ".join(description.split()) if description else None,
        "thematiques": themes,
        "frequence": frequence,
    }
    if auteur:
        fiche["auteur"] = auteur
    if flux:
        fiche["flux"] = flux
    fiche["gratuite"] = not re.search(r"- \[[xX]\] Elle est payante", verifications)
    return {k: v for k, v in fiche.items() if v is not None}, erreurs


def ecrire_sortie(**valeurs):
    chemin = os.environ.get("GITHUB_OUTPUT")
    if chemin:
        with open(chemin, "a", encoding="utf-8") as f:
            for cle, valeur in valeurs.items():
                f.write(f"{cle}={' '.join(str(valeur).split())}\n")


def main():
    message = Path(os.environ["MESSAGE_FILE"])
    thematiques = build.charger_thematiques()
    corps = Path(os.environ["ISSUE_BODY_FILE"]).read_text(encoding="utf-8")
    fiche, erreurs = construire_fiche(lire_sections(corps), thematiques)

    slug = slugifier(fiche.get("nom", ""))
    if not slug:
        erreurs.append("le nom de la newsletter est vide ou ne contient aucune lettre")
    else:
        # Vérifie tous les champs d'un coup pour signaler toutes les erreurs en un seul commentaire
        erreurs += [e.split(" : ", 1)[1] for e in build.valider_fiche(Path(f"{slug}.yml"), fiche, thematiques)]

    if not erreurs:
        chemin = build.NEWSLETTERS_DIR / f"{slug}.yml"
        url = build.normaliser_url(fiche["url"])
        existante = next(
            (p.name for p in build.fichiers_fiches()
             if build.normaliser_url(str(yaml.safe_load(p.read_text(encoding="utf-8")).get("url", ""))) == url),
            None,
        )
        if existante:
            erreurs.append(f"cette newsletter est déjà référencée (fiche `{existante}`)")
        elif chemin.exists():
            erreurs.append(f"une fiche `{chemin.name}` existe déjà dans le répertoire")
        else:
            date, source = activite.derniere_edition(fiche["url"], fiche.get("flux"))
            if date and activite.est_inactive(date):
                erreurs.append(
                    f"la dernière édition détectée date du {activite.formater_date(date)} (source : {source}). "
                    "Le répertoire ne référence que les newsletters ayant publié dans les 6 derniers mois. "
                    "Si cette date est fausse, indiquez le flux RSS de la newsletter dans le champ « Flux RSS » de l'issue"
                )
            elif date:
                etat_activite = f"✅ Activité vérifiée : dernière édition le {activite.formater_date(date)} (source : {source})."
            else:
                etat_activite = (
                    "⚠️ Activité non vérifiable automatiquement (aucun flux RSS ni date de publication trouvés) : "
                    "à vérifier lors de la relecture."
                )

        if not erreurs:
            chemin.write_text(
                yaml.safe_dump(fiche, allow_unicode=True, sort_keys=False, default_flow_style=None, width=1000),
                encoding="utf-8",
            )
            _, _, erreurs = build.valider()
            if erreurs:
                chemin.unlink()

    if erreurs:
        message.write_text(
            "❌ La fiche n'a pas pu être créée automatiquement :\n\n"
            + "\n".join(f"- {e}" for e in erreurs)
            + "\n\nModifiez votre issue (menu **⋯ → Edit**) pour corriger : la vérification se relancera.",
            encoding="utf-8",
        )
        ecrire_sortie(statut="erreur")
        print("\n".join(erreurs))
        return

    ecrire_sortie(statut="ok", slug=slug, nom=fiche["nom"], activite=etat_activite)
    print(f"Fiche newsletters/{slug}.yml créée")


if __name__ == "__main__":
    main()
