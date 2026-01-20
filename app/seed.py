from datetime import datetime, date
from app.database import SessionLocal, engine
from app.models import Base, Estagiario, Ciclo, NotaTecnica
from app.services import (
    montar_ciclos_a_partir_form,
    calcular_nao_gozados,
    montar_texto_conclusao_vba
)

# ============================================================
# CRIA AS TABELAS (CASO NÃO EXISTAM)
# ============================================================

Base.metadata.create_all(bind=engine)

db = SessionLocal()

# ============================================================
# LISTA DE ESTAGIÁRIOS DE TESTE
# ============================================================

estagiarios_teste = [
    {
        "nome": "Lauro José Nascimento Spinelli",
        "ocupacao": "Estágio",
        "matricula": "55587676/2",
        "processo_pae": "2023/1371833",
        "inicio": "06/01/2023",
        "fim": "31/05/2025",
        "ciclo1_gozados": 30,
        "ciclo2_gozados": 14,
    },
    {
        "nome": "Maria Clara Silva",
        "ocupacao": "Estágio",
        "matricula": "99887766/1",
        "processo_pae": "2022/554433",
        "inicio": "10/03/2022",
        "fim": "15/02/2024",
        "ciclo1_gozados": 20,
        "ciclo2_gozados": 10,
    },
    {
        "nome": "João Pedro Almeida",
        "ocupacao": "Estágio",
        "matricula": "11223344/5",
        "processo_pae": "2024/778899",
        "inicio": "01/02/2024",
        "fim": "01/12/2024",
        "ciclo1_gozados": 0,
        "ciclo2_gozados": 0,
    }
]

# ============================================================
# PROCESSA CADA ESTAGIÁRIO
# ============================================================

for dados in estagiarios_teste:

    # 1. Criar estagiário
    est = Estagiario(
        nome=dados["nome"],
        ocupacao=dados["ocupacao"],
        matricula=dados["matricula"],
        processo_pae=dados["processo_pae"],
        data_inicio_contrato=datetime.strptime(dados["inicio"], "%d/%m/%Y").date(),
        data_fim_contrato=datetime.strptime(dados["fim"], "%d/%m/%Y").date(),
    )
    db.add(est)
    db.commit()
    db.refresh(est)

    # 2. Calcular ciclos
    info = montar_ciclos_a_partir_form(dados["inicio"], dados["fim"])

    ciclos_criados = []

    # --- 1º ciclo ---
    c1 = info["ciclo1"]
    ciclo1 = Ciclo(
        estagiario_id=est.id,
        data_inicio=c1["inicio"],
        data_fim=c1["fim"],
        dias_gozados=dados["ciclo1_gozados"],
        dias_direito=c1["dias_direito"],
    )
    db.add(ciclo1)
    ciclos_criados.append((c1, dados["ciclo1_gozados"]))

    # --- 2º ciclo (se existir) ---
    c2 = info["ciclo2"]
    if c2["inicio"] and c2["fim"]:
        ciclo2 = Ciclo(
            estagiario_id=est.id,
            data_inicio=c2["inicio"],
            data_fim=c2["fim"],
            dias_gozados=dados["ciclo2_gozados"],
            dias_direito=c2["dias_direito"],
        )
        db.add(ciclo2)
        ciclos_criados.append((c2, dados["ciclo2_gozados"]))

    db.commit()

    # 3. Calcular total de dias não gozados
    total_nao_gozados = 0
    for ciclo_info, gozados in ciclos_criados:
        total_nao_gozados += calcular_nao_gozados(
            ciclo_info["dias_direito"],
            gozados
        )

    # 4. Criar Nota Técnica
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

    # 5. Gerar número oficial da nota
    nota.numero_nota = f"{nota.numero_sequencial}/{date.today().year} - DDVP/DRH/PCPA"
    db.commit()

db.close()

print("Banco de dados populado com sucesso!")
