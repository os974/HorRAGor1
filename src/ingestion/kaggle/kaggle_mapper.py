import polars as pl

KEEP_COLUMNS = [
    "id",
    "title",
    "original_title",
    "original_language",
    "overview",
    "tagline",
    "release_date",
    "popularity",
    "vote_count",
    "vote_average",
    "budget",
    "revenue",
    "runtime",
    "status",
    "genre_names",
    "collection_name",
]


def map(df: pl.DataFrame) -> pl.DataFrame:
    return df.select(KEEP_COLUMNS)
