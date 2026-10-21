"""Leitura de cocho diária: escore 1–5 (convertido em % de sobra equivalente) ou sobras pesadas (prevalecem)."""
from datetime import date, timedelta

from test_auditoria import lote_sintetico, sessao_memoria  # noqa: F401 (fixture)

from app import services
from app.monitor.fatos import HistoricoLote, leituras_cocho

KB = services.kb()


class R:  # registro mínimo para o histórico
    def __init__(self, d, ind, v):
        self.data, self.indicador, self.valor = d, ind, v


def test_escore_vira_percentual_e_pesagem_prevalece_no_mesmo_dia():
    hoje = date.today()
    h = HistoricoLote([R(hoje - timedelta(days=1), "escore_cocho", 4), R(hoje, "escore_cocho", 3),
                       R(hoje, "sobras_pct", 2.2)], [])
    l = leituras_cocho(h, hoje, KB.params)
    assert [(x["pct"], x["escore"]) for x in l] == [(7.5, 4), (2.2, None)]


def test_escore_1_em_dias_seguidos_e_cocho_vazio_e_alerta_cita_o_escore(sessao_memoria):
    s = sessao_memoria
    lote, d0 = lote_sintetico(s, del0=30, extra={(37, "escore_cocho"): 1, (38, "escore_cocho"): 1, (39, "escore_cocho"): 1})
    out = services.monitorar(s, lote, date.today())
    assert out["fatos"]["mon.dias_cocho_vazio"]["valor"] == 3
    assert "escore médio" in out["fatos"]["mon.sobras_texto"]["valor"]
    regras = {a["regra"]: a for a in out["alertas"]}
    assert "ACP-06" in regras and "ACP-S03" in regras and "escore" in regras["ACP-S03"]["titulo"]


def test_escore_na_meta_nao_gera_alerta(sessao_memoria):
    s = sessao_memoria
    lote, _ = lote_sintetico(s, del0=120, extra={(i, "escore_cocho"): 3 for i in range(35, 40)})
    regras = {a["regra"] for a in services.monitorar(s, lote, date.today())["alertas"]}
    assert not regras & {"ACP-S03", "ACP-S04", "ACP-06", "ACP-06B"}


def test_um_dia_fora_da_meta_nao_dispara(sessao_memoria):
    s = sessao_memoria
    lote, _ = lote_sintetico(s, del0=120, extra={(37, "escore_cocho"): 3, (38, "escore_cocho"): 4, (39, "escore_cocho"): 3})
    regras = {a["regra"] for a in services.monitorar(s, lote, date.today())["alertas"]}
    assert not regras & {"ACP-S03", "ACP-S04"}
    lote2, _ = lote_sintetico(s, del0=120, extra={(i, "escore_cocho"): 4 for i in (37, 38, 39)})
    assert "ACP-S04" in {a["regra"] for a in services.monitorar(s, lote2, date.today())["alertas"]}
