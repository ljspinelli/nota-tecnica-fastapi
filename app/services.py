from datetime import date, datetime, timedelta
from typing import List, Optional
from .models import Estagiario, Ciclo


# ============================================================
# 1. UTILIDADES DE DATA
# ============================================================

def str_to_date_br(valor: str) -> date:
    """Converte 'dd/mm/yyyy' para objeto date."""
    return datetime.strptime(valor, "%d/%m/%Y").date()


def dias_entre(inicio: date, fim: date) -> int:
    """Retorna a diferença em dias entre duas datas."""
    return (fim - inicio).days


# ============================================================
# 2. LÓGICA ANTIGA DO SISTEMA (MANTIDA)
# ============================================================

def calcular_meses_entre(inicio: date, fim: date) -> int:
    """Calcula meses completos entre duas datas."""
    anos = fim.year - inicio.year
    meses = fim.month - inicio.month
    total = anos * 12 + meses
    if fim.day < inicio.day:
        total -= 1
    return max(total, 0)


def obter_dias_recesso_por_meses(meses: int) -> int:
    """Tabela antiga de dias de recesso por meses."""
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
    """Cálculo antigo baseado em meses completos."""
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
    """Texto padrão da Nota Técnica (modelo antigo)."""
    total = sum(p["dias_direito"] for p in periodos)
    return (
        f"O(A) estagiário(a) {estagiario.nome} faz jus ao total de "
        f"{total} dias de recesso, conforme legislação vigente."
    )


# ============================================================
# 3. LÓGICA NOVA (TRADUÇÃO DO VBA)
# ============================================================

def calcular_dias_direito(dias_corridos: int) -> int:
    """Tabela de dias de direito baseada no VBA."""
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


def montar_ciclos_a_partir_form(contrato_inicio_str: str, contrato_fim_str: str):
    """
    Reproduz a lógica do VBA para dividir o contrato em:
    - 1º ciclo (até 364 dias)
    - 2º ciclo (restante)
    """
    inicio = str_to_date_br(contrato_inicio_str)
    fim = str_to_date_br(contrato_fim_str)

    dias_contrato = dias_entre(inicio, fim)

    # 1º ciclo
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

    # dias corridos
    dias_ciclo1 = dias_entre(ciclo1_inicio, ciclo1_fim)
    dias_ciclo2 = dias_entre(ciclo2_inicio, ciclo2_fim) if ciclo2_inicio else 0

    # dias de direito
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
    """Calcula dias não gozados conforme VBA."""
    if dias_usufruidos is None:
        return dias_direito
    return max(dias_direito - dias_usufruidos, 0)


# ============================================================
# 4. FUNÇÕES DE SUPORTE PARA NOTA TÉCNICA (NOVO MODELO)
# ============================================================

def montar_texto_conclusao_vba(nome: str, total_nao_gozados: int) -> str:
    """Texto final da Nota Técnica baseado no modelo VBA."""
    return (
        f"Após análise dos períodos aquisitivos e de gozo, "
        f"constata-se que o(a) estagiário(a) {nome} possui "
        f"{total_nao_gozados} dias de recesso não usufruídos, "
        f"fazendo jus ao pagamento correspondente."
    )
# ============================================================
# 5. AUTENTICAÇÃO DE USUÁRIOS (LOGIN)
# ============================================================

from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_senha(senha: str) -> str:
    """Gera hash seguro para senha."""
    return pwd_context.hash(senha)

def verificar_senha(senha: str, senha_hash: str) -> bool:
    """Verifica se a senha corresponde ao hash armazenado."""
    return pwd_context.verify(senha, senha_hash)
