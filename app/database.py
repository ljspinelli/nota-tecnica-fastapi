import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# ============================================================
# CONFIGURAÇÃO DO BANCO DE DADOS
# ============================================================

# Render: usa a variável de ambiente DATABASE_URL
# Local: usa SQLite automaticamente
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./database.db")

# ============================================================
# ENGINE
# ============================================================

if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    # SQLite (uso local)
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False,
    )
else:
    # PostgreSQL (Render)
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
