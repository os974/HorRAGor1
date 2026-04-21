from config.settings import TMDB_TOKEN
from ingestion.tmdb.tmdb_client import TMDBClient
from ingestion.tmdb.tmdb_extractor import TMDBExtractor
from ingestion.tmdb.tmdb_mapper import TMDBMapper


def run_tmdb_pipeline(max_pages=2):

    if not TMDB_TOKEN:
        raise RuntimeError("Missing TMDB_TOKEN")

    client = TMDBClient(token=TMDB_TOKEN)
    extractor = TMDBExtractor(client)

    raw_movies = extractor.fetch_movies(max_pages=max_pages)

    mapped_movies = [TMDBMapper.map(m) for m in raw_movies]

    return mapped_movies


if __name__ == "__main__":
    print("🚀 Lancement du pipeline HorRAGor...")
    data = run_tmdb_pipeline()
    print(f"{len(data)} films récupérés")
