class TMDBMapper:
    @staticmethod
    def map(movie):
        return {
            "tmdb_id": movie["id"],
            "title": movie["title"],
            "overview": movie["overview"],
            "release_date": movie["release_date"],
            "vote_average": movie["vote_average"],
            "popularity": movie["popularity"],
            "poster_path": movie["poster_path"],
        }


# from src.models.movie import Movie


# def map_tmdb_to_movie(data: dict) -> Movie:
#     return Movie(
#         id=str(data.get("id")),
#         tmdb_id=data.get("id"),
#         imdb_id=None,
#         title=data.get("title"),
#         original_title=data.get("original_title"),
#         release_date=data.get("release_date"),
#         year=int(data["release_date"][:4]) if data.get("release_date") else None,
#         genres=[g["name"] for g in data.get("genres", [])],
#         overview=data.get("overview"),
#         runtime=data.get("runtime"),
#         language=data.get("original_language"),
#         country=[c["name"] for c in data.get("production_countries", [])],
#         popularity=data.get("popularity"),
#         vote_average=data.get("vote_average"),
#         vote_count=data.get("vote_count"),
#         revenue=data.get("revenue"),
#         budget=data.get("budget"),
#         poster_url=data.get("poster_path"),
#         backdrop_url=data.get("backdrop_path"),
#         director=None,
#         cast=None,
#         production_companies=[c["name"] for c in data.get("production_companies", [])],
#         rt_score=None,
#         rt_reviews=None,
#         source_priority_score=1.0,
#     )
