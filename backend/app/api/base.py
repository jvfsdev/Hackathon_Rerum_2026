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
    opcoes = [o.strip() for o in str(p.get("unidade", "")).split("|")] if isinstance(p["valor"], str) else None
    numerico = isinstance(p["valor"], (int, float)) and not isinstance(p["valor"], bool)
    if not p.get("editavel") or not (numerico or opcoes):
        raise HTTPException(400, "parâmetro não editável por aqui")
    if opcoes and dados.valor not in opcoes:
        raise HTTPException(422, f"valor deve ser um de: {', '.join(opcoes)}")
    if numerico:
        try:
            dados.valor = float(dados.valor)
        except (TypeError, ValueError):
            raise HTTPException(422, "valor numérico inválido")
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


@router.get("/referencias")
def referencias():
    """Situação dos preços de referência: cotação vigente de cada item, idade, fonte e a última coleta."""
    from ..db.models import sessao as abrir
    from ..referencias import coletor
    from ..referencias.fontes import FONTES_POR_ITEM
    with abrir() as s:  # noqa: F841
        vig = coletor.vigentes(s)
        ult = coletor.ultima_coleta(s)
        itens = []
        for aid, a in list(services.kb().alimentos.items()) + [("leite", {"nome": "Leite ao produtor"})]:
            ref = vig.get(aid)
            idade = (date.today() - ref.data_cotacao).days if ref else None
            limite = max((f.idade_maxima_dias for f in coletor.FONTES if aid in f.itens), default=7)
            itens.append({"id": aid, "nome": a["nome"], "fontes": FONTES_POR_ITEM.get(aid, []),
                          "vigente": ref.model_dump() if ref else None, "idade_dias": idade, "idade_maxima": limite,
                          "situacao": "sem fonte pública" if not FONTES_POR_ITEM.get(aid) else
                                      ("aguardando coleta" if ref is None else ("atual" if idade <= limite else "desatualizado"))})
        return {"itens": itens, "ultima_coleta": ult.model_dump() if ult else None,
                "fontes": [{"nome": f.nome, "url": f.url, "itens": f.itens, "frequencia": f.frequencia,
                            "idade_maxima_dias": f.idade_maxima_dias} for f in coletor.FONTES]}


@router.post("/referencias/atualizar")
def atualizar_referencias():
    from ..db.models import sessao as abrir
    from ..referencias import coletor, fontes  # noqa: F401 — registra as fontes
    with abrir() as s:
        return coletor.coletar(s)


@router.get("/ferramentas/pearson")
def pearson(teor_a: float, teor_b: float, alvo: float):
    """Quadrado de Pearson: mistura de 2 ingredientes para atingir um teor (ex.: % de PB do concentrado)."""
    from ..calc.economics import quadrado_de_pearson
    try:
        return quadrado_de_pearson(teor_a, teor_b, alvo)
    except ValueError as e:
        raise HTTPException(422, str(e))


@router.get("/clima/{fazenda_id}")
def clima(fazenda_id: int, data: date | None = None):
    """Temperatura e umidade MÉDIAS do dia (o ITU das regras usa a média diária), da Open-Meteo, pela localização
    da fazenda; também a leitura atual, só informativa. Sem internet → disponivel=false (o usuário digita)."""
    from ..calc.climate import itu
    data = data or date.today()
    with sessao() as s:
        faz = s.get(Fazenda, fazenda_id)
    if not faz or faz.latitude is None or faz.longitude is None:
        return {"disponivel": False, "motivo": "fazenda sem localização cadastrada"}
    if data > date.today() or (date.today() - data).days > 90:
        return {"disponivel": False, "motivo": "a meteorologia cobre só os últimos 90 dias"}
    try:
        r = httpx.get("https://api.open-meteo.com/v1/forecast", timeout=5, params={
            "latitude": faz.latitude, "longitude": faz.longitude, "timezone": "America/Sao_Paulo",
            "hourly": "temperature_2m,relative_humidity_2m", "current": "temperature_2m,relative_humidity_2m",
            "start_date": data.isoformat(), "end_date": data.isoformat()})
        r.raise_for_status()
        j = r.json()
        t = [v for v in j["hourly"]["temperature_2m"] if v is not None]
        u = [v for v in j["hourly"]["relative_humidity_2m"] if v is not None]
        if not t or not u:
            return {"disponivel": False, "motivo": "sem dados para a data"}
        temp, ur = round(sum(t) / len(t), 1), round(sum(u) / len(u))
        return {"disponivel": True, "data": data, "temp": temp, "ur": ur, "itu": round(itu(temp, ur), 1),
                "temp_max": max(t), "agora": j.get("current") if data == date.today() else None,
                "fonte": "Open-Meteo (média horária do dia)", "local": faz.municipio}
    except Exception:  # noqa: BLE001 — offline-first: falha de rede vira entrada manual
        return {"disponivel": False, "motivo": "sem conexão com a meteorologia"}