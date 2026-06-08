# Orchestration Prefect — base de travail (option du brief Partie 2)

> **✅ Option implémentée** (2026-06) : `src/horragor/flow.py` + `tests/test_flow.py`.
> Installer l'extra puis lancer : `uv sync --extra orchestration` → `python -m horragor.flow`.
> Le DAG enveloppe les fonctions `run_*` de `orchestrator.py` (aucune réécriture de
> l'ingestion/réconciliation) : extractions parallèles, Spark après Kaggle, fusion
> best-effort (`allow_failure`) → persistance Supabase. Voir détails ci-dessous.
>
> Le reste du document est conservé comme **cadrage historique**.

## 1. Demande initiale (brief HorRAGor BOT — Partie 2, section « Option »)

> **L'orchestration avec Prefect (Option)** — La Partie 1 demandait de lancer 5 sources en
> parallèle. Au lieu d'un script Python global un peu fragile, utiliser **Prefect** pour
> orchestrer le flux. Le DAG HorRAGor :
> - **Task 1 à 4** : lancement **en parallèle** des extractions (API TMDB, scraping Rotten
>   Tomatoes, BDD, etc.).
> - **Task 5** : un **spark-submit** sur le cluster pour les gros volumes textuels.
> - **Task 6** (dépendance) : une fois les extractions OK, **réconciliation (Fuzzy Matching)**.
> - **Task 7** : **persistance finale dans Supabase**.

C'est **facultatif** (« Option ») et **interne à la Partie 1** (ce n'est pas un lien P1↔P2).

## 2. Analyse de l'existant (état au 2026-06)

**Prefect n'est pas utilisé** : aucun `import prefect` / `@flow` / `@task` ; absent de
`pyproject.toml` (seul `pyspark` y figure).

À la place, un **orchestrateur Python maison** : `python -m horragor`
(`src/horragor/__main__.py` → `src/horragor/orchestrator.py`).

`orchestrator.py` :
- `INGESTION = {tmdb, imdb, kaggle, rotten, spark}` → une fonction `run_*` par source
  (**lazy imports** : Selenium/PySpark importés seulement à l'exécution).
- `run_ingestion(sources)` : exécute les sources **séquentiellement** (dans l'ordre du registre),
  avec **isolation des pannes** (`_step` : try/except, log, `{source: succès}`).
- `run_fusion()` : réconciliation MDM → **Gold** (Parquet) — `reconciliation/gold.py`,
  fuzzy matching dans `reconciliation/matcher.py`.
- `run_load()` : chargement du Gold dans la base relationnelle (Supabase) — `load/gold_loader.py`
  (via `DATABASE_URL`, SQLAlchemy).
- `run_all()` : ingestion → fusion → (chargement). CLI : `--sources`, `--skip-ingestion`,
  `--no-load`, `--max-pages`.
- `run_spark()` : `split_kaggle()` puis `spark_main()` (PySpark **local**, pas un spark-submit
  cluster).

**Correspondance brief ↔ existant :**

| DAG Prefect (brief) | Existant HorRAGor1 | Écart |
|---|---|---|
| Task 1-4 extractions **parallèles** | `run_ingestion` (tmdb/imdb/kaggle/rotten) | **séquentiel** (pas parallèle) |
| Task 5 spark-submit (cluster) | `run_spark` (PySpark local) | pas de cluster |
| Task 6 réconciliation fuzzy | `run_fusion` (`matcher.py`) | ✅ équivalent |
| Task 7 persistance Supabase | `run_load` (`gold_loader.py`) | ✅ équivalent |

## 3. Conclusion

- L'**option Prefect n'a pas été prise**. L'orchestrateur maison couvre déjà l'isolation des
  pannes et l'idempotence ; le pipeline est fonctionnel (base Supabase chargée, 33 961 films).
  C'est **conforme au brief** (Prefect = optionnel).
- **Ce que Prefect apporterait réellement** : le **parallélisme** des extractions (Task 1-4,
  aujourd'hui séquentielles), plus retries automatiques, observabilité et UI.

### Si on prend l'option (migration suggérée, sans tout réécrire)
- `uv add prefect`.
- Créer un **flow** (ex. `src/horragor/flows/horragor_flow.py`) :
  - envelopper les fonctions **existantes** `run_tmdb/run_imdb/run_kaggle/run_rotten/run_spark`
    en `@task` ; les **soumettre en parallèle** (`.submit()` + task runner concurrent) → Task 1-5 ;
  - `run_fusion` en `@task` **dépendant** de toutes les extractions → Task 6 ;
  - `run_load` en `@task` final → Task 7 ;
  - un `@flow` qui assemble le tout.
- **Réutiliser** les `run_*` tels quels : Prefect = couche d'orchestration **au-dessus**, on ne
  réécrit ni l'ingestion ni la réconciliation.
- Garder `python -m horragor` comme fallback (les deux chemins coexistent).
- *(Optionnel)* viser un vrai `spark-submit` pour Task 5 si un cluster est dispo.

### Pour Claude dans ce dépôt
- Lire en premier : `src/horragor/orchestrator.py` et `src/horragor/__main__.py`.
- Réutiliser les fonctions `run_*` ; **ne pas** réécrire ingestion/réconciliation.
- Vérif : lancer le flow Prefect, comparer le **Gold** (Parquet) et le contenu **Supabase** à
  ceux du pipeline maison (`python -m horragor`) — résultats identiques attendus.
