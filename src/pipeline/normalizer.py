import re
from datetime import datetime


def normalize_date(date_str: str | None) -> str | None:
    """
    Convertit une date en ISO 8601 (YYYY-MM-DD).
    Si seule l'année est fournie → YYYY-01-01
    TMDB fournit déjà YYYY-MM-DD mais on sécurise pour la fusion future
    avec Kaggle/IMDB qui ont des formats différents.
    """
    if not date_str:
        return None

    # Format complet YYYY-MM-DD (TMDB, Kaggle)
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y-%m-%d")
    except ValueError:
        pass

    # Année seule (IMDB : startYear entier ou string)
    try:
        year = int(str(date_str).strip())
        return f"{year}-01-01"
    except ValueError:
        return None


def normalize_text(text: str | None) -> str | None:
    """
    Nettoie un texte :
    - Supprime les balises HTML résiduelles
    - Normalise les espaces
    - Encode en UTF-8
    """
    if not text:
        return None

    # Suppression balises HTML
    text = re.sub(r"<[^>]+>", "", text)

    # Normalisation whitespace (tabs, doubles espaces, newlines)
    text = re.sub(r"\s+", " ", text).strip()

    # Garantit UTF-8
    text = text.encode("utf-8", errors="ignore").decode("utf-8")

    return text


# def normalize_movie(movie: dict) -> dict:
#     """
#     Applique toutes les normalisations sur un film mappé.
#     Retourne un dict "Gold" prêt pour Supabase.
#     """
#     return {
#         "title": normalize_text(movie.get("title")),
#         "overview": normalize_text(movie.get("overview")),
#         "release_date": normalize_date(movie.get("release_date")),
#         "vote_average": movie.get("vote_average"),  # Déjà 0-10, rien à faire
#         "popularity": movie.get("popularity"),
#         "poster_path": movie.get("poster_path"),
#     }


def normalize_movie(movie: dict) -> dict:
    """
    Applique toutes les normalisations sur un film mappé.

    Principe : on part du dict complet (**movie) et on n'écrase que les
    champs qui nécessitent une transformation. Les nouveaux champs
    ajoutés par le mapper traversent automatiquement, sans modification
    ici. C'est le pattern "enrichissement non-destructif".
    """
    return {
        **movie,  # 🔑 préserve tmdb_id, genre_ids, vote_count, etc.
        "title": normalize_text(movie.get("title")),
        "overview": normalize_text(movie.get("overview")),
        "original_title": normalize_text(movie.get("original_title")),
        "release_date": normalize_date(movie.get("release_date")),
        # vote_average, popularity, poster_path : inchangés, déjà propres côté TMDB
    }
