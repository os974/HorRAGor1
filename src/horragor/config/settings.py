"""
Paramètres du projet : secrets (.env), URLs des sources et seuils métier.

Les chemins de fichiers sont définis séparément dans `paths.py`.
"""

import os

from dotenv import load_dotenv

load_dotenv()

# --- Secrets ----------------------------------------------------------------
TMDB_TOKEN = os.getenv("TMDB_TOKEN")

# --- TMDB (API) -------------------------------------------------------------
TMDB_BASE_URL = "https://api.themoviedb.org/3"
HORROR_GENRE_ID = 27  # id du genre "Horror" chez TMDB
TMDB_MAX_PAGES = 2  # nb de pages à parcourir par défaut

# --- IMDB (dumps publics) ---------------------------------------------------
IMDB_BASE_URL = "https://datasets.imdbws.com/"
IMDB_MAX_AGE_DAYS = 7  # re-télécharge les dumps au-delà de cet âge
IMDB_MIN_VOTES = 1000  # seuil qualité : exclut les films obscurs
IMDB_MIN_YEAR = 1970  # borne basse de l'année de sortie
IMDB_BATCH_SIZE = 50_000  # taille de lot pour le chargement SQLite
