"""Indicadores econômicos por lote."""
import math


def litros_por_kg_concentrado(litros: float, kg_concentrado: float) -> float | None:
    return litros / kg_concentrado if kg_concentrado else None


def custo_concentrado_por_litro(kg_concentrado: float, preco_conc: float, litros: float) -> float | None:
    return kg_concentrado * preco_conc / litros if litros else None


def margem_sobre_concentrado(litros: float, preco_leite: float, kg_concentrado: float, preco_conc: float) -> float:
    return litros * preco_leite - kg_concentrado * preco_conc


def resposta_marginal(litros_antes: float, litros_depois: float, conc_antes: float, conc_depois: float) -> float | None:
    """ΔL/Δkg de concentrado (por vaca) após uma mudança."""
    delta_c = conc_depois - conc_antes
    return (litros_depois - litros_antes) / delta_c if delta_c else None


def razao_precos(preco_conc: float, preco_leite: float) -> float:
    """R = P_conc / P_leite: litros que 1 kg de concentrado precisa gerar para se pagar."""
    return preco_conc / preco_leite


_PERDA_CCS = [(200, 0.0), (500, 6.0), (1000, 18.0), (1500, 29.0)]


def perda_producao_ccs_pct(ccs_mil: float) -> float:
    """Perda de produção do rebanho (%) pela CCS do tanque, interpolada em log (eXtension DHI)."""
    if ccs_mil <= _PERDA_CCS[0][0]:
        return 0.0
    for (c0, p0), (c1, p1) in zip(_PERDA_CCS, _PERDA_CCS[1:]):
        if ccs_mil <= c1:
            return p0 + (p1 - p0) * (math.log(ccs_mil) - math.log(c0)) / (math.log(c1) - math.log(c0))
    (c0, p0), (c1, p1) = _PERDA_CCS[-2], _PERDA_CCS[-1]
    return p1 + (p1 - p0) * (math.log(ccs_mil) - math.log(c1)) / (math.log(c1) - math.log(c0))


def media_geometrica(valores: list[float]) -> float:
    return math.exp(sum(math.log(v) for v in valores) / len(valores))
