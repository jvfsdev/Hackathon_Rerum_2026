"""Inferência: avaliação, formulação (PL), acompanhamento, consulta guiada (backward) e explicações."""
import uuid
from datetime import date

from fastapi import APIRouter, HTTPException

from .. import services
from ..db.models import Lote, SessaoInferencia, sessao
from ..engine.engine import Motor
from ..engine.explain import como, contrafactual, explicar_regra, por_que, resultado_de_dict
from .schemas import AjusteIn, AvaliarIn, AvaliarLoteIn, ConsultaIn, FormularIn, RespostaIn, SensibilidadeIn, SimularIn

router = APIRouter(prefix="/inferencia")

OBJETIVOS_CONSULTA = ["perfil.fase", "exig.cms", "exig.ell_total", "exig.pb_pct_alvo", "clima.itu"]
_CONSULTAS: dict[str, dict] = {}


def _lote(s, lote_id):
    lote = s.get(Lote, lote_id)
    if not lote:
        raise HTTPException(404, "lote não encontrado")
    return lote


@router.post("/avaliar")
def avaliar(dados: AvaliarIn):
    """Avaliação avulsa: fatos informados + dieta opcional → perfil, exigências, verificação e parecer."""
    itens = [i.model_dump() for i in dados.itens] if dados.itens else None
    return services.avaliar(dados.fatos, itens, set(dados.padroes))


@router.post("/lotes/{lote_id}/avaliar")
def avaliar_lote(lote_id: int, dados: AvaliarLoteIn | None = None):
    with sessao() as s:
        itens = [i.model_dump() for i in dados.itens] if dados and dados.itens else None
        return services.avaliar_lote(s, _lote(s, lote_id), itens)


@router.post("/lotes/{lote_id}/formular")
def formular_lote(lote_id: int, dados: FormularIn):
    with sessao() as s:
        return services.formular_lote(s, _lote(s, lote_id), dados.alimentos, dados.precos)


@router.post("/lotes/{lote_id}/ajuste")
def ajuste_minimo(lote_id: int, dados: AjusteIn | None = None):
    """Menor mudança na dieta (ativa ou informada) para ela passar em todas as verificações."""
    with sessao() as s:
        itens = [i.model_dump() for i in dados.itens] if dados and dados.itens else None
        return services.ajustar_dieta_lote(s, _lote(s, lote_id), itens)


@router.post("/lotes/{lote_id}/sensibilidade")
def sensibilidade(lote_id: int, dados: SensibilidadeIn):
    """Até que preço cada alimento fica na dieta de custo mínimo e quanto cada meta custa."""
    with sessao() as s:
        return services.sensibilidade_lote(s, _lote(s, lote_id), dados.alimentos)


@router.post("/lotes/{lote_id}/simular")
def simular(lote_id: int, dados: SimularIn):
    """Cenário "e se?": compara a dieta ativa com outra dieta, meta de leite ou preços (nada é gravado)."""
    with sessao() as s:
        return services.simular(s, _lote(s, lote_id), [i.model_dump() for i in dados.itens], dados.leite,
                                dados.preco_leite, dados.precos)


@router.post("/lotes/{lote_id}/acompanhar")
def acompanhar(lote_id: int, data: date | None = None):
    with sessao() as s:
        return services.monitorar(s, _lote(s, lote_id), data or date.today())


# ------------------------------------------------------------- consulta guiada (encadeamento regressivo)
def _proximas(c: dict) -> list[dict]:
    wm = services.memoria(c["fatos"], padroes=c["padroes"])
    # classifica antes de procurar o que falta: fatos derivados (fase, equação) podam perguntas desnecessárias
    Motor(services.kb(), ["classificacao"]).executar(wm)
    motor = Motor(services.kb(), services.MODULOS_AVALIACAO)
    vistas, perguntas = set(), []
    for objetivo in OBJETIVOS_CONSULTA:
        for p in motor.faltantes(objetivo, wm):
            if p["fato"] not in vistas and p["fato"] not in c["fatos"] and p["fato"] not in c["ignorados"]:
                vistas.add(p["fato"])
                regras = {r["id"]: r for r in services.kb().regras}
                p["por_que"] = [{"regra": rid, "descricao": regras[rid].get("descricao", "")} for rid in p["cadeia"]]
                perguntas.append(p)
    return perguntas


