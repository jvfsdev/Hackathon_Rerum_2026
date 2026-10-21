"""Cadastro: fazendas, lotes, dietas, registros, eventos e alertas."""
from datetime import date, timedelta

from fastapi import APIRouter, HTTPException
from sqlmodel import select

from .. import services
from ..db.models import AlertaDB, Dieta, Evento, Fazenda, Lote, Registro, sessao
from .schemas import AlertaUpdate, DietaIn, EventoIn, LoteIn, RegistroIn

router = APIRouter()


def _lote(s, lote_id: int) -> Lote:
    lote = s.get(Lote, lote_id)
    if not lote:
        raise HTTPException(404, "lote não encontrado")
    return lote


@router.get("/fazendas")
def listar_fazendas():
    with sessao() as s:
        return s.exec(select(Fazenda)).all()


@router.get("/fazendas/{fazenda_id}/painel")
def painel(fazenda_id: int):
    """Resumo por lote: produção de hoje × esperado, custo, dieta ativa e alertas recentes."""
    hoje = date.today()
    with sessao() as s:
        fazenda = s.get(Fazenda, fazenda_id)
        if not fazenda:
            raise HTTPException(404, "fazenda não encontrada")
        cards = []
        for lote in s.exec(select(Lote).where(Lote.fazenda_id == fazenda_id)).all():
            serie = services.serie_lote(s, lote, hoje)["producao"]
            ultimo = serie[-1] if serie else None
            dieta = services.dieta_ativa(s, lote.id)
            comp = None
            if dieta:
                from ..calc.diet import composicao
                comp = composicao(services.itens_dieta(dieta.itens))
            alertas = s.exec(select(AlertaDB).where(AlertaDB.lote_id == lote.id, AlertaDB.status == "ativo",
                                                    AlertaDB.data >= hoje - timedelta(days=13))
                             .order_by(AlertaDB.data.desc())).all()
            contagem = {n: sum(a.nivel == n for a in alertas) for n in ("critico", "atencao", "informativo")}
            cards.append({"lote": lote, "hoje": ultimo, "serie": serie[-30:], "dieta": dieta,
                          "custo_dieta": comp.get("custo_vaca_dia") if comp else None, "alertas": contagem,
                          "principal": alertas and sorted(alertas, key=lambda a: ["critico", "atencao", "informativo"].index(a.nivel))[0]})
        return {"fazenda": fazenda, "data": hoje, "lotes": cards}


@router.get("/lotes")
def listar_lotes(fazenda_id: int | None = None):
    with sessao() as s:
        q = select(Lote)
        if fazenda_id:
            q = q.where(Lote.fazenda_id == fazenda_id)
        return s.exec(q).all()


@router.get("/lotes/{lote_id}")
def obter_lote(lote_id: int):
    with sessao() as s:
        lote = _lote(s, lote_id)
        return {"lote": lote, "fatos": services.fatos_lote(lote, date.today(), services.historico(s, lote.id)),
                "dieta": services.dieta_ativa(s, lote.id)}


@router.post("/lotes")
def criar_lote(dados: LoteIn):
    with sessao() as s:
        lote = Lote(**dados.model_dump(), data_ref=date.today())
        s.add(lote)
        s.commit()
        s.refresh(lote)
        return lote


@router.put("/lotes/{lote_id}")
def atualizar_lote(lote_id: int, dados: LoteIn):
    with sessao() as s:
        lote = _lote(s, lote_id)
        for k, v in dados.model_dump().items():
            setattr(lote, k, v)
        lote.data_ref = date.today()
        s.add(lote)
        s.commit()
        s.refresh(lote)
        return lote


@router.get("/lotes/{lote_id}/dietas")
def listar_dietas(lote_id: int):
    with sessao() as s:
        return s.exec(select(Dieta).where(Dieta.lote_id == lote_id).order_by(Dieta.versao.desc())).all()


