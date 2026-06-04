"""
Chemins centralisés du projet HorRAGor.

Tous les chemins sont ancrés sur la racine du dépôt (et non sur le
répertoire courant), de sorte que les modules fonctionnent quel que soit
l'endroit d'où on lance le pipeline.

Convention des couches data/ :
  raw/          données brutes telles que reçues des sources
  intermediate/ artefacts de travail (DB IMDB, CSV intermédiaires)
  clean/        données nettoyées/normalisées par source
  gold/         dataset final unifié, prêt pour le RAG
"""

from pathlib import Path

# src/horragor/config/paths.py -> parents[3] = racine du repo
ROOT = Path(__file__).resolve().parents[3]

# --- Couches data -----------------------------------------------------------
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
INTERMEDIATE_DIR = DATA_DIR / "intermediate"
CLEAN_DIR = DATA_DIR / "clean"
GOLD_DIR = DATA_DIR / "gold"

# --- Base de données locale (agrégation avant Supabase) ---------------------
HORRAGOR_DB = DATA_DIR / "horragor.db"

# --- TMDB -------------------------------------------------------------------
TMDB_RAW = RAW_DIR / "tmdb_raw.json"
TMDB_CLEAN = CLEAN_DIR / "tmdb_normalized.json"

# --- IMDB -------------------------------------------------------------------
IMDB_RAW_DIR = RAW_DIR / "imdb"
IMDB_BASICS_GZ = IMDB_RAW_DIR / "title.basics.tsv.gz"
IMDB_RATINGS_GZ = IMDB_RAW_DIR / "title.ratings.tsv.gz"
IMDB_DB = INTERMEDIATE_DIR / "imdb.db"
IMDB_HORROR_RAW = INTERMEDIATE_DIR / "imdb_horror_raw.csv"
IMDB_HORROR_CLEAN = CLEAN_DIR / "imdb_horror_clean.csv"

# --- Kaggle -----------------------------------------------------------------
KAGGLE_RAW = RAW_DIR / "kaggle_raw.csv"
KAGGLE_CLEAN = CLEAN_DIR / "kaggle_clean.csv"

# --- Rotten Tomatoes --------------------------------------------------------
ROTTEN_RAW = RAW_DIR / "rotten_raw.json"
ROTTEN_CLEAN = CLEAN_DIR / "rotten_clean.json"

# --- Spark (big data : fichiers Kaggle splittés) ----------------------------
SPARK_INPUT_DIR = RAW_DIR / "spark"  # partitions CSV lues en parallèle par Spark
SPARK_CLEAN = CLEAN_DIR / "spark_clean.parquet"  # enrichissement textuel par film

# --- Gold (dataset final unifié) --------------------------------------------
GOLD_PARQUET = GOLD_DIR / "horragor_gold.parquet"
