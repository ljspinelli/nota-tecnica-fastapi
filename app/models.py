from sqlalchemy import Column, Integer, String, Date, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base

# ============================================================
# MODELO: ESTAGIÁRIO
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

    ciclos = relationship("Ciclo", back_populates="estagiario", cascade="all, delete-orphan")
    notas = relationship("NotaTecnica", back_populates="estagiario", cascade="all, delete-orphan")

# ============================================================
# MODELO: CICLO DE RECESSO
# ============================================================

class Ciclo(Base):
    __tablename__ = "ciclos"

    id = Column(Integer, primary_key=True, index=True)
    estagiario_id = Column(Integer, ForeignKey("estagiarios.id"), nullable=False)

    data_inicio = Column(Date, nullable=False)
    data_fim = Column(Date, nullable=False)
    dias_gozados = Column(Integer, nullable=False)
    dias_direito = Column(Integer, nullable=False)

    estagiario = relationship("Estagiario", back_populates="ciclos")

# ============================================================
# MODELO: NOTA TÉCNICA
# ============================================================

class NotaTecnica(Base):
    __tablename__ = "notas_tecnicas"

    id = Column(Integer, primary_key=True, index=True)
    estagiario_id = Column(Integer, ForeignKey("estagiarios.id"), nullable=False)

    numero_sequencial = Column(Integer, autoincrement=True)
    total_dias_nao_gozados = Column(Integer, nullable=False)
    texto_conclusao = Column(String, nullable=False)
    data_emissao = Column(Date, nullable=False)

    estagiario = relationship("Estagiario", back_populates="notas")
