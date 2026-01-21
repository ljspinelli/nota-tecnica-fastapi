from sqlalchemy import Column, Integer, String, Date, ForeignKey, Text, DateTime
from sqlalchemy.orm import relationship
from .database import Base


# ============================================================
# ESTAGIÁRIO
# ============================================================

class Estagiario(Base):
    __tablename__ = "estagiarios"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    ocupacao = Column(String, nullable=False)
    matricula = Column(String, nullable=False)
    processo_pae = Column(String, nullable=False)

    data_inicio_contrato = Column(Date, nullable=False)
    data_fim_contrato = Column(Date, nullable=False)

    ciclos = relationship("Ciclo", back_populates="estagiario")
    notas = relationship("NotaTecnica", back_populates="estagiario")


# ============================================================
# CICLO DE RECESSO
# ============================================================

class Ciclo(Base):
    __tablename__ = "ciclos"

    id = Column(Integer, primary_key=True, index=True)
    estagiario_id = Column(Integer, ForeignKey("estagiarios.id"))

    data_inicio = Column(Date, nullable=False)
    data_fim = Column(Date, nullable=False)

    dias_gozados = Column(Integer, default=0)
    dias_direito = Column(Integer, default=0)

    estagiario = relationship("Estagiario", back_populates="ciclos")


# ============================================================
# NOTA TÉCNICA
# ============================================================

class NotaTecnica(Base):
    __tablename__ = "notas_tecnicas"

    id = Column(Integer, primary_key=True, index=True)

    # Número sequencial gerado pelo sistema (não pelo banco)
    numero_sequencial = Column(Integer, unique=True, index=True)

    # Número oficial da nota (ex: "3/2026 - DDVP/DRH/PCPA")
    numero_nota = Column(String, index=True)

    estagiario_id = Column(Integer, ForeignKey("estagiarios.id"))
    total_dias_nao_gozados = Column(Integer, nullable=False)
    texto_conclusao = Column(Text, nullable=False)
    data_emissao = Column(Date, nullable=False)

    estagiario = relationship("Estagiario", back_populates="notas")


# ============================================================
# USUÁRIO DO SISTEMA
# ============================================================

class User(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    senha_hash = Column(String, nullable=False)

    # Data/hora do último login
    ultimo_acesso = Column(DateTime, default=None)
