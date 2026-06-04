-- =============================================================================
--  HorRAGor — MPD (Modèle Physique de Données)
--  Méthode Merise | Compatible SQLite (local) et PostgreSQL (Supabase)
--  Auteur : HorRAGor Project
-- =============================================================================
--
--  CONTEXTE :
--  Ce fichier définit le schéma physique de la base de données locale SQLite
--  utilisée comme couche d'agrégation avant déploiement sur Supabase.
--  Il est généré à partir du MCD via la méthodologie Merise.
--
--  ORDRE DE CRÉATION :
--  Les tables sans dépendance (GENRE) sont créées en premier,
--  puis les tables avec clés étrangères (MOVIE_GENRES, RATING, SOURCE_METADATA).
-- =============================================================================


-- -----------------------------------------------------------------------------
-- TABLE : genres
-- Référentiel des genres cinématographiques issus de TMDB.
-- Séparée de MOVIE pour éviter la redondance et permettre le filtrage thématique.
-- Exemple : id=27, name='Horror' — seul genre ciblé dans un premier temps.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS genres (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,  -- Clé primaire interne
    tmdb_genre_id INTEGER NOT NULL UNIQUE,            -- ID TMDB officiel (ex: 27 = Horror)
    name          VARCHAR(100) NOT NULL               -- Nom du genre (ex: 'Horror')
);


-- -----------------------------------------------------------------------------
-- TABLE : movies
-- Table centrale (source maîtresse TMDB).
-- Contient les métadonnées officielles de chaque film.
-- tmdb_id et imdb_id sont les clés de réconciliation MDM entre les sources.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS movies (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,   -- Clé primaire interne
    tmdb_id        INTEGER UNIQUE,                       -- ID TMDB (clé de réconciliation niveau 1)
    imdb_id        VARCHAR(20) UNIQUE,                   -- ID IMDB (clé de réconciliation niveau 2)
    title          VARCHAR(500) NOT NULL,                -- Titre principal (source TMDB)
    original_title VARCHAR(500),                         -- Titre original (peut différer du titre FR)
    overview       TEXT,                                 -- Synopsis — fallback sur source suivante si NULL
    release_date   DATE,                                 -- Format ISO 8601 : YYYY-MM-DD
    popularity     FLOAT,                                -- Score de popularité TMDB (float)
    poster_path    VARCHAR(300),                         -- Chemin relatif TMDB (ex: /abc123.jpg)
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- Date d'ingestion initiale
    updated_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP  -- Date de dernière mise à jour
);


-- -----------------------------------------------------------------------------
-- TABLE : movie_genres
-- Table de liaison N-N entre MOVIE et GENRE.
-- Générée depuis la relation "appartient" du MCD.
-- Un film peut appartenir à plusieurs genres, un genre regroupe plusieurs films.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS movie_genres (
    movie_id  INTEGER NOT NULL REFERENCES movies(id) ON DELETE CASCADE,
    genre_id  INTEGER NOT NULL REFERENCES genres(id) ON DELETE CASCADE,
    PRIMARY KEY (movie_id, genre_id)  -- Clé primaire composée — évite les doublons
);


-- -----------------------------------------------------------------------------
-- TABLE : ratings
-- Agrège les scores de toutes les sources en conservant leur échelle native :
--   - TMDB  : vote_average sur 0-10
--   - IMDB  : averageRating sur 0-10
--   - RT    : tomatometer_score / audience_score sur 0-100 (%)
-- Le champ 'source' permet de distinguer l'origine de chaque note.
-- critics_consensus est exclusif à Rotten Tomatoes (texte de synthèse critique).
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ratings (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    movie_id          INTEGER NOT NULL REFERENCES movies(id) ON DELETE CASCADE,
    source            VARCHAR(50) NOT NULL CHECK(source IN ('tmdb', 'imdb', 'rotten_tomatoes')),
    score             FLOAT,            -- Échelle native conservée (voir commentaire ci-dessus)
    vote_count        INTEGER,          -- Nombre de votes (pertinent pour TMDB et IMDB)
    critics_consensus TEXT,             -- Texte critique RT (NULL pour TMDB et IMDB)
    UNIQUE (movie_id, source)           -- Un seul enregistrement par film et par source
);


-- -----------------------------------------------------------------------------
-- TABLE : sources_metadata
-- Traçabilité du pipeline d'ingestion.
-- Permet de savoir quelle source a contribué à enrichir chaque film,
-- et quand l'ingestion a eu lieu. Utile pour les reruns et la qualité des données.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sources_metadata (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    movie_id    INTEGER NOT NULL REFERENCES movies(id) ON DELETE CASCADE,
    source_name VARCHAR(100) NOT NULL,                  -- Nom de la source (ex: 'tmdb', 'kaggle')
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP     -- Horodatage de l'ingestion
);


-- =============================================================================
--  DONNÉES INITIALES : Référentiel des genres TMDB
--  On pré-charge les genres Horror et quelques genres adjacents pour référence.
--  Le pipeline ne conserve que les films liés au genre id=27 (Horror).
-- =============================================================================
INSERT OR IGNORE INTO genres (tmdb_genre_id, name) VALUES
    (27,  'Horror'),
    (53,  'Thriller'),    -- Souvent couplé à Horror dans les films du corpus
    (9648,'Mystery'),     -- Idem
    (878, 'Science Fiction'), -- Ex: Alien
    (28,  'Action'),
    (18,  'Drama');


-- =============================================================================
--  INDEX — Optimisation des requêtes fréquentes
-- =============================================================================

-- Accès rapide par identifiants de réconciliation MDM
CREATE INDEX IF NOT EXISTS idx_movies_tmdb_id ON movies(tmdb_id);
CREATE INDEX IF NOT EXISTS idx_movies_imdb_id ON movies(imdb_id);

-- Accès rapide aux ratings d'un film donné
CREATE INDEX IF NOT EXISTS idx_ratings_movie_id ON ratings(movie_id);

-- Accès rapide aux genres d'un film donné
CREATE INDEX IF NOT EXISTS idx_movie_genres_movie_id ON movie_genres(movie_id);

-- Accès rapide aux métadonnées d'ingestion d'un film
CREATE INDEX IF NOT EXISTS idx_sources_metadata_movie_id ON sources_metadata(movie_id);


-- =============================================================================
--  FIN DU MPD
--  Prochaine étape : Traduire ce schéma en classes SQLAlchemy ORM (models.py)
--  puis connecter à Supabase (PostgreSQL) via la même interface ORM.
-- =============================================================================
