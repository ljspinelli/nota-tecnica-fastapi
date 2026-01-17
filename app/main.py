from .database import Base, engine
from . import models

Base.metadata.create_all(bind=engine)

from fastapi import FastAPI
from datetime import datetime, date
from typing import List
from pydantic import BaseModel
from .services import calcular_periodos_recesso, montar_texto_conclusao

app = FastAPI(title="Serviço de Nota Técnica – Estagiário")


# --------- SCHEMAS (Pydantic) ---------

class CicloSchema(BaseModel):
    data_inicio: date
    data_fim: date
    dias_gozados: int


class EstagiarioSchema(BaseModel):
    nome: str
    ocupacao: str
    matricula: str
    processo_pae: str
    data_inicio_contrato: date
    data_fim_contrato: date
    ciclos: List[CicloSchema]


class PeriodoRecessoSchema(BaseModel):
    periodo_aquisitivo_inicio: date
    periodo_aquisitivo_fim: date
    dias_direito: int
    dias_gozados: int
    dias_nao_gozados: int


class NotaTecnicaResponse(BaseModel):
    numero_nota: str
    estagiario: EstagiarioSchema
    periodos_recesso: List[PeriodoRecessoSchema]
    total_dias_nao_gozados: int
    texto_conclusao: str


# --------- ENDPOINT ---------

@app.post("/nota-tecnica", response_model=NotaTecnicaResponse)
def gerar_nota_tecnica(estagiario: EstagiarioSchema):
    # Converte ciclos do schema para objetos Ciclo (SQLAlchemy-like) apenas para cálculo
    ciclos_convertidos = []
    for c in estagiario.ciclos:
        ciclos_convertidos.append(
            models.Ciclo(
                data_inicio=c.data_inicio,
                data_fim=c.data_fim,
                dias_gozados=c.dias_gozados,
            )
        )

    # Cria um "Estagiario" em memória só para passar para as funções de serviço
    estagiario_obj = models.Estagiario(
        nome=estagiario.nome,
        ocupacao=estagiario.ocupacao,
        matricula=estagiario.matricula,
        processo_pae=estagiario.processo_pae,
        data_inicio_contrato=estagiario.data_inicio_contrato,
        data_fim_contrato=estagiario.data_fim_contrato,
    )
    estagiario_obj.ciclos = ciclos_convertidos

    # Calcula períodos de recesso
    periodos = calcular_periodos_recesso(estagiario_obj)

    # Soma total de dias não gozados
    total_dias_nao_gozados = sum(p["dias_nao_gozados"] for p in periodos)

    # Número da nota
    numero_nota = f"001/{datetime.now().year}"

    # Texto de conclusão
    texto_conclusao = montar_texto_conclusao(estagiario_obj, periodos)

    return NotaTecnicaResponse(
        numero_nota=numero_nota,
        estagiario=estagiario,
        periodos_recesso=periodos,
        total_dias_nao_gozados=total_dias_nao_gozados,
        texto_conclusao=texto_conclusao,
    )
from sqlalchemy import text
from .database import SessionLocal

@app.get("/testar-banco")
def testar_banco():
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))  # agora usando text() corretamente
        db.close()
        return {"status": "ok", "mensagem": "Banco SQLite acessado com sucesso!"}
    except Exception as e:
        return {"status": "erro", "detalhes": str(e)}

from fastapi import Depends
from sqlalchemy.orm import Session
from .database import SessionLocal
from .models import Estagiario, Ciclo

# Dependência para obter a sessão do banco
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/estagiario")
def criar_estagiario(estagiario: EstagiarioSchema, db: Session = Depends(get_db)):
    novo_estagiario = Estagiario(
        nome=estagiario.nome,
        ocupacao=estagiario.ocupacao,
        matricula=estagiario.matricula,
        processo_pae=estagiario.processo_pae,
        data_inicio_contrato=estagiario.data_inicio_contrato,
        data_fim_contrato=estagiario.data_fim_contrato,
    )
    db.add(novo_estagiario)
    db.commit()
    db.refresh(novo_estagiario)

    for ciclo in estagiario.ciclos:
        novo_ciclo = Ciclo(
            estagiario_id=novo_estagiario.id,
            data_inicio=ciclo.data_inicio,
            data_fim=ciclo.data_fim,
            dias_gozados=ciclo.dias_gozados,
        )
        db.add(novo_ciclo)

    db.commit()

    return {"status": "ok", "id": novo_estagiario.id}