def _estado(cid: str) -> dict:
    c = _CONSULTAS[cid]
    perguntas = _proximas(c)
    out = {"consulta": cid, "fatos": c["fatos"], "padroes": sorted(c["padroes"]), "pendentes": len(perguntas),
           "pergunta": perguntas[0] if perguntas else None}
    if not perguntas:
        out["resultado"] = services.avaliar(c["fatos"], c["itens"], c["padroes"])
    return out


@router.post("/consulta")
def iniciar_consulta(dados: ConsultaIn):
    cid = uuid.uuid4().hex[:10]
    _CONSULTAS[cid] = {"fatos": services.normalizar(dados.fatos), "padroes": set(), "ignorados": set(),
                       "itens": [i.model_dump() for i in dados.itens] if dados.itens else None}
    return _estado(cid)


@router.post("/consulta/{cid}/responder")
def responder(cid: str, r: RespostaIn):
    if cid not in _CONSULTAS:
        raise HTTPException(404, "consulta não encontrada")
    c = _CONSULTAS[cid]
    if r.nao_sei:
        pergunta = services.kb().perguntas.get(r.fato, {})
        if "padrao" in pergunta:
            c["fatos"][r.fato] = pergunta["padrao"]
            c["padroes"].add(r.fato)
        elif pergunta.get("opcional"):
            c["ignorados"].add(r.fato)     # regras que dependem dele simplesmente não se aplicam
        else:
            raise HTTPException(400, "esta informação é necessária para a conclusão e não tem valor padrão seguro")
    else:
        c["fatos"].update(services.normalizar({r.fato: r.valor}))
        c["padroes"].discard(r.fato)
    return _estado(cid)


# ------------------------------------------------------------- explicações
@router.get("/sessoes/{sessao_id}")
def obter_sessao(sessao_id: int):
    with sessao() as s:
        sess = s.get(SessaoInferencia, sessao_id)
        if not sess:
            raise HTTPException(404, "sessão não encontrada")
        return sess


@router.get("/sessoes/{sessao_id}/como")
def como_sessao(sessao_id: int, fato: str):
    with sessao() as s:
        sess = s.get(SessaoInferencia, sessao_id)
        if not sess:
            raise HTTPException(404, "sessão não encontrada")
        return como(resultado_de_dict(sess.resultado), fato)


@router.get("/sessoes/{sessao_id}/regra/{regra_id}")
def explicar_regra_sessao(sessao_id: int, regra_id: str):
    """Por que um alerta foi emitido: regra disparada, premissas e a derivação de cada uma."""
    with sessao() as s:
        sess = s.get(SessaoInferencia, sessao_id)
        if not sess:
            raise HTTPException(404, "sessão não encontrada")
        exp = explicar_regra(resultado_de_dict(sess.resultado), regra_id)
        if exp is None:
            raise HTTPException(404, "regra não disparou nesta sessão")
        regra = services.kb().regra(regra_id) or {}
        supressoes = sess.resultado.get("supressoes", {})
        return exp | {"regra_def": regra, "kb_version": sess.kb_version, "supressoes": supressoes}


@router.get("/sessoes/{sessao_id}/contrafactual/{regra_id}")
def contrafactual_sessao(sessao_id: int, regra_id: str):
    """O que precisaria mudar para a regra (e o alerta) deixar de valer."""
    with sessao() as s:
        sess = s.get(SessaoInferencia, sessao_id)
        if not sess:
            raise HTTPException(404, "sessão não encontrada")
        out = contrafactual(resultado_de_dict(sess.resultado), regra_id)
        if out is None:
            raise HTTPException(404, "regra não disparou nesta sessão")
        regra = services.kb().regra(regra_id) or {}
        return out | {"regra": regra_id, "modulo": regra.get("modulo"), "sessao_tipo": sess.tipo,
                      "lote_id": sess.lote_id}


@router.get("/por-que")
def por_que_pergunta(fato: str, objetivo: str = "exig.ell_total"):
    motor = Motor(services.kb(), services.MODULOS_AVALIACAO)
    return {"fato": fato, "objetivo": objetivo, "cadeia": por_que(motor, fato, objetivo),
            "pergunta": services.kb().perguntas.get(fato)}
