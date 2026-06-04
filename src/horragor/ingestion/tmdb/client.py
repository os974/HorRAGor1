import requests

from horragor.config.settings import HORROR_GENRE_ID, TMDB_BASE_URL


class TMDBClient:
    BASE_URL = TMDB_BASE_URL

    def __init__(self, token):
        self.headers = {"Authorization": f"Bearer {token}"}

    def discover_movies(self, page=1):
        url = f"{self.BASE_URL}/discover/movie"
        # Filtrage par genre Horreur (cf. HORROR_GENRE_ID dans settings)
        params = {"with_genres": HORROR_GENRE_ID, "page": page}
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()
