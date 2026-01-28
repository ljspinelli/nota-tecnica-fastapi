from datetime import date, datetime, timedelta
from typing import List, Optional
from .models import Estagiario, Ciclo

# ============================================================
# 1. UTILIDADES DE DATA
# ============================================================

def str_to_date_br(valor: str) -> date:
    """Converte string dd/mm/yyyy para date."""
    return datetime.strptime(valor, "%d/%m/%Y").date()

def dias_entre(inicio: date, fim: date) -> int:
    """Retorna a quantidade de dias corridos entre duas datas."""
    return (fim - inicio).days

# ============================================================
# 2. LÓGICA ANTIGA DO SISTEMA (LEGADO)
# ============================================================

def calcular_meses_entre(inicio: date, fim: date) -> int:
    anos = fim.year - inicio.year
    meses = fim.month - inicio.month
    total = anos * 12 + meses
    if fim.day < inicio.day:
        total -= 1
    return max(total, 0)

def obter_dias_recesso_por_meses(meses: int) -> int:
    if meses < 6:
        return 0
    elif meses == 6:
        return 15
    elif meses <= 7:
        return 18
    elif meses <= 8:
        return 20
    elif meses <= 9:
        return 23
    elif meses <= 10:
        return 25
    elif meses <= 11:
        return 28
    else:
        return 30

def calcular_periodos_recesso(estagiario: Estagiario):
    inicio = estagiario.data_inicio_contrato
    fim = estagiario.data_fim_contrato
    meses = calcular_meses_entre(inicio, fim)
    dias_direito = obter_dias_recesso_por_meses(meses)
    return [{
        "inicio": inicio,
        "fim": fim,
        "meses": meses,
        "dias_direito": dias_direito,
    }]

def montar_texto_conclusao(estagiario: Estagiario, periodos: List[dict]) -> str:
    total = sum(p["dias_direito"] for p in periodos)
    return (
        f"O(A) estagiário(a) {estagiario.nome} faz jus ao total de "
        f"{total} dias de recesso, conforme legislação vigente."
    )

# ============================================================
# 3. LÓGICA NOVA (VBA)
# ============================================================

def calcular_dias_direito(dias_corridos: int) -> int:
    """Tabela oficial de dias de recesso por dias corridos."""
    if dias_corridos < 180:
        return 0
    elif 180 <= dias_corridos <= 209:
        return 15
    elif 210 <= dias_corridos <= 239:
        return 18
    elif 240 <= dias_corridos <= 269:
        return 20
    elif 270 <= dias_corridos <= 299:
        return 23
    elif 300 <= dias_corridos <= 329:
        return 25
    elif 330 <= dias_corridos <= 359:
        return 28
    elif 360 <= dias_corridos <= 366:
        return 30
    else:
        return 0

def montar_ciclos_a_partir_form(contrato_inicio_str: str, contrato_fim_str: str):
    """Divide o contrato em 1 ou 2 ciclos conforme a regra dos 365 dias."""
    inicio = str_to_date_br(contrato_inicio_str)
    fim = str_to_date_br(contrato_fim_str)
    dias_contrato = dias_entre(inicio, fim)

    # Contratos menores que 365 dias têm apenas 1 ciclo
    if dias_contrato < 364:
        ciclo1_inicio = inicio
        ciclo1_fim = fim
        ciclo2_inicio = None
        ciclo2_fim = None
    else:
        ciclo1_inicio = inicio
        ciclo1_fim = inicio + timedelta(days=364)
        ciclo2_inicio = ciclo1_fim + timedelta(days=1)
        ciclo2_fim = fim

    dias_ciclo1 = dias_entre(ciclo1_inicio, ciclo1_fim)
    dias_ciclo2 = dias_entre(ciclo2_inicio, ciclo2_fim) if ciclo2_inicio else 0

    direito_ciclo1 = calcular_dias_direito(dias_ciclo1)
    direito_ciclo2 = calcular_dias_direito(dias_ciclo2)

    return {
        "dias_contrato": dias_contrato,
        "ciclo1": {
            "inicio": ciclo1_inicio,
            "fim": ciclo1_fim,
            "dias_corridos": dias_ciclo1,
            "dias_direito": direito_ciclo1,
        },
        "ciclo2": {
            "inicio": ciclo2_inicio,
            "fim": ciclo2_fim,
            "dias_corridos": dias_ciclo2,
            "dias_direito": direito_ciclo2,
        },
    }

def calcular_nao_gozados(dias_direito: int, dias_usufruidos: Optional[int]) -> int:
    """Calcula dias não gozados considerando o que foi usufruído."""
    if dias_usufruidos is None:
        return dias_direito
    return max(dias_direito - dias_usufruidos, 0)

def montar_texto_conclusao_vba(nome: str, total_nao_gozados: int) -> str:
    """Texto final da Nota Técnica."""
    return (
        f"Após análise dos períodos aquisitivos e de gozo, "
        f"constata-se que o(a) estagiário(a) {nome} possui "
        f"{total_nao_gozados} dias de recesso não usufruídos, "
        f"fazendo jus ao pagamento correspondente."
    )
