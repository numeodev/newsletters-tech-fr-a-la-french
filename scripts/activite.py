#!/usr/bin/env python3
"""Détecte la date de la dernière édition d'une newsletter via son flux RSS/Atom.

Usage :
    python scripts/activite.py rapport    # affiche la dernière édition détectée pour chaque fiche
    python scripts/activite.py nettoyer   # supprime les fiches inactives depuis plus de 6 mois

En mode `nettoyer`, un résumé Markdown est écrit dans le fichier désigné par RAPPORT_FILE
(s'il est défini) et le nombre de fiches supprimées dans la sortie GitHub `supprimees`.
"""

import os
import re
import sys
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
from xml.etree import ElementTree

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build  # noqa: E402

INACTIVITE_MAX = timedelta(days=183)  # 6 mois
TIMEOUT = 10
TAILLE_MAX = 5 * 1024 * 1024
USER_AGENT = "Mozilla/5.0 (compatible; newsletters-tech-fr/1.0; +https://github.com/numeodev/newsletters-tech-fr-a-la-french)"
CHEMINS_FLUX = ("feed", "rss", "feed.xml", "rss.xml", "atom.xml", "index.xml", "feed/", "rss/")
TYPES_FLUX = ("application/rss+xml", "application/atom+xml", "application/feed+json")


def telecharger(url):
    requete = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    with urlopen(requete, timeout=TIMEOUT) as reponse:
        return reponse.read(TAILLE_MAX), reponse.geturl()


class ChercheurFlux(HTMLParser):
    def __init__(self):
        super().__init__()
        self.flux = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "link" and "alternate" in (a.get("rel") or "").lower() and a.get("type") in TYPES_FLUX and a.get("href"):
            self.flux.append(a["href"])


def lire_date(texte):
    texte = (texte or "").strip()
    if not texte:
        return None
    try:
        date = parsedate_to_datetime(texte)  # RSS : RFC 822
    except (TypeError, ValueError):
        try:
            date = datetime.fromisoformat(texte.replace("Z", "+00:00"))  # Atom : ISO 8601
        except ValueError:
            return None
    return date if date.tzinfo else date.replace(tzinfo=timezone.utc)


def date_plus_recente(contenu):
    """Renvoie la date la plus récente des entrées d'un flux RSS/Atom, ou None."""
    try:
        racine = ElementTree.fromstring(contenu)
    except ElementTree.ParseError:
        return None
    dates = []
    for entree in racine.iter():
        if entree.tag.rsplit("}", 1)[-1] not in ("item", "entry"):
            continue
        for element in entree:
            if element.tag.rsplit("}", 1)[-1] in ("pubDate", "published", "updated", "date"):
                dates.append(lire_date(element.text))
    return garder_la_plus_recente(dates)


def garder_la_plus_recente(dates):
    # Ignore les dates futures (éditions programmées)
    limite = datetime.now(timezone.utc) + timedelta(days=1)
    dates = [d for d in dates if d and d <= limite]
    return max(dates) if dates else None


DATES_HTML = re.compile(
    r'"(?:datePublished|published_at|publish_date|override_scheduled_at)"\s*:\s*"([^"]{10,40})"'
    r'|<time[^>]+datetime="([^"]{10,40})"'
    r'|<meta[^>]+property="article:published_time"[^>]+content="([^"]{10,40})"'
)


def date_dans_page(html):
    """Cherche des dates de publication structurées dans une page HTML (pages d'archive sans flux)."""
    texte = html.decode("utf-8", "replace")
    return garder_la_plus_recente([lire_date(next(g for g in m if g)) for m in DATES_HTML.findall(texte)])


def candidats_flux(url):
    """Liste les URL de flux possibles pour une page, de la plus probable à la moins probable."""
    candidats = []
    try:
        html, url_finale = telecharger(url)
        chercheur = ChercheurFlux()
        chercheur.feed(html.decode("utf-8", "replace"))
        candidats += [urljoin(url_finale, f) for f in chercheur.flux]
        # Le contenu lui-même est peut-être déjà un flux
        if date_plus_recente(html):
            candidats.insert(0, url_finale)
    except (URLError, OSError, ValueError):
        url_finale = url

    racine = f"{urlparse(url_finale).scheme}://{urlparse(url_finale).netloc}/"
    base = url_finale if url_finale.endswith("/") else url_finale.rsplit("/", 1)[0] + "/"
    for prefixe in dict.fromkeys((base, racine)):
        candidats += [urljoin(prefixe, chemin) for chemin in CHEMINS_FLUX]
    return list(dict.fromkeys(candidats))


