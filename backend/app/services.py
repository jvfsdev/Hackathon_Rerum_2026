"""Orquestra banco, motor de inferência, otimizador e monitor. Não contém regras de decisão."""
from datetime import date, timedelta

from sqlmodel import Session, select

from .db.models import AlertaDB, Dieta, Evento, Fazenda, Lote, Registro, SessaoInferencia
from .engine.engine import Motor, Resultado
from .engine.explain import como
from .engine.rules_loader import BaseConhecimento, carregar
from .engine.working_memory import MemoriaTrabalho
from .monitor.fatos import HistoricoLote, del_em, fatos_monitoramento, serie_esperado
from .optimizer import lp

_KB: BaseConhecimento | None = None

MODULOS_AVALIACAO = ["classificacao", "exigencias", "verificacao"]
MODULOS_FORMULACAO = ["classificacao", "exigencias", "formulacao"]
MODULOS_ACOMPANHAMENTO = ["classificacao", "acompanhamento_diario", "acompanhamento_semanal", "acompanhamento_mensal", "meta"]
JANELA_DEDUP = {"acompanhamento_diario": 3, "acompanhamento_semanal": 7, "acompanhamento_mensal": 30, "classificacao": 3, "meta": 3}


def kb() -> BaseConhecimento:
    global _KB
    if _KB is None:
        _KB = carregar()
    return _KB


def recarregar_kb() -> BaseConhecimento:
    global _KB
    _KB = carregar()
    return _KB


# ------------------------------------------------------------------ fatos de entrada
def fatos_lote(lote: Lote, d: date | None = None, h: HistoricoLote | None = None) -> dict:
    """Fatos lote.* (DEL e gestação avançam a partir da data de referência)."""
    d = d or date.today()
    dias = (d - lote.data_ref).days
    f = {"lote.estado": lote.estado, "lote.sistema": lote.sistema, "lote.grupo_genetico": lote.grupo_genetico,
         "lote.pv": lote.pv, "lote.n_vacas": lote.n_vacas}
    if lote.estado == "lactacao" and lote.del_ref is not None:
        f["lote.del"] = del_em(lote, d)
    if lote.dias_para_parto_ref is not None:
        f["lote.dias_para_parto"] = max(0, lote.dias_para_parto_ref - dias)
    if lote.dias_gestacao_ref:
        f["lote.dias_gestacao"] = lote.dias_gestacao_ref + dias
    elif lote.dias_gestacao_ref == 0:
        f["lote.dias_gestacao"] = 0
    for campo in ("fracao_primiparas", "ecc", "distancia_km", "relevo", "leite", "gordura", "proteina"):
        v = getattr(lote, campo)
        if v is not None:
            f[f"lote.{campo}"] = v
    if h is not None:
        lv = [h.valor("litros", d - timedelta(days=i)) for i in range(7)]
        vc = [h.valor("vacas", d - timedelta(days=i)) for i in range(7)]
        pares = [(a, b) for a, b in zip(lv, vc) if a and b]
        if pares:
            f["lote.leite"] = sum(a / b for a, b in pares) / len(pares)
        for ind in ("temp", "ur"):
            v = h.valor(ind, d)
            if v is not None:
                f[f"lote.{ind}"] = v
        ecc = h.serie("ecc", d, 42)
        if ecc:
            f["lote.ecc"] = ecc[-1][1]
        for ind in ("gordura", "proteina"):
            pts = h.serie(f"laudo_{ind}", d)
            if pts:
                f[f"lote.{ind}"] = pts[-1][1]
    return f


def itens_dieta(itens: list[dict]) -> list[dict]:
    return [{"alimento": kb().alimentos[i["alimento"]], "kg_mn": i["kg_mn"]} for i in itens if i.get("kg_mn")]


def cf_itens(itens: list[dict]) -> float:
    return min((i["alimento"].get("cf", kb().params["cf_tabela"]["valor"]) for i in itens), default=1.0)


def memoria(fatos: dict, origem: str = "usuario", padroes: set | None = None) -> MemoriaTrabalho:
    wm = MemoriaTrabalho()
    cf_padrao = kb().params["cf_padrao"]["valor"]
    for nome, valor in fatos.items():
        if padroes and nome in padroes:
            wm.declarar(nome, valor, cf=cf_padrao, origem="padrao", nota="valor padrão (usuário não informou)")
        else:
            wm.declarar(nome, valor, cf=1.0, origem=origem)
    return wm


def historico(s: Session, lote_id: int) -> HistoricoLote:
    regs = s.exec(select(Registro).where(Registro.lote_id == lote_id)).all()
    evs = s.exec(select(Evento).where(Evento.lote_id == lote_id)).all()
    return HistoricoLote(regs, evs)


