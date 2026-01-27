from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta

from .database import engine, SessionLocal
from .models import Base, Estagiario, Ciclo, NotaTecnica
from .services import (
    montar_ciclos_a_partir_form,
    calcular_nao_gozados,
    montar_texto_conclusao_vba
)

# ============================================================
# CONFIGURAÇÃO DO FASTAPI
# ============================================================

app = FastAPI()

templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# ============================================================
# DEPENDÊNCIA DO BANCO
# ============================================================

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ============================================================
# MENU INICIAL
# ============================================================

@app.get("/", response_class=HTMLResponse)
def menu_inicial(request: Request):
    return templates.TemplateResponse("menu_inicial.html", {"request": request})

# ============================================================
# PAINEL PRINCIPAL (SEM LOGIN)
# ============================================================

@app.get("/admin", response_class=HTMLResponse)
def painel_admin(request: Request, db: Session = Depends(get_db)):
    total_estagiarios = db.query(Estagiario).count()
    total_notas = db.query(NotaTecnica).count()
    total_dias_pagos = sum(n.total_dias_nao_gozados for n in db.query(NotaTecnica).all())

    ultimas_notas = (
        db.query(NotaTecnica)
        .order_by(NotaTecnica.id.desc())
        .limit(5)
        .all()
    )

    return templates.TemplateResponse(
        "painel_admin.html",
        {
            "request": request,
            "total_estagiarios": total_estagiarios,
            "total_notas": total_notas,
            "total_dias_pagos": total_dias_pagos,
            "ultimas_notas": ultimas_notas,
        }
    )

# ============================================================
# LISTAGEM DE ESTAGIÁRIOS
# ============================================================

@app.get("/estagiarios", response_class=HTMLResponse)
def listar_estagiarios(request: Request, db: Session = Depends(get_db)):
    estagiarios = db.query(Estagiario).all()
    return templates.TemplateResponse("lista_estagiarios.html", {"request": request, "estagiarios": estagiarios})

# ============================================================
# LISTAGEM DE NOTAS TÉCNICAS
# ============================================================

@app.get("/notas-tecnicas", response_class=HTMLResponse)
def listar_notas(request: Request, db: Session = Depends(get_db)):
    notas = db.query(NotaTecnica).order_by(NotaTecnica.id.desc()).all()
    return templates.TemplateResponse("lista_notas.html", {"request": request, "notas": notas})

# ============================================================
# FORMULÁRIO DE NOTA TÉCNICA
# ============================================================

@app.get("/nota-tecnica/form", response_class=HTMLResponse)
def form_nota(request: Request):
    return templates.TemplateResponse("form_nota.html", {"request": request})

# ============================================================
# FUNÇÕES AUXILIARES PARA A PRÉVIA
# ============================================================

def calcular_direito(dias: int) -> int:
    if dias < 180:
        return 0
    elif 180 <= dias < 209:
        return 15
    elif 210 <= dias < 239:
        return 18
    elif 240 <= dias < 269:
        return 20
    elif 270 <= dias < 299:
        return 23
    elif 300 <= dias < 329:
        return 25
    elif 330 <= dias < 359:
        return 28
    elif 360 <= dias < 367:
        return 30
    else:
        return 0


