"""
Orchestrateur de bout en bout : 5 sources → fusion (Gold) → base.

Principes (cf. brief « Robustesse du Pipeline ») :
- **Lazy imports** : chaque source n'importe ses dépendances lourdes
  (Selenium, PySpark…) qu'au moment de s'exécuter. Lancer une seule source ne
  paie pas le coût des autres.
- **Isolation des pannes** : chaque étape d'ingestion est encapsulée ; un échec
  (réseau, anti-bot, source indisponible) est journalisé et n'interrompt PAS le
  pipeline. La fusion se fait avec les artefacts `clean` réellement produits
  (les adapters tolèrent les sources manquantes).
- **Idempotence** : les extracteurs sautent les sorties déjà présentes ; le
  chargement reconstruit la base depuis le Gold.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable

from horragor.config.settings import TMDB_MAX_PAGES

logger = logging.getLogger(__name__)


# --- Étapes d'ingestion (une fonction par source) ---------------------------
def run_tmdb(max_pages: int = TMDB_MAX_PAGES) -> None:
    from horragor.pipeline import run_tmdb_pipeline
    from horragor.transform.normalizer import normalize_movie
    from horragor.transform.saver import save_normalized

    mapped = run_tmdb_pipeline(max_pages=max_pages)
    save_normalized([normalize_movie(m) for m in mapped])


def run_imdb() -> None:
    from horragor.ingestion.imdb.db_builder import load_imdb_to_sqlite
    from horragor.ingestion.imdb.downloader import download_imdb_files
    from horragor.ingestion.imdb.extractor import extract_horror_movies
    from horragor.ingestion.imdb.transformer import transform_horror_movies

    download_imdb_files()
    load_imdb_to_sqlite()
    extract_horror_movies()
    transform_horror_movies()


def run_kaggle() -> None:
    from horragor.ingestion.kaggle.transformer import transform

    transform()


def run_rotten() -> None:
    from horragor.ingestion.rotten.extractor import main as rotten_main

    rotten_main()


def run_spark() -> None:
    from horragor.ingestion.spark.job import main as spark_main
    from horragor.ingestion.spark.splitter import split_kaggle

    split_kaggle()
    spark_main()


# Registre des sources, dans l'ordre logique d'ingestion.
INGESTION: dict[str, Callable[[], None]] = {
    "tmdb": run_tmdb,
    "imdb": run_imdb,
    "kaggle": run_kaggle,
    "rotten": run_rotten,
    "spark": run_spark,
}


def _step(name: str, fn: Callable[[], None]) -> bool:
    """Exécute une étape en isolant son éventuel échec. Retourne le succès."""
    logger.info("▶ %s …", name)
    t0 = time.time()
    try:
        fn()
        logger.info("✓ %s (%.1fs)", name, time.time() - t0)
        return True
    except Exception as e:  # noqa: BLE001 — on isole volontairement chaque source
        logger.error("✗ %s a échoué : %s — on continue.", name, e)
        return False


def run_ingestion(sources: list[str]) -> dict[str, bool]:
    """Ingestion des sources demandées. Retourne {source: succès}."""
    # Kaggle alimente Spark (fichiers splittés) : on l'ingère avant.
    ordered = [s for s in INGESTION if s in sources]
    return {s: _step(f"Ingestion {s}", INGESTION[s]) for s in ordered}


def run_fusion() -> dict:
    """Réconciliation MDM → Gold (Parquet). Retourne le rapport qualité."""
    from horragor.reconciliation.gold import build_gold, export_gold, quality_report

    df = build_gold()
    export_gold(df)
    return quality_report(df)


def run_load() -> dict:
    """Chargement du Gold dans la base relationnelle. Retourne les stats."""
    from horragor.load.gold_loader import load_gold

    return load_gold()


def run_all(
    sources: list[str] | None = None,
    *,
    skip_ingestion: bool = False,
    do_load: bool = True,
    max_pages: int = TMDB_MAX_PAGES,
) -> dict:
    """Pipeline complet : ingestion → fusion → (chargement). Retourne un résumé."""
    sources = sources if sources is not None else list(INGESTION)
    summary: dict = {"ingestion": {}, "gold": None, "load": None}

    if not skip_ingestion:
        # max_pages n'est paramétrable que pour TMDB : on rebinde son étape le
        # temps de l'ingestion, puis on restaure le registre.
        INGESTION["tmdb"] = lambda: run_tmdb(max_pages=max_pages)
        try:
            summary["ingestion"] = run_ingestion(sources)
        finally:
            INGESTION["tmdb"] = run_tmdb
    else:
        logger.info("⏭ Ingestion sautée (--skip-ingestion).")

    # Fusion : étape critique. Si elle échoue, on s'arrête.
    summary["gold"] = run_fusion()
    logger.info("📊 Gold : %s", summary["gold"])

    if do_load:
        summary["load"] = run_load()
        logger.info("📥 Base : %s", summary["load"])
    else:
        logger.info("⏭ Chargement base sauté (--no-load).")

    return summary
