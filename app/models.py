from sqlalchemy import Column, Integer, String, Date, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base

class Estagiario(Base):
    __tablename__ = "estagiarios"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String)
    ocupacao = Column(String)
    matricula = Column(String)
    processo_pae = Column(String)
    data_inicio_contrato = Column(Date)
    data_fim_contrato = Column(Date)

    ciclos = relationship("Ciclo", back_populates="estagiario")
    notas = relationship("NotaTecnica", back_populates="estagiario")


class Ciclo(Base):
    __tablename__ = "ciclos"

    id = Column(Integer, primary_key=True, index=True)
    estagiario_id = Column(Integer, ForeignKey("estagiarios.id"))
    data_inicio = Column(Date)
    data_fim = Column(Date)
    dias_gozados = Column(Integer)

    estagiario = relationship("Estagiario", back_populates="ciclos")


class NotaTecnica(Base):
    __tablename__ = "notas_tecnicas"

    id = Column(Integer, primary_key=True, index=True)
    estagiario_id = Column(Integer, ForeignKey("estagiarios.id"))
    numero_nota = Column(String)
    total_dias_nao_gozados = Column(Integer)
    texto_conclusao = Column(String)
    data_emissao = Column(Date)

    estagiario = relationship("Estagiario", back_populates="notas")
