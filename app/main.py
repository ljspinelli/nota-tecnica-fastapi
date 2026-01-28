from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime

from .database import SessionLocal
from .models import Estagiario, Ciclo, NotaTecnica
from .services import (
    calcular_dias_direito,
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
# PRÉVIA DA NOTA TÉCNICA
# ============================================================

@app.post("/nota-tecnica/preview", response_class=HTMLResponse)
async def preview_nota(request: Request):
    form = await request.form()

    inicio = datetime.strptime(form["inicio"], "%Y-%m-%d").date()
    fim = datetime.strptime(form["fim"], "%Y-%m-%d").date()
    dias_contrato = (fim - inicio).days + 1

    ciclo1_dias = dias_contrato
    ciclo1_direito = calcular_dias_direito(ciclo1_dias)
    ciclo1_gozados = int(form["ciclo1_gozados"])
    ciclo1_nao_gozados = max(ciclo1_direito - ciclo1_gozados, 0)

    dados = {
        "nome": form["nome"],
        "ocupacao": form["ocupacao"],
        "matricula": form["matricula"],
        "processo_pae": form["processo_pae"],
        "assunto": form.get("assunto", "Pagamento de Recesso Não Usufruído"),
        "inicio": form["inicio"],
        "fim": form["fim"],
        "dias_contrato": dias_contrato,
        "ciclo1_inicio": inicio.strftime("%Y-%m-%d"),
        "ciclo1_fim": fim.strftime("%Y-%m-%d"),
        "ciclo1_dias": ciclo1_dias,
        "ciclo1_direito": ciclo1_direito,
        "ciclo1_gozados": ciclo1_gozados,
        "ciclo1_nao_gozados": ciclo1_nao_gozados,
    }

    return templates.TemplateResponse("preview_nota.html", {"request": request, "dados": dados})

# ============================================================
# GRAVAÇÃO FINAL DA NOTA TÉCNICA
# ============================================================

@app.post("/nota-tecnica/gerar")
def gerar_nota(
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
    db: Session = Depends(get_db)
):
    # ============================================================
    # 1. Criar ou recuperar Estagiário
    # ============================================================
    est = db.query(Estagiario).filter_by(matricula=matricula).first()
    if not est:
        est = Estagiario(
            nome=nome,
            ocupacao=ocupacao,
            matricula=matricula,
            processo_pae=processo_pae,
            data_inicio_contrato=datetime.strptime(inicio, "%Y-%m-%d").date(),
            data_fim_contrato=datetime.strptime(fim, "%Y-%m-%d").date()
        )
        db.add(est)
        db.commit()
        db.refresh(est)

    # ============================================================
    # 2. Criar Nota Técnica
    # ============================================================
    total_nao_gozados = ciclo1_nao_gozados
    nota = NotaTecnica(
        assunto=assunto,
        estagiario_id=est.id,
        total_dias_nao_gozados=total_nao_gozados,
        texto_conclusao=montar_texto_conclusao_vba(nome, total_nao_gozados),
        data_emissao=datetime.today().date()
    )
    db.add(nota)
    db.commit()
    db.refresh(nota)

    # ============================================================
    # 3. Criar Ciclo
    # ============================================================
    ciclo1 = Ciclo(
        estagiario_id=est.id,
        data_inicio=datetime.strptime(ciclo1_inicio, "%Y-%m-%d").date(),
        data_fim=datetime.strptime(ciclo1_fim, "%Y-%m-%d").date(),
        dias_corridos=ciclo1_dias,
        dias_direito=ciclo1_direito,
        dias_gozados=ciclo1_gozados
    )
    db.add(ciclo1)
    db.commit()

    # ============================================================
    # 4. Redirecionar para listagem
    # ============================================================
    return RedirectResponse(url="/notas-tecnicas", status_code=303)
