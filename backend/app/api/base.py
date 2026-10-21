"""Base de conhecimento: regras, parâmetros (edição pelo especialista), alimentos, casos de teste e clima."""
import re
from datetime import date

import httpx
import yaml
from fastapi import APIRouter, HTTPException

from .. import services
from ..db.models import Fazenda, sessao
from ..engine.casos import executar_todos
from .schemas import ParametroUpdate

router = APIRouter()


@router.get("/kb")
def resumo():
    kb = services.kb()
    modulos: dict[str, int] = {}
    for r in kb.regras:
        modulos[r["modulo"]] = modulos.get(r["modulo"], 0) + 1
    return {"versao": kb.versao, "regras": len(kb.regras), "parametros": len(kb.params),
            "alimentos": len(kb.alimentos), "modulos": modulos,
            "changelog": (kb.diretorio / "CHANGELOG.md").read_text(encoding="utf-8")}


@router.get("/kb/regras")
def regras():
    return services.kb().regras


@router.get("/kb/parametros")
def parametros():
    return services.kb().params


@router.get("/kb/perguntas")
def perguntas():
    return services.kb().perguntas


@router.get("/alimentos")
def alimentos():
    return list(services.kb().alimentos.values())


@router.post("/kb/testes")
def rodar_testes():
    return executar_todos(services.kb())


def _subir_versao(versao: str) -> str:
    maior, menor, patch = (int(x) for x in versao.split("."))
    return f"{maior}.{menor}.{patch + 1}"


@router.put("/kb/parametros/{nome}")
def editar_parametro(nome: str, dados: ParametroUpdate):
    """Aquisição de conhecimento: o especialista muda um limiar → nova versão da base → casos de teste rodam."""
    kb = services.kb()
    if nome not in kb.params:
        raise HTTPException(404, "parâmetro inexistente")
    p = kb.params[nome]
    if not p.get("editavel") or not isinstance(p["valor"], (int, float)) or isinstance(p["valor"], bool):
        raise HTTPException(400, "parâmetro não editável por aqui")
    arq = kb.diretorio / "params.yaml"
    texto = arq.read_text(encoding="utf-8")
    padrao = re.compile(rf"^({re.escape(nome)}: \{{valor: )([^,]+)(,)", re.M)
    if not padrao.search(texto):
        raise HTTPException(500, "linha do parâmetro não encontrada")
    antigo = p["valor"]
    arq.write_text(padrao.sub(lambda m: f"{m.group(1)}{dados.valor}{m.group(3)}", texto), encoding="utf-8")
    nova = _subir_versao(kb.versao)
    (kb.diretorio / "kb.yaml").write_text(
        "# Versão da base de conhecimento. Suba a versão a cada mudança de regra/parâmetro e anote em CHANGELOG.md.\n"
        f'kb_version: "{nova}"\n', encoding="utf-8")
    log = kb.diretorio / "CHANGELOG.md"
    titulo, _, resto = log.read_text(encoding="utf-8").partition("\n\n")
    entrada = f"## {nova} — {date.today():%d/%m/%Y}\n- Parâmetro `{nome}`: {antigo} → {dados.valor}. {dados.motivo}".rstrip()
    log.write_text(f"{titulo}\n\n{entrada}\n\n{resto}", encoding="utf-8")
    kb = services.recarregar_kb()
    return {"versao": kb.versao, "parametro": nome, "antes": antigo, "depois": dados.valor, "testes": executar_todos(kb)}


@router.get("/clima/{fazenda_id}")
def clima(fazenda_id: int):
    """Temperatura e umidade atuais (Open-Meteo); sem internet, o usuário digita manualmente."""
    with sessao() as s:
        faz = s.get(Fazenda, fazenda_id)
    if not faz or faz.latitude is None:
        return {"disponivel": False}
    try:
        r = httpx.get("https://api.open-meteo.com/v1/forecast", timeout=3,
                      params={"latitude": faz.latitude, "longitude": faz.longitude,
                              "current": "temperature_2m,relative_humidity_2m"})
        atual = r.json()["current"]
        return {"disponivel": True, "temp": atual["temperature_2m"], "ur": atual["relative_humidity_2m"], "fonte": "Open-Meteo"}
    except Exception:  # noqa: BLE001 — offline-first: falha de rede vira entrada manual
        return {"disponivel": False}
