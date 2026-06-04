"""
Parsing d'une page film Rotten Tomatoes (fonction pure, testable hors-ligne).

POURQUOI séparer ce parsing du fetch Selenium ?
- Le fetch dépend d'un navigateur + réseau + protections anti-bot : impossible
  à tester de façon déterministe.
- Le parsing, lui, est une fonction pure (HTML -> dict) : on peut le couvrir
  par des tests sur fixtures, et il reste isolé des pannes réseau.

STRATÉGIE DE PARSING (en deux couches, par robustesse) :
1. Le JSON-LD (`<script type="application/ld+json">`) est le contrat le plus
   stable (schema.org). Il fournit titre, année, genres et le Tomatometer
   (aggregateRating). C'est la source primaire car peu sensible aux refontes
   du design RT.
2. Les web components RT (`<rt-text slot="...">`, `#critics-consensus`)
   complètent ce que le JSON-LD ne porte pas : le score audience (Popcornmeter)
   et le texte du Critics Consensus. Ces sélecteurs sont plus fragiles (ils ont
   déjà changé au fil des refontes), d'où leur rôle de complément/fallback.
"""

from __future__ import annotations

import json
import re

from bs4 import BeautifulSoup


def _extract_jsonld(soup: BeautifulSoup) -> dict:
    """Renvoie le 1er bloc JSON-LD de type Movie (ou {} si absent/illisible)."""
    for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
        if not tag.string:
            continue
        try:
            data = json.loads(tag.string)
        except (ValueError, TypeError):
            continue
        candidates = data if isinstance(data, list) else [data]
        for item in candidates:
            if isinstance(item, dict) and item.get("name"):
                return item
    return {}


def _year(date_str: str | None) -> int | None:
    """Première année (4 chiffres) trouvée dans une chaîne de date."""
    match = re.search(r"\d{4}", date_str or "")
    return int(match.group()) if match else None


def _percent(text: str | None) -> int | None:
    """Convertit '90%' -> 90 (échelle native RT 0-100, conservée telle quelle)."""
    match = re.search(r"(\d{1,3})\s*%", text or "")
    return int(match.group(1)) if match else None


def _slot_text(soup: BeautifulSoup, slot: str) -> str | None:
    el = soup.find("rt-text", attrs={"slot": slot})
    return el.get_text(strip=True) if el else None


# RT suffixe les titres ambigus par l'année (« A Quiet Place (2018) »). On
# retire ce suffixe : sinon il fait chuter la similarité du fuzzy [titre+année]
# et empêche le rattachement aux autres sources (le titre canonique est nu).
_YEAR_SUFFIX = re.compile(r"\s*\(\d{4}\)\s*$")


def _strip_year_suffix(title: str | None) -> str | None:
    return _YEAR_SUFFIX.sub("", title).strip() if title else title


def parse_movie_page(html: str) -> dict:
    """
    Extrait les métadonnées d'une page film RT.

    Retourne : title, year, genres, tomatometer (0-100), audience (0-100),
    critics_consensus. Tout champ introuvable vaut None (les scores RT sont
    conservés en échelle native, cf. brief — ce sont des métriques distinctes).
    """
    soup = BeautifulSoup(html, "html.parser")
    ld = _extract_jsonld(soup)

    # --- Titre (JSON-LD prioritaire, sinon slot du scorecard) ---
    title = _strip_year_suffix(ld.get("name") or _slot_text(soup, "title"))

    # --- Année (JSON-LD ; fallback sur les slots metadata 'R, 2018, 2h 7m') ---
    year = _year(ld.get("dateCreated") or ld.get("datePublished"))
    if year is None:
        for el in soup.find_all("rt-text", attrs={"slot": "metadata-prop"}):
            year = _year(el.get_text())
            if year:
                break

    # --- Genres (liste JSON-LD ; permet le filtrage thématique Horror) ---
    genres = ld.get("genre") or []
    if isinstance(genres, str):
        genres = [genres]

    # --- Tomatometer (JSON-LD aggregateRating ; fallback slot critics-score) ---
    tomatometer = None
    agg = ld.get("aggregateRating")
    if isinstance(agg, dict) and str(agg.get("name", "")).lower().startswith("tomato"):
        try:
            tomatometer = int(float(agg["ratingValue"]))
        except (KeyError, TypeError, ValueError):
            tomatometer = None
    if tomatometer is None:
        tomatometer = _percent(_slot_text(soup, "critics-score"))

    # --- Audience / Popcornmeter (absent du JSON-LD : web component requis) ---
    audience = _percent(_slot_text(soup, "audience-score"))

    # --- Critics Consensus (texte ; on retire le libellé d'en-tête) ---
    consensus = None
    el = soup.find(id="critics-consensus")
    if el:
        text = el.get_text(" ", strip=True)
        text = re.sub(r"^.*?Critics Consensus\s*", "", text).strip()
        consensus = text or None

    return {
        "title": title,
        "year": year,
        "genres": genres,
        "tomatometer": tomatometer,
        "audience": audience,
        "critics_consensus": consensus,
    }
