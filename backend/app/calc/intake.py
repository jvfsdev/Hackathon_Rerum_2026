"""Consumo de matéria seca (CMS)."""
import math

from .conversions import lcg4


def cms_nrc2001(pv: float, leite: float, gordura_pct: float, semana_lactacao: float) -> float:
    """NRC 2001, vacas em lactação."""
    return (0.372 * lcg4(leite, gordura_pct) + 0.0968 * pv**0.75) * (1 - math.exp(-0.192 * (semana_lactacao + 3.67)))


def cms_brleite(pv: float, leite: float, gordura_pct: float, del_: float) -> float:
    """BR-Leite 2024, Eq. 1.1 (Holandês e Girolando confinados/semiconfinados)."""
    return (lcg4(leite, gordura_pct) * 0.3261 + pv**0.75 * 0.1114) * (1 - math.exp(-0.0134 * (del_ + 92.4786)))


def cms_brleite_cana(pv: float, leite: float, gordura_pct: float, del_: float) -> float:
    """BR-Leite 2024, Eq. 1.2 com cana-de-açúcar como volumoso (Cana = 1)."""
    lcg = lcg4(leite, gordura_pct)
    pv75 = pv**0.75
    return (lcg * 0.2417 + pv75 * 0.1248 + lcg * 0.1517 - pv75 * 0.0191) * (1 - math.exp(-0.0140 * (del_ + 83.4485)))


def cms_preparto(pv: float, pct_pv: float) -> float:
    """Vacas secas/pré-parto: % do PV (NASEM 2021 via Drackley: 1,8–2%)."""
    return pv * pct_pv / 100


def teto_fibra(pv: float, fdn_dieta_pct: float, limite_pct_pv: float) -> float:
    """CMS máximo pelo enchimento: consumo de FDN ≤ limite% do PV (Mertens)."""
    return limite_pct_pv * pv / fdn_dieta_pct


def cms_pct_pv(cms: float, pv: float) -> float:
    return 100 * cms / pv


def cms_nasem2021(pv: float, leite: float, gordura_pct: float, proteina_pct: float, ecc: float, del_: float,
                  fracao_multiparas: float, lactose_pct: float | None = None) -> float:
    """NASEM 2021, equação baseada no animal (ICAR Appendix 2):
    DMI = [(3,7 + Par·5,7) + 0,305·MilkE + 0,022·PV + (−0,689 − 1,87·Par)·ECC] × [1 − (0,212 + Par·0,136)·e^(−0,053·DEL)]
    MilkE = energia do leite (Mcal/d). Par = fração de multíparas no lote (interpolação no lote: escolha de engenharia)."""
    from .energy import ell_leite_por_kg
    par = fracao_multiparas
    milk_e = leite * ell_leite_por_kg(gordura_pct, proteina_pct, lactose_pct)
    base = (3.7 + par * 5.7) + 0.305 * milk_e + 0.022 * pv + (-0.689 - 1.87 * par) * ecc
    return base * (1 - (0.212 + par * 0.136) * math.exp(-0.053 * del_))


def cms_final(equacao: float, ajuste: float = 0.0, teto: float | None = None) -> float:
    """CMS esperado = equação + ajustes (ex.: digestibilidade da FDN), limitado pelo teto de enchimento."""
    valor = equacao + (ajuste or 0.0)
    return min(valor, teto) if teto is not None else valor
