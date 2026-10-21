"""Séries diárias por lote: esperado × observado, resíduo, detectores com persistência."""
import statistics
from datetime import timedelta

_um_dia = timedelta(days=1)


def residuo_relativo(observado: float, esperado: float) -> float:
    """(obs − esp) / esp."""
    return (observado - esperado) / esperado if esperado else 0.0


def sigma_robusto(valores: list[float]) -> float:
    """MAD × 1,4826 (estimador robusto do desvio-padrão)."""
    if len(valores) < 3:
        return 0.0
    med = statistics.median(valores)
    return 1.4826 * statistics.median(abs(v - med) for v in valores)


def padronizar(residuos: list[float], janela: int = 45, piso: float = 0.02) -> list[float]:
    """Resíduo padronizado de cada dia usando o sigma robusto dos dias anteriores (piso evita dividir por ~0)."""
    z = []
    for i, r in enumerate(residuos):
        hist = residuos[max(0, i - janela):i]
        s = max(sigma_robusto(hist), piso)
        z.append(r / s)
    return z


def ewma(valores: list[float], lam: float, limite_z: float = 3.5) -> list[float]:
    """EWMA sobre a série padronizada. Cada z é limitado a ±limite_z para um único dia anômalo (erro de registro)
    não cruzar o limite sozinho — dia isolado é papel do Shewhart (ACP-D01), não de queda sustentada."""
    out, atual = [], 0.0
    for v in valores:
        atual = lam * max(-limite_z, min(limite_z, v)) + (1 - lam) * atual
        out.append(atual)
    return out


def limite_ewma(lam: float, L: float) -> float:
    """Limite assintótico do EWMA para série padronizada."""
    return L * (lam / (2 - lam)) ** 0.5


def cusum_negativo(z: list[float], k: float) -> list[float]:
    """CUSUM unilateral para quedas sobre série padronizada."""
    out, s = [], 0.0
    for v in z:
        s = max(0.0, s - v - k)
        out.append(s)
    return out


def corrida_abaixo(pontos: list[tuple], ate, limiar: float = -0.02, janela: int = 14) -> tuple[int, float]:
    """Dias consecutivos de calendário, terminando em `ate`, com resíduo abaixo de `limiar` (ruído não conta),
    olhando no máximo `janela` dias; devolve (dias, pior resíduo nessa corrida). Dia sem dado quebra a corrida."""
    por_dia = dict(pontos)
    dias, pior = 0, 0.0
    for i in range(janela):
        r = por_dia.get(ate - _um_dia * i)
        if r is None or r >= limiar:
            break
        dias += 1
        pior = min(pior, r)
    return dias, pior


def mediana_janela(pontos: list[tuple], inicio, fim) -> float | None:
    """Mediana dos valores com data em [inicio, fim] (robusta a um dia anômalo)."""
    vals = [v for d, v in pontos if inicio <= d <= fim]
    return statistics.median(vals) if vals else None


def media_movel(valores: list[float], n: int) -> float | None:
    vals = [v for v in valores[-n:] if v is not None]
    return sum(vals) / len(vals) if vals else None
