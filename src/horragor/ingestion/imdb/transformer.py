import logging
from pathlib import Path

import pandas as pd

from horragor.config.paths import IMDB_HORROR_CLEAN, IMDB_HORROR_RAW

logger = logging.getLogger(__name__)

INPUT_CSV = IMDB_HORROR_RAW
OUTPUT_CSV = IMDB_HORROR_CLEAN


def transform_horror_movies() -> Path:
    if OUTPUT_CSV.exists():
        logger.info(f"Déjà transformé : {OUTPUT_CSV}, skip.")
        return OUTPUT_CSV

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(INPUT_CSV)
    logger.info(f"Chargé : {len(df)} films bruts")

    # Nettoyage
    df["startYear"] = pd.to_numeric(df["startYear"], errors="coerce")
    df["runtimeMinutes"] = pd.to_numeric(df["runtimeMinutes"], errors="coerce")
    df = df.dropna(subset=["startYear", "averageRating", "numVotes"])
    df["startYear"] = df["startYear"].astype(int)

    # Colonnes enrichies
    df["decade"] = (df["startYear"] // 10 * 10).astype(str) + "s"
    df["is_pure_horror"] = df["genres"].str.strip() == "Horror"
    df["sub_genres"] = df["genres"].apply(
        lambda g: (
            [x for x in g.split(",") if x != "Horror"] if isinstance(g, str) else []
        )
    )
    df["num_genres"] = df["sub_genres"].apply(len) + 1

    # Score composite (pour ranking futur)
    df["score"] = (df["averageRating"] * df["numVotes"].apply(lambda v: v**0.5)).round(
        2
    )

    # Ordre propre
    df = df.sort_values("numVotes", ascending=False).reset_index(drop=True)

    df.to_csv(OUTPUT_CSV, index=False)
    logger.info(f"Transformé : {len(df)} films → {OUTPUT_CSV}")
    logger.info(f"Période : {df['startYear'].min()} - {df['startYear'].max()}")
    logger.info(f"Rating moyen : {df['averageRating'].mean():.2f}")
    logger.info(f"Films pure Horror : {df['is_pure_horror'].sum()}")

    return OUTPUT_CSV


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
    )
    transform_horror_movies()
