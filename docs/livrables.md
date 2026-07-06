# HorRAGor — Suivi des livrables (Partie 1)

> Checklist de vérification des 5 livrables attendus par `brief.md`, avec
> pointeur vers le fichier/dossier correspondant dans le dépôt.

---

## 1. Dépôt GitHub — code source organisé

Dépôt : https://github.com/os974/HorRAGor1

| Élément demandé | Emplacement |
|---|---|
| Scripts d'extraction | `src/horragor/ingestion/` — un sous-dossier par source : `tmdb/`, `rotten/`, `kaggle/`, `imdb/`, `spark/` |
| Modules de nettoyage | `src/horragor/transform/normalizer.py`, `saver.py` + fusion MDM dans `src/horragor/reconciliation/` (`adapters.py`, `matcher.py`, `gold.py`) |
| Modèles SQLAlchemy | `src/horragor/db/models.py` |

**Statut : ✅ complet**, poussé sur `main`.

---

## 2. Documentation de modélisation (Merise)

| Modèle | Fichier | Statut |
|---|---|---|
| MCD | `docs/merise/mcd.png` / `.svg` | ✅ image exportée |
| MLD | `docs/merise/mld.png` / `.svg` | ✅ image exportée |
| MPD | `docs/merise/mpd.png` (+ `src/horragor/db/schema.sql` comme source de vérité) | ✅ image exportée |

Détail de la démarche Merise : `docs/merise/merise.md`.

**Statut : ✅ complet**.

---

## 3. Base de données opérationnelle Supabase

- Instance PostgreSQL Supabase déployée et chargée (33 961 films, cf. `docs/plan-projet.md` §Supabase).
- Connexion pilotée par la variable d'environnement `DATABASE_URL` (voir `.env.example` pour le format).
- Credentials **non commités** (secret) — à transmettre séparément à l'évaluateur (ex. message privé, coffre-fort de partage), jamais via Git.

**Statut : ⚠️ instance prête, transmission des accès à faire hors dépôt.**

---

## 4. Fichier de dépendances

`pyproject.toml` (racine) + `uv.lock` pour un environnement reproductible bit-à-bit.

**Statut : ✅ complet**.

---

## 5. Échantillon Gold au format Parquet

`docs/samples/horragor_gold_sample.parquet` — échantillon représentatif du dataset
Gold final (structure et qualité de la donnée fusionnée), extrait de
`data/gold/horragor_gold.parquet` (fichier complet non versionné, cf. `.gitignore`).

**Statut : ✅ complet**.
