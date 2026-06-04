"""Tests du pipeline Spark : helper pur, splitter, adapter canonique.

Le job Spark lui-même (SparkSession) est validé par un run réel, pas en
unitaire ; ici on couvre la logique pure et l'intégration des artefacts.
"""

import polars as pl

from horragor.ingestion.spark import splitter
from horragor.ingestion.spark.job import top_keywords
from horragor.reconciliation import adapters
from horragor.reconciliation.adapters import spark_films


class TestTopKeywords:
    def test_ranks_by_tfidf_weight_desc(self):
        vocab = ["the", "horror", "blood", "night"]
        # indices/valeurs d'un vecteur TF-IDF creux
        indices = [0, 1, 2, 3]
        values = [0.1, 0.9, 0.5, 0.7]
        assert top_keywords(indices, values, vocab, k=2) == ["horror", "night"]

    def test_k_limits_result(self):
        vocab = ["a", "b", "c"]
        assert top_keywords([0, 1, 2], [3.0, 2.0, 1.0], vocab, k=10) == ["a", "b", "c"]

    def test_empty(self):
        assert top_keywords([], [], ["x"], k=5) == []


class TestSplitter:
    def test_splits_and_preserves_all_rows(self, tmp_path, monkeypatch):
        src = tmp_path / "kaggle.csv"
        pl.DataFrame(
            {
                "id": list(range(10)),
                "title": [f"t{i}" for i in range(10)],
                "overview": [f"synopsis {i}" for i in range(10)],
            }
        ).write_csv(src)
        out_dir = tmp_path / "spark_in"
        monkeypatch.setattr(splitter, "KAGGLE_CLEAN", src)
        monkeypatch.setattr(splitter, "SPARK_INPUT_DIR", out_dir)

        paths = splitter.split_kaggle(num_partitions=3)
        assert len(paths) == 3
        total = sum(pl.read_csv(p).height for p in paths)
        assert total == 10  # aucune ligne perdue

    def test_purges_old_partitions(self, tmp_path, monkeypatch):
        src = tmp_path / "kaggle.csv"
        pl.DataFrame({"id": [1], "title": ["x"], "overview": ["y"]}).write_csv(src)
        out_dir = tmp_path / "spark_in"
        out_dir.mkdir()
        (out_dir / "part_99.csv").write_text("stale")  # ancienne partition
        monkeypatch.setattr(splitter, "KAGGLE_CLEAN", src)
        monkeypatch.setattr(splitter, "SPARK_INPUT_DIR", out_dir)

        splitter.split_kaggle(num_partitions=2)
        assert not (out_dir / "part_99.csv").exists()


class TestSparkAdapter:
    def test_maps_keywords_and_word_count(self, tmp_path, monkeypatch):
        p = tmp_path / "spark_clean.parquet"
        pl.DataFrame(
            {
                "tmdb_id": [42],
                "overview_word_count": [12],
                "keywords": [["horror", "blood"]],
            },
            schema={
                "tmdb_id": pl.Int64,
                "overview_word_count": pl.Int64,
                "keywords": pl.List(pl.Utf8),
            },
        ).write_parquet(p)
        monkeypatch.setattr(adapters, "SPARK_CLEAN", p)

        films = spark_films()
        assert len(films) == 1
        f = films[0]
        assert f.tmdb_id == 42
        assert f.overview_word_count == 12
        assert f.keywords == ["horror", "blood"]
        assert f.sources == ["spark"]

    def test_missing_file_returns_empty(self, tmp_path, monkeypatch):
        monkeypatch.setattr(adapters, "SPARK_CLEAN", tmp_path / "absent.parquet")
        assert spark_films() == []
