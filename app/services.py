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
