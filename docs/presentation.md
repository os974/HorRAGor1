---
marp: true
theme: gaia
class: lead
paginate: true
---

<!--
Deck de présentation HorRAGor — à présenter à l'oral (~8-10 min).
Format Marp : `marp presentation.md --pdf` (ou extension Marp dans VS Code)
pour générer des slides PDF/PPTX. Les notes "🗣️" sont des repères de discours.
-->

# 🩸 HorRAGor BOT

### Forger une base de connaissances de l'horreur
#### à partir de 5 sources hétérogènes

*Pipeline d'ingestion & réconciliation de données — Bloc E1*

🗣️ *« Comment construire le cerveau d'un chatbot qui ne doit JAMAIS halluciner ? »*

---

## L'histoire

On veut un **chatbot spécialisé horreur** (cinéma).
Un chatbot qui invente des films, c'est un **monstre** : il hallucine.

Pour qu'il dise vrai, il lui faut une **mémoire fiable** :
une base de connaissances **unique, propre, sans doublon**.

> Le problème : cette mémoire n'existe nulle part en un seul endroit.
> Elle est **éparpillée** dans 5 sources qui s'ignorent.

🗣️ *Notre mission : rassembler les morceaux et recoudre une seule créature cohérente.*

---

## Les 5 fragments (sources)

| # | Source | Techno | Ce qu'elle apporte |
|---|--------|--------|--------------------|
| 1 | **TMDB** (API) | `requests` | 🥇 Identité officielle : titres, IDs, synopsis |
| 2 | **Rotten Tomatoes** | **Selenium** | Scores critiques + public + consensus |
| 3 | **Kaggle** (CSV) | **Polars** | Budget, recettes, métadonnées |
| 4 | **IMDB** (SQLite) | SQL | Notes & nombre de votes |
| 5 | **Spark Data** | **PySpark** | Mots-clés des synopsis (TF-IDF) |

🗣️ *Cinq formats différents, cinq vocabulaires différents… et le même film sous plusieurs noms.*

---

## Le flux global

```
  5 SOURCES        NETTOYAGE        RÉCONCILIATION       SORTIES
 ┌─────────┐      ┌──────────┐      ┌────────────┐    ┌──────────┐
 │  TMDB   │─┐    │ normalise│      │  matching  │    │  GOLD    │
 │  RT     │ ├──▶ │  dates   │ ──▶  │  exact +   │──▶ │ (Parquet)│
 │  Kaggle │ │    │  textes  │      │  fuzzy MDM │    └────┬─────┘
 │  IMDB   │ │    │  filtre  │      │  + fusion  │         │
 │  Spark  │─┘    │  horreur │      └────────────┘         ▼
 └─────────┘      └──────────┘                        ┌──────────┐
                                                      │ SUPABASE │
                                                      │ (Postgres)│
                                                      └──────────┘
   extract     →     clean     →     reconcile     →    load
```

🗣️ *Extraire → nettoyer → réconcilier → charger. Une seule « source de vérité » à la fin.*

---

## Étapes 1-2 — Acquérir & nettoyer

Chaque source a **sa propre techno**, adaptée à sa nature :

- **API TMDB** → simples requêtes HTTP (`requests`)
- **Rotten Tomatoes** → site dynamique (scores injectés en JS) → **Selenium** (vrai navigateur)
- **Kaggle (32k films)** → **Polars** (ultra-rapide sur gros CSV)
- **IMDB** → requête **SQL** (jointure + seuil `numVotes ≥ 1000`)
- **Spark** → **PySpark** pour le volume (calcul distribué)

Puis on **homogénéise** : dates en ISO 8601, textes nettoyés (HTML/espaces),
filtrage strict du **genre horreur**.

🗣️ *« Le bon outil pour la bonne donnée. »*

---

## Étape 3 — La réconciliation (le cœur 🫀)

Le même film apparaît dans plusieurs sources… **sous des formes différentes** :
`The Texas Chain Saw Massacre` vs `The Texas Chainsaw Massacre`.

**Stratégie MDM** (Master Data Management), par priorité :
**TMDB > Rotten Tomatoes > Kaggle > IMDB > Spark**

Matching en **3 niveaux** :
1. ID exact `tmdb_id`
2. ID exact `imdb_id`
3. **Fuzzy** : similarité `titre + année` (distance de Levenshtein)

🗣️ *Reconnaître le même monstre, peu importe le nom qu'il porte.*

---

## Le « boss fight » 👹 — le fuzzy matching

**Le défi :** IMDB et Rotten Tomatoes n'ont **aucun identifiant commun**.
Seul le titre permet de les relier… mais comparer **38 000** entrées
deux à deux, c'est **explosif** (O(n²)).

**Les solutions :**
- **Union-find** pour regrouper en clusters
- **Blocking par année** : on ne compare que les films de la même année (±1)
- Seuil de similarité **≥ 90 %**

> 🐛 Piège résolu : RT nomme `"A Quiet Place (2018)"` → on retire le `(année)`,
> sinon le match échoue.

🗣️ *C'est LA difficulté du projet — et celle que le brief demande d'expliquer.*

---

## Le résultat — le dataset « Gold »

La créature est recousue : **un film = une entité unique, enrichie**.

| Indicateur | Valeur |
|---|---|
| 🎬 Films unifiés | **33 961** |
| 🧬 Multi-sources | **31 286** |
| ♻️ Doublons | **0** |
| ✅ Complétude (titre/année) | **100 %** |

Exporté en **Parquet** (format colonne, prêt pour l'analyse / le RAG).

🗣️ *Zéro doublon, et l'objectif de complétude > 95 % du brief est dépassé.*

---

## Modélisation & persistance

**Méthode Merise** : MCD → MLD → MPD (diagrammes fournis)
Schéma **relationnel en 3NF** : `movies`, `genres`, `ratings`,
`movie_keywords`, traçabilité des sources.

**SQLAlchemy ORM** comme interface → déployé sur **Supabase** (PostgreSQL).

⚡ **Astuce perf :** chargement via `COPY` PostgreSQL
→ **27 s** pour ~475 000 lignes (vs >40 min en insertion classique).

🗣️ *Le même code tourne en local (SQLite) ou en prod (Supabase) — une variable d'environnement suffit.*

---

## Une seule incantation 🪄

```bash
python -m horragor          # 5 sources → Gold → Supabase, en 1 commande
```

- **Modulaire** : un sous-paquet par source
- **Robuste** : chaque source est **isolée** — si le scraping tombe,
  le pipeline continue avec les autres
- **Testé** : 65 tests automatisés, linting propre

🗣️ *Tout s'enchaîne automatiquement, et une panne réseau ne fait pas tout s'effondrer.*

---

## Bilan & suite

✅ **5 sources** fusionnées · **MDM** (exact + fuzzy) · **Gold** sans doublon
✅ Base **PostgreSQL/Supabase** opérationnelle · Modélisation **Merise**
✅ Pipeline **automatisé** de bout en bout

**La suite (Partie 2) :** brancher un **RAG** sur cette base
→ le chatbot répond en s'appuyant sur des faits vérifiés. Plus d'hallucination. 🧠

---

# Merci 🙏

### Questions ?

*HorRAGor — de 5 sources chaotiques à une seule source de vérité.*
