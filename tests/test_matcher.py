"""Tests du matcher MDM (clustering + réconciliation)."""

from horragor.reconciliation.matcher import cluster_films, reconcile
from horragor.reconciliation.schema import Film


def _clusters_as_sets(clusters):
    """Représente chaque cluster par l'ensemble de ses sources, pour comparaison."""
    return sorted((sorted(f.sources[0] for f in c) for c in clusters))


class TestExactMatching:
    def test_n1_groups_by_tmdb_id(self):
        films = [
            Film(tmdb_id=42, title="Alien", sources=["tmdb"]),
            Film(tmdb_id=42, title="Alien", year=1979, sources=["kaggle"]),
            Film(tmdb_id=99, title="Saw", sources=["tmdb"]),
        ]
        clusters = cluster_films(films)
        assert _clusters_as_sets(clusters) == [["kaggle", "tmdb"], ["tmdb"]]

    def test_n2_groups_by_imdb_id(self):
        films = [
            Film(imdb_id="tt0001", title="X", sources=["imdb"]),
            Film(imdb_id="tt0001", title="X", sources=["spark"]),
        ]
        clusters = cluster_films(films)
        assert len(clusters) == 1
        assert {f.sources[0] for f in clusters[0]} == {"imdb", "spark"}


class TestFuzzyMatching:
    def test_n3_links_imdb_to_tmdb_by_title_year(self):
        # IMDB n'a pas de tmdb_id : seul le fuzzy titre+année peut le rattacher
        films = [
            Film(tmdb_id=1, title="The Texas Chain Saw Massacre", year=1974, sources=["tmdb"]),
            Film(imdb_id="tt0072271", title="The Texas Chainsaw Massacre", year=1974, sources=["imdb"]),
        ]
        clusters = cluster_films(films)
        assert len(clusters) == 1  # rattachés malgré l'orthographe différente

    def test_dissimilar_titles_not_merged(self):
        films = [
            Film(tmdb_id=1, title="Hereditary", year=2018, sources=["tmdb"]),
            Film(imdb_id="tt1", title="Midsommar", year=2018, sources=["imdb"]),
        ]
        clusters = cluster_films(films)
        assert len(clusters) == 2  # même année mais titres trop différents

    def test_year_out_of_tolerance_not_merged(self):
        films = [
            Film(tmdb_id=1, title="It", year=1990, sources=["tmdb"]),
            Film(imdb_id="tt1", title="It", year=2017, sources=["imdb"]),
        ]
        clusters = cluster_films(films)
        assert len(clusters) == 2  # même titre mais 27 ans d'écart

    def test_year_within_tolerance_merged(self):
        films = [
            Film(tmdb_id=1, title="Nosferatu", year=1922, sources=["tmdb"]),
            Film(imdb_id="tt1", title="Nosferatu", year=1921, sources=["imdb"]),
        ]
        clusters = cluster_films(films)
        assert len(clusters) == 1  # écart d'1 an toléré


class TestReconcileEndToEnd:
    def test_three_sources_one_film(self):
        films = [
            Film(tmdb_id=694, title="The Shining", year=1980, overview=None, sources=["tmdb"]),
            Film(tmdb_id=694, budget=19_000_000, sources=["kaggle"]),
            Film(imdb_id="tt0081505", title="The Shining", year=1980,
                 imdb_average_rating=8.4, sources=["imdb"]),
        ]
        unified = reconcile(films)
        assert len(unified) == 1
        f = unified[0]
        assert f.tmdb_id == 694
        assert f.imdb_id == "tt0081505"  # apporté par IMDB via fuzzy
        assert f.budget == 19_000_000  # apporté par Kaggle
        assert f.imdb_average_rating == 8.4
        assert set(f.sources) == {"tmdb", "kaggle", "imdb"}
