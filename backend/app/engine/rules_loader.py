"""Carrega e valida a base de conhecimento (YAML versionado em backend/kb/)."""
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .conditions import fatos_citados
from .registry import FUNCOES

KB_DIR = Path(__file__).resolve().parents[2] / "kb"

ORDEM_MODULOS = {"classificacao": 1, "exigencias": 2, "verificacao": 3, "formulacao": 3,
                 "acompanhamento_diario": 4, "acompanhamento_semanal": 4, "acompanhamento_mensal": 4, "meta": 5}


@dataclass
class BaseConhecimento:
    versao: str
    regras: list[dict]
    params: dict
    alimentos: dict
    perguntas: dict
    diretorio: Path = field(default=KB_DIR)

    def regra(self, rid: str) -> dict | None:
        return next((r for r in self.regras if r["id"] == rid), None)


def carregar(diretorio: Path = KB_DIR) -> BaseConhecimento:
    meta = yaml.safe_load((diretorio / "kb.yaml").read_text(encoding="utf-8"))
    params = yaml.safe_load((diretorio / "params.yaml").read_text(encoding="utf-8"))
    alimentos = {a["id"]: a for a in yaml.safe_load((diretorio / "foods.yaml").read_text(encoding="utf-8"))}
    perguntas = yaml.safe_load((diretorio / "perguntas.yaml").read_text(encoding="utf-8"))
    regras = []
    for arq in sorted((diretorio / "rules").glob("*.yaml")):
        for r in yaml.safe_load(arq.read_text(encoding="utf-8")) or []:
            r.setdefault("prioridade", 50)
            r.setdefault("cf", 1.0)
            r.setdefault("se", [])
            r["arquivo"] = arq.name
            regras.append(r)
    kb = BaseConhecimento(meta["kb_version"], regras, params, alimentos, perguntas, diretorio)
    validar(kb)
    return kb


def validar(kb: BaseConhecimento) -> None:
    ids = [r["id"] for r in kb.regras]
    dup = {i for i in ids if ids.count(i) > 1}
    if dup:
        raise ValueError(f"IDs de regra duplicados: {dup}")
    for r in kb.regras:
        if r.get("modulo") not in ORDEM_MODULOS:
            raise ValueError(f"{r['id']}: módulo inválido {r.get('modulo')}")
        for ref in _refs_params(r):
            if ref not in kb.params:
                raise ValueError(f"{r['id']}: parâmetro inexistente @params.{ref}")
        for acao in r.get("entao", []):
            if "calcular" in acao and acao["calcular"]["funcao"] not in FUNCOES:
                raise ValueError(f"{r['id']}: função inexistente {acao['calcular']['funcao']}")


def _refs_params(obj) -> list[str]:
    if isinstance(obj, str):
        out = []
        for parte in obj.replace("|", " ").split():
            if parte.startswith("@params."):
                out.append(parte[len("@params."):])
        return out
    if isinstance(obj, dict):
        return [x for v in obj.values() for x in _refs_params(v)]
    if isinstance(obj, list):
        return [x for v in obj for x in _refs_params(v)]
    return []


def fatos_concluidos(regra: dict) -> list[str]:
    """Fatos (ou prefixos) que a regra conclui."""
    out = []
    for acao in regra.get("entao", []):
        if "concluir" in acao:
            out.append(acao["concluir"]["fato"])
        if "calcular" in acao:
            out.append(acao["calcular"]["fato"])
    return out


def fatos_requeridos(regra: dict) -> list[str]:
    """Fatos citados nas condições e nos argumentos obrigatórios das ações."""
    out = [f for c in regra.get("se", []) for f in fatos_citados(c)]
    for acao in regra.get("entao", []):
        if "calcular" in acao:
            for v in acao["calcular"].get("args", {}).values():
                for item in v if isinstance(v, list) else [v]:
                    if isinstance(item, str) and item.startswith("$"):
                        out.append(item[1:].partition("|")[0])
    return out
