# src/ingestion/imdb/imdb_downloader.py
# Mise à jour régulières szur IMDB, relancer le téléchargement si fichiers actuels agées d'au moins 7 jours

import logging
import shutil
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

IMDB_BASE_URL = "https://datasets.imdbws.com/"

IMDB_FILES = {
    "title.basics.tsv.gz": "data/raw/imdb/title.basics.tsv.gz",
    "title.ratings.tsv.gz": "data/raw/imdb/title.ratings.tsv.gz",
}

MAX_AGE_DAYS = 7


def _is_fresh(path: Path) -> bool:
    """Retourne True si le fichier existe et a moins de MAX_AGE_DAYS jours."""
    if not path.exists():
        return False
    age = datetime.now() - datetime.fromtimestamp(path.stat().st_mtime)
    return age < timedelta(days=MAX_AGE_DAYS)


def _download_file(filename: str, dest_path: Path) -> None:
    url = IMDB_BASE_URL + filename
    logger.info(f"Téléchargement : {url}")
    with urllib.request.urlopen(url) as response, open(dest_path, "wb") as out_file:
        shutil.copyfileobj(response, out_file)
    logger.info(
        f"Sauvegardé : {dest_path} ({dest_path.stat().st_size / 1_000_000:.1f} MB)"
    )


def download_imdb_files(force: bool = False) -> dict[str, Path]:
    """
    Télécharge les dumps IMDB si absents ou obsolètes.
    Retourne un dict {nom_fichier: chemin_local}.
    """
    paths = {}

    for filename, raw_path_str in IMDB_FILES.items():
        dest_path = Path(raw_path_str)
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        if not force and _is_fresh(dest_path):
            logger.info(f"Fichier frais, skip : {dest_path}")
        else:
            _download_file(filename, dest_path)

        paths[filename] = dest_path

    return paths


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
    )
    result = download_imdb_files()
    for name, path in result.items():
        print(f"✅ {name} → {path}")
