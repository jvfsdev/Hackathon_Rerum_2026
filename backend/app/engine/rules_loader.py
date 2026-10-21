"""Carrega e valida a base de conhecimento (YAML versionado em backend/kb/)."""
from dataclasses import dataclass, field
from pathlib import Path

import yaml

import inspect
import re

from .conditions import OPERADORES, fatos_citados
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


OPS_VALIDOS = set(OPERADORES) | {"existe", "ausente"}
ACOES_VALIDAS = {"concluir", "calcular", "alerta", "suprimir", "rebaixar"}
NIVEIS_VALIDOS = {"critico", "atencao", "informativo"}
# Fatos que entram na memória de trabalho vindos de fora das regras (usuário, registros, laudos, sistema).
PREFIXOS_ENTRADA = ("lote.", "dieta.", "mon.", "laudo.", "fazenda.", "formulacao.", "pl.")
_TEMPLATE = re.compile(r"\{([@a-z_][\w\.]*)(?::[^}]+)?\}")


def validar(kb: BaseConhecimento) -> None:
    """Checagem estática da base. Tudo que quebraria ou silenciaria em execução vira erro ao carregar."""
    erros: list[str] = []
    ids = [r["id"] for r in kb.regras]
    dup = {i for i in ids if ids.count(i) > 1}
    if dup:
        erros.append(f"IDs de regra duplicados: {dup}")
    produzidos = {f for r in kb.regras for f in fatos_concluidos(r)}
    categorias = {a["alerta"].get("categoria", "geral") for r in kb.regras for a in r.get("entao", []) if "alerta" in a}

    def conhecido(fato: str) -> bool:
        return (fato in kb.perguntas or fato.startswith(PREFIXOS_ENTRADA)
                or any(fato == p or fato.startswith(p + ".") for p in produzidos))

    for r in kb.regras:
        rid = r["id"]
        if r.get("modulo") not in ORDEM_MODULOS:
            erros.append(f"{rid}: módulo inválido {r.get('modulo')}")
        if not isinstance(r["cf"], (int, float)) or not -1 <= r["cf"] <= 1:
            erros.append(f"{rid}: cf fora de [-1, 1]: {r['cf']}")
        if not isinstance(r["prioridade"], (int, float)):
            erros.append(f"{rid}: prioridade não numérica")
        for ref in _refs_params(r):
            if ref not in kb.params:
                erros.append(f"{rid}: parâmetro inexistente @params.{ref}")
        for cond in r["se"]:
            erros += [f"{rid}: {e}" for e in _validar_condicao(cond)]
            erros += [f"{rid}: fato desconhecido '{f}' (nenhuma regra conclui, não é pergunta nem entrada)"
                      for f in fatos_citados(cond) if not conhecido(f)]
        for acao in r.get("entao", []):
            tipo = set(acao) & ACOES_VALIDAS
            if len(acao) != 1 or not tipo:
                erros.append(f"{rid}: ação inválida {list(acao)}")
                continue
            spec = acao[next(iter(tipo))]
            if "concluir" in acao and "fato" not in spec:
                erros.append(f"{rid}: concluir sem fato")
            if "calcular" in acao:
                fn = FUNCOES.get(spec.get("funcao"))
                if fn is None:
                    erros.append(f"{rid}: função inexistente {spec.get('funcao')}")
                else:
                    try:
                        inspect.signature(fn).bind(**spec.get("args", {}))
                    except TypeError as e:
                        erros.append(f"{rid}: argumentos de {spec['funcao']} inválidos ({e})")
            if "alerta" in acao:
                if spec.get("nivel", "atencao") not in NIVEIS_VALIDOS:
                    erros.append(f"{rid}: nível de alerta inválido {spec.get('nivel')}")
                for campo in ("titulo", "causa", "acao"):
                    for ref in _TEMPLATE.findall(spec.get(campo, "")):
                        if ref.startswith("@params.") and ref[8:] not in kb.params:
                            erros.append(f"{rid}: {campo} cita @{ref[1:]} inexistente")
                        elif not ref.startswith("@") and not conhecido(ref):
                            erros.append(f"{rid}: {campo} cita fato desconhecido '{ref}'")
            for tipo_sup in ("suprimir", "rebaixar"):
                if tipo_sup in acao:
                    for cat in spec["categorias"]:
                        if cat not in categorias:
                            erros.append(f"{rid}: {tipo_sup} categoria sem alertas '{cat}'")
                    if spec.get("para", "informativo") not in NIVEIS_VALIDOS:
                        erros.append(f"{rid}: nível 'para' inválido")
    if erros:
        raise ValueError("Base de conhecimento inválida:\n  " + "\n  ".join(erros))


def _validar_condicao(cond: dict) -> list[str]:
    if "qualquer" in cond or "todos" in cond:
        return [e for c in cond.get("qualquer", cond.get("todos", [])) for e in _validar_condicao(c)]
    if "fato" not in cond:
        return [f"condição sem fato: {cond}"]
    if cond.get("op", "existe") not in OPS_VALIDOS:
        return [f"operador inválido '{cond.get('op')}' em {cond['fato']}"]
    return []


def _refs_params(obj) -> list[str]:
    if isinstance(obj, str):
        return re.findall(r"@params\.(\w+)", obj)
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
