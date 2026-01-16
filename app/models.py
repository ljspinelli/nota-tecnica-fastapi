from pydantic import BaseModel
from datetime import date
from typing import List


class Ciclo(BaseModel):
    data_inicio: date
    data_fim: date
    dias_gozados: int = 0


class Estagiario(BaseModel):
    nome: str
    ocupacao: str
    matricula: str
    processo_pae: str
    data_inicio_contrato: date
    data_fim_contrato: date
    ciclos: List[Ciclo]


class PeriodoRecesso(BaseModel):
    periodo_aquisitivo_inicio: date
    periodo_aquisitivo_fim: date
    dias_direito: int
    dias_gozados: int
    dias_nao_gozados: int


class NotaTecnicaResponse(BaseModel):
    numero_nota: str
    estagiario: Estagiario
    periodos_recesso: List[PeriodoRecesso]
    total_dias_nao_gozados: int
    texto_conclusao: str