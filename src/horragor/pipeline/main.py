import json
from pathlib import Path

from horragor.config.settings import TMDB_TOKEN
from horragor.ingestion.tmdb.tmdb_client import TMDBClient
from horragor.ingestion.tmdb.tmdb_extractor import TMDBExtractor
from horragor.ingestion.tmdb.tmdb_mapper import TMDBMapper
from horragor.pipeline.normalizer import normalize_movie
from horragor.pipeline.saver import save_normalized

# Chemin de sauvegarde brute
# On utilise Path pour être compatible Windows/Linux/Mac
RAW_OUTPUT_PATH = Path("data/raw/tmdb_raw.json")


def save_raw(data: list[dict], path: Path) -> None:
    """
    Sauvegarde les données brutes en JSON.

    Pourquoi sauvegarder le brut ?
    - Evite de refaire des appels API (quota limité) si le pipeline plante après
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


def run_tmdb_pipeline(max_pages=2):

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


if __name__ == "__main__":
    print("🚀 Lancement du pipeline HorRAGor...")

    mapped_movies = run_tmdb_pipeline()
    print(f"✅ {len(mapped_movies)} films récupérés et mappés")

    # Après le mapping
    normalized_movies = [normalize_movie(m) for m in mapped_movies]
    print(normalized_movies[0])  # affiche le premier film normalisé
    save_normalized(normalized_movies)
