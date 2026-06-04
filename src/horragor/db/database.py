"""Configuration de l'engine et factory de sessions SQLAlchemy."""

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from horragor.config.paths import HORRAGOR_DB
from horragor.db.models import Base

DB_PATH = HORRAGOR_DB

# URL : bascule facile vers Supabase en changeant cette variable
DATABASE_URL = f"sqlite:///{DB_PATH}"
# Exemple Supabase : "postgresql+psycopg://user:pwd@host:5432/postgres"

engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


# Active les FK SQLite à chaque connexion (sinon ignorées silencieusement)
@event.listens_for(Engine, "connect")
def _enable_sqlite_fk(dbapi_connection, _):
    if DATABASE_URL.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")
        cursor.close()


def init_db() -> None:
    """Crée toutes les tables à partir des modèles ORM."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    print(f"✅ Base initialisée via ORM : {DB_PATH}")


if __name__ == "__main__":
    init_db()
