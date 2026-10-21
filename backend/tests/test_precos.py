"""Preços por fazenda: vigente = registro mais recente; valem na verificação, na formulação e no acompanhamento."""
from datetime import date, timedelta

import pytest
from sqlmodel import Session, SQLModel, create_engine

from app import services
from app.db.models import Fazenda, Lote

LOTE = dict(nome="L", estado="lactacao", grupo_genetico="girolando", sistema="confinado", pv=550, del_ref=120,
            leite=18, gordura=3.8, proteina=3.2, fracao_primiparas=0.2)
ALIMENTOS = ["silagem_milho", "milho_moido", "polpa_citrica", "farelo_soja", "ureia", "nucleo_mineral"]


@pytest.fixture
def s():
    eng = create_engine("sqlite://")
    SQLModel.metadata.create_all(eng)
    with Session(eng) as sessao:
        faz = Fazenda(nome="F")
        sessao.add(faz)
        sessao.commit()
        sessao.add(Lote(fazenda_id=faz.id, data_ref=date.today(), **LOTE))
        sessao.commit()
        yield sessao


def test_preco_vigente_e_historico(s):
    faz = s.get(Fazenda, 1)
    ontem = date.today() - timedelta(days=1)
    services.registrar_precos(s, faz, {"milho_moido": 1.30}, ontem, "cotação cooperativa")
    services.registrar_precos(s, faz, {"milho_moido": 1.55, "leite": 2.80}, date.today(), "nota fiscal")
    assert services.precos_fazenda(s, 1) == {"milho_moido": 1.55}
    assert [p.preco for p in services.historico_precos(s, 1)["milho_moido"]] == [1.55, 1.30]
    assert faz.preco_leite == 2.80


def test_preco_da_fazenda_muda_custo_e_escolha_da_formulacao(s):
    lote = s.get(Lote, 1)
    antes = services.formular_lote(s, lote, ALIMENTOS)
    usa_milho = {i["alimento"]: i["kg_mn"] for i in antes["pl"]["itens"]}.get("milho_moido", 0)
    services.registrar_precos(s, s.get(Fazenda, 1), {"milho_moido": 4.00}, date.today(), "teste")
    depois = services.formular_lote(s, lote, ALIMENTOS)
    assert depois["pl"]["status"] == "otimo"
    assert {i["alimento"]: i["kg_mn"] for i in depois["pl"]["itens"]}.get("milho_moido", 0) < usa_milho
    assert depois["verificacao"]["fatos"]["dieta.custo_vaca_dia"]["valor"] == pytest.approx(depois["pl"]["custo"], rel=0.01)


def test_avaliacao_usa_preco_da_fazenda(s):
    itens = [{"alimento": "silagem_milho", "kg_mn": 30}, {"alimento": "milho_moido", "kg_mn": 4}]
    ref = services.avaliar_lote(s, s.get(Lote, 1), itens)["fatos"]["dieta.custo_vaca_dia"]["valor"]
    services.registrar_precos(s, s.get(Fazenda, 1), {"silagem_milho": 0.35}, date.today(), "")
    novo = services.avaliar_lote(s, s.get(Lote, 1), itens)["fatos"]["dieta.custo_vaca_dia"]["valor"]
    assert novo == pytest.approx(ref + 30 * (0.35 - 0.25))


@pytest.mark.parametrize("precos", [{"milho_moido": 0}, {"milho_moido": -1}, {"inexistente": 1.0}])
def test_preco_invalido_e_rejeitado(s, precos):
    with pytest.raises(services.EntradaInvalida):
        services.registrar_precos(s, s.get(Fazenda, 1), precos, date.today(), "")
