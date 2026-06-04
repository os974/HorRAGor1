import json
from pathlib import Path

from horragor.config.paths import TMDB_CLEAN


def save_normalized(movies: list, path: Path = TMDB_CLEAN) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)  # crée les dossiers si absents
    with open(path, "w", encoding="utf-8") as f:  # "w" écrase le fichier existant
        json.dump(movies, f, ensure_ascii=False, indent=2)
    print(f"✅ {len(movies)} films normalisés sauvegardés dans {path}")
