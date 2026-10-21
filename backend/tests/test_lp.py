"""PL de custo mínimo: solução viável que respeita as restrições e diagnóstico de inviabilidade."""
from pytest import approx

from app.engine.rules_loader import carregar
from app.optimizer.lp import formular

A = carregar().alimentos
R = {"cms": 16.0, "ms_min": 15.2, "ms_max": 16.8, "fator_ms_min": 0.95, "ell_min": 24.0, "pb_min": 15.0, "pb_max": 18.0, "fdn_min": 28.0,
     "fdnf_min": 19.0, "cnf_max": 44.0, "ee_max": 6.0, "ureia_max": 1.0, "fdn_max_kg": 6.9}


def test_pl_viavel_lote_girolando():
    alimentos = [A[i] for i in ("silagem_milho", "milho_moido", "farelo_soja", "nucleo_mineral", "ureia")]
    res = formular(alimentos, R)
    assert res["status"] == "otimo"
    c = res["composicao"]
    assert R["ms_min"] - 1e-6 <= c["ms_kg"] <= R["ms_max"] + 1e-6
    assert c["ell_mcal"] >= R["ell_min"] - 1e-6
    assert R["pb_min"] - 1e-6 <= c["pb_pct"] <= R["pb_max"] + 1e-6
    assert c["fdn_pct"] >= R["fdn_min"] - 1e-6 and c["fdnf_pct"] >= R["fdnf_min"] - 1e-6
    assert c["ureia_pct"] <= 1.0 + 1e-6
    assert res["custo"] == approx(c["custo_vaca_dia"], rel=1e-6)


def test_pl_inviavel_cana_e_nucleo_para_alta_producao():
    r = R | {"cms": 20.0, "ms_min": 19.0, "ms_max": 21.0, "ell_min": 32.0, "pb_min": 16.0, "pb_max": 19.0, "fdn_max_kg": 7.5}
    res = formular([A["cana"], A["nucleo_mineral"]], r)
    assert res["status"] == "inviavel"
    assert "energia" in res["restricoes_violadas"] or "proteina" in res["restricoes_violadas"]


def test_pl_so_energia_inatingivel_devolve_melhor_dieta_possivel():
    alimentos = [A[i] for i in ("silagem_milho", "milho_moido", "farelo_soja", "nucleo_mineral")]
    res = formular(alimentos, R | {"ell_min": 40.0})
    assert res["status"] == "parcial"
    assert res["restricoes_violadas"] == ["energia"]
    assert res["deficit"]["energia_mcal"] > 0
    c = res["composicao"]                      # o resto das restrições continua valendo
    assert c["fdn_pct"] >= R["fdn_min"] - 1e-6 and c["ee_pct"] <= R["ee_max"] + 1e-6


def test_pl_inviavel_volumoso_fibroso_aponta_varias_restricoes():
    alimentos = [A[i] for i in ("capim_elefante", "farelo_soja", "nucleo_mineral")]
    res = formular(alimentos, R | {"ell_min": 30.0})
    assert res["status"] == "inviavel"
    assert "energia" in res["restricoes_violadas"] and "enchimento" in res["restricoes_violadas"]


def test_dieta_sugerida_arredondada_passa_na_verificacao():
    """Regressão: ureia no limite exato + arredondamento para cima bloqueava a dieta (VER-04)."""
    from app import services
    fatos = {"lote.estado": "lactacao", "lote.del": 60, "lote.grupo_genetico": "girolando", "lote.sistema": "confinado",
             "lote.pv": 480, "lote.leite": 18, "lote.gordura": 3.8, "lote.proteina": 3.2, "lote.fracao_primiparas": 1.0}
    out = services.formular(fatos, ["silagem_milho", "milho_moido", "farelo_soja", "ureia", "nucleo_mineral"])
    assert out["pl"]["status"] == "otimo"
    assert out["verificacao"]["fatos"]["parecer.dieta"]["valor"] != "bloqueada"


def test_pl_nao_sugere_dieta_que_a_verificacao_reprova():
    """Regressão: com todos os alimentos, o PL escolhia cana como único volumoso e a VER-07 reprovava a sugestão."""
    from app import services
    fatos = {"lote.estado": "lactacao", "lote.del": 104, "lote.grupo_genetico": "girolando", "lote.sistema": "confinado",
             "lote.pv": 560, "lote.leite": 21, "lote.gordura": 3.3, "lote.proteina": 3.22, "lote.fracao_primiparas": 0.25,
             "lote.ecc": 2.75}
    out = services.formular(fatos, list(services.kb().alimentos))
    assert out["pl"]["status"] == "otimo"
    verif = out["verificacao"]
    assert verif["fatos"]["parecer.dieta"]["valor"] == "adequada", [a["titulo"] for a in verif["alertas"]]
    assert "braquiaria" not in [i["alimento"] for i in out["pl"]["itens"]]   # confinado não pasteja (FOR-06)


def test_pl_so_com_cana_aponta_falta_de_outro_volumoso():
    from app import services
    fatos = {"lote.estado": "lactacao", "lote.del": 104, "lote.grupo_genetico": "girolando", "lote.sistema": "confinado",
             "lote.pv": 560, "lote.leite": 21, "lote.gordura": 3.3, "lote.proteina": 3.22}
    out = services.formular(fatos, ["cana", "milho_moido", "farelo_soja", "ureia", "nucleo_mineral"])
    assert out["pl"]["status"] == "inviavel" and "cana" in out["pl"]["restricoes_violadas"]
    assert "FOR-15" in [a["regra"] for a in out["alertas"]]
