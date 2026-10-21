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


def faixa_bonificacao(valor: float, faixas: list[dict]) -> float:
    """Ajuste (R$/L) da faixa em que o valor cai. Faixa: {"min": x|None, "max": y|None, "rs_l": z} (limites inclusivos)."""
    for f in faixas:
        if (f.get("min") is None or valor >= f["min"]) and (f.get("max") is None or valor <= f["max"]):
            return float(f["rs_l"])
    return 0.0


def bonificacao(laudo: dict, tabela: dict) -> dict:
    """Bonificação/penalização do laticínio por qualidade. laudo: {"ccs": 520, "cbt": 90, "gordura": 3.9, ...};
    tabela: {parametro: [faixas]}. Devolve o total atual, o de cada parâmetro e o máximo possível."""
    por, melhor = {}, 0.0
    for parametro, faixas in tabela.items():
        if not faixas:
            continue
        melhor += max(float(f["rs_l"]) for f in faixas)
        if laudo.get(parametro) is not None:
            por[parametro] = faixa_bonificacao(laudo[parametro], faixas)
    total = sum(por.values())
    return {"total": total, "por_parametro": por, "maximo": melhor, "perda_vs_maximo": melhor - total
            if len(por) == len([f for f in tabela.values() if f]) else None}


def iofc(litros_vaca: float, preco_leite: float, custo_dieta_vaca: float) -> float:
    """Receita do leite menos o custo de TODA a dieta, por vaca/dia (income over feed cost)."""
    return litros_vaca * preco_leite - custo_dieta_vaca


def quadrado_de_pearson(teor_a: float, teor_b: float, alvo: float) -> dict:
    """Mistura de 2 ingredientes para atingir um teor (ex.: % PB): partes de A e B e % de cada na mistura."""
    if not min(teor_a, teor_b) < alvo < max(teor_a, teor_b):
        raise ValueError("o alvo precisa estar entre os teores dos dois ingredientes")
    partes_a, partes_b = abs(teor_b - alvo), abs(teor_a - alvo)
    total = partes_a + partes_b
    return {"partes_a": partes_a, "partes_b": partes_b, "pct_a": 100 * partes_a / total, "pct_b": 100 * partes_b / total}