@router.post("/lotes/{lote_id}/dietas")
def nova_dieta(lote_id: int, dados: DietaIn):
    """Cria nova versão da dieta (com motivo) e anexa o parecer da inferência."""
    with sessao() as s:
        lote = _lote(s, lote_id)
        anteriores = s.exec(select(Dieta).where(Dieta.lote_id == lote_id)).all()
        for d in anteriores:
            d.ativa = False
            s.add(d)
        itens = [i.model_dump() for i in dados.itens]
        parecer = services.avaliar_lote(s, lote, itens)
        silagem = next((i for i in itens if i["alimento"].startswith("silagem")), None)
        ms_ref = None
        if silagem:
            ms = services.historico(s, lote_id).serie("ms_silagem", date.today(), 14)
            ms_ref = ms[-1][1] if ms else services.kb().alimentos[silagem["alimento"]]["ms"]
        dieta = Dieta(lote_id=lote_id, versao=max((d.versao for d in anteriores), default=0) + 1, itens=itens,
                      origem=dados.origem, motivo=dados.motivo, inicio=date.today(), ativa=True, ms_silagem_ref=ms_ref,
                      parecer={"parecer": parecer["fatos"].get("parecer.dieta", {}).get("valor"),
                               "sessao_id": parecer["sessao_id"], "kb_version": parecer["kb_version"]})
        s.add(dieta)
        s.commit()
        s.refresh(dieta)
        return dieta


@router.post("/lotes/{lote_id}/registros")
def registrar(lote_id: int, dados: RegistroIn):
    """Grava os valores do dia (substitui o mesmo indicador na mesma data) e roda o acompanhamento."""
    with sessao() as s:
        lote = _lote(s, lote_id)
        for ind, valor in dados.valores.items():
            existente = s.exec(select(Registro).where(Registro.lote_id == lote_id, Registro.data == dados.data,
                                                      Registro.indicador == ind)).first()
            if existente:
                existente.valor = valor
                s.add(existente)
            else:
                s.add(Registro(lote_id=lote_id, data=dados.data, indicador=ind, valor=valor, metodo=dados.metodo))
        s.commit()
        hoje = date.today()
        if dados.data < hoje:   # registro retroativo: os dias seguintes dependem dele (série, corrida, médias)
            services.reprocessar(s, lote, dados.data + timedelta(days=1), hoje)
        return services.monitorar(s, lote, dados.data)


@router.get("/lotes/{lote_id}/registros")
def listar_registros(lote_id: int, desde: date | None = None):
    with sessao() as s:
        q = select(Registro).where(Registro.lote_id == lote_id)
        if desde:
            q = q.where(Registro.data >= desde)
        return s.exec(q.order_by(Registro.data)).all()


@router.post("/lotes/{lote_id}/eventos")
def registrar_evento(lote_id: int, dados: EventoIn):
    with sessao() as s:
        _lote(s, lote_id)
        ev = Evento(lote_id=lote_id, **dados.model_dump())
        s.add(ev)
        s.commit()
        s.refresh(ev)
        return ev


@router.get("/lotes/{lote_id}/serie")
def serie(lote_id: int):
    with sessao() as s:
        return services.serie_lote(s, _lote(s, lote_id))


@router.get("/alertas")
def listar_alertas(lote_id: int | None = None, dias: int = 60, incluir_suprimidos: bool = True):
    with sessao() as s:
        q = select(AlertaDB).where(AlertaDB.data >= date.today() - timedelta(days=dias))
        if lote_id:
            q = q.where(AlertaDB.lote_id == lote_id)
        if not incluir_suprimidos:
            q = q.where(AlertaDB.status == "ativo")
        return s.exec(q.order_by(AlertaDB.data.desc(), AlertaDB.id.desc())).all()


@router.patch("/alertas/{alerta_id}")
def atualizar_alerta(alerta_id: int, dados: AlertaUpdate):
    with sessao() as s:
        a = s.get(AlertaDB, alerta_id)
        if not a:
            raise HTTPException(404, "alerta não encontrado")
        a.status_usuario = dados.status_usuario
        s.add(a)
        s.commit()
        s.refresh(a)
        return a
