"""Executa os casos de teste com resultado conhecido (tests/cases.yaml) contra a versão atual da base."""
from pathlib import Path

import yaml

from .engine import Motor
from .rules_loader import BaseConhecimento
from .working_memory import MemoriaTrabalho

CASOS = Path(__file__).resolve().parents[2] / "tests" / "cases.yaml"
TODOS_MODULOS = None


def montar_memoria(caso: dict, kb: BaseConhecimento) -> MemoriaTrabalho:
    wm = MemoriaTrabalho()
    for nome, valor in caso.get("fatos", {}).items():
        wm.declarar(nome, valor, cf=1.0, origem="usuario")
    if "dieta" in caso:
        itens = [{"alimento": kb.alimentos[i["alimento"]], "kg_mn": i["kg_mn"]} for i in caso["dieta"]]
        wm.declarar("dieta.itens", itens, cf=1.0, origem="usuario")
    return wm


def executar_caso(caso: dict, kb: BaseConhecimento) -> dict:
    wm = montar_memoria(caso, kb)
    resultado = Motor(kb, caso.get("modulos", TODOS_MODULOS)).executar(wm)
    disparadas = set(resultado.disparadas())
    ativos = {a.regra for a in resultado.alertas if a.status == "ativo"}
    suprimidos = {a.regra for a in resultado.alertas if a.status == "suprimido"}
    falhas = []
    esp = caso.get("espera", {})
    for nome, valor in esp.get("fatos", {}).items():
        obtido = wm.valor(nome)
        if obtido != valor:
            falhas.append(f"{nome}: esperado {valor!r}, obtido {obtido!r}")
    for nome, (valor, tol) in esp.get("aprox", {}).items():
        obtido = wm.valor(nome)
        if obtido is None or abs(obtido - valor) > tol:
            falhas.append(f"{nome}: esperado {valor} ± {tol}, obtido {obtido}")
    for nome, (valor, tol) in esp.get("cf", {}).items():
        f = wm.get(nome)
        if f is None or abs(f.cf - valor) > tol:
            falhas.append(f"CF de {nome}: esperado {valor} ± {tol}, obtido {f.cf if f else None}")
    for nome in esp.get("ausentes", []):
        if nome in wm:
            falhas.append(f"{nome} deveria estar ausente (= {wm.valor(nome)!r})")
    for rid in esp.get("disparadas", []):
        if rid not in disparadas:
            falhas.append(f"regra {rid} deveria disparar")
    for rid in esp.get("nao_disparadas", []):
        if rid in disparadas:
            falhas.append(f"regra {rid} não deveria disparar")
    for rid in esp.get("alertas", []):
        if rid not in ativos:
            falhas.append(f"alerta ativo de {rid} esperado")
    for rid in esp.get("suprimidos", []):
        if rid not in suprimidos:
            falhas.append(f"alerta de {rid} deveria estar suprimido")
    if "so_alertas" in esp and ativos != set(esp["so_alertas"]):
        falhas.append(f"alertas ativos esperados {sorted(esp['so_alertas'])}, obtidos {sorted(ativos)}")
    return {"id": caso["id"], "descricao": caso.get("descricao", ""), "testa": caso.get("testa", ""),
            "passou": not falhas, "falhas": falhas, "disparadas": resultado.disparadas()}


def carregar_casos(caminho: Path = CASOS) -> list[dict]:
    return yaml.safe_load(caminho.read_text(encoding="utf-8"))


def executar_todos(kb: BaseConhecimento) -> dict:
    resultados = [executar_caso(c, kb) for c in carregar_casos()]
    return {"kb_version": kb.versao, "total": len(resultados),
            "passaram": sum(r["passou"] for r in resultados), "resultados": resultados}
