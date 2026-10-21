"""Transforma os registros e eventos do lote em fatos datados (mon.*, laudo.*) para a memória de trabalho.

Aqui só há cálculo numérico (séries, médias, resíduos); quem decide se algo é alerta são as regras ACP.
"""
import statistics
from collections import defaultdict
from datetime import date, datetime, time, timedelta

from ..calc import climate, economics, lactation_curve
from . import series

INDICADORES_LAUDO = ("gordura", "proteina", "lactose", "nul", "ureia", "ccs", "cbt", "crioscopia")


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


TIPOS_TRANSICAO = ("movimentacao", "correcao_ms")


def em_transicao(h: HistoricoLote, d: date, horas: float) -> bool:
    """Dia dentro da janela após movimentação de vacas ou correção de MS: queda transitória esperada."""
    fim = datetime.combine(d, time(23, 59))
    for tipo in TIPOS_TRANSICAO:
        ev = h.ultimo_evento(tipo, fim)
        if ev and (fim - ev.data_hora).total_seconds() / 3600 <= horas:
            return True
    return False


def ajustar_k(lote, h: HistoricoLote, params, ate: date, dias: int = 14) -> float | None:
    """Escala da curva da fazenda ajustada nos primeiros dias DESTA lactação (DEL > 0), excluindo dias de calor
    acima do limiar e dias de transição. Com menos de `calibracao_dias_min` pontos devolve None (curva ainda
    não calibrada: sem alertas de produção)."""
    if lote.k_curva:
        return lote.k_curva
    limiar, _ = parametros_itu(lote, params)
    horas = params["janela_supressao_h"]["valor"]
    obs = []
    for d in sorted(h.por_ind.get("litros", {})):
        if d > ate or len(obs) >= dias:
            break
        t, y, i2 = del_em(lote, d), litros_vaca(h, d), itu_2d(h, d)
        if t is None or t <= 0 or y is None or (i2 is not None and i2 > limiar) or em_transicao(h, d, horas):
            continue
        obs.append((t, y))
    if len(obs) < params["calibracao_dias_min"]["valor"]:
        return None
    return lactation_curve.ajustar_k(obs)


def serie_esperado(lote, h: HistoricoLote, params, ate: date, janela: int = 60) -> list[dict]:
    """Observado × esperado por dia (para o motor e para os gráficos). Dias de transição vêm marcados."""
    k = ajustar_k(lote, h, params, ate)
    if k is None:
        return []
    limiar, perda = parametros_itu(lote, params)
    horas = params["janela_supressao_h"]["valor"]
    pontos = []
    for d, _ in h.serie("litros", ate, janela):
        obs, t = litros_vaca(h, d), del_em(lote, d)
        if obs is None or t is None or t <= 0:
            continue
        i2 = itu_2d(h, d)
        esp = lactation_curve.esperado_por_vaca(t, k, i2, limiar, perda)
        pontos.append({"data": d, "del": t, "observado": obs, "esperado": esp, "itu_2d": i2, "itu": itu_do_dia(h, d),
                       "residuo": series.residuo_relativo(obs, esp), "transicao": em_transicao(h, d, horas)})
    return pontos


def dias_calibrados(lote, h: HistoricoLote, ate: date) -> int:
    return sum(1 for d in h.por_ind.get("litros", {}) if d <= ate and (del_em(lote, d) or 0) > 0)


def leituras_cocho(h: HistoricoLote, d: date, params, dias: int = 10) -> list[dict]:
    """Leituras de cocho por dia (mais antiga primeiro), em % de sobra equivalente. Escore 1–5 convertido pela tabela
    @params.escore_cocho_pct; se no mesmo dia houver sobra pesada, ela prevalece (é medida)."""
    tabela = {int(k): v for k, v in params["escore_cocho_pct"]["valor"].items()}
    pesadas = dict(h.serie("sobras_pct", d, dias))
    escores = dict(h.serie("escore_cocho", d, dias))
    out = []
    for dia in sorted(set(pesadas) | set(escores)):
        if dia in pesadas:
            pct, esc = pesadas[dia], None
        else:
            esc = int(round(escores[dia]))
            pct = tabela.get(esc, tabela[3])
        out.append({"data": dia, "pct": pct, "escore": esc, "vazio": esc == 1 if esc is not None else pct <= 0.5})
    return out


