"""Insumos cadastrados pela fazenda: validação, uso na verificação e na formulação, desativação."""
from datetime import date

import pytest
from sqlmodel import Session, SQLModel, create_engine

from app import services
from app.db.models import Fazenda, Lote

LOTE = dict(nome="L", estado="lactacao", grupo_genetico="girolando", sistema="confinado", pv=550, del_ref=120,
            leite=18, gordura=3.8, proteina=3.2, fracao_primiparas=0.2)
SILAGEM_LAB = dict(nome="Silagem de milho — silo 3 (análise)", tipo="volumoso", ms=34.0, pb=8.2, fdn=48.0, ndt=68.0,
                   ee=3.0, mm=4.0, origem_dado="laboratorio", fonte="Laudo bromatológico 0921", preco_kg_mn=0.27)


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


def test_cadastro_entra_no_catalogo_com_cf_da_origem_e_preco(s):
    a = services.criar_alimento(s, s.get(Fazenda, 1), dict(SILAGEM_LAB))
    cat = services.catalogo(s, 1)
    assert a.codigo.startswith("f1_silagem_de_milho") and cat[a.codigo]["cf"] == 1.0
    assert services.precos_fazenda(s, 1)[a.codigo] == 0.27
    assert services.e_silagem(cat[a.codigo])
    b = services.criar_alimento(s, s.get(Fazenda, 1), dict(SILAGEM_LAB))
    assert b.codigo != a.codigo                     # mesmo nome, código único


@pytest.mark.parametrize("erro", [
    {"nome": " "}, {"tipo": "farelo"}, {"ms": 0}, {"pb": 120}, {"fdn": 70, "pb": 30},
    {"ndt": 0}, {"pastejo": True, "tipo": "concentrado"}, {"origem_dado": "achismo"}, {"preco_kg_mn": None},
])
def test_dados_invalidos_sao_recusados(s, erro):
    with pytest.raises(services.EntradaInvalida):
        services.criar_alimento(s, s.get(Fazenda, 1), SILAGEM_LAB | erro)


def test_insumo_da_fazenda_na_verificacao_e_na_formulacao(s):
    a = services.criar_alimento(s, s.get(Fazenda, 1), dict(SILAGEM_LAB))
    lote = s.get(Lote, 1)
    out = services.avaliar_lote(s, lote, [{"alimento": a.codigo, "kg_mn": 30}, {"alimento": "farelo_soja", "kg_mn": 2.5},
                                          {"alimento": "nucleo_mineral", "kg_mn": 0.2}])
    assert out["fatos"]["dieta.custo_vaca_dia"]["valor"] == pytest.approx(30 * 0.27 + 2.5 * 2.6 + 0.2 * 4.0)
    pl = services.formular_lote(s, lote, [a.codigo, "milho_moido", "farelo_soja", "ureia", "nucleo_mineral"])
    assert pl["pl"]["status"] == "otimo" and a.codigo in {i["alimento"] for i in pl["pl"]["itens"]}
    assert pl["verificacao"]["fatos"]["parecer.dieta"]["valor"] == "adequada"


def test_desativado_sai_da_lista_mas_dieta_antiga_continua_valida(s):
    a = services.criar_alimento(s, s.get(Fazenda, 1), dict(SILAGEM_LAB))
    a.ativo = False
    s.add(a)
    s.commit()
    assert a.codigo not in services.catalogo(s, 1, so_ativos=True)
    out = services.avaliar_lote(s, s.get(Lote, 1), [{"alimento": a.codigo, "kg_mn": 30}])
    assert out["fatos"]["dieta.ms_kg"]["valor"] == pytest.approx(30 * 0.34)


def test_alimento_desconhecido_e_erro_claro(s):
    with pytest.raises(services.EntradaInvalida, match="desconhecido"):
        services.avaliar_lote(s, s.get(Lote, 1), [{"alimento": "f9_nao_existe", "kg_mn": 3}])
