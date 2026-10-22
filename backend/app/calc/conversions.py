"""Conversões básicas usadas em toda a base."""


def mn_para_ms(kg_mn: float, ms_pct: float) -> float:
    """kg de matéria natural → kg de matéria seca."""
    return kg_mn * ms_pct / 100


def ms_para_mn(kg_ms: float, ms_pct: float) -> float:
    """kg de matéria seca → kg de matéria natural."""
    return kg_ms / (ms_pct / 100)


def lcg4(leite_kg: float, gordura_pct: float) -> float:
    """Leite corrigido para 4% de gordura (Gaines 1928; NRC 2001 e BR-Leite)."""
    return leite_kg * (0.4 + 0.15 * gordura_pct)


def ecm(leite_kg: float, gordura_pct: float, proteina_pct: float) -> float:
    """Leite corrigido para energia (Penn State): 12,82 G + 7,13 P + 0,323 L (kg)."""
    return 12.82 * leite_kg * gordura_pct / 100 + 7.13 * leite_kg * proteina_pct / 100 + 0.323 * leite_kg


def ureia_para_nul(ureia_mg_dl: float) -> float:
    """Ureia no leite (mg/dL) → nitrogênio ureico (NUL, mg/dL)."""
    return ureia_mg_dl * 0.4667


def ndt_para_ell(ndt_pct: float) -> float:
    """NDT (% MS) → ELl (Mcal/kg MS): conversão linear do NRC 1989 (desconto fixo de 8%; o NRC 2001 passa por ED/EM)."""
    return 0.0245 * ndt_pct - 0.12
