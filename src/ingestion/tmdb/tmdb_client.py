import requests


class TMDBClient:
    BASE_URL = "https://api.themoviedb.org/3"

    def __init__(self, token):
        self.headers = {"Authorization": f"Bearer {token}"}

    def discover_movies(self, page=1):
        url = f"{self.BASE_URL}/discover/movie"
        # For demonstration, we're filtering by the "Horror" genre (genre ID 27).
        # GET /discover/movie?with_genres=27 = genre horreur
        params = {"with_genres": 27, "page": page}
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()
