"""Configuration de l'engine et factory de sessions SQLAlchemy."""

import os

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from horragor.config.paths import HORRAGOR_DB
from horragor.db.models import Base

DB_PATH = HORRAGOR_DB

# Bascule SQLite local <-> Supabase SANS toucher au code : on lit DATABASE_URL
# dans l'environnement (.env). Absent -> SQLite local par défaut.
# Exemple Supabase : DATABASE_URL=postgresql+psycopg://user:pwd@host:5432/postgres
_IS_SQLITE = "DATABASE_URL" not in os.environ
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")

engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


# Active les FK SQLite à chaque connexion (sinon ignorées silencieusement).
# Sans effet sur PostgreSQL/Supabase qui applique les FK nativement.
@event.listens_for(Engine, "connect")
def _enable_sqlite_fk(dbapi_connection, _):
    if DATABASE_URL.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")
        cursor.close()


def init_db() -> None:
    """Crée toutes les tables à partir des modèles ORM."""
    if _IS_SQLITE:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    print(f"✅ Base initialisée via ORM : {DATABASE_URL}")


if __name__ == "__main__":
    init_db()
