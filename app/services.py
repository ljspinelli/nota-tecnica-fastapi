from datetime import date
from typing import List
from .models import Estagiario, Ciclo


# ---------------------------------------------------------
# Cálculo de meses entre duas datas
# ---------------------------------------------------------
def calcular_meses_entre(inicio: date, fim: date) -> int:
    anos = fim.year - inicio.year
    meses = fim.month - inicio.month
    total = anos * 12 + meses

    # Se o dia final é maior que o inicial, conta como mês cheio
    if fim.day > inicio.day:
        total += 1

    return total


# ---------------------------------------------------------
# Dias de recesso conforme meses trabalhados
# ---------------------------------------------------------
def obter_dias_recesso_por_meses(meses: int) -> int:
    if meses <= 6:
        return 15
    elif meses <= 12:
        return 30
    return 30


# ---------------------------------------------------------
# Cálculo dos períodos de recesso (com blindagem)
# ---------------------------------------------------------
def calcular_periodos_recesso(estagiario: Estagiario):
    periodos = []

    # 🔒 Blindagem: garantir que estagiario.ciclos existe e é lista
    ciclos = getattr(estagiario, "ciclos", [])
    if not isinstance(ciclos, list):
        ciclos = []

    for ciclo in ciclos:
        meses = calcular_meses_entre(ciclo.data_inicio, ciclo.data_fim)
        dias_direito = obter_dias_recesso_por_meses(meses)
        dias_nao_gozados = max(dias_direito - ciclo.dias_gozados, 0)

        periodo = {
            "periodo_aquisitivo_inicio": ciclo.data_inicio,
            "periodo_aquisitivo_fim": ciclo.data_fim,
            "dias_direito": dias_direito,
            "dias_gozados": ciclo.dias_gozados,
            "dias_nao_gozados": dias_nao_gozados,
        }

        periodos.append(periodo)

    return periodos


# ---------------------------------------------------------
# Montagem do texto de conclusão
# ---------------------------------------------------------
def montar_texto_conclusao(estagiario: Estagiario, periodos: List[dict]) -> str:
    if not periodos:
        return (
            f"Conclui-se que o(a) ex-estagiário(a) {estagiario.nome} "
            f"não possui períodos de recesso registrados."
        )

    linhas = []
    for p in periodos:
        linhas.append(
            f"{p['periodo_aquisitivo_inicio'].strftime('%d/%m/%Y')} a "
            f"{p['periodo_aquisitivo_fim'].strftime('%d/%m/%Y')} – "
            f"{p['dias_nao_gozados']} dias"
        )

    corpo = " | ".join(linhas)

    return (
        f"Conclui-se que o(a) ex-estagiário(a) {estagiario.nome} faz jus ao recebimento "
        f"dos dias de recesso não gozados referentes aos períodos: {corpo}."
    )

from datetime import datetime, date
from typing import Optional


def str_to_date_br(valor: str) -> date:
    return datetime.strptime(valor, "%d/%m/%Y").date()


def dias_entre(inicio: date, fim: date) -> int:
    return (fim - inicio).days


def calcular_dias_direito(dias_corridos: int) -> int:
    if dias_corridos < 180:
        return 0
    elif dias_corridos == 180:
        return 15
    elif dias_corridos <= 210:
        return 18
    elif dias_corridos <= 240:
        return 20
    elif dias_corridos <= 270:
        return 23
    elif dias_corridos <= 300:
        return 25
    elif dias_corridos <= 330:
        return 28
    elif dias_corridos <= 366:
        return 30
    return 0


def montar_ciclos_a_partir_form(
    contrato_inicio_str: str,
    contrato_fim_str: str,
) -> dict:
    """
    Reproduz a lógica do VBA para:
    - TextBox6 (início contrato)
    - TextBox7 (fim contrato)
    - TextBox10, 12, 11, 13
    - TextBox14, 15
    - TextBox16, 17
    """
    inicio = str_to_date_br(contrato_inicio_str)
    fim = str_to_date_br(contrato_fim_str)
    dias_corridos = dias_entre(inicio, fim)

    # TextBox22: dias de contrato
    dias_contrato = dias_corridos

    # 1º ciclo
    if dias_corridos < 364:
        ciclo1_inicio = inicio
        ciclo1_fim = fim
        ciclo2_inicio = None
        ciclo2_fim = None
    else:
        ciclo1_inicio = inicio
        ciclo1_fim = inicio.replace() + (fim - inicio).__class__(364)  # 364 dias
        ciclo2_inicio = ciclo1_fim + (fim - fim.__class__(1))  # +1 dia
        ciclo2_fim = fim

    # dias corridos por ciclo
    dias_ciclo1 = dias_entre(ciclo1_inicio, ciclo1_fim) if ciclo1_fim else 0
    dias_ciclo2 = dias_entre(ciclo2_inicio, ciclo2_fim) if ciclo2_inicio and ciclo2_fim else 0

    # dias de direito por ciclo
    direito_ciclo1 = calcular_dias_direito(dias_ciclo1) if ciclo1_fim else 0
    direito_ciclo2 = calcular_dias_direito(dias_ciclo2) if ciclo2_fim else 0

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
    if dias_usufruidos is None:
        return dias_direito
    return max(dias_direito - dias_usufruidos, 0)
