import json
import os


def save_normalized(movies: list, path: str = "data/clean/tmdb_normalized.json"):
    os.makedirs(os.path.dirname(path), exist_ok=True)  # crée les dossiers si absents
    with open(
        path, "w", encoding="utf-8"
    ) as f:  # "w" écrase le fichier s'il existe déjà
        json.dump(movies, f, ensure_ascii=False, indent=2)
    print(f"✅ {len(movies)} films normalisés sauvegardés dans {path}")
