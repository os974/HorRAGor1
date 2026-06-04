"""
Réconciliation MDM : regroupe les Film partiels décrivant le même film,
puis les fusionne en records canoniques uniques.

Matching en 3 niveaux (brief) :
  N1 — correspondance exacte sur tmdb_id
  N2 — correspondance exacte sur imdb_id
  N3 — fuzzy [titre + année] (distance de Levenshtein) en l'absence d'ID

Mise en œuvre : un union-find regroupe d'abord les partiels par ID (N1, N2).
Les sources sans ID partagé (typiquement IMDB) restent isolées et sont
rattachées en N3 aux clusters « ancrés » (porteurs d'un tmdb_id) via une
similarité de titre, avec blocking par année pour rester tractable.
"""

from __future__ import annotations

from collections import defaultdict

from fuzzywuzzy import fuzz

from horragor.reconciliation.schema import Film, merge_films, source_rank

FUZZY_THRESHOLD = 90  # ratio de similarité minimal (0-100) pour un match titre
YEAR_TOLERANCE = 1  # écart d'année toléré (IMDB startYear vs TMDB release_date)


class _UnionFind:
    def __init__(self, n: int) -> None:
        self.parent = list(range(n))
        self.rank = [0] * n

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]  # compression de chemin
            x = self.parent[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        if self.rank[ra] < self.rank[rb]:
            ra, rb = rb, ra
        self.parent[rb] = ra
        if self.rank[ra] == self.rank[rb]:
            self.rank[ra] += 1


def _normalize_title(title: str | None) -> str:
    return (title or "").strip().lower()


def _cluster_rep(films: list[Film]) -> tuple[str | None, int | None, bool]:
    """Représentant d'un cluster : (titre prioritaire, année, porte un tmdb_id)."""
    ordered = sorted(films, key=lambda f: source_rank(f.sources[0] if f.sources else "?"))
    title = next((f.title for f in ordered if f.title), None)
    year = next((f.year for f in ordered if f.year is not None), None)
    has_tmdb = any(f.tmdb_id is not None for f in films)
    return title, year, has_tmdb


def cluster_films(
    films: list[Film],
    fuzzy_threshold: int = FUZZY_THRESHOLD,
    year_tolerance: int = YEAR_TOLERANCE,
) -> list[list[Film]]:
    """Regroupe les partiels en clusters (un cluster = un film réel)."""
    n = len(films)
    uf = _UnionFind(n)

    # --- Phase 1 : matching exact par identifiants (N1, N2) ---
    by_tmdb: dict[int, list[int]] = defaultdict(list)
    by_imdb: dict[str, list[int]] = defaultdict(list)
    for idx, f in enumerate(films):
        if f.tmdb_id is not None:
            by_tmdb[f.tmdb_id].append(idx)
        if f.imdb_id:
            by_imdb[f.imdb_id].append(idx)
    for group in (*by_tmdb.values(), *by_imdb.values()):
        first = group[0]
        for other in group[1:]:
            uf.union(first, other)

    # --- Construction des clusters intermédiaires ---
    roots: dict[int, list[int]] = defaultdict(list)
    for idx in range(n):
        roots[uf.find(idx)].append(idx)

    # --- Phase 2 : fuzzy [titre + année] (N3) ---
    # On indexe les clusters ANCRÉS (porteurs d'un tmdb_id) par année, puis on
    # rattache chaque cluster FLOTTANT (sans tmdb_id, ex. IMDB) au meilleur ancré.
    anchored_by_year: dict[int, list[tuple[str, int]]] = defaultdict(list)
    floating: list[tuple[str, int, int]] = []  # (titre_norm, année, idx_membre)
    for root, members in roots.items():
        title, year, has_tmdb = _cluster_rep([films[i] for i in members])
        if title is None or year is None:
            continue
        norm = _normalize_title(title)
        if has_tmdb:
            anchored_by_year[year].append((norm, root))
        else:
            floating.append((norm, year, root))

    for norm, year, root in floating:
        best_ratio, best_root = 0, None
        for y in range(year - year_tolerance, year + year_tolerance + 1):
            for cand_norm, cand_root in anchored_by_year.get(y, []):
                ratio = fuzz.ratio(norm, cand_norm)
                if ratio > best_ratio:
                    best_ratio, best_root = ratio, cand_root
        if best_root is not None and best_ratio >= fuzzy_threshold:
            uf.union(root, best_root)

    # --- Clusters finaux ---
    final: dict[int, list[Film]] = defaultdict(list)
    for idx in range(n):
        final[uf.find(idx)].append(films[idx])
    return list(final.values())


def reconcile(films: list[Film], **kwargs) -> list[Film]:
    """Clustering + fusion -> liste de Film canoniques uniques."""
    return [merge_films(cluster) for cluster in cluster_films(films, **kwargs)]
