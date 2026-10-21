"""Módulo de explicação: "como?" (derivação de uma conclusão) e "por quê?" (por que um dado é pedido)."""
from .engine import Motor, Resultado, _resumo
from .rules_loader import fatos_concluidos, fatos_requeridos


def como(resultado: Resultado, fato: str, profundidade: int = 6) -> dict:
    """Árvore de derivação do fato a partir do traço de inferência."""
    f = resultado.wm.get(fato)
    if f is None:
        return {"fato": fato, "conhecido": False}
    no = {"fato": fato, "valor": _resumo(f.valor), "cf": round(f.cf, 3), "origem": f.origem, "nota": f.nota}
    if f.origem != "regra" or profundidade == 0:
        return no
    no["regras"] = []
    for rid in f.regra.split("+"):
        entrada = next((t for t in resultado.traco if t["regra"] == rid), None)
        if entrada is None:
            continue
        no["regras"].append({
            "regra": rid, "descricao": entrada["descricao"], "cf_regra": entrada["cf_regra"],
            "fonte": entrada["fonte"], "forca": entrada["forca"],
            "premissas": [como(resultado, p["fato"], profundidade - 1) | {"op": p["op"], "esperado": p["esperado"]}
                          for p in entrada["premissas"] if p["op"] != "ausente"],
            "calculo": next((a for a in entrada["acoes"] if a.get("tipo") == "calcular" and
                             (a["fato"] == fato or fato.startswith(a["fato"] + "."))), None),
        })
    return no


def como_texto(arvore: dict, nivel: int = 0) -> list[str]:
    """Versão em linhas de texto da árvore (para docs e testes)."""
    pad = "  " * nivel
    linhas = [f"{pad}{arvore['fato']} = {arvore.get('valor')} (CF {arvore.get('cf')}, {arvore.get('origem')})"]
    for r in arvore.get("regras", []):
        linhas.append(f"{pad}  ← {r['regra']}: {r['descricao']} [fonte: {r['fonte']}; força {r['forca']}]")
        for p in r["premissas"]:
            linhas += como_texto(p, nivel + 2)
    return linhas


def por_que(motor: Motor, fato: str, objetivo: str) -> list[dict]:
    """Cadeia de regras que liga o dado pedido ao objetivo da consulta."""
    caminho = _caminho(motor, fato, objetivo, set())
    return [{"regra": r["id"], "descricao": r.get("descricao", ""), "fonte": r.get("fonte", "")} for r in caminho or []]


def _caminho(motor, fato, objetivo, visitados):
    if fato == objetivo:
        return []
    for regra in motor.regras:
        if regra["id"] in visitados or fato not in fatos_requeridos(regra):
            continue
        for concluido in fatos_concluidos(regra):
            sub = _caminho(motor, concluido, objetivo, visitados | {regra["id"]})
            if sub is not None:
                return [regra] + sub
            if objetivo.startswith(concluido + "."):
                return [regra]
    return None


def resultado_de_dict(dados: dict) -> Resultado:
    """Reconstrói um Resultado salvo (sessão de inferência) para explicar depois."""
    from .facts import Fato
    from .working_memory import MemoriaTrabalho
    wm = MemoriaTrabalho()
    for nome, f in dados.get("fatos", {}).items():
        wm.fatos[nome] = Fato(nome, f["valor"], f["cf"], f["origem"], f.get("regra"), f.get("ciclo", 0), f.get("nota"))
    return Resultado(wm, traco=dados.get("traco", []), kb_version=dados.get("kb_version", ""))


def explicar_regra(resultado: Resultado, regra_id: str) -> dict | None:
    """Entrada do traço de uma regra + árvore "como?" de cada premissa (usado para explicar um alerta)."""
    entrada = next((t for t in resultado.traco if t["regra"] == regra_id), None)
    if entrada is None:
        return None
    return entrada | {"arvores": [como(resultado, p["fato"]) | {"op": p["op"], "esperado": p["esperado"]}
                                  for p in entrada["premissas"] if p["op"] != "ausente"]}
