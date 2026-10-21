"""Coleta de preços de referência: isolamento de falhas, plausibilidade, deduplicação e uso no catálogo."""
from datetime import date, timedelta

import pytest
from sqlmodel import Session, SQLModel, create_engine

from app import services
from app.db.models import Fazenda
from app.referencias import coletor
from app.referencias.base import Cotacao, Fonte


class FonteFalsa(Fonte):
    def __init__(self, nome, cotacoes=None, erro=None):
        self.nome, self._c, self._erro = nome, cotacoes or [], erro

    def coletar(self):
        if self._erro:
            raise self._erro
        return self._c


@pytest.fixture
def s():
    eng = create_engine("sqlite://")
    SQLModel.metadata.create_all(eng)
    with Session(eng) as sessao:
        sessao.add(Fazenda(nome="F"))
        sessao.commit()
        yield sessao


def test_converte_unidade_e_entra_no_catalogo(s):
    ontem = date.today() - timedelta(days=1)
    coletor.coletar(s, [FonteFalsa("Teste", [Cotacao("milho_moido", 72.0, "R$/saca 60 kg", ontem, "Campinas-SP")])])
    a = services.catalogo(s, 1)["milho_moido"]
    assert a["preco_kg_mn"] == pytest.approx(1.20)
    assert a["preco_ref"]["fonte"] == "Teste" and a["preco_ref"]["data"] == ontem.isoformat()


def test_falha_de_uma_fonte_nao_afeta_as_outras_nem_apaga_valores(s):
    hoje = date.today()
    coletor.coletar(s, [FonteFalsa("A", [Cotacao("farelo_soja", 2500.0, "R$/tonelada", hoje)])])
    r = coletor.coletar(s, [FonteFalsa("Quebrada", erro=ConnectionError("sem internet")),
                            FonteFalsa("B", [Cotacao("milho_moido", 1.3, "R$/kg", hoje)])])
    assert r["Quebrada"]["ok"] is False and "sem internet" in r["Quebrada"]["erro"]
    assert r["B"]["ok"] is True
    vig = coletor.vigentes(s)
    assert vig["farelo_soja"].preco == pytest.approx(2.5) and vig["milho_moido"].preco == pytest.approx(1.3)


def test_valor_implausivel_e_descartado_e_cotacao_repetida_nao_duplica(s):
    hoje = date.today()
    fonte = FonteFalsa("A", [Cotacao("milho_moido", 7200.0, "R$/kg", hoje), Cotacao("farelo_soja", 2.6, "R$/kg", hoje)])
    r = coletor.coletar(s, [fonte])
    assert r["A"]["descartadas"] and "milho_moido" not in coletor.vigentes(s)
    r2 = coletor.coletar(s, [fonte])
    assert r2["A"]["novas"] == 0


def test_preco_da_fazenda_prevalece_sobre_a_referencia(s):
    coletor.coletar(s, [FonteFalsa("A", [Cotacao("milho_moido", 1.30, "R$/kg", date.today())])])
    services.registrar_precos(s, s.get(Fazenda, 1), {"milho_moido": 1.60}, date.today(), "nota fiscal")
    cat = services.catalogo(s, 1)
    assert services.alimento_com_preco("milho_moido", services.precos_fazenda(s, 1), cat)["preco_kg_mn"] == 1.60


# ------------------------------------------------------------------ leitura das páginas (sem internet)
from app.referencias.fontes import ler_cepea_leite, ler_cepea_milho, ler_ipeadata  # noqa: E402

PAGINA_MILHO = """<p>Nota: Reais por saca de 60 kg, &agrave; vista</p><table><tr><th>&nbsp;</th><th>Valor R$*</th>
<th>Var./Dia</th></tr><tr><td>20/10/2026</td><td>64,34</td><td>-0,62%</td></tr><tr><td>19/10/2026</td><td>64,74</td></tr></table>"""
PAGINA_LEITE = """<table><tr><th>&nbsp;</th><th>Estado</th><th>Preço médio</th></tr><tr><td>ago/26</td><td>RS</td>
<td>2,6545</td></tr><tr><td>ago/26</td><td>MG</td><td>3,0446</td></tr></table>"""


def test_le_indicador_do_milho_cepea():
    c = ler_cepea_milho(PAGINA_MILHO)
    assert (c.item, c.valor, c.data) == ("milho_moido", 64.34, date(2026, 10, 20))
    assert c.preco_convertido() == pytest.approx(1.0723, abs=1e-4)


def test_layout_do_milho_mudou_e_erro_nao_valor_errado():
    with pytest.raises(ValueError):
        ler_cepea_milho(PAGINA_MILHO.replace("saca de 60 kg", "tonelada"))


def test_le_leite_ao_produtor_de_mg():
    c = ler_cepea_leite(PAGINA_LEITE)
    assert (c.item, c.valor, c.data, c.unidade) == ("leite", 3.0446, date(2026, 8, 1), "R$/L")


def test_le_serie_ipeadata():
    c = ler_ipeadata({"value": [{"VALDATA": "2026-08-01T00:00:00-03:00", "VALVALOR": 2100.0},
                                {"VALDATA": "2026-09-01T00:00:00-03:00", "VALVALOR": 2171.4}]}, "farelo_soja", "R$/tonelada", "PR")
    assert c.data == date(2026, 9, 1) and c.preco_convertido() == pytest.approx(2.1714)
