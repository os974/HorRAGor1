class TMDBExtractor:
    def __init__(self, client):
        self.client = client

    def fetch_movies(self, max_pages=5):
        all_movies = []

        for page in range(1, max_pages + 1):
            data = self.client.discover_movies(page)
            all_movies.extend(data["results"])

        return all_movies
