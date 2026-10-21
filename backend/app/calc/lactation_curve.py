"""Curva de lactação: o "esperado" de cada lote."""
import math


def cobuci(t: float) -> float:
    """Cobuci (Rosa et al. 2022, Girolando ¾): Y = 14,0342 − 0,0252 t + ln t. Pico ~dia 40, 16,7 kg."""
    t = max(t, 1.0)
    return 14.0342 - 0.0252 * t + math.log(t)


def wood(t: float, a: float, b: float, c: float) -> float:
    t = max(t, 1.0)
    return a * t**b * math.exp(-c * t)


def esperado_por_vaca(del_medio: float, k_fazenda: float, itu_2d: float | None = None,
                      itu_limiar: float | None = None, perda_por_unidade: float = 0.0) -> float:
    """Leite esperado por vaca: curva × fator da fazenda − perda por calor acima do limiar."""
    esperado = cobuci(del_medio) * k_fazenda
    if itu_2d is not None and itu_limiar is not None:
        esperado -= perda_por_unidade * max(0.0, itu_2d - itu_limiar)
    return esperado


def ajustar_k(observacoes: list[tuple[float, float]]) -> float:
    """Fator de escala da fazenda por mínimos quadrados: k = Σ y·f / Σ f², com (DEL, L/vaca)."""
    num = sum(y * cobuci(t) for t, y in observacoes)
    den = sum(cobuci(t) ** 2 for t, _ in observacoes)
    return num / den if den else 1.0
