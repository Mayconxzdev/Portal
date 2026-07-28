from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.core.config import settings

# Criar engine de conexão
# Em desenvolvimento, o echo=True é útil para auditar queries SQL no console, mas pode ser desativado
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

class Base(DeclarativeBase):
    """
    Classe base do SQLAlchemy 2.0 para todos os modelos de tabelas do Portal Vesper.
    """
    pass

def get_db():
    """
    Dependency para injeção de sessão do banco de dados em endpoints do FastAPI.
    Garante o fechamento correto da sessão após o término da requisição.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
