"""Itens do plano e dos documentos de referência implementados por último: NASEM com ECC, FDND, gestação/secagem/
pré-parto, caminhada em pasto, altura do pasto, crioscopia, bonificação, IOFC, eficiência alimentar, Pearson, CSV."""
from dataclasses import replace
from datetime import date

import pytest
from pytest import approx
from sqlmodel import Session, SQLModel, create_engine

from app import services
from app.calc import economics
from app.db.models import Fazenda, Lote, Registro
from app.engine.engine import Motor
from app.importacao import MODELOS, ler

KB = services.kb()
HOLANDES = {"lote.estado": "lactacao", "lote.del": 42, "lote.grupo_genetico": "holandes", "lote.sistema": "confinado",
            "lote.pv": 650, "lote.leite": 35, "lote.gordura": 3.8, "lote.proteina": 3.2, "lote.fracao_primiparas": 0.0}


def rodar(fatos, modulos, kb=KB, itens=None):
    wm = services.memoria(fatos)
    if itens:
        wm.declarar("dieta.itens", itens, cf=1.0, origem="usuario")
    return Motor(kb, modulos).executar(wm)


def alertas(r):
    return {a.regra for a in r.alertas if a.status == "ativo"}


def com_param(nome, valor):
    params = dict(KB.params)
    params[nome] = params[nome] | {"valor": valor}
    return replace(KB, params=params)


SEM = ["classificacao", "acompanhamento_semanal", "meta"]
MEN = ["classificacao", "acompanhamento_mensal", "meta"]
DIA = ["classificacao", "acompanhamento_diario", "meta"]


def test_exg08_nasem_com_ecc_e_opcao_configuravel():
    fatos = HOLANDES | {"lote.ecc": 3.0}
    r = rodar(fatos, ["classificacao", "exigencias"])
    assert r.wm.valor("perfil.equacao_cms") == "nrc2001"           # padrão continua NRC 2001
    r = rodar(fatos, ["classificacao", "exigencias"], com_param("equacao_cms_com_ecc", "nasem2021"))
    assert r.wm.valor("perfil.equacao_cms") == "nasem2021" and r.wm.valor("exig.cms_equacao") == approx(22.82, abs=0.02)


def test_exg09_fdnd_do_volumoso_ajusta_o_consumo():
    silagem = KB.alimentos["silagem_milho"] | {"fdnd": 60}       # 10 pontos acima da referência (50)
    itens = [{"alimento": silagem, "kg_mn": 30}, {"alimento": KB.alimentos["farelo_soja"], "kg_mn": 2}]
    r = rodar(HOLANDES, ["classificacao", "exigencias"], itens=itens)
    assert r.wm.valor("exig.cms_ajuste_fdnd") == approx(1.7)
    assert r.wm.valor("exig.cms") == approx(min(r.wm.valor("exig.cms_equacao") + 1.7, r.wm.valor("exig.cms_teto_fibra")))


@pytest.mark.parametrize("gestacao,espera", [(192, True), (200, False), (180, False)])
def test_acp12_aviso_ao_entrar_nos_190_dias(gestacao, espera):
    r = rodar(HOLANDES | {"lote.dias_gestacao": gestacao}, SEM)
    assert ("ACP-12" in alertas(r)) is espera


def test_secagem_e_pre_parto_pelas_datas_previstas():
    r = rodar(HOLANDES | {"lote.del": 280, "lote.dias_gestacao": 225}, SEM)
    assert "ACP-SEC" in alertas(r) and r.wm.valor("mon.dias_para_parto_previsto") == 55
    r = rodar({"lote.estado": "seca", "lote.dias_para_parto": 15, "lote.fracao_primiparas": 0.3}, SEM)
    assert "ACP-PRE" in alertas(r)
    r = rodar({"lote.estado": "seca", "lote.dias_para_parto": 40}, SEM)
    assert "ACP-PRE" not in alertas(r)


def test_acp11_caminhada_maior_com_perda_de_ecc_em_pasto():
    base = {"lote.estado": "lactacao", "lote.del": 150, "lote.sistema": "pasto", "mon.ecc_perda": 0.6}
    assert "ACP-11" in alertas(rodar(base | {"mon.distancia_delta": 1.0}, SEM))
    assert "ACP-11" not in alertas(rodar(base | {"mon.distancia_delta": 0.2}, SEM))


