"""Avaliação das condições (SE) das regras e resolução de valores."""
from typing import Any

from .working_memory import MemoriaTrabalho

FALTA = object()


class Resolvedor:
    """Resolve literais, `@params.nome` e `$fato` (com `$fato|padrão` opcional)."""

    def __init__(self, wm: MemoriaTrabalho, params: dict):
        self.wm, self.params = wm, params

    def valor(self, expr: Any, usados: list | None = None) -> Any:
        if isinstance(expr, list):
            return [self.valor(e, usados) for e in expr]
        if not isinstance(expr, str):
            return expr
        if expr.startswith("@params."):
            nome = expr[len("@params."):]
            if nome not in self.params:
                raise KeyError(f"parâmetro inexistente: {nome}")
            return self.params[nome]["valor"]
        if expr.startswith("$"):
            nome, _, padrao = expr[1:].partition("|")
            f = self.wm.get(nome)
            if f is None:
                return self.valor(_literal(padrao), usados) if padrao else FALTA
            if usados is not None:
                usados.append(f)
            return f.valor
        return expr


def _literal(txt: str) -> Any:
    if txt.startswith("@") or txt.startswith("$"):
        return txt
    for conv in (int, float):
        try:
            return conv(txt)
        except ValueError:
            pass
    return {"true": True, "false": False, "null": None}.get(txt, txt)


OPERADORES = {
    "=": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    ">": lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
    "in": lambda a, b: a in b,
    "nao_in": lambda a, b: a not in b,
    "entre": lambda a, b: b[0] <= a <= b[1],
    "contem": lambda a, b: b in a,
}


def avaliar(cond: dict, res: Resolvedor) -> tuple[bool, list[dict], list[str]]:
    """Retorna (casou, premissas usadas, fatos faltantes)."""
    if "qualquer" in cond:
        faltas = []
        for sub in cond["qualquer"]:
            ok, usadas, f = avaliar(sub, res)
            if ok:
                return True, usadas, []
            faltas += f
        return False, [], faltas
    if "todos" in cond:
        usadas_tot, faltas = [], []
        for sub in cond["todos"]:
            ok, usadas, f = avaliar(sub, res)
            if not ok:
                return False, [], f
            usadas_tot += usadas
        return True, usadas_tot, faltas

    nome, op = cond["fato"], cond.get("op", "existe")
    fato = res.wm.get(nome)
    if op == "ausente":
        return fato is None, [{"fato": nome, "op": op, "esperado": None, "valor": None, "cf": 1.0}], []
    if fato is None:
        return False, [], [nome]
    if op == "existe":
        return True, [_premissa(nome, op, None, fato)], []
    usados: list = []
    esperado = res.valor(cond.get("valor"), usados)
    if esperado is FALTA or (isinstance(esperado, list) and FALTA in esperado):
        refs = cond["valor"] if isinstance(cond["valor"], list) else [cond["valor"]]
        return False, [], [r[1:].partition("|")[0] for r in refs if isinstance(r, str) and r.startswith("$")]
    try:
        ok = bool(OPERADORES[op](fato.valor, esperado))
    except TypeError:
        ok = False
    premissas = [_premissa(nome, op, esperado, fato)] + [_premissa(u.nome, "ref", None, u) for u in usados]
    return ok, premissas if ok else [], []


def _premissa(nome, op, esperado, fato) -> dict:
    return {"fato": nome, "op": op, "esperado": esperado, "valor": fato.valor, "cf": fato.cf}


def fatos_citados(cond: dict) -> list[str]:
    """Todos os fatos citados numa condição (para encadeamento regressivo)."""
    if "qualquer" in cond:
        return [f for c in cond["qualquer"] for f in fatos_citados(c)]
    if "todos" in cond:
        return [f for c in cond["todos"] for f in fatos_citados(c)]
    out = [cond["fato"]]
    v = cond.get("valor")
    if isinstance(v, str) and v.startswith("$"):
        out.append(v[1:].partition("|")[0])
    return out
