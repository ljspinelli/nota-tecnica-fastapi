from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session
from datetime import datetime, date

from .database import engine, SessionLocal
from .models import Base, Estagiario, Ciclo, NotaTecnica, User
from .services import (
    montar_ciclos_a_partir_form,
    calcular_nao_gozados,
    montar_texto_conclusao_vba,
    verificar_senha,
    hash_senha
)

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="CHAVE-SECRETA-MUITO-FORTE")
templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def usuario_logado(request: Request, db: Session):
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Não autorizado")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="Não autorizado")

    return user


@app.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
def login(request: Request, username: str = Form(...), senha: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()

    if not user or not verificar_senha(senha, user.senha_hash):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "erro": "Usuário ou senha inválidos"}
        )

    request.session["user_id"] = user.id
    user.ultimo_acesso = datetime.now()
    db.commit()

    return RedirectResponse(url="/admin", status_code=303)


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)


@app.get("/", response_class=HTMLResponse)
def menu_inicial(request: Request):
    return templates.TemplateResponse("menu_inicial.html", {"request": request})


@app.get("/admin", response_class=HTMLResponse)
def painel_admin(request: Request, db: Session = Depends(get_db)):
    usuario_logado(request, db)

    total_estagiarios = db.query(Estagiario).count()
    total_notas = db.query(NotaTecnica).count()
    total_dias_pagos = sum([n.total_dias_nao_gozados for n in db.query(NotaTecnica).all()])
    ultimas_notas = db.query(NotaTecnica).order_by(NotaTecnica.id.desc()).limit(5).all()

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


@app.get("/estagiarios", response_class=HTMLResponse)
def listar_estagiarios(request: Request, db: Session = Depends(get_db)):
    usuario_logado(request, db)
    estagiarios = db.query(Estagiario).all()
    return templates.TemplateResponse("lista_estagiarios.html", {"request": request, "estagiarios": estagiarios})


@app.get("/notas-tecnicas", response_class=HTMLResponse)
def listar_notas(request: Request, db: Session = Depends(get_db)):
    usuario_logado(request, db)
    notas = db.query(NotaTecnica).order_by(NotaTecnica.numero_sequencial.asc()).all()
    return templates.TemplateResponse("lista_notas.html", {"request": request, "notas": notas})


@app.get("/nota-tecnica/form", response_class=HTMLResponse)
def form_nota(request: Request, db: Session = Depends(get_db)):
    usuario_logado(request, db)
    return templates.TemplateResponse("form_nota.html", {"request": request})


@app.post("/nota-tecnica/gerar")
def gerar_nota(
    request: Request,
    nome: str = Form(...),
    ocupacao: str = Form(...),
    matricula: str = Form(...),
    processo_pae: str = Form(...),
    inicio: str = Form(...),
    fim: str = Form(...),
    ciclo1_gozados: int = Form(...),
    ciclo2_gozados: int = Form(...),
    db: Session = Depends(get_db)
):
    usuario_logado(request, db)

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

    info = montar_ciclos_a_partir_form(inicio, fim)
    ciclos_criados = []

    c1 = info["ciclo1"]
    ciclo1 = Ciclo(
        estagiario_id=est.id,
        data_inicio=c1["inicio"],
        data_fim=c1["fim"],
        dias_gozados=ciclo1_gozados,
        dias_direito=c1["dias_direito"],
    )
    db.add(ciclo1)
    ciclos_criados.append((c1, ciclo1_gozados))

    c2 = info["ciclo2"]
    if c2["inicio"] and c2["fim"]:
        ciclo2 = Ciclo(
            estagiario_id=est.id,
            data_inicio=c2["inicio"],
            data_fim=c2["fim"],
            dias_gozados=ciclo2_gozados,
            dias_direito=c2["dias_direito"],
        )
        db.add(ciclo2)
        ciclos_criados.append((c2, ciclo2_gozados))

    db.commit()

    total_nao_gozados = sum(
        calcular_nao_gozados(c["dias_direito"], gozados)
        for c, gozados in ciclos_criados
    )

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

    nota.numero_nota = f"{nota.numero_sequencial}/{date.today().year} - DDVP/DRH/PCPA"
    db.commit()

    return RedirectResponse(url="/notas-tecnicas", status_code=303)


@app.get("/criar-admin")
def criar_admin(db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == "admin").first():
        return {"mensagem": "Usuário admin já existe."}

    admin = User(
        username="admin",
        senha_hash=hash_senha("123456")
    )
    db.add(admin)
    db.commit()
    return {"mensagem": "Usuário admin criado com sucesso!"}


@app.on_event("startup")
def startup_event():
    Base.metadata.create_all(bind=engine)