def test_altura_do_pasto_por_forrageira():
    rot = {"lote.estado": "lactacao", "lote.del": 150, "lote.sistema": "pasto", "lote.forrageira": "mombaca"}
    assert {"ACP-P1", "ACP-P2"} <= alertas(rodar(rot | {"mon.altura_entrada": 110, "mon.altura_saida": 20}, SEM))
    assert not {"ACP-P1", "ACP-P2"} & alertas(rodar(rot | {"mon.altura_entrada": 95, "mon.altura_saida": 40}, SEM))
    cont = rot | {"lote.forrageira": "decumbens"}
    assert "ACP-P3" in alertas(rodar(cont | {"mon.altura_media": 15}, SEM))
    assert "ACP-P3" not in alertas(rodar(cont | {"mon.altura_media": 26}, SEM))


@pytest.mark.parametrize("crio,espera", [(-0.510, True), (-0.560, True), (-0.540, False)])
def test_crioscopia(crio, espera):
    assert ("ACP-M09" in alertas(rodar({"laudo.crioscopia": crio}, MEN))) is espera


def test_iofc_e_eficiencia_alimentar():
    assert "ACP-D08" in alertas(rodar({"mon.alimento_pct_receita": 65, "mon.iofc": 8.0}, DIA))
    meio = {"lote.estado": "lactacao", "lote.del": 180, "lote.gordura": 3.5, "lote.proteina": 3.1, "mon.cms_medido": 20}
    r = rodar(meio | {"mon.litros_vaca": 20}, DIA)
    assert r.wm.valor("mon.ea") == approx(0.99, abs=0.01) and "ACP-EA1" in alertas(r)
    assert "ACP-EA1" not in alertas(rodar(meio | {"mon.litros_vaca": 30}, DIA))
    inicio = meio | {"lote.del": 40, "mon.cms_medido": 12, "mon.litros_vaca": 30}
    assert "ACP-EA2" in alertas(rodar(inicio, DIA))


def test_bonificacao_do_laticinio_no_acompanhamento():
    tabela = {"ccs": [{"max": 200, "rs_l": 0.03}, {"min": 200.01, "max": 400, "rs_l": 0.0}, {"min": 400.01, "rs_l": -0.03}],
              "cbt": [{"max": 100, "rs_l": 0.02}, {"min": 100.01, "rs_l": -0.02}]}
    b = economics.bonificacao({"ccs": 520, "cbt": 90}, tabela)
    assert b["total"] == approx(-0.01) and b["perda_vs_maximo"] == approx(0.06)
    eng = create_engine("sqlite://")
    SQLModel.metadata.create_all(eng)
    with Session(eng) as s:
        faz = Fazenda(nome="F", bonificacao=tabela)
        s.add(faz)
        s.commit()
        lote = Lote(fazenda_id=faz.id, nome="L", grupo_genetico="girolando", pv=520, data_ref=date.today(), del_ref=150)
        s.add(lote)
        s.commit()
        for ind, v in {"vacas": 20, "litros": 300, "laudo_ccs": 520, "laudo_cbt": 90}.items():
            s.add(Registro(lote_id=lote.id, data=date.today(), indicador=ind, valor=v))
        s.commit()
        out = services.monitorar(s, lote, date.today())
        assert out["fatos"]["mon.bonificacao_perda_rs_mes"]["valor"] == approx(0.06 * 300 * 30)
        assert "ACP-M08" in {a["regra"] for a in out["alertas"]}


def test_quadrado_de_pearson():
    r = economics.quadrado_de_pearson(9.0, 48.8, 18.0)
    assert r["pct_a"] * 9.0 / 100 + r["pct_b"] * 48.8 / 100 == approx(18.0)
    with pytest.raises(ValueError):
        economics.quadrado_de_pearson(9.0, 48.8, 50.0)


def test_importacao_csv_previa_e_erros():
    r = ler(MODELOS["diario"])
    assert not r["erros"] and len(r["registros"]) == 14 and r["periodo"] == [date(2026, 10, 20), date(2026, 10, 21)]
    r = ler("Data,Leite (L),CCS,Coluna estranha\n01/10/2026,\"1.234,5\",abc,x\n31/02/2026,10,200,y\n02/10/2026,10,99999,z")
    assert r["colunas"]["Coluna estranha"] is None
    assert {e["motivo"].split(" ")[0] for e in r["erros"]} == {"não", "data", "fora"}
    assert {"data": date(2026, 10, 1), "indicador": "litros", "valor": 1234.5} in r["registros"]
    with pytest.raises(ValueError, match="data"):
        ler("leite;ccs\n10;20")