def dieta_ativa(s: Session, lote_id: int) -> Dieta | None:
    return s.exec(select(Dieta).where(Dieta.lote_id == lote_id, Dieta.ativa == True)  # noqa: E712
                  .order_by(Dieta.versao.desc())).first()


def dieta_vigente(s: Session, lote_id: int, d: date) -> Dieta | None:
    """Versão da dieta em vigor na data d (a de início mais recente até d)."""
    return s.exec(select(Dieta).where(Dieta.lote_id == lote_id, Dieta.inicio <= d)
                  .order_by(Dieta.inicio.desc(), Dieta.versao.desc())).first()


def _pacote(resultado: Resultado, explicar: list[str]) -> dict:
    out = resultado.to_dict()
    out["explicacoes"] = {f: como(resultado, f) for f in explicar if f in resultado.wm}
    return out


def _salvar_sessao(s: Session, lote_id, tipo, resultado: dict, d: date | None = None) -> int:
    sessao = SessaoInferencia(lote_id=lote_id, tipo=tipo, kb_version=kb().versao, resultado=resultado, data_ref=d)
    s.add(sessao)
    s.commit()
    s.refresh(sessao)
    return sessao.id


# ------------------------------------------------------------------ avaliação (perfil + exigências + dieta)
EXPLICAR_AVALIACAO = ["perfil.fase", "exig.cms", "exig.ell_total", "exig.pb_pct_alvo", "meta.fdn_min", "meta.cnf_max",
                      "ver.razao_energia", "ver.razao_pb", "ver.risco_acidose", "parecer.dieta", "clima.itu"]


def avaliar(fatos: dict, itens: list[dict] | None, padroes: set | None = None) -> dict:
    wm = memoria(fatos, padroes=padroes)
    if itens:
        enriquecidos = itens_dieta(itens)
        wm.declarar("dieta.itens", enriquecidos, cf=cf_itens(enriquecidos), origem="tabela",
                    nota="composição dos alimentos de tabela")
    resultado = Motor(kb(), MODULOS_AVALIACAO).executar(wm)
    return _pacote(resultado, EXPLICAR_AVALIACAO)


def avaliar_lote(s: Session, lote: Lote, itens: list[dict] | None = None) -> dict:
    h = historico(s, lote.id)
    dieta = dieta_ativa(s, lote.id)
    itens = itens if itens is not None else (dieta.itens if dieta else None)
    out = avaliar(fatos_lote(lote, date.today(), h), itens)
    out["sessao_id"] = _salvar_sessao(s, lote.id, "avaliacao", out)
    return out


# ------------------------------------------------------------------ formulação (PL)
def formular(fatos: dict, alimentos_ids: list[str], precos: dict | None = None) -> dict:
    base = kb()
    wm = memoria(fatos)
    wm.declarar("formulacao.solicitada", True, origem="sistema")
    motor = Motor(base, MODULOS_FORMULACAO)
    resultado = motor.executar(wm)
    v = wm.valor
    if v("exig.cms") is None or v("exig.ell_total") is None or v("exig.pb_pct_alvo") is None:
        out = _pacote(resultado, ["exig.cms", "exig.ell_total"])
        out["pl"] = {"status": "dados_insuficientes"}
        return out
    restricoes = {"cms": v("exig.cms"), "folga_ms": v("pl.folga_ms"), "ell_min": v("pl.ell_min"),
                  "pb_min": v("pl.pb_min"), "pb_max": v("pl.pb_max"), "fdn_min": v("meta.fdn_min"),
                  "fdnf_min": v("meta.fdnf_min"), "cnf_max": v("meta.cnf_max"), "ee_max": v("meta.ee_max"),
                  "ureia_max": v("meta.ureia_max"), "fdn_max_kg": v("pl.fdn_max_kg")}
    alimentos = [dict(base.alimentos[a], **({"preco_kg_mn": precos[a]} if precos and a in precos else {}))
                 for a in alimentos_ids]
    pl = lp.formular(alimentos, restricoes)
    wm.declarar("pl.status", pl["status"], origem="sistema")
    wm.declarar("pl.restricoes_violadas", pl["restricoes_violadas"], origem="sistema")
    if pl["status"] == "otimo":
        wm.declarar("pl.custo", pl["custo"], origem="sistema")
    motor.executar(wm, resultado)   # segunda fase: regras de diagnóstico do resultado do PL
    out = _pacote(resultado, ["exig.cms", "exig.ell_total", "exig.pb_pct_alvo", "pl.ell_min"])
    out["pl"] = {"status": pl["status"], "restricoes": restricoes, "restricoes_violadas": pl["restricoes_violadas"]}
    if pl["status"] == "otimo":
        itens = [{"alimento": i["alimento"]["id"], "kg_mn": round(i["kg_mn"], 2)} for i in pl["itens"]]
        out["pl"].update({"custo": pl["custo"], "itens": itens, "composicao": pl["composicao"]})
        out["verificacao"] = avaliar(fatos, itens)   # a dieta do PL passa pela verificação das regras
    return out


