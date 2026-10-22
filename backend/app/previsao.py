"""Previsão dos próximos dias: leite pela curva de lactação ajustada ao lote (com faixa de incerteza e calor previsto),
secagem e parto pelas datas de gestação, custo pela dieta do dia (transições incluídas) e preços vigentes.
Aqui só há cálculo; o que vira aviso é decidido pelas regras PRV (módulo previsao)."""
import os
import statistics
from datetime import date, timedelta

import httpx
from sqlmodel import Session, select

from . import estoque, services
from .calc import economics, lactation_curve
from .calc.climate import itu
from .calc.diet import composicao
from .db.models import Fazenda, Lote
from .engine.engine import Motor
from .monitor import series
from .monitor.fatos import INDICADORES_LAUDO, ajustar_k, itu_do_dia, litros_vaca, parametros_itu, serie_esperado


def clima_previsto(fazenda: Fazenda, dias: int = 16) -> dict[date, float]:
    """ITU médio previsto por dia (Open-Meteo, até 16 dias). Sem internet ou sem localização: {} (sem desconto de calor)."""
    if os.environ.get("LEITE_SEM_COLETA") or fazenda.latitude is None or fazenda.longitude is None:
        return {}
    try:
        r = httpx.get("https://api.open-meteo.com/v1/forecast", timeout=5, params={
            "latitude": fazenda.latitude, "longitude": fazenda.longitude, "timezone": "America/Sao_Paulo",
            "daily": "temperature_2m_mean,relative_humidity_2m_mean", "forecast_days": min(dias, 16)})
        r.raise_for_status()
        d = r.json()["daily"]
        return {date.fromisoformat(t): itu(tm, ur) for t, tm, ur in
                zip(d["time"], d["temperature_2m_mean"], d["relative_humidity_2m_mean"]) if tm is not None and ur is not None}
    except Exception:  # noqa: BLE001 — offline-first
        return {}


def _preco_leite(fazenda: Fazenda, h, hoje: date, params) -> tuple[float, float]:
    """Preço do leite + bonificação pelo último laudo válido (a qualidade atual é mantida na projeção)."""
    laudo = {}
    for ind in INDICADORES_LAUDO:
        pts = h.serie(f"laudo_{ind}", hoje)
        if pts and (hoje - pts[-1][0]).days <= params["laudo_validade_dias"]["valor"]:
            laudo[ind] = pts[-1][1]
    bonus = economics.bonificacao(laudo, fazenda.bonificacao)["total"] if fazenda.bonificacao and laudo else 0.0
    return fazenda.preco_leite + bonus, bonus