def fatos_monitoramento(lote, fazenda, dieta, h: HistoricoLote, params, alimentos, d: date) -> dict:
    """Fatos mon.* e laudo.* do lote no dia d."""
    f: dict = {}
    fim_do_dia = datetime.combine(d, time(23, 59))
    limiar, _ = parametros_itu(lote, params)
    f["mon.itu_limiar"] = limiar
    f["fazenda.preco_leite"] = fazenda.preco_leite

    # --- diário: produção × esperado
    if lote.estado == "lactacao" and h.valor("litros", d) is None:
        f["mon.sem_registro_hoje"] = True
    if litros_vaca(h, d) is not None:      # produção do dia vale para economia mesmo com a curva ainda calibrando
        f["mon.litros_vaca"], f["mon.litros_lote"] = litros_vaca(h, d), h.valor("litros", d)
    pontos = serie_esperado(lote, h, params, d)
    if lote.estado == "lactacao" and not pontos and h.valor("litros", d) is not None:
        f["mon.calibrando_dias"] = dias_calibrados(lote, h, d)
    if pontos and pontos[-1]["data"] == d:
        uteis = [p for p in pontos if not p["transicao"]]          # transição não entra nos detectores
        res = [p["residuo"] for p in uteis]
        z = series.padronizar(res) if res else [0.0]
        lam, L = params["ewma_lambda"]["valor"], params["ewma_L"]["valor"]
        ew = series.ewma(z, lam)
        dias, pior = series.corrida_abaixo([(p["data"], p["residuo"]) for p in uteis], d,
                                           params["corrida_residuo_min"]["valor"], params["corrida_janela"]["valor"])
        hoje = pontos[-1]
        f.update({"mon.litros_vaca": hoje["observado"], "mon.esperado_vaca": hoje["esperado"],
                  "mon.residuo": hoje["residuo"], "mon.corrida_dias": dias, "mon.corrida_pior": pior,
                  "mon.ewma_limite_inf": -series.limite_ewma(lam, L), "mon.litros_lote": h.valor("litros", d)})
        if not hoje["transicao"]:
            f.update({"mon.z": z[-1], "mon.ewma": ew[-1]})
        # variação de 7 dias por data, com medianas (um dia anômalo não decide)
        lv = [(p["data"], p["observado"]) for p in uteis]
        agora = series.mediana_janela(lv, d - timedelta(days=2), d)
        antes = series.mediana_janela(lv, d - timedelta(days=9), d - timedelta(days=7))
        n_agora = sum(1 for x, _ in lv if d - timedelta(days=2) <= x <= d)
        if agora and antes and n_agora >= 2:
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
    if ev and pontos:
        dias_ev = (d - ev.data_hora.date()).days
        if 5 <= dias_ev <= 14:
            desvio = {p["data"]: p["observado"] - p["esperado"] for p in pontos if not p["transicao"]}  # L/vaca acima da curva
            antes = [ev.data_hora.date() - timedelta(days=i) for i in range(1, 6)]
            depois = [d - timedelta(days=i) for i in range(3)]
            da = [desvio[x] for x in antes if x in desvio]
            dd = [desvio[x] for x in depois if x in desvio]
            ca = [h.valor("concentrado_kg_vaca", x) for x in antes if h.valor("concentrado_kg_vaca", x)]
            cd = [h.valor("concentrado_kg_vaca", x) for x in depois if h.valor("concentrado_kg_vaca", x)]
            if da and dd and ca and cd and sum(cd) / len(cd) > sum(ca) / len(ca):
                # ΔL/Δkg medido sobre o desvio da curva: desconta a queda natural da lactação no período
                f["mon.resposta_marginal"] = economics.resposta_marginal(
                    sum(da) / len(da), sum(dd) / len(dd), sum(ca) / len(ca), sum(cd) / len(cd))

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
        silagem = next((i for i in dieta.itens if alimentos.get(i["alimento"], {}).get("tipo") == "volumoso"
                        and "silagem" in alimentos.get(i["alimento"], {}).get("nome", "").lower()), None)
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

    # --- diário: leitura de cocho (escore 1–5) ou sobras pesadas (%); no mesmo dia, a pesagem prevalece
    leituras = leituras_cocho(h, d, params, dias=10)
    recentes = [l for l in leituras if l["data"] > d - timedelta(days=3)]
    if recentes:
        pct = sum(l["pct"] for l in recentes) / len(recentes)
        f["mon.sobras_mm3"] = pct
        if len(recentes) >= 3:      # "3 dias fora da meta" (Inferências): menor e maior leitura dos 3 dias
            f["mon.sobras_min3"] = min(l["pct"] for l in recentes)
            f["mon.sobras_max3"] = max(l["pct"] for l in recentes)
        escores = [l["escore"] for l in recentes if l["escore"] is not None]
        if len(escores) == len(recentes):
            f["mon.sobras_texto"] = f"escore médio {sum(escores) / len(escores):.1f} (≈ {pct:.1f}% de sobra)"
        else:
            f["mon.sobras_texto"] = f"{pct:.1f}% de sobra" + (" (pesada)" if not escores else " (pesagem e escore)")
        vazio = 0
        for l in reversed(leituras):
            if l["vazio"] and (d - l["data"]).days == vazio:
                vazio += 1
            else:
                break
        if vazio:
            f["mon.dias_cocho_vazio"] = vazio

    # --- semanal: ECC, fezes, ruminação
    ecc = [v for _, v in h.serie("ecc", d, 42)]
    if len(ecc) >= 2:
        # mediana de 3 nos pontos internos: uma leitura isolada fora da curva não vira "perda de ECC",
        # mas as pontas ficam como medidas (senão uma tendência real de queda é achatada)
        suave = [statistics.median(ecc[i - 1:i + 2]) if 0 < i < len(ecc) - 1 else ecc[i] for i in range(len(ecc))]
        perda = max(suave) - suave[-1]
        if perda > 0:
            f["mon.ecc_perda"] = perda
    fz = h.serie("escore_fezes", d, 7)
    if fz:
        f["mon.fezes"] = fz[-1][1]
    dist = h.serie("distancia_km", d, 30)
    if len(dist) >= 2:
        f["mon.distancia_delta"] = dist[-1][1] - dist[0][1]
    for ind in ("altura_entrada", "altura_saida", "altura_media"):       # régua no pasto (última leitura da semana)
        pts = h.serie(ind, d, 7)
        if pts:
            f[f"mon.{ind}"] = pts[-1][1]
    rum = h.serie("ruminacao", d, 10)
    if len(rum) >= 6:
        f["mon.ruminacao_queda"] = sum(v for _, v in rum[:-3]) / len(rum[:-3]) - sum(v for _, v in rum[-3:]) / 3

    # --- mensal: laudo (último dos últimos 35 dias), base de comparação até 120 dias, média geométrica de 3 meses
    janela_laudo, janela_base = params["laudo_validade_dias"]["valor"], params["laudo_base_dias"]["valor"]
    for ind in INDICADORES_LAUDO:
        pts = h.serie(f"laudo_{ind}", d)
        if pts and (d - pts[-1][0]).days <= janela_laudo:
            f[f"laudo.{ind}"] = pts[-1][1]
    for ind, fato in (("gordura", "laudo.gordura_delta"), ("proteina", "laudo.proteina_delta_abs")):
        pts = h.serie(f"laudo_{ind}", d, janela_base)
        if len(pts) >= 2 and f"laudo.{ind}" in f:
            base = [v for _, v in pts[-4:-1]]
            delta = pts[-1][1] - sum(base) / len(base)
            f[fato] = abs(delta) if fato.endswith("_abs") else delta
    for ind in ("ccs", "cbt"):
        pts = h.serie(f"laudo_{ind}", d, 100)          # ~3 meses
        if f"laudo.{ind}" not in f:
            continue
        if len(pts) >= 3:                               # IN 76: média geométrica de 3 meses exige 3 amostras
            f[f"laudo.{ind}_mg3"] = economics.media_geometrica([v for _, v in pts[-3:]])
        if ind == "ccs" and len(pts) >= 2 and pts[-1][1] >= 1.2 * pts[-2][1] \
                and pts[-1][1] >= params["ccs_tendencia_min"]["valor"]:
            f["laudo.ccs_tendencia"] = "subindo"
    return f
