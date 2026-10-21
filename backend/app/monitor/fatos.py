"""Transforma os registros e eventos do lote em fatos datados (mon.*, laudo.*) para a memória de trabalho.

Aqui só há cálculo numérico (séries, médias, resíduos); quem decide se algo é alerta são as regras ACP.
"""
import statistics
from collections import defaultdict
from datetime import date, datetime, time, timedelta

from ..calc import climate, economics, lactation_curve
from . import series

INDICADORES_LAUDO = ("gordura", "proteina", "lactose", "nul", "ureia", "ccs", "cbt")


class HistoricoLote:
    """Registros do lote indexados por indicador e por data."""

    def __init__(self, registros, eventos):
        self.por_ind: dict[str, dict[date, float]] = defaultdict(dict)
        for r in registros:
            self.por_ind[r.indicador][r.data] = r.valor
        self.eventos = sorted(eventos, key=lambda e: e.data_hora)

    def valor(self, ind: str, d: date):
        return self.por_ind.get(ind, {}).get(d)

    def serie(self, ind: str, ate: date, dias: int | None = None) -> list[tuple[date, float]]:
        pts = sorted((d, v) for d, v in self.por_ind.get(ind, {}).items() if d <= ate and v is not None)
        if dias is not None:
            pts = [(d, v) for d, v in pts if d > ate - timedelta(days=dias)]
        return pts

    def ultimo_evento(self, tipo: str, ate: datetime):
        evs = [e for e in self.eventos if e.tipo == tipo and e.data_hora <= ate]
        return evs[-1] if evs else None


def del_em(lote, d: date) -> float | None:
    if lote.del_ref is None:
        return None
    return lote.del_ref + (d - lote.data_ref).days


def itu_do_dia(h: HistoricoLote, d: date) -> float | None:
    t, ur = h.valor("temp", d), h.valor("ur", d)
    return climate.itu(t, ur) if t is not None and ur is not None else None


def parametros_itu(lote, params) -> tuple[float, float]:
    zebuino = lote.grupo_genetico in params["grupos_zebuinos"]["valor"]
    if zebuino:
        return params["itu_limiar_zebuino"]["valor"], params["perda_itu_zebuino"]["valor"]
    return params["itu_limiar_holandes"]["valor"], params["perda_itu_holandes"]["valor"]


def itu_2d(h: HistoricoLote, d: date) -> float | None:
    vals = [v for v in (itu_do_dia(h, d - timedelta(days=1)), itu_do_dia(h, d - timedelta(days=2))) if v is not None]
    return sum(vals) / len(vals) if vals else None


def litros_vaca(h: HistoricoLote, d: date) -> float | None:
    litros, vacas = h.valor("litros", d), h.valor("vacas", d)
    return litros / vacas if litros is not None and vacas else None


def ajustar_k(lote, h: HistoricoLote, ate: date, dias: int = 14) -> float:
    """Escala da curva ajustada nos primeiros dias com registro (sem calor forte)."""
    if lote.k_curva:
        return lote.k_curva
    datas = sorted(h.por_ind.get("litros", {}))[:dias]
    obs = [(del_em(lote, d), litros_vaca(h, d)) for d in datas if d <= ate and litros_vaca(h, d) is not None]
    obs = [(t, y) for t, y in obs if t is not None and t > 0]
    return lactation_curve.ajustar_k(obs) if obs else 1.0


def serie_esperado(lote, h: HistoricoLote, params, ate: date, janela: int = 60) -> list[dict]:
    """Observado × esperado por dia (para o motor e para os gráficos)."""
    k = ajustar_k(lote, h, ate)
    limiar, perda = parametros_itu(lote, params)
    pontos = []
    for d, _ in h.serie("litros", ate, janela):
        obs, t = litros_vaca(h, d), del_em(lote, d)
        if obs is None or t is None or t <= 0:
            continue
        i2 = itu_2d(h, d)
        esp = lactation_curve.esperado_por_vaca(t, k, i2, limiar, perda)
        pontos.append({"data": d, "del": t, "observado": obs, "esperado": esp, "itu_2d": i2, "itu": itu_do_dia(h, d),
                       "residuo": series.residuo_relativo(obs, esp)})
    return pontos


