from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from datetime import datetime, date
from typing import List
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text

from .database import Base, engine, SessionLocal
from .models import Estagiario, Ciclo, NotaTecnica
from .services import calcular_periodos_recesso, montar_texto_conclusao

# Criar tabelas no banco
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Serviço de Nota Técnica – Estagiário")

# Suporte a templates HTML
templates = Jinja2Templates(directory="app/templates")


# ---------------------------------------------------------
# Função para converter datas no formato brasileiro
# ---------------------------------------------------------
def parse_data_br(data_str: str):
    return datetime.strptime(data_str, "%d/%m/%Y").date()


# ---------------------------------------------------------
# SCHEMAS (aceitando datas como string BR)
# ---------------------------------------------------------
class CicloSchema(BaseModel):
    data_inicio: str
    data_fim: str
    dias_gozados: int


class EstagiarioSchema(BaseModel):
    nome: str
    ocupacao: str
    matricula: str
    processo_pae: str
    data_inicio_contrato: str
    data_fim_contrato: str
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


class NotaTecnicaListaSchema(BaseModel):
    id: int
    numero_nota: str
    estagiario: str
    total_dias_nao_gozados: int
    data_emissao: date


# ---------------------------------------------------------
# Dependência de banco
# ---------------------------------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------
# Endpoint de teste do banco
# ---------------------------------------------------------
@app.get("/testar-banco")
def testar_banco():
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        return {"status": "ok", "mensagem": "Banco SQLite acessado com sucesso!"}
    except Exception as e:
        return {"status": "erro", "detalhes": str(e)}


# ---------------------------------------------------------
# Criar estagiário
# ---------------------------------------------------------
@app.post("/estagiario")
def criar_estagiario(estagiario: EstagiarioSchema, db: Session = Depends(get_db)):
    novo_estagiario = Estagiario(
        nome=estagiario.nome,
        ocupacao=estagiario.ocupacao,
        matricula=estagiario.matricula,
        processo_pae=estagiario.processo_pae,
        data_inicio_contrato=parse_data_br(estagiario.data_inicio_contrato),
        data_fim_contrato=parse_data_br(estagiario.data_fim_contrato),
    )

    db.add(novo_estagiario)
    db.commit()
    db.refresh(novo_estagiario)

    for ciclo in estagiario.ciclos:
        novo_ciclo = Ciclo(
            estagiario_id=novo_estagiario.id,
            data_inicio=parse_data_br(ciclo.data_inicio),
            data_fim=parse_data_br(ciclo.data_fim),
            dias_gozados=ciclo.dias_gozados,
        )
        db.add(novo_ciclo)

    db.commit()

    return {"status": "ok", "id": novo_estagiario.id}


# ---------------------------------------------------------
# Gerar Nota Técnica por ID
# ---------------------------------------------------------
@app.post("/nota-tecnica/{estagiario_id}", response_model=NotaTecnicaResponse)
def gerar_nota_tecnica_por_id(estagiario_id: int, db: Session = Depends(get_db)):
    est = db.query(Estagiario).filter(Estagiario.id == estagiario_id).first()
    if not est:
        raise HTTPException(status_code=404, detail="Estagiário não encontrado")

    ciclos = db.query(Ciclo).filter(Ciclo.estagiario_id == estagiario_id).all()
    est.ciclos = ciclos

    periodos = calcular_periodos_recesso(est)
    total_dias_nao_gozados = sum(p["dias_nao_gozados"] for p in periodos)

    numero_nota = f"{estagiario_id:03d}/{datetime.now().year}"
    texto_conclusao = montar_texto_conclusao(est, periodos)

    nova_nota = NotaTecnica(
        estagiario_id=estagiario_id,
        numero_nota=numero_nota,
        total_dias_nao_gozados=total_dias_nao_gozados,
        texto_conclusao=texto_conclusao,
        data_emissao=date.today(),
    )

    db.add(nova_nota)
    db.commit()
    db.refresh(nova_nota)

    est_schema = EstagiarioSchema(
        nome=est.nome,
        ocupacao=est.ocupacao,
        matricula=est.matricula,
        processo_pae=est.processo_pae,
        data_inicio_contrato=est.data_inicio_contrato.strftime("%d/%m/%Y"),
        data_fim_contrato=est.data_fim_contrato.strftime("%d/%m/%Y"),
        ciclos=[
            CicloSchema(
                data_inicio=c.data_inicio.strftime("%d/%m/%Y"),
                data_fim=c.data_fim.strftime("%d/%m/%Y"),
                dias_gozados=c.dias_gozados,
            )
            for c in ciclos
        ],
    )

    periodos_schema = [
        PeriodoRecessoSchema(
            periodo_aquisitivo_inicio=p["periodo_aquisitivo_inicio"],
            periodo_aquisitivo_fim=p["periodo_aquisitivo_fim"],
            dias_direito=p["dias_direito"],
            dias_gozados=p["dias_gozados"],
            dias_nao_gozados=p["dias_nao_gozados"],
        )
        for p in periodos
    ]

    return NotaTecnicaResponse(
        numero_nota=numero_nota,
        estagiario=est_schema,
        periodos_recesso=periodos_schema,
        total_dias_nao_gozados=total_dias_nao_gozados,
        texto_conclusao=texto_conclusao,
    )