def processar_dados_formulario(form):
    dados = {}

    # Dados básicos
    dados["nome"] = form["nome"]
    dados["ocupacao"] = form["ocupacao"]
    dados["matricula"] = form["matricula"]
    dados["processo_pae"] = form["processo_pae"]
    dados["assunto"] = form.get("assunto", "Pagamento de Recesso Não Usufruído")

    # Datas
    inicio = datetime.strptime(form["inicio"], "%Y-%m-%d").date()
    fim = datetime.strptime(form["fim"], "%Y-%m-%d").date()

    dados["inicio"] = form["inicio"]
    dados["fim"] = form["fim"]

    # Dias de contrato
    dias_contrato = (fim - inicio).days
    dados["dias_contrato"] = dias_contrato

    # ============================================================
    # CÁLCULO DOS CICLOS
    # ============================================================

    ciclo1_inicio = inicio
    if dias_contrato < 364:
        ciclo1_fim = fim
        ciclo2_inicio = None
        ciclo2_fim = None
    else:
        ciclo1_fim = inicio + timedelta(days=364)
        ciclo2_inicio = ciclo1_fim + timedelta(days=1)
        ciclo2_fim = fim

    dados["ciclo1_inicio"] = ciclo1_inicio.strftime("%Y-%m-%d")
    dados["ciclo1_fim"] = ciclo1_fim.strftime("%Y-%m-%d")
    dados["ciclo1_dias"] = (ciclo1_fim - ciclo1_inicio).days
    dados["ciclo1_direito"] = calcular_direito(dados["ciclo1_dias"])

    if ciclo2_inicio:
        dados["ciclo2_inicio"] = ciclo2_inicio.strftime("%Y-%m-%d")
        dados["ciclo2_fim"] = ciclo2_fim.strftime("%Y-%m-%d")
        dados["ciclo2_dias"] = (ciclo2_fim - ciclo2_inicio).days
        dados["ciclo2_direito"] = calcular_direito(dados["ciclo2_dias"])
    else:
        dados["ciclo2_inicio"] = ""
        dados["ciclo2_fim"] = ""
        dados["ciclo2_dias"] = ""
        dados["ciclo2_direito"] = ""

    # ============================================================
    # GOZO
    # ============================================================

    dados["ciclo1_gozados"] = int(form["ciclo1_gozados"])
    dados["ciclo1_nao_gozados"] = max(
        dados["ciclo1_direito"] - dados["ciclo1_gozados"], 0
    )

    dados["ciclo2_gozados"] = int(form["ciclo2_gozados"])
    dados["ciclo2_nao_gozados"] = (
        max(dados["ciclo2_direito"] - dados["ciclo2_gozados"], 0)
        if dados["ciclo2_direito"] != "" else ""
    )

    return dados

# ============================================================
# ROTA DE PRÉVIA DA NOTA TÉCNICA
# ============================================================

@app.post("/nota-tecnica/preview", response_class=HTMLResponse)
async def preview_nota(request: Request):
    form = await request.form()
    dados = processar_dados_formulario(form)

    return templates.TemplateResponse(
        "preview_nota.html",
        {"request": request, "dados": dados}
    )

# ============================================================
# PROCESSAMENTO FINAL DA NOTA TÉCNICA (GRAVAÇÃO)
# ============================================================

@app.post("/nota-tecnica/gerar")
def gerar_nota(
    request: Request,
    nome: str = Form(...),
    ocupacao: str = Form(...),
    matricula: str = Form(...),
    processo_pae: str = Form(...),
    assunto: str = Form(...),
    inicio: str = Form(...),
    fim: str = Form(...),
    dias_contrato: int = Form(...),

    ciclo1_inicio: str = Form(...),
    ciclo1_fim: str = Form(...),
    ciclo1_dias: int = Form(...),
    ciclo1_direito: int = Form(...),
    ciclo1_gozados: int = Form(...),
    ciclo1_nao_gozados: int = Form(...),

    ciclo2_inicio: str = Form(""),
    ciclo2_fim: str = Form(""),
    ciclo2_dias: str = Form(""),
    ciclo2_direito: str = Form(""),
    ciclo2_gozados: int = Form(...),
    ciclo2_nao_gozados: str = Form(""),

    db: Session = Depends(get_db)
):
    # ============================================================
    # 1. Criar Estagiário
    # ============================================================
    est = Estagiario(
        nome=nome,
        ocupacao=ocupacao,
        matricula=matricula,
        processo_pae=processo_pae,
        data_inicio_contrato=datetime.strptime(inicio, "%Y-%m-%d").
    )