def projetar_lote(s: Session, lote: Lote, dias: int = 30, hoje: date | None = None, itu_futuro: dict | None = None) -> dict:
    hoje = hoje or date.today()
    kb = services.kb()
    p = kb.params
    fazenda = s.get(Fazenda, lote.fazenda_id)
    h = services.historico(s, lote.id)
    cat = services.catalogo(s, lote.fazenda_id)
    precos = services.precos_fazenda(s, lote.fazenda_id)
    fatos = services.fatos_lote(lote, hoje, h)
    vacas = services.vacas_em(h, lote, hoje)
    itu_futuro = itu_futuro or {}
    limiar, perda = parametros_itu(lote, p)
    preco_leite, bonus = _preco_leite(fazenda, h, hoje, p)
    z = p["prev_z_faixa"]["valor"]

    # escala da curva e incerteza (sigma robusto dos desvios dos últimos 60 dias, fora dos dias de transição)
    k = ajustar_k(lote, h, p, hoje) if lote.estado == "lactacao" else None
    pontos = serie_esperado(lote, h, p, hoje) if k else []
    residuos = [pt["residuo"] for pt in pontos if not pt["transicao"]]
    sigma = max(series.sigma_robusto(residuos), p["sigma_piso"]["valor"]) if len(residuos) >= 7 else p["prev_sigma_padrao"]["valor"]
    # o lote segue na distância atual da curva (mediana dos últimos 7 dias úteis): uma queda em curso não some sozinha
    desvio = statistics.median(residuos[-7:]) if len(residuos) >= 3 else 0.0
    base_plana = None
    if lote.estado == "lactacao" and k is None:           # curva ainda calibrando: média dos últimos 7 dias, sem queda
        lv = [litros_vaca(h, hoje - timedelta(days=i)) for i in range(7)]
        lv = [x for x in lv if x]
        base_plana = sum(lv) / len(lv) if lv else fatos.get("lote.leite")

    gest = fatos.get("lote.dias_gestacao")
    secagem = (hoje + timedelta(days=max(0, round(p["dias_gestacao_secagem"]["valor"] - gest)))
               if lote.estado == "lactacao" and gest else None)
    parto = (hoje + timedelta(days=round(fatos["lote.dias_para_parto"]))
             if lote.estado == "seca" and fatos.get("lote.dias_para_parto") is not None else None)

    def itu_em(d):
        return itu_futuro.get(d) if d > hoje else itu_do_dia(h, d)

    dieta = services.dieta_ativa(s, lote.id)
    custo_cache: dict[str, float] = {}
    serie = []
    for i in range(1, dias + 1):
        d = hoje + timedelta(days=i)
        produzindo = lote.estado == "lactacao" and not (secagem and d >= secagem)
        esp = baixo = alto = None
        if produzindo:
            if k is not None:
                its = [x for x in (itu_em(d - timedelta(days=1)), itu_em(d - timedelta(days=2))) if x is not None]
                i2 = sum(its) / len(its) if its else None
                esp = lactation_curve.esperado_por_vaca(fatos["lote.del"] + i, k, i2, limiar, perda) * (1 + desvio)
            else:
                esp = base_plana
            if esp is not None:
                baixo, alto = max(0.0, esp * (1 - z * sigma)), esp * (1 + z * sigma)
        itens = services.itens_do_dia(dieta, d)
        chave = repr(itens)
        if chave not in custo_cache:
            comp = composicao(services.itens_dieta(itens, precos, cat)) if itens else {}
            custo_cache[chave] = comp.get("custo_vaca_dia") or 0.0
        custo = custo_cache[chave] * vacas
        receita = (esp or 0.0) * vacas * preco_leite
        serie.append({"data": d.isoformat(), "leite_vaca": esp, "baixo": baixo, "alto": alto,
                      "leite_lote": (esp or 0.0) * vacas, "receita": receita, "custo": custo, "margem": receita - custo,
                      "itu": itu_futuro.get(d), "produzindo": produzindo})

    leite_total = sum(x["leite_lote"] for x in serie)
    margem_total = sum(x["margem"] for x in serie)
    marcos = []
    if secagem and secagem <= hoje + timedelta(days=dias):
        marcos.append({"data": secagem.isoformat(), "tipo": "secagem", "texto": "Secagem prevista"})
    if parto and parto <= hoje + timedelta(days=dias):
        marcos.append({"data": parto.isoformat(), "tipo": "parto", "texto": "Parto previsto"})
    if dieta and dieta.transicao:
        fim = date.fromisoformat(dieta.transicao["plano"][-1]["data"]) + timedelta(days=1)
        if hoje < fim <= hoje + timedelta(days=dias):
            marcos.append({"data": fim.isoformat(), "tipo": "dieta", "texto": "Dieta nova completa"})

    # fatos para as regras de previsão
    f = {"lote.estado": lote.estado, "prev.dias": dias, "prev.lote.leite_total": leite_total,
         "prev.lote.margem_total": margem_total, "prev.lote.nome": lote.nome}
    prod = [x for x in serie if x["leite_vaca"]]
    if lote.estado == "lactacao" and len(prod) >= 7 and pontos:
        hoje_esp = pontos[-1]["esperado"] * (1 + desvio)
        f["prev.lote.variacao_leite_pct"] = 100 * (sum(x["leite_vaca"] for x in prod[-7:]) / 7 / hoje_esp - 1)
    if secagem and secagem <= hoje + timedelta(days=dias):
        f["prev.lote.dias_para_secagem"] = (secagem - hoje).days
        f["prev.lote.leite_dia_antes_secagem"] = (prod[-1]["leite_vaca"] if prod else 0.0) * vacas
    negativos = [x for x in serie if x["produzindo"] and x["margem"] < 0]
    if negativos:
        f["prev.lote.data_margem_negativa"] = date.fromisoformat(negativos[0]["data"]).strftime("%d/%m")
        f["prev.lote.dias_margem_negativa"] = len(negativos)
    if dieta and prod and lote.estado == "lactacao":
        aval = services.avaliar(fatos | {"lote.leite": prod[0]["leite_vaca"]}, dieta.itens, precos=precos, cat=cat)
        permitido = aval["fatos"].get("ver.leite_permitido", {}).get("valor")
        if permitido is not None:
            f["prev.lote.sobra_energia_l"] = permitido - sum(x["leite_vaca"] for x in prod[:7]) / len(prod[:7])
    res = Motor(kb, ["previsao"]).executar(services.memoria(f, origem="sistema"))
    return {"lote": {"id": lote.id, "nome": lote.nome, "estado": lote.estado}, "vacas": vacas, "dias": dias,
            "hoje": hoje.isoformat(), "preco_leite": preco_leite, "bonificacao": bonus, "sigma": sigma, "desvio_atual": desvio,
            "calibrando": lote.estado == "lactacao" and k is None, "clima_dias": len(itu_futuro),
            "historico": [{"data": pt["data"].isoformat(), "observado": pt["observado"], "esperado": pt["esperado"]}
                          for pt in pontos[-30:]],
            "serie": serie, "marcos": marcos, "totais": {"leite": leite_total, "receita": sum(x["receita"] for x in serie),
                                                       "custo": sum(x["custo"] for x in serie), "margem": margem_total},
            "alertas": [a.to_dict() for a in res.alertas]}


