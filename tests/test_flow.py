"""Tests du flow Prefect (DAG) — ordre des étapes et best-effort.

Ignorés si l'extra `orchestration` n'est pas installé (`uv sync --extra orchestration`).
Les `orchestrator.run_*` sont monkeypatchés (no-op) : aucun travail réel, aucun réseau.
"""

import pytest

pytest.importorskip("prefect")

from prefect.testing.utilities import prefect_test_harness  # noqa: E402

from horragor import flow, orchestrator  # noqa: E402


@pytest.fixture(autouse=True, scope="module")
def _prefect_harness():
    """Base Prefect temporaire en mémoire pour les tests (pas de serveur réel)."""
    with prefect_test_harness():
        yield


def _recorder(calls: list, name: str, *, fail: bool = False):
    def _fn(*args, **kwargs):
        calls.append(name)
        if fail:
            raise RuntimeError(f"{name} KO")
        return {name: "ok"}

    return _fn


def _patch_all(monkeypatch, calls, *, fail_source: str | None = None):
    for src in ("tmdb", "imdb", "kaggle", "rotten", "spark", "fusion", "load"):
        fail = src == fail_source
        monkeypatch.setattr(orchestrator, f"run_{src}", _recorder(calls, src, fail=fail))


def test_dag_order(monkeypatch):
    """Fusion après TOUTES les extractions ; load après la fusion."""
    calls: list[str] = []
    _patch_all(monkeypatch, calls)

    flow.horragor_flow(do_load=True)

    assert {"tmdb", "imdb", "kaggle", "rotten", "spark"} <= set(calls)
    extraction_idx = [calls.index(s) for s in ("tmdb", "imdb", "kaggle", "rotten", "spark")]
    assert calls.index("fusion") > max(extraction_idx)  # fusion en aval des extractions
    assert calls.index("load") > calls.index("fusion")  # load en aval de la fusion


def test_best_effort_continues_despite_source_failure(monkeypatch):
    """Une extraction qui échoue n'empêche pas fusion + load (allow_failure)."""
    calls: list[str] = []
    _patch_all(monkeypatch, calls, fail_source="tmdb")
    # Évite d'attendre les retries de la task qui échoue pendant le test.
    monkeypatch.setattr(flow, "tmdb_task", flow.tmdb_task.with_options(retries=0))

    flow.horragor_flow(do_load=True)

    assert "tmdb" in calls  # la task a bien été tentée
    assert "fusion" in calls and "load" in calls  # … mais le pipeline a continué


def test_skip_ingestion_runs_only_fusion_and_load(monkeypatch):
    """skip_ingestion : aucune extraction, juste fusion → load."""
    calls: list[str] = []
    _patch_all(monkeypatch, calls)

    flow.horragor_flow(do_load=True, skip_ingestion=True)

    assert calls == ["fusion", "load"]


def test_no_load_stops_after_fusion(monkeypatch):
    calls: list[str] = []
    _patch_all(monkeypatch, calls)

    flow.horragor_flow(do_load=False, skip_ingestion=True)

    assert calls == ["fusion"]
