from .database import Base, engine
from . import models

Base.metadata.create_all(bind=engine)

from fastapi import FastAPI
from datetime import datetime
from .models import Estagiario, Ciclo, NotaTecnica
from .services import calcular_periodos_recesso, montar_texto_conclusao

app = FastAPI(title="Serviço de Nota Técnica – Estagiário")


@app.post("/nota-tecnica")
def gerar_nota_tecnica(estagiario: Estagiario):
    periodos = calcular_periodos_recesso(estagiario)
    total_dias_nao_gozados = sum(p.dias_nao_gozados for p in periodos)

    numero_nota = f"001/{datetime.now().year}"
    texto_conclusao = montar_texto_conclusao(estagiario, periodos)

    return NotaTecnicaResponse(
        numero_nota=numero_nota,
        estagiario=estagiario,
        periodos_recesso=periodos,
        total_dias_nao_gozados=total_dias_nao_gozados,
        texto_conclusao=texto_conclusao,

    )