def derniere_edition(url, flux=None):
    """Renvoie (date, source) ou (None, None) si aucune date n'a pu être trouvée.

    Cherche d'abord un flux RSS/Atom, puis, à défaut, des dates structurées dans la page
    et dans sa page d'archive (cas de Beehiiv, qui n'expose pas de flux par défaut).
    """
    for candidat in [flux] if flux else candidats_flux(url):
        try:
            contenu, _ = telecharger(candidat)
        except (URLError, OSError, ValueError):
            continue
        date = date_plus_recente(contenu)
        if date:
            return date, candidat
    if flux:
        return None, None

    racine = f"{urlparse(url).scheme}://{urlparse(url).netloc}/"
    for page in dict.fromkeys((url, urljoin(racine, "archive"))):
        try:
            html, _ = telecharger(page)
        except (URLError, OSError, ValueError):
            continue
        date = date_dans_page(html)
        if date:
            return date, page
    return None, None


def est_inactive(date, maintenant=None):
    return (maintenant or datetime.now(timezone.utc)) - date > INACTIVITE_MAX


def analyser_fiches():
    resultats = []
    for chemin in build.fichiers_fiches():
        fiche = yaml.safe_load(chemin.read_text(encoding="utf-8"))
        date, flux = derniere_edition(fiche["url"].strip(), fiche.get("flux"))
        resultats.append((chemin, fiche, date, flux))
    return resultats


def formater_date(date):
    return date.strftime("%d/%m/%Y")


def rapport():
    for chemin, fiche, date, flux in analyser_fiches():
        if date is None:
            etat = "❓ non vérifiable"
        elif est_inactive(date):
            etat = f"💤 inactive (dernière édition le {formater_date(date)})"
        else:
            etat = f"✅ active (dernière édition le {formater_date(date)})"
        print(f"{chemin.name:40} {etat}" + (f"  ← {flux}" if flux else ""))


def nettoyer():
    supprimees, inconnues = [], []
    for chemin, fiche, date, flux in analyser_fiches():
        if date is None:
            inconnues.append(f"- {fiche['nom']} (`{chemin.name}`) : {fiche['url'].strip()}")
        elif est_inactive(date):
            chemin.unlink()
            supprimees.append(f"- **{fiche['nom']}** : dernière édition le {formater_date(date)} (source : {flux})")

    lignes = ["Newsletters sans nouvelle édition depuis plus de 6 mois, supprimées du répertoire :\n"]
    lignes += supprimees or ["_Aucune._"]
    if supprimees:
        lignes += [
            "",
            "> [!WARNING]",
            "> Vérifiez chaque suppression avant de fusionner : la date vient du flux trouvé, qui peut être celui "
            "d'un blog plutôt que de la newsletter. Pour garder une fiche supprimée à tort, ajoutez-lui un champ "
            "`flux:` pointant vers le bon flux sur `main`, puis relancez le workflow : la pull request sera mise à jour.",
        ]
    if inconnues:
        lignes += [
            "",
            "<details><summary>Activité non vérifiable automatiquement (aucun flux RSS trouvé) : "
            f"{len(inconnues)} fiche(s) à vérifier à la main</summary>\n",
            *inconnues,
            "\nAjoutez un champ `flux:` à ces fiches si la newsletter a un flux RSS non détecté.",
            "</details>",
        ]
    texte = "\n".join(lignes)
    print(texte)

    if os.environ.get("RAPPORT_FILE"):
        Path(os.environ["RAPPORT_FILE"]).write_text(texte + "\n", encoding="utf-8")
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as f:
            f.write(f"supprimees={len(supprimees)}\n")


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("rapport", "nettoyer"):
        sys.exit(__doc__)
    rapport() if sys.argv[1] == "rapport" else nettoyer()
