# Journal de bord (Logbook) — HorRAGor

> Auto-évaluation : difficultés rencontrées et solutions apportées au fil du
> projet (cf. brief — bloc E1). Document rédigé, distinct des logs applicatifs.
> Les passages **[à compléter]** appellent une réflexion personnelle.

---

## 1. Contexte

Construction d'un pipeline d'ingestion fusionnant **5 sources hétérogènes**
(TMDB API, Rotten Tomatoes scraping, Kaggle/Polars, IMDB/SQLite, PySpark) vers
un dataset « Gold » dédoublonné et complet, persisté en base relationnelle
(SQLAlchemy → Supabase). Travail individuel.

---

## 2. Chronologie (grandes étapes)

1. **Remise en ordre de la structure** (src-layout, conventions, chemins centralisés).
2. **Schéma canonique « Film »** + règles de fusion (priorité / fallback).
3. **Adapters par source** (harmonisation des sorties `clean` vers le schéma canonique).
4. **Matcher MDM** : matching exact (tmdb_id, imdb_id) + fuzzy (titre+année).
5. **Dataset Gold** : filtrage thématique, contrôles qualité, export Parquet.
6. **Rotten Tomatoes** (Selenium) puis **PySpark** (analyses textuelles TF-IDF).
7. **Schéma relationnel étendu** + chargement du Gold en base (bulk).
8. **Modélisation Merise** (MCD/MLD/MPD) + **orchestrateur unique** `python -m horragor`.

---

## 3. Difficultés rencontrées & solutions

### 3.1 Matching fuzzy (le point sensible du brief)

**Problème.** IMDB et Rotten Tomatoes n'exposent **aucun identifiant commun**
(ni `tmdb_id` ni `imdb_id`) avec TMDB/Kaggle : impossible de les rattacher par
correspondance exacte. Seule la similarité **titre + année** permet de les relier.

**Obstacle de volume.** Un fuzzy « tous contre tous » est en O(n²) : avec ~38 000
partiels (dont 32 000 Kaggle), c'est intractable.

**Solutions retenues :**
- **Union-find** pour le clustering, en deux phases : Phase 1 = regroupement par
  identifiants exacts (rapide, par hachage) ; Phase 2 = fuzzy **uniquement** pour
  les clusters « flottants » (sans `tmdb_id`, typiquement IMDB) rattachés aux
  clusters « ancrés ».
- **Blocking par année** (±1) : on ne compare que des titres de la même année,
  ce qui réduit drastiquement le nombre de paires.
- Seuil de similarité **Levenshtein ≥ 90** (fuzzywuzzy) — compromis précision/rappel.

**Pièges secondaires résolus :**
- Rotten Tomatoes suffixe les titres ambigus : `"A Quiet Place (2018)"`. Le
  suffixe faisait chuter le ratio sous le seuil → **non-match**. Solution : retrait
  du suffixe `(YYYY)` dans le parser. Résultat : 12/12 films RT rattachés.
- L'année IMDB (`startYear`) et l'année TMDB (`release_date`) diffèrent parfois
  d'un an (festival vs sortie) → **tolérance ±1 an**.

**Résultat.** 38 500 partiels → 33 961 films unifiés (~16 s), 0 doublon
(`tmdb_id`/`imdb_id`), 31 285 films multi-sources.

**[à compléter]** *Ce que cette étape m'a appris / ce que je ferais autrement.*

### 3.2 Scraping Rotten Tomatoes (Selenium)

**Problème.** Les scores (Tomatometer, Popcornmeter) et le consensus sont
injectés **par JavaScript** : une requête HTTP simple ne les voit pas → Selenium
obligatoire (« extraction dynamique »).

**Phase de recherche (analyse DOM).** Sondes successives pour identifier les vrais
sélecteurs : `media-scorecard`, `rt-text[slot="critics-score"]` / `["audience-score"]`,
`#critics-consensus`, et le **JSON-LD** (`aggregateRating`, `dateCreated`, `genre`).

