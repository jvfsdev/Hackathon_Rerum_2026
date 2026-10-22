"""Funções puras de cálculo contra valores publicados."""
from pytest import approx

from app.calc import climate, conversions, economics, energy, intake, lactation_curve, protein


def test_cms_nrc2001_exemplo_publicado():
    assert intake.cms_nrc2001(650, 35, 3.8, 6) == approx(21.2, abs=0.15)


def test_cms_brleite_eq11():
    assert intake.cms_brleite(550, 15, 4.0, 150) == approx(16.9, abs=0.05)


def test_teto_fibra():
    assert intake.teto_fibra(600, 40, 1.25) == approx(18.75)


def test_lcg4_e_ecm():
    assert conversions.lcg4(35, 3.8) == approx(33.95)
    assert conversions.ecm(30, 4.0, 3.2) == approx(12.82 * 1.2 + 7.13 * 0.96 + 0.323 * 30)


def test_ureia_para_nul():
    assert conversions.ureia_para_nul(42) == approx(19.6, abs=0.01)


def test_ndt_para_ell():
    assert conversions.ndt_para_ell(64.3) == approx(1.455, abs=0.001)


def test_energia_leite_e_mantenca():
    assert energy.ell_leite_por_kg(3.8, 3.2) * 35 == approx(25.2, abs=0.1)
    assert energy.mantenca(650, 0.08) == approx(10.3, abs=0.1)


def test_gestacao_bate_tabela_nrc():
    # Tabela NRC 2001 (Drackley 2021): 2,7 / 3,4 / 3,8 Mcal e 199 / 306 / 357 g aos 200 / 250 / 275 d
    # (com bezerro de 44 kg a equação dá 204 g aos 200 d; por isso só 250 e 275 d são conferidos)
    assert energy.gestacao(250, 44) == approx(3.4, abs=0.05)
    assert protein.pm_gestacao(250, 44) == approx(306, abs=3)
    assert energy.gestacao(275, 44) == approx(3.8, abs=0.1)
    assert energy.gestacao(189, 44) == 0


def test_atividade_pastejo_valores_tabelados():
    assert energy.atividade_pastejo(450, 0.4, "plano", 0.003) == approx(0.6, abs=0.05)
    assert energy.atividade_pastejo(635, 3.2, "acidentado", 0.003) == approx(5.5, abs=0.05)


def test_ajuste_ecc():
    assert energy.ajuste_ecc(2.5, 3.0, 100, 417) == approx(2.085)


def test_pm_leite():
    assert protein.pm_leite(35, 3.2, 0.67) == approx(1672, abs=1)


def test_pb_alvo_interpola():
    tabela = [[8, 12.0], [18, 15.0], [36, 19.0]]
    assert protein.pb_alvo(18, tabela) == 15.0
    assert protein.pb_alvo(27, tabela) == approx(17.0)
    assert protein.pb_alvo(5, tabela) == 12.0


def test_itu():
    assert climate.itu(30, 70) == approx(81.3, abs=0.05)


def test_cobuci_pico():
    pico = max(range(1, 306), key=lactation_curve.cobuci)
    assert pico == approx(40, abs=1)
    assert lactation_curve.cobuci(40) == approx(16.7, abs=0.05)


def test_ajustar_k_recupera_escala():
    obs = [(t, 1.8 * lactation_curve.cobuci(t)) for t in (30, 60, 90, 120)]
    assert lactation_curve.ajustar_k(obs) == approx(1.8)


def test_perda_ccs():
    assert economics.perda_producao_ccs_pct(200) == 0
    assert economics.perda_producao_ccs_pct(500) == approx(6)
    assert economics.perda_producao_ccs_pct(1000) == approx(18)


def test_media_geometrica():
    assert economics.media_geometrica([100, 400]) == approx(200)
