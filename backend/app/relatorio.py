"""Relatório semanal da fazenda: produção, custo, margem, avisos, ações e próximos passos de cada lote, em linguagem
do produtor (os textos dos avisos vêm das regras: titulo_produtor / acao_produtor)."""
from datetime import date, datetime, time, timedelta

from sqlmodel import Session, select

from . import estoque, services
from .calc.diet import composicao
from .db.models import AlertaDB, Dieta, Evento, Fazenda, HistoricoAlerta, Lote
from .monitor.fatos import litros_vaca, serie_esperado

NIVEL = {"critico": 0, "atencao": 1, "informativo": 2}


def _media(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def _texto(a: AlertaDB) -> dict:
    return {"id": a.id, "nivel": a.nivel, "titulo": a.titulo_produtor or a.titulo, "acao": a.acao_produtor or a.acao,
            "estado": a.estado, "desde": a.aberto_em.isoformat()}


def gerar(s: Session, fazenda_id: int, dias: int = 7, fim: date | None = None) -> dict:
    fim = fim or date.today()
    ini = fim - timedelta(days=dias - 1)
    ini_ant, fim_ant = ini - timedelta(days=dias), ini - timedelta(days=1)
    fazenda = s.get(Fazenda, fazenda_id)
    cat = services.catalogo(s, fazenda_id)
    precos = services.precos_fazenda(s, fazenda_id)
    lotes = []
    for lote in s.exec(select(Lote).where(Lote.fazenda_id == fazenda_id)).all():
        h = services.historico(s, lote.id)
        periodo = [ini + timedelta(days=k) for k in range(dias)]
        anterior = [ini_ant + timedelta(days=k) for k in range(dias)]
        leite = _media([litros_vaca(h, d) for d in periodo])
        leite_ant = _media([litros_vaca(h, d) for d in anterior])
        esperado = _media([p["esperado"] for p in serie_esperado(lote, h, services.kb().params, fim, dias)])
        vacas = services.vacas_em(h, lote, fim)
        dieta = services.dieta_ativa(s, lote.id)
        custo = None
        if dieta:
            comp = composicao(services.itens_dieta(dieta.itens, precos, cat))
            custo = comp.get("custo_vaca_dia")
        receita = leite * fazenda.preco_leite if leite is not None else None
        eps = s.exec(select(AlertaDB).where(AlertaDB.lote_id == lote.id)).all()
        pendentes = sorted([a for a in eps if a.estado in ("aberto", "aceito") and not a.suprimido],
                           key=lambda a: (NIVEL[a.nivel], a.aberto_em))
        resolvidos = [a for a in eps if a.estado == "resolvido" and a.estado_em and ini <= a.estado_em <= fim]
        acoes = s.exec(select(HistoricoAlerta).where(
            HistoricoAlerta.lote_id == lote.id, HistoricoAlerta.automatico == False,  # noqa: E712
            HistoricoAlerta.data_hora >= datetime.combine(ini, time.min),
            HistoricoAlerta.data_hora <= datetime.combine(fim, time.max)).order_by(HistoricoAlerta.data_hora)).all()
        eventos = s.exec(select(Evento).where(Evento.lote_id == lote.id,
                                              Evento.data_hora >= datetime.combine(ini, time.min),
                                              Evento.data_hora <= datetime.combine(fim, time.max))).all()
        dietas = s.exec(select(Dieta).where(Dieta.lote_id == lote.id, Dieta.inicio >= ini, Dieta.inicio <= fim)).all()
        lotes.append({
            "lote": {"id": lote.id, "nome": lote.nome}, "vacas": vacas,
            "leite_vaca": leite, "leite_vaca_anterior": leite_ant, "esperado_vaca": esperado,
            "variacao_pct": 100 * (leite / leite_ant - 1) if leite and leite_ant else None,
            "leite_lote_dia": leite * vacas if leite is not None else None,
            "custo_vaca_dia": custo, "custo_por_litro": custo / leite if custo is not None and leite else None,
            "margem_vaca_dia": receita - custo if receita is not None and custo is not None else None,
            "pendentes": [_texto(a) for a in pendentes],
            "resolvidos": [_texto(a) | {"resolucao": a.resolucao} for a in resolvidos],
            "acoes": [{"data": h.data_hora.isoformat(), "tipo": h.tipo, "descricao": h.descricao,
                       "aviso": next((a.titulo_produtor or a.titulo for a in eps if a.id == h.alerta_id), "")}
                      for h in acoes],
            "eventos": [{"data": e.data_hora.isoformat(), "tipo": e.tipo, "descricao": e.descricao} for e in eventos],
            "dietas_novas": [{"versao": d.versao, "inicio": d.inicio.isoformat(), "motivo": d.motivo} for d in dietas],
            "proximos_passos": [p["acao"] for p in [_texto(a) for a in pendentes][:3] if p["acao"]],
        })
    soma = lambda k: sum(l[k] for l in lotes if l[k] is not None)
    margem_dia = sum(l["margem_vaca_dia"] * l["vacas"] for l in lotes if l["margem_vaca_dia"] is not None)
    est = estoque.situacao(s, fazenda_id, fim)
    from . import previsao
    prev = previsao.projetar_fazenda(s, fazenda_id, 30, fim)
    return {"fazenda": {"id": fazenda.id, "nome": fazenda.nome, "municipio": fazenda.municipio},
            "inicio": ini.isoformat(), "fim": fim.isoformat(), "dias": dias, "preco_leite": fazenda.preco_leite,
            "totais": {"vacas": soma("vacas"), "leite_dia": soma("leite_lote_dia"), "margem_dia": margem_dia,
                       "pendentes": sum(len(l["pendentes"]) for l in lotes),
                       "resolvidos": sum(len(l["resolvidos"]) for l in lotes)},
            "lotes": lotes,
            "previsao": {"totais": prev["totais"], "dias": prev["dias"],
                         "avisos": [{"nivel": a["nivel"], "titulo": a["titulo_produtor"] or a["titulo"]}
                                    for a in prev["alertas"] + [x for l in prev["lotes"] for x in l["alertas"]]],
                         "marcos": [m | {"lote": l["lote"]["nome"]} for l in prev["lotes"] for m in l["marcos"]]},
            "estoque": [{"nivel": a["nivel"], "titulo": a["titulo_produtor"] or a["titulo"],
                         "acao": a["acao_produtor"] or a["acao"]} for a in est["alertas"]]}