def formular_lote(s: Session, lote: Lote, alimentos_ids: list[str], precos: dict | None = None) -> dict:
    out = formular(fatos_lote(lote, date.today(), historico(s, lote.id)), alimentos_ids, precos)
    out["sessao_id"] = _salvar_sessao(s, lote.id, "formulacao", out)
    return out


# ------------------------------------------------------------------ acompanhamento
EXPLICAR_ACOMPANHAMENTO = ["hipotese.queda_sustentada", "hipotese.causa_calor", "hipotese.causa_volumoso",
                           "hipotese.acidose", "hipotese.mastite", "laudo.nul", "mon.silagem_kg_mn_novo"]


def monitorar(s: Session, lote: Lote, d: date, h: HistoricoLote | None = None, persistir: bool = True) -> dict:
    base = kb()
    h = h or historico(s, lote.id)
    fazenda = s.get(Fazenda, lote.fazenda_id)
    dieta = dieta_vigente(s, lote.id, d)
    fatos = fatos_lote(lote, d, h)
    fatos.update(fatos_monitoramento(lote, fazenda, dieta, h, base.params, base.alimentos, d))
    resultado = Motor(base, MODULOS_ACOMPANHAMENTO).executar(memoria(fatos, origem="medido"))
    out = _pacote(resultado, EXPLICAR_ACOMPANHAMENTO)
    if persistir:
        out["sessao_id"] = _salvar_sessao(s, lote.id, "acompanhamento", out, d)
        _persistir_alertas(s, lote.id, d, resultado, out["sessao_id"])
    return out


def _persistir_alertas(s: Session, lote_id: int, d: date, resultado: Resultado, sessao_id: int):
    modulo_de = {r["id"]: r["modulo"] for r in kb().regras}
    for a in resultado.alertas:
        modulo = modulo_de.get(a.regra, "")
        janela = JANELA_DEDUP.get(modulo, 3)
        recente = s.exec(select(AlertaDB).where(AlertaDB.lote_id == lote_id, AlertaDB.regra == a.regra,
                                                AlertaDB.status == a.status,
                                                AlertaDB.data > d - timedelta(days=janela), AlertaDB.data <= d)).first()
        if recente:
            continue
        s.add(AlertaDB(lote_id=lote_id, data=d, regra=a.regra, modulo=modulo, nivel=a.nivel, titulo=a.titulo,
                       causa=a.causa, acao=a.acao, categoria=a.categoria, cf=a.cf, fonte=a.fonte, forca=a.forca,
                       status=a.status, nota=a.nota, sessao_id=sessao_id))
    s.commit()


def reprocessar(s: Session, lote: Lote, inicio: date, fim: date):
    """Roda o acompanhamento dia a dia (usado no seed para gerar o histórico de alertas)."""
    h = historico(s, lote.id)
    d = inicio
    while d <= fim:
        if lote.estado != "lactacao" or (del_em(lote, d) or 0) >= 1:   # lote ainda sem vacas paridas
            monitorar(s, lote, d, h)
        d += timedelta(days=1)


def serie_lote(s: Session, lote: Lote, ate: date | None = None) -> dict:
    """Séries para os gráficos de acompanhamento."""
    ate = ate or date.today()
    h = historico(s, lote.id)
    pontos = serie_esperado(lote, h, kb().params, ate)
    indicadores = {}
    for ind in ("sobras_pct", "ms_silagem", "ecc", "escore_fezes", "concentrado_kg_vaca", "laudo_nul", "laudo_gordura",
                "laudo_proteina", "laudo_lactose", "laudo_ccs", "laudo_cbt", "temp", "ur", "vacas"):
        indicadores[ind] = [{"data": d.isoformat(), "valor": v} for d, v in h.serie(ind, ate, 60)]
    eventos = [{"data": e.data_hora.isoformat(), "tipo": e.tipo, "descricao": e.descricao} for e in h.eventos]
    return {"producao": [p | {"data": p["data"].isoformat()} for p in pontos], "indicadores": indicadores, "eventos": eventos}
