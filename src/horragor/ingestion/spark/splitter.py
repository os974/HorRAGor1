"""
Préparation des « fichiers Kaggle splittés » pour le traitement Big Data.

POURQUOI splitter ?
Le brief impose un traitement PySpark d'un « volume massif de données des
fichiers Kaggle splittés ». Spark est conçu pour lire en parallèle un
RÉPERTOIRE de partitions (un thread/cœur par fichier). On découpe donc le
dataset Kaggle en N fichiers CSV : c'est la forme d'entrée réaliste d'un
pipeline distribué, et ça permet à Spark d'exploiter son parallélisme.

On ne garde que les colonnes utiles à l'analyse textuelle (id = tmdb_id,
title, overview) pour alléger les partitions.
"""

from __future__ import annotations

import logging

import polars as pl

from horragor.config.paths import KAGGLE_CLEAN, SPARK_INPUT_DIR
from horragor.config.settings import SPARK_NUM_PARTITIONS

logger = logging.getLogger(__name__)

# Colonnes nécessaires en aval (texte + clé de réconciliation).
_COLUMNS = ["id", "title", "overview"]


def split_kaggle(num_partitions: int = SPARK_NUM_PARTITIONS) -> list:
    """Découpe le Kaggle clean en `num_partitions` fichiers CSV sous SPARK_INPUT_DIR."""
    df = pl.read_csv(KAGGLE_CLEAN, infer_schema_length=10000).select(_COLUMNS)
    n = df.height
    logger.info("Kaggle clean : %d lignes -> %d partitions", n, num_partitions)

    SPARK_INPUT_DIR.mkdir(parents=True, exist_ok=True)
    # Purge des anciennes partitions pour éviter les mélanges entre exécutions.
    for old in SPARK_INPUT_DIR.glob("part_*.csv"):
        old.unlink()

    # Découpage en tranches contiguës de tailles ~égales.
    chunk = -(-n // num_partitions)  # division entière arrondie au supérieur
    paths = []
    for i in range(num_partitions):
        part = df.slice(i * chunk, chunk)
        if part.height == 0:
            break
        path = SPARK_INPUT_DIR / f"part_{i:02d}.csv"
        part.write_csv(path)
        paths.append(path)

    logger.info("%d partitions écrites dans %s", len(paths), SPARK_INPUT_DIR)
    return paths


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
    )
    split_kaggle()
