"""
Orchestrateur du pipeline HorRAGor.
Enchaîne : Extract → Save Raw → Map → Normalize → Save Clean → Load DB.
"""

import json
from pathlib import Path

from horragor.config.paths import TMDB_CLEAN, TMDB_RAW
from horragor.config.settings import TMDB_MAX_PAGES, TMDB_TOKEN
from horragor.db.database import init_db
from horragor.db.seed import seed_genres
from horragor.ingestion.tmdb.client import TMDBClient
from horragor.ingestion.tmdb.extractor import TMDBExtractor
from horragor.ingestion.tmdb.mapper import TMDBMapper
from horragor.load.db_loader import load_tmdb_normalized
from horragor.transform.normalizer import normalize_movie
from horragor.transform.saver import save_normalized

# Chemins centralisés (cf. horragor.config.paths)
RAW_OUTPUT_PATH = TMDB_RAW
CLEAN_OUTPUT_PATH = TMDB_CLEAN


def save_raw(data: list[dict], path: Path) -> None:
    """
    Sauvegarde les données brutes en JSON.

    Pourquoi sauvegarder le brut ?
    - Évite de refaire des appels API (quota limité) si le pipeline plante après
    - Permet de déboguer en inspectant les données avant transformation
    - Trace de ce qui a été reçu de l'API
    """
    # Crée les dossiers parents si ils n'existent pas (data/raw/)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        # indent=2 pour lisibilité humaine
        # ensure_ascii=False pour conserver les caractères spéciaux (accents, etc.)
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"💾 Données brutes sauvegardées → {path}")


def run_tmdb_pipeline(max_pages: int = TMDB_MAX_PAGES) -> list[dict]:
    """Extract + Save Raw + Map. Retourne les films mappés."""
    if not TMDB_TOKEN:
        raise RuntimeError("Missing TMDB_TOKEN")

    client = TMDBClient(token=TMDB_TOKEN)
    extractor = TMDBExtractor(client)

    # Récupération brute : liste de dicts tels que retournés par l'API TMDB
    raw_movies = extractor.fetch_movies(max_pages=max_pages)

    # Sauvegarde brute AVANT transformation
    # Pourquoi avant ? Pour garder une trace fidèle de ce que l'API a retourné
    # Si le mapper plante, on a quand même les données
    save_raw(raw_movies, RAW_OUTPUT_PATH)

    # Transformation : on ne garde que les champs utiles au projet
    mapped_movies = [TMDBMapper.map(m) for m in raw_movies]
    return mapped_movies


def main(max_pages: int = TMDB_MAX_PAGES) -> None:
    print("🚀 Lancement du pipeline HorRAGor...")

    # 0. Préparation de la base (idempotent)
    init_db()
    seed_genres()

    # 1-3. Extract + Save Raw + Map
    mapped_movies = run_tmdb_pipeline(max_pages=max_pages)
    print(f"✅ {len(mapped_movies)} films récupérés et mappés")

    # 4. Normalisation
    normalized_movies = [normalize_movie(m) for m in mapped_movies]
    print(f"🧹 {len(normalized_movies)} films normalisés")

    # 5. Sauvegarde clean
    save_normalized(normalized_movies)

    # 6. 🆕 Chargement en base
    stats = load_tmdb_normalized(CLEAN_OUTPUT_PATH)
    print(f"📊 Ingestion DB : {stats}")


if __name__ == "__main__":
    main()
