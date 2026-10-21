"""Ambiente."""


def itu(temp_c: float, ur_pct: float) -> float:
    """ITU = 0,8 T + UR/100 (T − 14,4) + 46,4 (T em °C, UR em %)."""
    return 0.8 * temp_c + ur_pct / 100 * (temp_c - 14.4) + 46.4


def itu_negri(temp_c: float, ur_pct: float) -> float:
    """Fórmula usada por Negri et al. 2021 (Holandesas de MG)."""
    return (1.8 * temp_c + 32) - (0.55 - 0.0055 * ur_pct) * (1.8 * temp_c - 26)
