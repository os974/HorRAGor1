"""Tests de l'orchestrateur et de son CLI."""

import pytest

from horragor import __main__ as cli
from horragor import orchestrator


class TestParseArgs:
    def test_defaults(self):
        args = cli.parse_args([])
        assert args.sources == "tmdb,imdb,kaggle,rotten,spark"
        assert args.skip_ingestion is False
        assert args.no_load is False

    def test_flags(self):
        args = cli.parse_args(["--sources", "tmdb,kaggle", "--skip-ingestion", "--no-load"])
        assert args.sources == "tmdb,kaggle"
        assert args.skip_ingestion is True
        assert args.no_load is True

    def test_unknown_source_rejected(self):
        with pytest.raises(SystemExit):
            cli._resolve_sources("tmdb,banana")

    def test_resolve_valid(self):
        assert cli._resolve_sources("tmdb, spark") == ["tmdb", "spark"]


class TestStepIsolation:
    def test_step_returns_true_on_success(self):
        assert orchestrator._step("ok", lambda: None) is True

    def test_step_isolates_failure(self):
        def boom():
            raise RuntimeError("réseau down")

        # Ne doit pas propager l'exception, juste retourner False.
        assert orchestrator._step("ko", boom) is False

    def test_run_ingestion_continues_after_failure(self, monkeypatch):
        calls = []
        monkeypatch.setitem(orchestrator.INGESTION, "tmdb", lambda: calls.append("tmdb"))

        def fail():
            raise RuntimeError("x")

        monkeypatch.setitem(orchestrator.INGESTION, "imdb", fail)
        monkeypatch.setitem(orchestrator.INGESTION, "kaggle", lambda: calls.append("kaggle"))

        result = orchestrator.run_ingestion(["tmdb", "imdb", "kaggle"])
        assert result == {"tmdb": True, "imdb": False, "kaggle": True}
        assert calls == ["tmdb", "kaggle"]  # kaggle exécuté malgré l'échec imdb


class TestToleranceAdapters:
    def test_missing_clean_files_return_empty(self, tmp_path, monkeypatch):
        from horragor.reconciliation import adapters

        for attr in ("TMDB_CLEAN", "IMDB_HORROR_CLEAN", "KAGGLE_CLEAN"):
            monkeypatch.setattr(adapters, attr, tmp_path / f"{attr}.absent")
        assert adapters.tmdb_films() == []
        assert adapters.imdb_films() == []
        assert adapters.kaggle_films() == []
