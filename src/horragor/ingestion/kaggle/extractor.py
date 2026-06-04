import logging

import polars as pl

from horragor.config.paths import KAGGLE_RAW

logger = logging.getLogger(__name__)

INPUT_CSV = KAGGLE_RAW


def extract() -> pl.DataFrame:
    logger.info(f"Lecture : {INPUT_CSV}")

    df = pl.read_csv(INPUT_CSV, infer_schema_length=10000)

    logger.info(f"Chargé : {len(df)} films, {len(df.columns)} colonnes")
    logger.info(f"Colonnes : {df.columns}")

    return df


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
    )
    df = extract()
    print(df.head(5))