**Obstacles :**
- Certaines pages renvoyaient une redirection / page générique (mur anti-bot) →
  **user-agent réaliste** + **attente explicite** du `media-scorecard` (signal que
  le JS a fini d'injecter les scores).

**Solution de conception.** Parser **en deux couches** (JSON-LD stable +
web components) pour résister aux refontes du site, et **séparé du fetch** Selenium
pour rester testable hors-ligne (fixtures).

**[à compléter]** *Difficultés de stabilité du scraping observées de mon côté.*

### 3.3 PySpark — analyses textuelles

**Choix.** Pourquoi Spark plutôt que Polars ? Le **TF-IDF** est un calcul à
l'échelle du **corpus** (la pondération IDF dépend de tous les films) : c'est le
cas d'usage du parallélisme Spark. On a découpé le Kaggle en partitions pour
simuler une entrée big-data lue en parallèle.

**Difficulté technique.** Récupérer, par film, les top-K mots-clés depuis le
vecteur TF-IDF : il a fallu **broadcaster le vocabulaire** du `CountVectorizer`
pour traduire les indices en mots dans une UDF.

**[à compléter]** *Réglages / temps de calcul observés.*

### 3.4 Hétérogénéité des sources

- **Genres** exprimés différemment : ids TMDB, noms IMDB (`"Crime,Drama"`),
  `genre_names` Kaggle, libellés RT (`"Mystery & Thriller"`). Harmonisation en
  **noms** (table `genres` keyée par `name`, map id→nom pour TMDB).
- **Découverte utile** : le champ `id` du dataset Kaggle est en réalité un
  `tmdb_id` (dataset extrait via l'API TMDB) → exploité pour le matching exact N1.
- **Écarts de périmètre du sujet** (assumés) : le PDF parle de « littérature
  d'épouvante » pour Kaggle alors que le dataset est des **films** ; il assigne à
  IMDB un rôle « casting/trivia » alors que les dumps publics ne donnent que
  notes/votes.

### 3.5 Autres points techniques

- **Structure de départ** : imports incohérents, projet non installable (pas de
  `[build-system]`), chemins relatifs au CWD → refonte en **src-layout**
  (`src/horragor`), package installable, chemins centralisés (`config/paths.py`).
- **Schéma DB évolutif** : le schéma initial (TMDB-centré) ne pouvait accueillir
  le Gold fusionné → extension **additive** (BIGINT pour budget/revenue,
  `audience_score` RT, table `movie_keywords` en 3NF, genres par nom).
- **Performance du chargement** : 34 k films + 294 k mots-clés en upsert
  ligne-à-ligne = trop lent → **insertion en masse** avec IDs attribués côté
  Python (~4 s).
- **Diagrammes Merise** : aucun moteur de rendu local (`dot`/`mmdc` absents) →
  rendu via l'API **Kroki**. Kroki refusait les commentaires `%%`/`//` et limitait
  le volume d'attributs → sources épurées, attributs clés seulement dans le visuel.

---

## 4. Décisions de conception marquantes

- **Approche « fusion-first »** : schéma canonique → adapters → matcher → Gold,
  conformément au flux du brief (la base est une *projection* du Gold).
- **Priorité MDM** : TMDB > Rotten Tomatoes > Kaggle > IMDB > Spark, avec
  **fallback** automatique sur les champs manquants.
- **Tolérance aux pannes** : chaque source est isolée dans l'orchestrateur ; un
  échec est journalisé sans interrompre le pipeline (la fusion se fait avec les
  sources qui ont réussi).
- **SOURCE dénormalisée** en attribut codé (CHECK) plutôt qu'une table-dimension.

---

## 5. Bilan & axes d'amélioration

**Atteint.** 5/5 sources, fusion MDM, Gold (0 doublon, 100 % de complétude sur les
champs critiques), base 3NF chargée et Supabase-ready, MCD/MLD/MPD, orchestrateur
en une commande, 65 tests.

**À améliorer.** Retries réseau (TMDB/RT), tests d'intégration du run complet,
déploiement effectif sur Supabase.

**[à compléter]** *Bilan personnel : ce qui a été le plus formateur, le plus
frustrant, les compétences acquises.*
