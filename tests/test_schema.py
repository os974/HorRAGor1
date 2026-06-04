"""Tests du schéma canonique et des règles de fusion (MDM)."""

from horragor.reconciliation.schema import (
    SOURCE_PRIORITY,
    Film,
    merge_films,
    source_rank,
)


class TestSourceRank:
    def test_tmdb_is_top_priority(self):
        assert source_rank("tmdb") == 0
        assert source_rank("tmdb") < source_rank("imdb")

    def test_priority_order_matches_brief(self):
        assert SOURCE_PRIORITY == (
            "tmdb",
            "rotten_tomatoes",
            "kaggle",
            "imdb",
            "spark",
        )

    def test_unknown_source_goes_last(self):
        assert source_rank("???") == len(SOURCE_PRIORITY)


class TestMergeFilms:
    def test_higher_priority_wins_on_conflict(self):
        tmdb = Film(title="The Thing", sources=["tmdb"])
        imdb = Film(title="The Thing (1982)", sources=["imdb"])
        merged = merge_films([imdb, tmdb])  # ordre d'entrée indifférent
        assert merged.title == "The Thing"  # TMDB prioritaire

    def test_fallback_fills_missing_field(self):
        # TMDB sans synopsis -> bascule sur Kaggle
        tmdb = Film(tmdb_id=42, title="Alien", overview=None, sources=["tmdb"])
        kaggle = Film(tmdb_id=42, overview="In space...", sources=["kaggle"])
        merged = merge_films([tmdb, kaggle])
        assert merged.overview == "In space..."
        assert merged.title == "Alien"

    def test_score_columns_are_per_source(self):
        tmdb = Film(tmdb_vote_average=8.2, sources=["tmdb"])
        imdb = Film(imdb_average_rating=8.1, sources=["imdb"])
        merged = merge_films([tmdb, imdb])
        assert merged.tmdb_vote_average == 8.2
        assert merged.imdb_average_rating == 8.1

    def test_genres_are_unioned_deduplicated(self):
        tmdb = Film(genres=["Horror", "Thriller"], sources=["tmdb"])
        imdb = Film(genres=["Horror", "Mystery"], sources=["imdb"])
        merged = merge_films([tmdb, imdb])
        assert merged.genres == ["Horror", "Thriller", "Mystery"]

    def test_sources_collected(self):
        merged = merge_films(
            [Film(sources=["tmdb"]), Film(sources=["imdb"]), Film(sources=["kaggle"])]
        )
        assert set(merged.sources) == {"tmdb", "imdb", "kaggle"}

    def test_single_partial_passthrough(self):
        merged = merge_films([Film(tmdb_id=1, title="X", sources=["tmdb"])])
        assert merged.tmdb_id == 1
        assert merged.title == "X"
