class TMDBMapper:
    """
    Transforme la réponse brute de l'API TMDB en dict standardisé.

    Règle : le mapper est le SEUL endroit qui décide ce qui traverse le
    pipeline. Tout champ absent ici sera perdu pour toujours.
    """

    @staticmethod
    def map(movie: dict) -> dict:
        return {
            "tmdb_id": movie["id"],
            "title": movie.get("title"),
            "original_title": movie.get(
                "original_title"
            ),  # utile pour dédoublonnage futur
            "original_language": movie.get("original_language"),
            "overview": movie.get("overview"),
            "release_date": movie.get("release_date"),
            "vote_average": movie.get("vote_average"),
            "vote_count": movie.get("vote_count"),  # pour pondérer les notes
            "popularity": movie.get("popularity"),
            "poster_path": movie.get("poster_path"),
            "genre_ids": movie.get("genre_ids", []),  # INDISPENSABLE pour movie_genres
        }
