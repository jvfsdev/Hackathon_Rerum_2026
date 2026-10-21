"""Mecânica do motor: CF, refração, resolução de conflito, encadeamento regressivo e explicação."""
from pathlib import Path

import yaml
from pytest import approx

from app.engine.cf import combinar, propagar
from app.engine.engine import Motor
from app.engine.explain import como, por_que
from app.engine.rules_loader import carregar
from app.engine.working_memory import MemoriaTrabalho

KB = carregar()


def test_combinacao_mycin():
    assert combinar(0.7, 0.6) == approx(0.88)
    assert combinar(-0.5, -0.5) == approx(-0.75)
    assert propagar(0.8, [1.0, 0.6]) == approx(0.48)


def _kb_mini(tmp_path: Path, regras: list[dict]):
    """Base mínima isolada para testar a mecânica do motor."""
    for nome in ("params.yaml", "foods.yaml", "perguntas.yaml"):
        (tmp_path / nome).write_text((KB.diretorio / nome).read_text(encoding="utf-8"), encoding="utf-8")
    (tmp_path / "kb.yaml").write_text('kb_version: "teste"', encoding="utf-8")
    (tmp_path / "rules").mkdir()
    (tmp_path / "rules" / "r.yaml").write_text(yaml.safe_dump(regras, allow_unicode=True), encoding="utf-8")
    return carregar(tmp_path)


def test_resolucao_de_conflito_por_prioridade_e_especificidade(tmp_path):
    regras = [
        {"id": "R-BAIXA", "modulo": "classificacao", "prioridade": 10, "se": [{"fato": "lote.x", "op": "existe"}],
         "entao": [{"concluir": {"fato": "lote.ordem_baixa", "valor": True}}]},
        {"id": "R-ALTA", "modulo": "classificacao", "prioridade": 90, "se": [{"fato": "lote.x", "op": "existe"}],
         "entao": [{"concluir": {"fato": "lote.ordem_alta", "valor": True}}]},
        {"id": "R-ESPECIFICA", "modulo": "classificacao", "prioridade": 10,
         "se": [{"fato": "lote.x", "op": "existe"}, {"fato": "lote.y", "op": "existe"}],
         "entao": [{"concluir": {"fato": "lote.ordem_especifica", "valor": True}}]},
        {"id": "R-MODULO2", "modulo": "exigencias", "prioridade": 100, "se": [{"fato": "lote.x", "op": "existe"}],
         "entao": [{"concluir": {"fato": "lote.ordem_modulo2", "valor": True}}]},
    ]
    kb = _kb_mini(tmp_path, regras)
    wm = MemoriaTrabalho()
    wm.declarar("lote.x", 1)
    wm.declarar("lote.y", 1)
    r = Motor(kb).executar(wm)
    assert r.disparadas() == ["R-ALTA", "R-ESPECIFICA", "R-BAIXA", "R-MODULO2"]
    assert set(r.traco[0]["concorrentes"]) == {"R-ESPECIFICA", "R-BAIXA", "R-MODULO2"}


def test_refracao_nao_redispara_na_mesma_sessao():
    wm = MemoriaTrabalho()
    wm.declarar("lote.estado", "lactacao")
    wm.declarar("lote.del", 10)
    motor = Motor(KB, ["classificacao"])
    r = motor.executar(wm)
    motor.executar(wm, r)
    assert r.disparadas().count("CLS-01") == 1
    assert wm.get("perfil.fase").cf == 1.0


def test_valor_informado_prevalece_sobre_conclusao():
    wm = MemoriaTrabalho()
    wm.declarar("lote.estado", "lactacao")
    wm.declarar("lote.del", 10)
    wm.declarar("perfil.fase", "meio")
    Motor(KB, ["classificacao"]).executar(wm)
    assert wm.valor("perfil.fase") == "meio"


def test_backward_pergunta_so_o_que_falta():
    wm = MemoriaTrabalho()
    wm.declarar("lote.estado", "lactacao")
    wm.declarar("lote.sistema", "confinado")
    faltam = {p["fato"] for p in Motor(KB, ["classificacao", "exigencias"]).faltantes("exig.ell_total", wm)}
    assert {"lote.pv", "lote.del", "lote.leite", "lote.gordura", "lote.proteina"} <= faltam
    assert "lote.dias_para_parto" not in faltam      # lote em lactação: CLS-05 podada
    assert "lote.distancia_km" not in faltam         # confinado: atividade de pastejo podada
    assert "lote.estado" not in faltam               # já conhecido


def test_backward_cadeia_explica_por_que():
    wm = MemoriaTrabalho()
    perguntas = Motor(KB, ["classificacao", "exigencias"]).faltantes("exig.ell_total", wm)
    pv = next(p for p in perguntas if p["fato"] == "lote.pv")
    assert pv["cadeia"][0] == "EXG-02Z" and pv["cadeia"][-1] == "EXG-02A"


def test_por_que_liga_dado_ao_objetivo():
    cadeia = [r["regra"] for r in por_que(Motor(KB, ["classificacao", "exigencias"]), "lote.del", "exig.ell_total")]
    assert cadeia[-1] == "EXG-02Z"


def test_como_monta_arvore_com_fontes():
    wm = MemoriaTrabalho()
    for k, v in {"lote.estado": "lactacao", "lote.del": 42, "lote.grupo_genetico": "holandes", "lote.pv": 650,
                 "lote.leite": 35, "lote.gordura": 3.8, "lote.proteina": 3.2}.items():
        wm.declarar(k, v)
    r = Motor(KB, ["classificacao", "exigencias"]).executar(wm)
    arvore = como(r, "exig.cms")
    assert arvore["regras"][0]["regra"] == "EXG-01E"
    filhos = {p["fato"] for p in arvore["regras"][0]["premissas"]}
    assert "exig.cms_equacao" in filhos
