"""Fatores de certeza no estilo MYCIN."""


def combinar(cf1: float, cf2: float) -> float:
    """Combina dois CFs que sustentam a mesma conclusão."""
    if cf1 >= 0 and cf2 >= 0:
        return cf1 + cf2 * (1 - cf1)
    if cf1 < 0 and cf2 < 0:
        return cf1 + cf2 * (1 + cf1)
    return (cf1 + cf2) / (1 - min(abs(cf1), abs(cf2)))


def propagar(cf_regra: float, cfs_premissas: list[float]) -> float:
    """CF da conclusão = CF da regra × menor CF entre as premissas (conjunção)."""
    return cf_regra * (min(cfs_premissas) if cfs_premissas else 1.0)
