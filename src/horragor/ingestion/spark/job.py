"""
Job PySpark : analyses textuelles lourdes des synopsis Kaggle (rôle MDM
« Enrichissement 4 : Spark Data »).

PIPELINE (distribué) :
  lecture des partitions CSV  ->  tokenisation  ->  retrait des stop-words
  ->  TF (CountVectorizer)  ->  TF-IDF (IDF)  ->  top-K mots-clés par film.

POURQUOI Spark (et pas Polars) ici ?
Le TF-IDF est une analyse à l'échelle du CORPUS (la pondération IDF dépend de
la fréquence d'un terme dans TOUS les films) : c'est exactement le type de
calcul que Spark parallélise bien sur un dataset partitionné. On illustre le
parallélisme exigé par le brief, là où Polars sert l'agilité mono-machine.

Sortie : un enrichissement par film (tmdb_id, overview_word_count, keywords)
réconcilié ensuite par tmdb_id (matching exact N1, pas de fuzzy nécessaire).
"""

from __future__ import annotations

import logging

import polars as pl

from horragor.config.paths import SPARK_CLEAN, SPARK_INPUT_DIR
from horragor.config.settings import (
    SPARK_KEYWORDS_TOP_K,
    SPARK_MIN_DF,
    SPARK_MIN_TOKEN_LEN,
    SPARK_VOCAB_SIZE,
)

logger = logging.getLogger(__name__)


def top_keywords(
    indices: list[int],
    values: list[float],
    vocabulary: list[str],
    k: int,
) -> list[str]:
    """
    Sélectionne les `k` termes de plus fort poids TF-IDF d'un film.

    Fonction PURE (pas de dépendance Spark) : testable hors-ligne. `indices` et
    `values` proviennent du vecteur creux TF-IDF ; on les trie par poids
    décroissant et on traduit les indices en mots via le vocabulaire.
    """
    pairs = sorted(zip(values, indices), reverse=True)[:k]
    return [vocabulary[i] for _, i in pairs]


def run_spark_text_analysis() -> pl.DataFrame:
    """Exécute le job Spark et retourne l'enrichissement (collecté en Polars)."""
    # Imports Spark locaux : on n'impose pas le coût d'import si le module est
    # seulement chargé (ex. tests du helper pur ci-dessus).
    from pyspark.ml.feature import (
        CountVectorizer,
        IDF,
        RegexTokenizer,
        StopWordsRemover,
    )
    from pyspark.sql import SparkSession
    from pyspark.sql import functions as F
    from pyspark.sql.types import ArrayType, StringType

    spark = (
        SparkSession.builder.master("local[*]")
        .appName("horragor-text-analysis")
        .config("spark.ui.enabled", "false")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("ERROR")

    try:
        # multiLine=True : les synopsis peuvent contenir des retours à la ligne.
        df = (
            spark.read.option("header", True)
            .option("multiLine", True)
            .option("escape", '"')
            .csv(f"{SPARK_INPUT_DIR}/part_*.csv")
            .filter(F.col("overview").isNotNull() & (F.length("overview") > 0))
        )

        tokenizer = RegexTokenizer(
            inputCol="overview",
            outputCol="tokens",
            pattern=r"\W+",
            toLowercase=True,
            minTokenLength=SPARK_MIN_TOKEN_LEN,
        )
        remover = StopWordsRemover(inputCol="tokens", outputCol="filtered")
        cv = CountVectorizer(
            inputCol="filtered",
            outputCol="tf",
            vocabSize=SPARK_VOCAB_SIZE,
            minDF=SPARK_MIN_DF,
        )

        tokenized = remover.transform(tokenizer.transform(df))
        cv_model = cv.fit(tokenized)
        tf = cv_model.transform(tokenized)
        idf_model = IDF(inputCol="tf", outputCol="tfidf").fit(tf)
        tfidf = idf_model.transform(tf)

        # Le vocabulaire est broadcasté pour traduire indices -> mots côté workers.
        vocab = spark.sparkContext.broadcast(cv_model.vocabulary)
        k = SPARK_KEYWORDS_TOP_K

        @F.udf(returnType=ArrayType(StringType()))
        def _keywords(vec):
            if vec is None:
                return []
            return top_keywords(list(vec.indices), list(vec.values), vocab.value, k)

        result = tfidf.select(
            F.col("id").cast("long").alias("tmdb_id"),
            F.size("filtered").alias("overview_word_count"),
            _keywords(F.col("tfidf")).alias("keywords"),
        ).filter(F.col("tmdb_id").isNotNull())

        rows = [r.asDict() for r in result.collect()]
        logger.info("Spark : %d films enrichis", len(rows))
    finally:
        spark.stop()

    return pl.DataFrame(
        rows,
        schema={
            "tmdb_id": pl.Int64,
            "overview_word_count": pl.Int64,
            "keywords": pl.List(pl.Utf8),
        },
    )


def main() -> None:
    df = run_spark_text_analysis()
    SPARK_CLEAN.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(SPARK_CLEAN)
    logger.info("Enrichissement Spark sauvegardé : %s (%d films)", SPARK_CLEAN, df.height)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
    )
    main()
