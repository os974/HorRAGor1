# HorRAGor — Pipeline d'ingestion (Partie 1)

Pipeline d'ingestion multi-sources qui collecte, nettoie et **fusionne 5 sources
hétérogènes** (TMDB, Rotten Tomatoes, Kaggle, IMDB, Spark) en un dataset « Gold »
prêt pour la future architecture RAG d'un chatbot spécialisé horreur.

## Installation

```bash
git clone <repo-horragor> && cd horragor
uv sync   # crée le venv + installe les versions exactes du lock
cp .env.example .env   # puis renseigner TMDB_TOKEN (et DATABASE_URL pour Supabase)
```

Prérequis pour certaines sources : **Java** (PySpark), **Chrome/Firefox** (Selenium).

## Lancement (orchestrateur unique)

```bash
python -m horragor                    # 5 sources → fusion (Gold) → base
python -m horragor --sources tmdb,kaggle
python -m horragor --skip-ingestion   # (re)construit Gold + base depuis les clean existants
python -m horragor --no-load          # s'arrête au Gold (Parquet)
python -m horragor --max-pages 3      # profondeur du scan TMDB
```

Chaque source est isolée : un échec (réseau, anti-bot…) est journalisé sans
interrompre le pipeline — la fusion se fait avec les sources qui ont réussi.

### Option : orchestration Prefect (DAG)

Même pipeline orchestré par **Prefect** — extractions **en parallèle**, retries
automatiques et UI. Réutilise les mêmes étapes ; résultat identique.

```bash
uv sync --extra orchestration         # installe Prefect (extra optionnel)
python -m horragor.flow               # DAG : extractions ∥ → fusion → base
python -m horragor.flow --skip-ingestion --no-load
```

## Architecture

`src/horragor/` : `ingestion/` (1 sous-paquet par source) → `transform/` →
`reconciliation/` (matching MDM + Gold) → `load/` (base) ; `db/` (ORM SQLAlchemy)
et `config/` (chemins + secrets). Détails : [docs/plan-projet.md](docs/plan-projet.md).

Modélisation Merise (MCD/MLD/MPD) : [docs/merise/merise.md](docs/merise/merise.md).

## Qualité

```bash
uv run pytest          # tests
uv run ruff check .    # lint
```
