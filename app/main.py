from fastapi import FastAPI, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import date, datetime

from .database import SessionLocal, engine
from .models import Base, Estagiario, Ciclo, NotaTecnica
from .services import (
    calcular_periodos_recesso,
    montar_texto_conclusao,
    montar_ciclos_a_partir_form,
    calcular_nao_gozados,
    montar_texto_conclusao_vba,
)

# ============================================================
# CONFIGURAÇÃO INICIAL
# ============================================================

Base.metadata.create_all(bind=engine)

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
# PÁGINA INICIAL
# ============================================================

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# ============================================================
# FORMULÁRIO PARA LANÇAMENTO DE DADOS (NOVO)
# ============================================================

@app.get("/nota-tecnica/form", response_class=HTMLResponse)
def form_nota_tecnica(request: Request):
    return templates.TemplateResponse(
        "lancamento_dados.html",
        {"request": request},
    )


@app.post("/nota-tecnica/form")
def criar_nota_tecnica_form(
    request: Request,
    nome: str = Form(...),
    ocupacao: str = Form(...),
    matricula: str = Form(...),
    processo_pae: str = Form(...),
    assunto: str = Form(""),
    contrato_inicio: str = Form(...),
    contrato_fim: str = Form(...),
    ciclo1_usufruidos: int = Form(0),
    ciclo2_usufruidos: int = Form(0),
    db: Session = Depends(get_db),
):

    # ============================================================
    # 1. CRIAR ESTAGIÁRIO
    # ============================================================

    est = Estagiario(
        nome=nome,
        ocupacao=ocupacao,
        matricula=matricula,
        processo_pae=processo_pae,
        data_inicio_contrato=datetime.strptime(contrato_inicio, "%d/%m/%Y").date(),
        data_fim_contrato=datetime.strptime(contrato_fim, "%d/%m/%Y").date(),
    )
    db.add(est)
    db.commit()
    db.refresh(est)

    # ============================================================
    # 2. CALCULAR CICLOS (LÓGICA VBA)
    # ============================================================

    info = montar_ciclos_a_partir_form(contrato_inicio, contrato_fim)

    ciclos_criados = []

    # --- 1º ciclo ---
    c1 = info["ciclo1"]
    ciclo1 = Ciclo(
        estagiario_id=est.id,
        data_inicio=c1["inicio"],
        data_fim=c1["fim"],
        dias_gozados=ciclo1_usufruidos,
    )
    db.add(ciclo1)
    ciclos_criados.append((c1, ciclo1_usufruidos))

    # --- 2º ciclo (se existir) ---
    c2 = info["ciclo2"]
    if c2["inicio"] and c2["fim"]:
        ciclo2 = Ciclo(
            estagiario_id=est.id,
            data_inicio=c2["inicio"],
            data_fim=c2["fim"],
            dias_gozados=ciclo2_usufruidos,
        )
        db.add(ciclo2)
        ciclos_criados.append((c2, ciclo2_usufruidos))

    db.commit()

    # ============================================================
    # 3. CALCULAR TOTAL DE DIAS NÃO GOZADOS
    # ============================================================

    total_nao_gozados = 0
    for ciclo_info, gozados in ciclos_criados:
        nao_gozados = calcular_nao_gozados(ciclo_info["dias_direito"], gozados)
        total_nao_gozados += nao_gozados

    # ============================================================
    # 4. CRIAR NOTA TÉCNICA
    # ============================================================

    numero_nota = f"{est.id:04d}/{date.today().year}"

    texto_conclusao = montar_texto_conclusao_vba(
        nome=est.nome,
        total_nao_gozados=total_nao_gozados
    )

    nota = NotaTecnica(
        estagiario_id=est.id,
        numero_nota=numero_nota,
        total_dias_nao_gozados=total_nao_gozados,
        texto_conclusao=texto_conclusao,
        data_emissao=date.today(),
    )
    db.add(nota)
    db.commit()
    db.refresh(nota)

    # ============================================================
    # 5. REDIRECIONAR PARA VISUALIZAÇÃO
    # ============================================================

    return RedirectResponse(
        url=f"/nota-tecnica/{nota.id}/visualizar",
        status_code=303,
    )


# ============================================================
# VISUALIZAÇÃO DA NOTA TÉCNICA
# ============================================================

@app.get("/nota-tecnica/{nota_id}/visualizar", response_class=HTMLResponse)
def visualizar_nota_tecnica(nota_id: int, request: Request, db: Session = Depends(get_db)):
    nota = db.query(NotaTecnica).filter(NotaTecnica.id == nota_id).first()
    est = db.query(Estagiario).filter(Estagiario.id == nota.estagiario_id).first()
    ciclos = db.query(Ciclo).filter(Ciclo.estagiario_id == est.id).all()

    return templates.TemplateResponse(
        "nota_tecnica.html",
        {
            "request": request,
            "nota": nota,
            "estagiario": est,
            "ciclos": ciclos,
        }
    )
@app.get("/estagiarios", response_class=HTMLResponse)
def listar_estagiarios(request: Request, db: Session = Depends(get_db)):
    estagiarios = db.query(Estagiario).all()
    return templates.TemplateResponse(
        "lista_estagiarios.html",
        {
            "request": request,
            "estagiarios": estagiarios
        }
    )
@app.get("/notas-tecnicas", response_class=HTMLResponse)
def listar_notas_tecnicas(request: Request, db: Session = Depends(get_db)):
    notas = (
        db.query(NotaTecnica)
        .order_by(NotaTecnica.numero_sequencial.asc())
        .all()
    )
    return templates.TemplateResponse(
        "lista_notas.html",
        {
            "request": request,
            "notas": notas
        }
    )
