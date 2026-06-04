import logging
from pathlib import Path

import polars as pl

from horragor.ingestion.kaggle.kaggle_extractor import extract
from horragor.ingestion.kaggle.kaggle_mapper import map

logger = logging.getLogger(__name__)

OUTPUT_CSV = Path("data/clean/kaggle_clean.csv")


def transform() -> pl.DataFrame:
    df = extract()
    df = map(df)

    total_avant = len(df)

    # Suppression doublons
    df = df.unique(subset=["title", "release_date"], keep="first")
    logger.info(f"Doublons supprimés : {total_avant - len(df)}")

    # Nettoyage release_date
    df = df.with_columns(
        pl.col("release_date").str.strptime(pl.Date, "%Y-%m-%d", strict=False)
    )

    # Remplace NA string par null
    for col in ["collection_name", "tagline", "overview"]:
        df = df.with_columns(
            pl.when(pl.col(col) == "NA").then(None).otherwise(pl.col(col)).alias(col)
        )

    # Budget/revenue 0 → null
    for col in ["budget", "revenue"]:
        df = df.with_columns(
            pl.when(pl.col(col) == 0).then(None).otherwise(pl.col(col)).alias(col)
        )

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.write_csv(OUTPUT_CSV)

    logger.info(f"Films après nettoyage : {len(df)}")
    logger.info(f"Sauvegardé : {OUTPUT_CSV}")

    return df


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
    )
    transform()
