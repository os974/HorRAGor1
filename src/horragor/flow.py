"""
Flow Prefect — orchestration en DAG du pipeline HorRAGor (option brief Partie 2).

Couche d'orchestration AU-DESSUS des fonctions `run_*` de `orchestrator.py` : on
ne réécrit NI l'ingestion NI la réconciliation. Apports vs `python -m horragor` :
- extractions (Task 1-4) lancées **en parallèle** (task runner concurrent) ;
- **retries** automatiques par task + **observabilité** (UI Prefect) ;
- **best-effort** : une source en échec (après retries) n'arrête pas le flow grâce
  à `allow_failure` — la fusion se fait avec les sources réussies (les adapters de
  `reconciliation/adapters.py` tolèrent les artefacts `clean` manquants).

Lancement :  python -m horragor.flow            (fallback maison : python -m horragor)
Prérequis :  uv sync --extra orchestration
"""

from __future__ import annotations

from prefect import allow_failure, flow, task

from horragor import orchestrator

# Les tasks sont des wrappers MINCES qui appellent `orchestrator.run_*` AU RUNTIME
# (et non en liant l'objet fonction à l'import) : cela préserve les lazy imports
# des sources et permet de monkeypatcher les `run_*` dans les tests.


@task(name="extract-tmdb", retries=2, retry_delay_seconds=10)
def tmdb_task() -> None:
    orchestrator.run_tmdb()


@task(name="extract-imdb", retries=1, retry_delay_seconds=30)
def imdb_task() -> None:
    orchestrator.run_imdb()


@task(name="extract-kaggle", retries=1)
def kaggle_task() -> None:
    orchestrator.run_kaggle()


@task(name="scrape-rotten", retries=2, retry_delay_seconds=15)
def rotten_task() -> None:
    orchestrator.run_rotten()


@task(name="spark-text-analysis", retries=1)
def spark_task() -> None:
    orchestrator.run_spark()


@task(name="reconcile-gold")
def fusion_task() -> dict:
    return orchestrator.run_fusion()


@task(name="load-supabase", retries=2, retry_delay_seconds=10)
def load_task() -> dict:
    return orchestrator.run_load()


@flow(name="horragor")
def horragor_flow(do_load: bool = True, skip_ingestion: bool = False) -> None:
    """DAG : extractions (parallèle) → réconciliation → persistance Supabase."""
    if skip_ingestion:
        # (Re)construit Gold + base depuis les artefacts clean existants.
        f_fusion = fusion_task.submit()
    else:
        # Task 1-4 : extractions indépendantes, en parallèle.
        f_tmdb = tmdb_task.submit()
        f_imdb = imdb_task.submit()
        f_kaggle = kaggle_task.submit()
        f_rotten = rotten_task.submit()
        # Task 5 : Spark a besoin de `kaggle_clean.csv` → dépend de Kaggle.
        f_spark = spark_task.submit(wait_for=[f_kaggle])

        extractions = [f_tmdb, f_imdb, f_kaggle, f_rotten, f_spark]
        # Task 6 : réconciliation fuzzy → Gold. `allow_failure` => best-effort :
        # la fusion tourne même si une extraction a échoué.
        f_fusion = fusion_task.submit(
            wait_for=[allow_failure(f) for f in extractions]
        )

    # Task 7 : persistance Supabase, en aval de la fusion.
    if do_load:
        load_task.submit(wait_for=[f_fusion]).result()
    else:
        f_fusion.result()


def _main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        prog="horragor.flow",
        description="Pipeline HorRAGor orchestré par Prefect (DAG).",
    )
    parser.add_argument(
        "--skip-ingestion",
        action="store_true",
        help="(Re)construit Gold + base depuis les clean existants (pas d'extraction).",
    )
    parser.add_argument(
        "--no-load",
        action="store_true",
        help="S'arrête après le Gold (Parquet), sans charger la base.",
    )
    args = parser.parse_args()
    horragor_flow(do_load=not args.no_load, skip_ingestion=args.skip_ingestion)


if __name__ == "__main__":
    _main()
