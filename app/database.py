from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# ============================================================
# CONFIGURAÇÃO DO BANCO DE DADOS
# ============================================================

# Render fornece a URL do banco via variável de ambiente DATABASE_URL
# Se estiver rodando localmente, você pode definir manualmente:
# export DATABASE_URL="postgresql://usuario:senha@localhost:5432/nota_tecnica"

import os
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    # Fallback para desenvolvimento local
    DATABASE_URL = "sqlite:///./local.db"

# Para Postgres no Render, precisamos ajustar a URL se vier com "postgres://"
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# ============================================================
# ENGINE E SESSÃO
# ============================================================

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para os modelos
Base = declarative_base()
