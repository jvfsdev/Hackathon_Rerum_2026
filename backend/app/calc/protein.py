"""Proteína."""


def pm_leite(leite: float, proteina_pct: float, eficiencia: float = 0.67) -> float:
    """Proteína metabolizável para leite (g/d), NRC 2001."""
    return 10 * leite * proteina_pct / eficiencia


def pm_gestacao(dias_gestacao: float, peso_bezerro: float, inicio: float = 190) -> float:
    """PM de gestação (g/d), NRC 2001; zero antes do início da exigência (190 dias)."""
    if dias_gestacao < inicio:
        return 0.0
    return (0.69 * dias_gestacao - 69.2) * (peso_bezerro / 45) / 0.33


def interpolar(x: float, pontos: list[list[float]]) -> float:
    """Interpolação linear numa tabela [[x, y], ...] ordenada, com saturação nas pontas."""
    if x <= pontos[0][0]:
        return pontos[0][1]
    for (x0, y0), (x1, y1) in zip(pontos, pontos[1:]):
        if x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return pontos[-1][1]


def pb_alvo(leite: float, tabela: list[list[float]]) -> float:
    """PB alvo (% MS) por produção, a partir da tabela da base (MSD Vet Manual)."""
    return interpolar(leite, tabela)
