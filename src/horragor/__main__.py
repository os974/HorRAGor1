"""
Point d'entrée du pipeline HorRAGor : `python -m horragor`.

Exemples :
  python -m horragor                      # 5 sources → Gold → base
  python -m horragor --sources tmdb,kaggle
  python -m horragor --skip-ingestion     # (re)construit Gold + base depuis les clean existants
  python -m horragor --no-load            # s'arrête au Gold (Parquet)
  python -m horragor --max-pages 3        # profondeur du scan TMDB
"""

from __future__ import annotations

import argparse
import logging
import sys

from horragor.config.settings import TMDB_MAX_PAGES
from horragor.orchestrator import INGESTION, run_all

ALL_SOURCES = list(INGESTION)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="horragor",
        description="Pipeline d'ingestion HorRAGor : 5 sources → Gold → base.",
    )
    parser.add_argument(
        "--sources",
        default=",".join(ALL_SOURCES),
        help=f"Sources à ingérer, séparées par des virgules (défaut : {','.join(ALL_SOURCES)}).",
    )
    parser.add_argument(
        "--skip-ingestion",
        action="store_true",
        help="N'ingère rien ; (re)construit le Gold et la base depuis les clean existants.",
    )
    parser.add_argument(
        "--no-load",
        action="store_true",
        help="S'arrête après l'export du Gold (Parquet), sans charger la base.",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=TMDB_MAX_PAGES,
        help=f"Nombre de pages TMDB à parcourir (défaut : {TMDB_MAX_PAGES}).",
    )
    return parser.parse_args(argv)


def _resolve_sources(raw: str) -> list[str]:
    requested = [s.strip() for s in raw.split(",") if s.strip()]
    unknown = [s for s in requested if s not in INGESTION]
    if unknown:
        raise SystemExit(
            f"Source(s) inconnue(s) : {', '.join(unknown)}. "
            f"Choix possibles : {', '.join(ALL_SOURCES)}."
        )
    return requested


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
    )
    sources = _resolve_sources(args.sources)

    print("🚀 HorRAGor — pipeline d'ingestion")
    summary = run_all(
        sources,
        skip_ingestion=args.skip_ingestion,
        do_load=not args.no_load,
        max_pages=args.max_pages,
    )

    # Résumé final lisible (utile pour la démo « live »).
    print("\n================ RÉSUMÉ ================")
    if summary["ingestion"]:
        for src, ok in summary["ingestion"].items():
            print(f"  {'✓' if ok else '✗'} ingestion {src}")
    print(f"  Gold : {summary['gold']}")
    if summary["load"] is not None:
        print(f"  Base : {summary['load']}")
    print("=======================================")

    # Code de sortie non nul si une source a échoué (utile en CI).
    if any(not ok for ok in summary["ingestion"].values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
