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
    notas = db.query(NotaTecnica).order_by(NotaTecnica.numero_sequencial.asc()).all()
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

def calcular_direito(dias):
    if dias < 180:
        return 0
    if dias == 180:
        return 15
    if dias <= 210:
        return 18
    if dias <= 240:
        return 20
    if dias <= 270:
        return 23
    if dias <= 300:
        return 25
    if dias <= 330:
        return 28
    if dias <= 360:
        return 30
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
        data_inicio_contrato=datetime.strptime(inicio, "%Y-%m-%d").date(),
        data_fim_contrato=datetime.strptime(fim, "%Y-%m-%d").date(),
    )
    db.add(est)
    db.commit()
    db.refresh(est)

    # ============================================================
    # 2. Criar Ciclo 1
    # ============================================================
    ciclo1 = Ciclo(
        estagiario_id=est.id,
        data_inicio=datetime.strptime(ciclo1_inicio, "%Y-%m-%d").date(),
        data_fim=datetime.strptime(ciclo1_fim, "%Y-%m-%d").date(),
        dias_gozados=ciclo1_gozados,
        dias_direito=ciclo1_direito,
    )
    db.add(ciclo1)

    # ============================================================
    # 3. Criar Ciclo 2 (se existir)
    # ============================================================
    ciclos = [ciclo1]
    if ciclo2_inicio and ciclo2_fim:
        ciclo2 = Ciclo(
            estagiario_id=est.id,
            data_inicio=datetime.strptime(ciclo2_inicio, "%Y-%m-%d").date(),
            data_fim=datetime.strptime(ciclo2_fim, "%Y-%m-%d").date(),
            dias_gozados=ciclo2_gozados,
            dias_direito=int(ciclo2_direito),
        )
        db.add(ciclo2)
        ciclos.append(ciclo2)

    db.commit()

    # ============================================================
    # 4. Total de não usufruídos (já calculado)
    # ============================================================
    total_nao_gozados = ciclo1_nao_gozados
    if ciclo2_nao_gozados != "":
        total_nao_gozados += int(ciclo2_nao_gozados)

    # ============================================================
    # 5. Criar Nota Técnica
    # ============================================================
    nota = NotaTecnica(
        estagiario_id=est.id,
        total_dias_nao_gozados=total_nao_gozados,
        texto_conclusao=montar_texto_conclusao_vba(
            nome=est.nome,
            total_nao_gozados=total_nao_gozados
        ),
        data_emissao=date.today(),
    )
    db.add(nota)
    db.commit()
    db.refresh(nota)

    # Número sequencial
    nota.numero_nota = f"{nota.numero_sequencial}/{date.today().year} - DDVP/DRH/PCPA"
    db.commit()

    # ============================================================
    # 6. Redirecionar para a página final da Nota Técnica
    # ============================================================
    return RedirectResponse(
        url=f"/nota-tecnica/{nota.id}/visualizar",
        status_code=303
    )
# ============================================================
# CRIAÇÃO AUTOMÁTICA DAS TABELAS NO STARTUP
# ============================================================

@app.on_event("startup")
def startup_event():
    Base.metadata.create_all(bind=engine)

# ============================================================
# DEBUG OPCIONAL
# ============================================================

@app.get("/debug-db")
def debug_db(db: Session = Depends(get_db)):
    try:
        db.query(Estagiario).all()
        return {"status": "OK", "mensagem": "Banco acessível."}
    except Exception as e:
        return {"status": "ERRO", "detalhes": str(e)}

@app.get("/nota-tecnica/{nota_id}/visualizar", response_class=HTMLResponse)
def visualizar_nota(nota_id: int, request: Request, db: Session = Depends(get_db)):
    nota = db.query(NotaTecnica).filter(NotaTecnica.id == nota_id).first()
    est = db.query(Estagiario).filter(Estagiario.id == nota.estagiario_id).first()
    ciclos = db.query(Ciclo).filter(Ciclo.estagiario_id == est.id).all()

    return templates.TemplateResponse(
        "nota_final.html",
        {
            "request": request,
            "nota": nota,
            "est": est,
            "ciclos": ciclos
        }
    )