# ---------------------------------------------------------
# Listar todas as notas técnicas
# ---------------------------------------------------------
@app.get("/notas-tecnicas", response_model=List[NotaTecnicaListaSchema])
def listar_notas_tecnicas(db: Session = Depends(get_db)):
    notas = db.query(NotaTecnica).all()

    resposta = []
    for nota in notas:
        est = db.query(Estagiario).filter(Estagiario.id == nota.estagiario_id).first()

        resposta.append(
            NotaTecnicaListaSchema(
                id=nota.id,
                numero_nota=nota.numero_nota,
                estagiario=est.nome if est else "Desconhecido",
                total_dias_nao_gozados=nota.total_dias_nao_gozados,
                data_emissao=nota.data_emissao
            )
        )

    return resposta


# ---------------------------------------------------------
# Listar todos os estagiários
# ---------------------------------------------------------
@app.get("/estagiarios")
def listar_estagiarios(db: Session = Depends(get_db)):
    estagiarios = db.query(Estagiario).all()

    resposta = []
    for est in estagiarios:
        resposta.append({
            "id": est.id,
            "nome": est.nome,
            "ocupacao": est.ocupacao,
            "matricula": est.matricula,
            "processo_pae": est.processo_pae,
            "data_inicio_contrato": est.data_inicio_contrato.strftime("%d/%m/%Y"),
            "data_fim_contrato": est.data_fim_contrato.strftime("%d/%m/%Y")
        })

    return resposta


# ---------------------------------------------------------
# Buscar estagiário por ID
# ---------------------------------------------------------
@app.get("/estagiario/{estagiario_id}")
def buscar_estagiario(estagiario_id: int, db: Session = Depends(get_db)):
    est = db.query(Estagiario).filter(Estagiario.id == estagiario_id).first()

    if not est:
        raise HTTPException(status_code=404, detail="Estagiário não encontrado")

    ciclos = db.query(Ciclo).filter(Ciclo.estagiario_id == estagiario_id).all()

    return {
        "id": est.id,
        "nome": est.nome,
        "ocupacao": est.ocupacao,
        "matricula": est.matricula,
        "processo_pae": est.processo_pae,
        "data_inicio_contrato": est.data_inicio_contrato.strftime("%d/%m/%Y"),
        "data_fim_contrato": est.data_fim_contrato.strftime("%d/%m/%Y"),
        "ciclos": [
            {
                "data_inicio": c.data_inicio.strftime("%d/%m/%Y"),
                "data_fim": c.data_fim.strftime("%d/%m/%Y"),
                "dias_gozados": c.dias_gozados
            }
            for c in ciclos
        ]
    }


# ---------------------------------------------------------
# Buscar nota técnica por ID
# ---------------------------------------------------------
@app.get("/nota-tecnica/{nota_id}")
def buscar_nota_tecnica(nota_id: int, db: Session = Depends(get_db)):
    nota = db.query(NotaTecnica).filter(NotaTecnica.id == nota_id).first()

    if not nota:
        raise HTTPException(status_code=404, detail="Nota Técnica não encontrada")

    est = db.query(Estagiario).filter(Estagiario.id == nota.estagiario_id).first()

    return {
        "id": nota.id,
        "numero_nota": nota.numero_nota,
        "estagiario": est.nome if est else "Desconhecido",
        "total_dias_nao_gozados": nota.total_dias_nao_gozados,
        "texto_conclusao": nota.texto_conclusao,
        "data_emissao": nota.data_emissao.strftime("%d/%m/%Y")
    }


# ---------------------------------------------------------
# VISUALIZAR NOTA TÉCNICA EM HTML
# ---------------------------------------------------------
@app.get("/nota-tecnica/{nota_id}/visualizar", response_class=HTMLResponse)
def visualizar_nota_tecnica(nota_id: int, request: Request, db: Session = Depends(get_db)):
    nota = db.query(NotaTecnica).filter(NotaTecnica.id == nota_id).first()
    if not nota:
        raise HTTPException(status_code=404, detail="Nota Técnica não encontrada")

    est = db.query(Estagiario).filter(Estagiario.id == nota.estagiario_id).first()
    if not est:
        raise HTTPException(status_code=404, detail="Estagiário não encontrado")

    # 🔧 Carregar ciclos do estagiário
    ciclos = db.query(Ciclo).filter(Ciclo.estagiario_id == est.id).all()
    est.ciclos = ciclos

    # 🔧 Calcular períodos de recesso
    periodos = calcular_periodos_recesso(est)

    # 🔧 Preparar estagiário como dicionário com datas formatadas
    est_dict = {
        "nome": est.nome,
        "ocupacao": est.ocupacao,
        "matricula": est.matricula,
        "processo_pae": est.processo_pae,
        "data_inicio_contrato": est.data_inicio_contrato.strftime("%d/%m/%Y"),
        "data_fim_contrato": est.data_fim_contrato.strftime("%d/%m/%Y")
    }

    # 🔧 Formatar datas dos períodos para o template
    periodos_formatados = []
    for p in periodos:
        periodos_formatados.append({
            "periodo_aquisitivo_inicio": p["periodo_aquisitivo_inicio"].strftime("%d/%m/%Y"),
            "periodo_aquisitivo_fim": p["periodo_aquisitivo_fim"].strftime("%d/%m/%Y"),
            "dias_direito": p["dias_direito"],
            "dias_gozados": p["dias_gozados"],
            "dias_nao_gozados": p["dias_nao_gozados"]
        })

    return templates.TemplateResponse(
        "nota_tecnica.html",
        {
            "request": request,
            "numero_nota": nota.numero_nota,
            "estagiario": est_dict,
            "periodos": periodos_formatados,
            "texto_conclusao": nota.texto_conclusao,
            "data_emissao": nota.data_emissao.strftime("%d/%m/%Y")
        }
    )

