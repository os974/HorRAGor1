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

# --- Rotten Tomatoes (scraping Selenium) ------------------------------------
ROTTEN_BASE_URL = "https://www.rottentomatoes.com"
ROTTEN_PAGE_TIMEOUT = 20  # attente max (s) du rendu JS du media-scorecard
ROTTEN_REQUEST_DELAY = 1.5  # pause entre deux pages (politesse anti-surcharge)
# Cibles par défaut : slugs RT de films d'horreur de référence.
# En production, cette liste serait alimentée par la page browse/trending RT
# ou par les titres déjà présents dans le Gold (enrichissement ciblé).
ROTTEN_HORROR_SLUGS = (
    "hereditary",
    "midsommar",
    "get_out_2017",
    "a_quiet_place",
    "the_conjuring",
    "the_witch_2015",
    "it_2017",
    "the_babadook",
    "us_2019",
    "smile_2022",
    "talk_to_me_2023",
    "the_substance",
)
