"""PL de custo mínimo: solução viável que respeita as restrições e diagnóstico de inviabilidade."""
from pytest import approx

from app.engine.rules_loader import carregar
from app.optimizer.lp import formular

A = carregar().alimentos
R = {"cms": 16.0, "folga_ms": 0.8, "ell_min": 24.0, "pb_min": 15.0, "pb_max": 18.0, "fdn_min": 28.0,
     "fdnf_min": 19.0, "cnf_max": 44.0, "ee_max": 6.0, "ureia_max": 1.0, "fdn_max_kg": 6.9}


def test_pl_viavel_lote_girolando():
    alimentos = [A[i] for i in ("silagem_milho", "milho_moido", "farelo_soja", "nucleo_mineral", "ureia")]
    res = formular(alimentos, R)
    assert res["status"] == "otimo"
    c = res["composicao"]
    assert R["cms"] - R["folga_ms"] - 1e-6 <= c["ms_kg"] <= R["cms"] + R["folga_ms"] + 1e-6
    assert c["ell_mcal"] >= R["ell_min"] - 1e-6
    assert R["pb_min"] - 1e-6 <= c["pb_pct"] <= R["pb_max"] + 1e-6
    assert c["fdn_pct"] >= R["fdn_min"] - 1e-6 and c["fdnf_pct"] >= R["fdnf_min"] - 1e-6
    assert c["ureia_pct"] <= 1.0 + 1e-6
    assert res["custo"] == approx(c["custo_vaca_dia"], rel=1e-6)


def test_pl_inviavel_cana_e_nucleo_para_alta_producao():
    r = R | {"cms": 20.0, "folga_ms": 1.0, "ell_min": 32.0, "pb_min": 16.0, "pb_max": 19.0, "fdn_max_kg": 7.5}
    res = formular([A["cana"], A["nucleo_mineral"]], r)
    assert res["status"] == "inviavel"
    assert "energia" in res["restricoes_violadas"] or "proteina" in res["restricoes_violadas"]


def test_pl_inviavel_so_por_energia():
    alimentos = [A[i] for i in ("silagem_milho", "milho_moido", "farelo_soja", "nucleo_mineral")]
    res = formular(alimentos, R | {"ell_min": 40.0})
    assert res["status"] == "inviavel"
    assert res["restricoes_violadas"] == ["energia"]


def test_pl_inviavel_volumoso_fibroso_aponta_varias_restricoes():
    alimentos = [A[i] for i in ("capim_elefante", "farelo_soja", "nucleo_mineral")]
    res = formular(alimentos, R | {"ell_min": 30.0})
    assert res["status"] == "inviavel"
    assert "energia" in res["restricoes_violadas"] and "enchimento" in res["restricoes_violadas"]
