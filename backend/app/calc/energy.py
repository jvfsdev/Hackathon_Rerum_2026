"""Exigências de energia líquida de lactação (ELl, Mcal/dia)."""


def mantenca(pv: float, k: float) -> float:
    """k × PV^0,75; k = 0,08 (NRC 2001) ou 0,10 (NASEM 2021)."""
    return k * pv**0.75


def ell_leite_por_kg(gordura_pct: float, proteina_pct: float, lactose_pct: float | None = None) -> float:
    """NRC 2001. Sem lactose medida usa a constante 0,192."""
    if lactose_pct is None:
        return 0.0929 * gordura_pct + 0.0547 * proteina_pct + 0.192
    return 0.0929 * gordura_pct + 0.0547 * proteina_pct + 0.0395 * lactose_pct


def gestacao(dias_gestacao: float, peso_bezerro: float) -> float:
    """NRC 2001 (Bell & Ehrhardt): zero antes de 190 dias."""
    if dias_gestacao < 190:
        return 0.0
    return (0.00318 * dias_gestacao - 0.0352) * (peso_bezerro / 45) / 0.218


def crescimento_primiparas(mantenca_mcal: float, fracao_primiparas: float, acrescimo: float) -> float:
    """Acréscimo de mantença para primíparas, ponderado pela fração delas no lote."""
    return mantenca_mcal * acrescimo * fracao_primiparas


def atividade_pastejo(pv: float, distancia_km: float, relevo: str) -> float:
    """NRC 2001: 0,00045·PV·km + 0,0012·PV; terreno acidentado soma 0,006·PV.

    Reproduz os valores tabelados (450 kg, plano, 0,4 km ≈ 0,6 Mcal; 635 kg, acidentado, 3,2 km ≈ 5,5 Mcal).
    Ondulado usa metade do acréscimo de acidentado (escolha de engenharia).
    """
    base = 0.00045 * pv * distancia_km + 0.0012 * pv
    extra = {"plano": 0.0, "ondulado": 0.003, "acidentado": 0.006}.get(relevo, 0.0)
    return base + extra * pv


def ajuste_ecc(ecc_atual: float, ecc_meta: float, dias: float, mcal_por_ponto: float) -> float:
    """Energia/dia para levar o ECC à meta (Penn State: ~417 Mcal por ponto). Negativo = mobilização."""
    if dias <= 0:
        return 0.0
    return mcal_por_ponto * (ecc_meta - ecc_atual) / dias


def soma(*partes: float | None) -> float:
    return sum(p for p in partes if p is not None)