def projetar_fazenda(s: Session, fazenda_id: int, dias: int = 30, hoje: date | None = None) -> dict:
    hoje = hoje or date.today()
    fazenda = s.get(Fazenda, fazenda_id)
    itu_futuro = clima_previsto(fazenda, dias)
    lotes = [projetar_lote(s, l, dias, hoje, itu_futuro)
             for l in s.exec(select(Lote).where(Lote.fazenda_id == fazenda_id)).all()]
    por_dia = []
    for i in range(dias):
        por_dia.append({"data": lotes[0]["serie"][i]["data"] if lotes else (hoje + timedelta(days=i + 1)).isoformat(),
                        **{k: sum(l["serie"][i][k] for l in lotes) for k in ("leite_lote", "receita", "custo", "margem")}})
    tot = {k: sum(l["totais"][k] for l in lotes) for k in ("leite", "receita", "custo", "margem")}
    f = {"prev.dias": dias, "prev.fazenda.margem_total": tot["margem"]}
    if len(por_dia) >= 14:
        ini = sum(x["receita"] for x in por_dia[:7]) / 7
        fim = sum(x["receita"] for x in por_dia[-7:]) / 7
        if ini:
            f["prev.fazenda.variacao_receita_pct"] = 100 * (fim / ini - 1)
    res = Motor(services.kb(), ["previsao"]).executar(services.memoria(f, origem="sistema"))
    est = estoque.situacao(s, fazenda_id, hoje)
    acaba = [{"item": i["item"], "nome": i["nome"], "data": (hoje + timedelta(days=int(i["dias_restantes"]))).isoformat()}
             for i in est["itens"] if i["dias_restantes"] is not None and i["dias_restantes"] <= dias]
    return {"fazenda": {"id": fazenda.id, "nome": fazenda.nome}, "dias": dias, "hoje": hoje.isoformat(),
            "clima_dias": len(itu_futuro), "totais": tot, "por_dia": por_dia, "estoque_acaba": acaba,
            "lotes": [{k: l[k] for k in ("lote", "vacas", "totais", "marcos", "alertas", "calibrando")} for l in lotes],
            "alertas": [a.to_dict() for a in res.alertas]}