def fatos_monitoramento(lote, fazenda, dieta, h: HistoricoLote, params, alimentos, d: date) -> dict:
    """Fatos mon.* e laudo.* do lote no dia d."""
    f: dict = {}
    fim_do_dia = datetime.combine(d, time(23, 59))
    limiar, _ = parametros_itu(lote, params)
    f["mon.itu_limiar"] = limiar
    f["fazenda.preco_leite"] = fazenda.preco_leite

    # --- diário: produção × esperado
    if h.valor("litros", d) is None:
        f["mon.sem_registro_hoje"] = True
    pontos = serie_esperado(lote, h, params, d)
    if pontos and pontos[-1]["data"] == d:
        res = [p["residuo"] for p in pontos]
        z = series.padronizar(res)
        lam, L = params["ewma_lambda"]["valor"], params["ewma_L"]["valor"]
        ew = series.ewma(z, lam)
        dias, pior = series.corrida_abaixo(res)
        hoje = pontos[-1]
        f.update({"mon.litros_vaca": hoje["observado"], "mon.esperado_vaca": hoje["esperado"],
                  "mon.residuo": hoje["residuo"], "mon.z": z[-1], "mon.ewma": ew[-1],
                  "mon.ewma_limite_inf": -series.limite_ewma(lam, L), "mon.corrida_dias": dias,
                  "mon.corrida_pior": pior, "mon.litros_lote": h.valor("litros", d)})
        lv = [p["observado"] for p in pontos]
        if len(lv) >= 10:
            agora, antes = sum(lv[-3:]) / 3, sum(lv[-10:-7]) / 3
            f["mon.queda_7d"] = agora / antes - 1
    i2 = itu_2d(h, d)
    if i2 is not None:
        f["mon.itu_2d"] = i2

    # --- diário: concentrado e economia
    lv_hoje, conc = litros_vaca(h, d), h.valor("concentrado_kg_vaca", d)
    if lv_hoje and conc:
        f["mon.litros_por_kg_conc"] = lv_hoje / conc
        custo = economics.custo_concentrado_por_litro(conc, fazenda.preco_concentrado, lv_hoje)
        hist = [economics.custo_concentrado_por_litro(c, fazenda.preco_concentrado, litros_vaca(h, dd))
                for dd, c in h.serie("concentrado_kg_vaca", d - timedelta(days=1), 30) if litros_vaca(h, dd)]
        f["mon.custo_conc_litro"] = custo
        if len(hist) >= 10:
            ref = statistics.median(hist)
            f["mon.custo_conc_litro_ref"] = ref
            f["mon.custo_conc_razao"] = custo / ref
    f["mon.razao_precos"] = economics.razao_precos(fazenda.preco_concentrado, fazenda.preco_leite)
    ev = h.ultimo_evento("mudanca_concentrado", fim_do_dia)
    if ev:
        dias_ev = (d - ev.data_hora.date()).days
        if 5 <= dias_ev <= 14:
            antes = [dd for dd in (ev.data_hora.date() - timedelta(days=i) for i in range(1, 6))]
            depois = [d - timedelta(days=i) for i in range(3)]
            la = [litros_vaca(h, x) for x in antes if litros_vaca(h, x)]
            ld = [litros_vaca(h, x) for x in depois if litros_vaca(h, x)]
            ca = [h.valor("concentrado_kg_vaca", x) for x in antes if h.valor("concentrado_kg_vaca", x)]
            cd = [h.valor("concentrado_kg_vaca", x) for x in depois if h.valor("concentrado_kg_vaca", x)]
            if la and ld and ca and cd:
                rm = economics.resposta_marginal(sum(la) / len(la), sum(ld) / len(ld), sum(ca) / len(ca), sum(cd) / len(cd))
                if rm is not None and sum(cd) / len(cd) > sum(ca) / len(ca):
                    f["mon.resposta_marginal"] = rm

    # --- eventos (janelas de supressão e atribuição de causa)
    for tipo, fato in (("movimentacao", "mon.horas_desde_movimentacao"), ("correcao_ms", "mon.horas_desde_correcao_ms")):
        ev = h.ultimo_evento(tipo, fim_do_dia)
        if ev:
            horas = (fim_do_dia - ev.data_hora).total_seconds() / 3600
            if horas <= 24 * 7:
                f[fato] = horas
    ev = h.ultimo_evento("troca_volumoso", fim_do_dia)
    if ev and (d - ev.data_hora.date()).days <= 30:
        f["mon.dias_desde_troca_volumoso"] = (d - ev.data_hora.date()).days
    ev = h.ultimo_evento("silo_novo", fim_do_dia)
    if ev and (d - ev.data_hora.date()).days <= 7:
        f["mon.silo_novo"] = True

    # --- semanal: MS da silagem
    ms_pts = h.serie("ms_silagem", d, 14)
    if ms_pts and dieta:
        silagem = next((i for i in dieta.itens if alimentos.get(i["alimento"], {}).get("id", "").startswith("silagem")), None)
        ref = dieta.ms_silagem_ref or (alimentos[silagem["alimento"]]["ms"] if silagem else None)
        if ref:
            limiar_ms = params["ms_delta_recalcular"]["valor"]
            ultimos = [v for _, v in ms_pts[-2:]]
            confirmadas = 0
            for _, v in reversed(ms_pts):
                if abs(v - ref) >= limiar_ms and (v - ref) * (ultimos[-1] - ref) > 0:
                    confirmadas += 1
                else:
                    break
            atual = sum(ultimos) / len(ultimos)
            f.update({"mon.ms_silagem_formulacao": ref, "mon.ms_silagem_atual": atual,
                      "mon.ms_delta_abs": abs(atual - ref), "mon.ms_leituras_confirmadas": confirmadas})
            if silagem:
                f["mon.silagem_kg_mn_atual"] = silagem["kg_mn"]
                f["mon.silagem_kg_ms"] = silagem["kg_mn"] * ref / 100

    # --- semanal: cocho, ECC, fezes, ruminação
    sob = h.serie("sobras_pct", d, 3)
    if sob:
        f["mon.sobras_mm3"] = sum(v for _, v in sob) / len(sob)
        vazio = 0
        for _, v in reversed(h.serie("sobras_pct", d, 10)):
            if v <= 0.5:
                vazio += 1
            else:
                break
        if vazio:
            f["mon.dias_cocho_vazio"] = vazio
    ecc = h.serie("ecc", d, 42)
    if len(ecc) >= 2:
        perda = max(v for _, v in ecc) - ecc[-1][1]
        if perda > 0:
            f["mon.ecc_perda"] = perda
    fz = h.serie("escore_fezes", d, 7)
    if fz:
        f["mon.fezes"] = fz[-1][1]
    rum = h.serie("ruminacao", d, 10)
    if len(rum) >= 6:
        f["mon.ruminacao_queda"] = sum(v for _, v in rum[:-3]) / len(rum[:-3]) - sum(v for _, v in rum[-3:]) / 3

    # --- mensal: laudo (último dos últimos 35 dias) e tendências
    for ind in INDICADORES_LAUDO:
        pts = h.serie(f"laudo_{ind}", d)
        if pts and (d - pts[-1][0]).days <= 35:
            f[f"laudo.{ind}"] = pts[-1][1]
    gord, prot = h.serie("laudo_gordura", d), h.serie("laudo_proteina", d)
    if len(gord) >= 2 and "laudo.gordura" in f:
        base = [v for _, v in gord[-4:-1]]
        f["laudo.gordura_delta"] = gord[-1][1] - sum(base) / len(base)
    if len(prot) >= 2 and "laudo.proteina" in f:
        base = [v for _, v in prot[-4:-1]]
        f["laudo.proteina_delta_abs"] = abs(prot[-1][1] - sum(base) / len(base))
    for ind in ("ccs", "cbt"):
        pts = h.serie(f"laudo_{ind}", d)
        if pts and f"laudo.{ind}" in f:
            f[f"laudo.{ind}_mg3"] = economics.media_geometrica([v for _, v in pts[-3:]])
            if ind == "ccs" and len(pts) >= 2 and pts[-1][1] >= 1.2 * pts[-2][1]:
                f["laudo.ccs_tendencia"] = "subindo"
    return f
