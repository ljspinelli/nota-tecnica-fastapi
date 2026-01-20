from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# ============================================================
# CONFIGURAÇÃO DO BANCO DE DADOS
# ============================================================

# Para SQLite local:
# SQLALCHEMY_DATABASE_URL = "sqlite:///./database.db"

# Para Render / PostgreSQL:
# Exemplo:
# SQLALCHEMY_DATABASE_URL = "postgresql://usuario:senha@host:porta/banco"

SQLALCHEMY_DATABASE_URL = "sqlite:///./database.db"

# ============================================================
# ENGINE
# ============================================================

# Para SQLite, precisamos do connect_args
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False,  # coloque True se quiser ver logs SQL
    )
else:
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        pool_pre_ping=True,
        echo=False,
    )

# ============================================================
# SESSÃO DO BANCO
# ============================================================

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# ============================================================
# BASE DO SQLALCHEMY
# ============================================================

Base = declarative_base()
