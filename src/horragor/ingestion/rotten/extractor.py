"""
Orchestration du scraping Rotten Tomatoes : fetch (Selenium) + parse (pur)
-> sauvegarde brute -> nettoyage -> sortie clean.

Pourquoi sauvegarder le brut avant de nettoyer : le scraping est lent et
faillible (réseau/anti-bot). Garder `rotten_raw.json` évite de re-scraper à
chaque itération et trace ce qui a réellement été extrait.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from horragor.config.paths import ROTTEN_CLEAN, ROTTEN_RAW
from horragor.config.settings import ROTTEN_HORROR_SLUGS
from horragor.ingestion.rotten.parser import parse_movie_page
from horragor.ingestion.rotten.scraper import RottenScraper
from horragor.transform.normalizer import normalize_text

logger = logging.getLogger(__name__)


def _save_json(data: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def scrape_rotten(slugs: tuple[str, ...] | None = None, headless: bool = True) -> list[dict]:
    """Scrape chaque slug, parse le HTML, sauvegarde le brut. Retourne les bruts."""
    slugs = slugs if slugs is not None else ROTTEN_HORROR_SLUGS
    results: list[dict] = []
    with RottenScraper(headless=headless) as scraper:
        for slug in slugs:
            html = scraper.fetch_movie_html(slug)
            if html is None:
                continue
            movie = parse_movie_page(html)
            movie["slug"] = slug  # trace la cible scrapée
            results.append(movie)
            logger.info(
                "✓ %s -> tomatometer=%s audience=%s",
                slug,
                movie.get("tomatometer"),
                movie.get("audience"),
            )
    _save_json(results, ROTTEN_RAW)
    logger.info("Brut sauvegardé : %s (%d films)", ROTTEN_RAW, len(results))
    return results


def transform_rotten(raw: list[dict] | None = None) -> list[dict]:
    """
    Nettoie les bruts : normalise le texte du consensus (HTML/whitespace/UTF-8,
    cf. normalizer transverse) et écarte les entrées sans titre exploitable.
    """
    if raw is None:
        raw = json.loads(ROTTEN_RAW.read_text(encoding="utf-8"))

    clean: list[dict] = []
    for m in raw:
        if not m.get("title"):
            continue  # sans titre, impossible de réconcilier -> on jette
        clean.append(
            {
                "title": normalize_text(m.get("title")),
                "year": m.get("year"),
                "genres": m.get("genres") or [],
                "tomatometer": m.get("tomatometer"),
                "audience": m.get("audience"),
                "critics_consensus": normalize_text(m.get("critics_consensus")),
            }
        )

    _save_json(clean, ROTTEN_CLEAN)
    logger.info("Clean sauvegardé : %s (%d films)", ROTTEN_CLEAN, len(clean))
    return clean


def main(headless: bool = True) -> None:
    raw = scrape_rotten(headless=headless)
    transform_rotten(raw)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
    )
    main()
