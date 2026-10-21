"""Minerais e DCAD do pré-parto: cálculo, verificação (VER-15) e formulação que respeita a mesma regra (FOR-07)."""
import pytest
from pytest import approx

from app import services
from app.calc.diet import composicao, dcad_meq_kg
from app.engine.engine import Motor

KB = services.kb()
# minerais em % da MS (valores típicos para o teste; na base virão do CQBAL)
MINERAIS = {
    "silagem_milho": dict(ca=0.25, p=0.22, mg=0.18, k=1.20, na=0.01, cl=0.25, s=0.12),
    "capim_elefante": dict(ca=0.40, p=0.25, mg=0.25, k=2.20, na=0.02, cl=0.50, s=0.15),
    "milho_moido": dict(ca=0.03, p=0.28, mg=0.11, k=0.38, na=0.01, cl=0.06, s=0.10),
    "farelo_soja": dict(ca=0.35, p=0.68, mg=0.30, k=2.30, na=0.02, cl=0.07, s=0.42),
    "nucleo_mineral": dict(ca=20.0, p=8.0, mg=2.0, k=0.0, na=10.0, cl=15.0, s=1.5),
}
SAL_ANIONICO = {"id": "sal_anionico", "nome": "Sal aniônico", "tipo": "mineral", "ms": 98, "pb": 0, "fdn": 0, "ndt": 0,
                "ee": 0, "mm": 100, "ca": 0, "p": 0, "mg": 5, "k": 0, "na": 0, "cl": 30, "s": 8, "preco_kg_mn": 3.0,
                "max_kg_ms": 0.6}
CAT = {aid: KB.alimentos[aid] | m for aid, m in MINERAIS.items()} | {"sal_anionico": SAL_ANIONICO}
PREPARTO = {"lote.estado": "seca", "lote.dias_para_parto": 15, "lote.pv": 620, "lote.grupo_genetico": "holandes",
            "lote.sistema": "confinado", "lote.fracao_primiparas": 0.3}


def test_formula_da_dcad():
    assert dcad_meq_kg(0.1, 1.5, 0.4, 0.25) == approx(159.2, abs=0.1)


def test_composicao_so_tem_minerais_quando_todos_os_alimentos_tem():
    com = composicao([{"alimento": CAT["silagem_milho"], "kg_mn": 30}, {"alimento": CAT["farelo_soja"], "kg_mn": 1}])
    assert "dcad_meq_kg" in com and com["k_pct"] > 1
    sem = composicao([{"alimento": CAT["silagem_milho"], "kg_mn": 30}, {"alimento": KB.alimentos["capim_elefante"], "kg_mn": 5}])
    assert "dcad_meq_kg" not in sem and "cl_pct" not in sem     # capim-elefante sem Cl no CQBAL


def rodar(fatos, itens):
    wm = services.memoria(fatos)
    wm.declarar("dieta.itens", [{"alimento": CAT[a], "kg_mn": kg} for a, kg in itens], cf=1.0, origem="usuario")
    return Motor(KB, ["classificacao", "exigencias", "verificacao"]).executar(wm)


def test_preparto_com_dcad_positiva_e_novilhas_e_falta_de_dado():
    r = rodar(PREPARTO, [("capim_elefante", 40), ("milho_moido", 1), ("nucleo_mineral", 0.15)])
    assert r.wm.valor("dieta.dcad_meq_kg") > 0 and "VER-15" in {a.regra for a in r.alertas}
    assert r.wm.valor("parecer.dieta") == "ajustar"
    novilhas = rodar(PREPARTO | {"lote.fracao_primiparas": 1.0},
                     [("silagem_milho", 25), ("sal_anionico", 0.5), ("nucleo_mineral", 0.15)])
    assert novilhas.wm.valor("dieta.dcad_meq_kg") < 0 and "VER-15N" in {a.regra for a in novilhas.alertas}
    wm = services.memoria(PREPARTO)
    wm.declarar("dieta.itens", [{"alimento": KB.alimentos["capim_elefante"], "kg_mn": 40}], cf=1.0, origem="usuario")
    assert "VER-15I" in {a.regra for a in Motor(KB, ["classificacao", "exigencias", "verificacao"]).executar(wm).alertas}


def test_formulacao_do_preparto_atinge_dcad_negativa_com_sal_anionico():
    out = services.formular(PREPARTO, ["silagem_milho", "milho_moido", "farelo_soja", "nucleo_mineral", "sal_anionico"], cat=CAT)
    assert out["pl"]["status"] == "otimo"
    v = out["verificacao"]
    assert v["fatos"]["dieta.dcad_meq_kg"]["valor"] <= 0 and v["fatos"]["parecer.dieta"]["valor"] == "adequada"
    sem_sal = services.formular(PREPARTO, ["capim_elefante", "farelo_soja", "nucleo_mineral"], cat=CAT)
    assert sem_sal["pl"]["status"] in ("inviavel", "parcial") and "dcad" in sem_sal["pl"]["restricoes_violadas"]
    assert "FOR-18" in {a["regra"] for a in sem_sal["alertas"]}
