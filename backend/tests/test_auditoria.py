"""Regressões dos achados das auditorias (motor, base de conhecimento e acompanhamento).
Cada teste reproduz um cenário que antes dava resultado errado."""
import random
from datetime import date, datetime, time, timedelta
from pathlib import Path

import pytest
import yaml
from pytest import approx
from sqlmodel import Session, SQLModel, create_engine

from app import services
from app.calc.lactation_curve import cobuci
from app.db.models import AlertaDB, Dieta, Evento, Fazenda, Lote, Registro
from app.engine.cf import combinar
from app.engine.engine import Motor
from app.engine.explain import como, por_que
from app.engine.rules_loader import carregar
from app.engine.working_memory import MemoriaTrabalho

KB = services.kb()
LACTACAO = {"lote.estado": "lactacao", "lote.del": 120, "lote.grupo_genetico": "girolando", "lote.sistema": "confinado",
            "lote.pv": 550, "lote.leite": 18, "lote.gordura": 3.8, "lote.proteina": 3.2}
DIETA = [{"alimento": "silagem_milho", "kg_mn": 35}, {"alimento": "milho_moido", "kg_mn": 2.5},
         {"alimento": "farelo_soja", "kg_mn": 3.2}, {"alimento": "nucleo_mineral", "kg_mn": 0.2}]


def rodar(fatos, modulos=("classificacao", "exigencias", "verificacao"), itens=None):
    wm = services.memoria(fatos)
    if itens:
        enr = services.itens_dieta(itens)
        wm.declarar("dieta.itens", enr, cf=services.cf_itens(enr), origem="tabela")
    return Motor(KB, list(modulos)).executar(wm)


def ativos(r):
    return {a.regra for a in r.alertas if a.status == "ativo"}


# ============================================================== motor
def test_lactacao_sem_dado_de_leite_nao_vira_so_mantenca_nem_dieta_adequada():
    fatos = {k: v for k, v in LACTACAO.items() if k != "lote.proteina"}
    r = rodar(fatos, itens=DIETA)
    assert "exig.ell_total" not in r.wm
    assert r.wm.valor("parecer.dieta") != "adequada"


def test_sessao_continuada_recalcula_conclusoes():
    wm = services.memoria(LACTACAO)
    motor = Motor(KB, ["classificacao", "exigencias"])
    r = motor.executar(wm)
    wm.declarar("lote.dias_gestacao", 200)
    motor.executar(wm, r)
    novo = Motor(KB, ["classificacao", "exigencias"]).executar(services.memoria(LACTACAO | {"lote.dias_gestacao": 200}))
    assert wm.valor("exig.ell_total") == approx(novo.wm.valor("exig.ell_total"))
    wm.declarar("lote.del", 10)
    motor.executar(wm, r)
    assert wm.valor("perfil.fase") == "recem_parida"


def test_backward_classifica_antes_de_perguntar():
    wm = services.memoria({"lote.estado": "seca", "lote.dias_para_parto": 40, "lote.sistema": "confinado"})
    Motor(KB, ["classificacao"]).executar(wm)
    faltam = {p["fato"] for p in Motor(KB, services.MODULOS_AVALIACAO).faltantes("exig.ell_total", wm)}
    assert "lote.ecc" not in faltam and "lote.leite" not in faltam
    assert "lote.pv" in faltam


def test_tipos_de_entrada_sao_validados_e_convertidos():
    assert services.normalizar({"lote.ecc": "2,5"})["lote.ecc"] == 2.5
    with pytest.raises(services.EntradaInvalida):
        services.normalizar({"lote.del": "abc"})
    with pytest.raises(services.EntradaInvalida):
        services.normalizar({"lote.grupo_genetico": "zebu"})
    wm = MemoriaTrabalho()                       # tipo errado direto na memória não derruba o motor
    for k, v in (LACTACAO | {"lote.del": "42"}).items():
        wm.declarar(k, v)
    r = Motor(KB, ["classificacao"]).executar(wm)
    assert any(a.get("efeito") == "ignorado" for t in r.traco for a in t["acoes"])


@pytest.mark.parametrize("defeito", [
    {"se": [{"fato": "lote.del", "op": "=>", "valor": 1}]},
    {"se": [{"fato": "clima.ITU", "op": ">", "valor": 1}]},
    {"entao": [{"alerta": {"nivel": "atencao", "titulo": "x {@params.itu_frote}"}}]},
    {"entao": [{"calcular": {"fato": "exig.x", "funcao": "itu", "args": {"temperatura": 1, "ur": 2}}}]},
    {"entao": [{"concluri": {"fato": "exig.x", "valor": 1}}]},
    {"cf": 7},
])
def test_validador_rejeita_base_com_defeito(tmp_path: Path, defeito):
    for nome in ("params.yaml", "foods.yaml", "perguntas.yaml", "kb.yaml"):
        (tmp_path / nome).write_text((KB.diretorio / nome).read_text(encoding="utf-8"), encoding="utf-8")
    (tmp_path / "rules").mkdir()
    regra = {"id": "X-01", "modulo": "classificacao", "se": [{"fato": "lote.del", "op": "existe"}],
             "entao": [{"concluir": {"fato": "perfil.x", "valor": 1}}]} | defeito
    (tmp_path / "rules" / "r.yaml").write_text(yaml.safe_dump([regra], allow_unicode=True), encoding="utf-8")
    with pytest.raises(ValueError, match="Base de conhecimento inválida"):
        carregar(tmp_path)


def test_como_mostra_as_entradas_do_calculo():
    wm = services.memoria(LACTACAO, padroes={"lote.pv"})
    r = Motor(KB, ["classificacao", "exigencias"]).executar(wm)
    arvore = como(r, "exig.cms_equacao")
    filhos = {p["fato"]: p for p in arvore["regras"][0]["premissas"]}
    assert "lote.pv" in filhos and filhos["lote.pv"]["origem"] == "padrao"


def test_por_que_atravessa_fatos_calculados_em_dicionario():
    cadeia = por_que(Motor(KB, services.MODULOS_AVALIACAO), "dieta.itens", "parecer.dieta")
    assert cadeia and cadeia[0]["regra"] == "EXG-00"


def test_cf_contraditorio_e_limiar():
    assert combinar(-1, 1) == 0.0
    r = rodar({"lote.temp": 30, "lote.ur": 70}, modulos=["classificacao"])
    assert "CLS-11" in ativos(r)
    wm = MemoriaTrabalho()
    wm.declarar("lote.temp", 30, cf=0.1)
    wm.declarar("lote.ur", 70, cf=0.1)
    assert "CLS-11" not in {t["regra"] for t in Motor(KB, ["classificacao"]).executar(wm).traco}


# ============================================================== base de conhecimento
def test_vaca_seca_sem_dias_de_gestacao_deriva_do_parto():
    r = rodar({"lote.estado": "seca", "lote.dias_para_parto": 15, "lote.pv": 600}, modulos=["classificacao", "exigencias"])
    assert r.wm.valor("perfil.dias_gestacao") == 265
    assert r.wm.valor("exig.ell_gestacao") > 3


def test_sem_temperatura_nao_ha_itu_e_pv_nao_tem_padrao():
    r = rodar(LACTACAO, modulos=["classificacao"])
    assert "clima.itu" not in r.wm
    assert "padrao" not in KB.perguntas["lote.pv"] and "padrao" not in KB.perguntas["lote.temp"]


def test_recem_parida_tem_mobilizacao_calculada_e_nao_soma_recuperacao():
    fatos = {"lote.estado": "lactacao", "lote.del": 5, "lote.grupo_genetico": "jersey", "lote.sistema": "confinado",
             "lote.pv": 420, "lote.leite": 26, "lote.gordura": 4.2, "lote.proteina": 3.4, "lote.ecc": 2.25}
    r = rodar(fatos, modulos=["classificacao", "exigencias"])
    assert "EXG-06C" not in {t["regra"] for t in r.traco}
    r = rodar(fatos | {"lote.ecc": 3.0}, modulos=["classificacao", "exigencias"])
    assert 0.6 < r.wm.valor("meta.fator_energia_min") < 0.95
    out = services.formular(fatos | {"lote.ecc": 3.0}, list(KB.alimentos))
    assert out["pl"]["status"] in ("otimo", "parcial")


def test_metas_de_fibra_nao_extrapolam_e_fdnf_muito_baixo_bloqueia():
    fatos = LACTACAO | {"dieta.ms_kg": 15, "dieta.fdn_pct": 20, "dieta.fdnf_pct": 0, "dieta.cnf_pct": 60,
                        "dieta.pb_pct": 16, "dieta.ee_pct": 4, "dieta.ureia_pct": 0, "dieta.ell_mcal_kg": 1.8}
    r = rodar(fatos)
    assert r.wm.valor("meta.fdn_min") == approx(33) and r.wm.valor("meta.cnf_max") == approx(36)
    assert r.wm.valor("parecer.dieta") == "bloqueada" and "VER-03D" in ativos(r)


def test_cms_plausivel_nao_acusa_pos_parto():
    r = rodar(LACTACAO | {"lote.del": 5}, modulos=["classificacao", "exigencias", "verificacao"])
    assert "VER-09" not in {t["regra"] for t in r.traco}


def test_excesso_de_energia_e_ecc_alto():
    seca = {"lote.estado": "seca", "lote.dias_para_parto": 40, "lote.pv": 600, "lote.grupo_genetico": "holandes",
            "lote.sistema": "confinado", "lote.ecc": 4.0}
    r = rodar(seca, itens=[{"alimento": "silagem_milho", "kg_mn": 36}, {"alimento": "milho_moido", "kg_mn": 2},
                           {"alimento": "nucleo_mineral", "kg_mn": 0.15}])
    assert {"VER-10", "VER-11"} <= ativos(r)
    out = services.formular(seca, ["silagem_milho", "milho_moido", "capim_elefante", "farelo_soja", "nucleo_mineral"])
    assert out["pl"]["status"] == "otimo"
    assert out["verificacao"]["fatos"]["ver.razao_energia"]["valor"] <= KB.params["fator_energia_max"]["valor"]


def test_semiconfinado_tem_gasto_de_atividade():
    r = rodar(LACTACAO | {"lote.sistema": "semiconfinado", "lote.distancia_km": 2.0, "lote.relevo": "plano"},
              modulos=["classificacao", "exigencias"])
    assert r.wm.valor("exig.ell_atividade") > 0


def test_jersey_usa_tabela_de_pb_de_racas_menores():
    r = rodar(LACTACAO | {"lote.grupo_genetico": "jersey", "lote.leite": 25}, modulos=["classificacao", "exigencias"])
    assert r.wm.valor("exig.pb_pct_alvo") == approx(16.56, abs=0.05)


def test_verificacao_confere_inclusao_pastejo_e_mineral():
    r = rodar(LACTACAO, itens=[{"alimento": "silagem_milho", "kg_mn": 25}, {"alimento": "caroco_algodao", "kg_mn": 6},
                               {"alimento": "braquiaria", "kg_mn": 5}])
    assert {"VER-12", "VER-13", "VER-14"} <= ativos(r)


def test_formulacao_avisa_alimento_excluido():
    out = services.formular(LACTACAO, ["braquiaria", "silagem_milho", "milho_moido", "farelo_soja", "nucleo_mineral"])
    assert "FOR-16" in {a["regra"] for a in out["alertas"]}


# ============================================================== acompanhamento (banco em memória)
@pytest.fixture
def sessao_memoria():
    eng = create_engine("sqlite://")
    SQLModel.metadata.create_all(eng)
    with Session(eng) as s:
        yield s


def lote_sintetico(s, dias=40, k=1.3, del0=60, efeitos=None, estado="lactacao", extra=None, eventos=()):
    """Lote com `dias` de registros terminando hoje; efeitos: {indice_dia: fator multiplicativo no leite}."""
    hoje = date.today()
    d0 = hoje - timedelta(days=dias - 1)
    faz = Fazenda(nome="Teste", preco_leite=2.5, preco_concentrado=2.0)
    s.add(faz)
    s.commit()
    lote = Lote(fazenda_id=faz.id, nome="L", estado=estado, grupo_genetico="girolando", n_vacas=20, pv=520,
                data_ref=d0, del_ref=del0 if estado == "lactacao" else None, dias_para_parto_ref=None if estado == "lactacao" else 50)
    s.add(lote)
    s.commit()
    s.add(Dieta(lote_id=lote.id, itens=DIETA, inicio=d0, ms_silagem_ref=30.9))
    rnd = random.Random(1)
    for i in range(dias):
        d = d0 + timedelta(days=i)
        y = cobuci(del0 + i) * k * (efeitos or {}).get(i, 1.0) * (1 + rnd.uniform(-0.01, 0.01))
        for ind, v in {"vacas": 20, "litros": y * 20, "concentrado_kg_vaca": 3.0, "temp": 21.0, "ur": 65.0}.items():
            s.add(Registro(lote_id=lote.id, data=d, indicador=ind, valor=v))
        for (dia, ind), v in (extra or {}).items():
            if dia == i:
                s.add(Registro(lote_id=lote.id, data=d, indicador=ind, valor=v))
    for dia, tipo in eventos:
        s.add(Evento(lote_id=lote.id, data_hora=datetime.combine(d0 + timedelta(days=dia), time(8)), tipo=tipo))
    s.commit()
    return lote, d0


def test_um_dia_errado_e_queda_brusca_nao_queda_sustentada(sessao_memoria):
    lote, _ = lote_sintetico(sessao_memoria, efeitos={39: 0.45})
    out = services.monitorar(sessao_memoria, lote, date.today())
    regras = {a["regra"] for a in out["alertas"]}
    assert "ACP-D01" in regras and "ACP-D04" not in regras


def test_corrigir_o_dado_revisa_o_alerta(sessao_memoria):
    from sqlmodel import select
    s = sessao_memoria
    lote, _ = lote_sintetico(s, efeitos={39: 0.45})
    hoje = date.today()
    services.monitorar(s, lote, hoje)
    reg = s.exec(select(Registro).where(Registro.lote_id == lote.id, Registro.data == hoje, Registro.indicador == "litros")).one()
    reg.valor = cobuci(60 + 39) * 1.3 * 20
    s.add(reg)
    s.commit()
    services.monitorar(s, lote, hoje)
    assert not s.exec(select(AlertaDB).where(AlertaDB.lote_id == lote.id, AlertaDB.regra == "ACP-D01")).all()


def test_calibracao_ignora_calor_e_lote_novo_nao_alerta(sessao_memoria):
    from app.monitor.fatos import HistoricoLote, ajustar_k
    from sqlmodel import select
    s = sessao_memoria
    lote, _ = lote_sintetico(s, dias=30, k=1.3, efeitos={i: 0.85 for i in range(10)},
                             extra={(i, "temp"): 32.0 for i in range(10)})
    regs = s.exec(select(Registro).where(Registro.lote_id == lote.id)).all()
    # com calor (e queda de 15%) nos primeiros dias, o ajuste usa só os dias sem calor
    h = HistoricoLote(regs, [])
    assert ajustar_k(lote, h, KB.params, date.today()) == approx(1.3, rel=0.03)
    lote2, _ = lote_sintetico(s, dias=4)
    out = services.monitorar(s, lote2, date.today())
    assert {a["regra"] for a in out["alertas"]} == {"ACP-D00B"}


def test_calor_rebaixa_queda_e_lote_seco_sem_lembrete(sessao_memoria):
    s = sessao_memoria
    calor = {(i, "temp"): 31.0 for i in range(30, 40)} | {(i, "ur"): 72.0 for i in range(30, 40)}
    lote, _ = lote_sintetico(s, efeitos={i: 0.88 for i in range(32, 40)}, extra=calor)
    out = services.monitorar(s, lote, date.today())
    d04 = [a for a in out["alertas"] if a["regra"] == "ACP-D04"]
    assert "ACP-10" in {a["regra"] for a in out["alertas"]}
    assert d04 and d04[0]["nivel"] == "atencao"
    seco = Lote(fazenda_id=lote.fazenda_id, nome="Seco", estado="seca", grupo_genetico="girolando", pv=520,
                data_ref=date.today(), dias_para_parto_ref=40)
    s.add(seco)
    s.commit()
    assert "ACP-D00" not in {a["regra"] for a in services.monitorar(s, seco, date.today())["alertas"]}


def test_laudos_respeitam_idade_e_quantidade(sessao_memoria):
    s = sessao_memoria
    extra = {(39, "laudo_ccs"): 520.0, (39, "laudo_lactose"): 4.25, (20, "laudo_ccs"): 100.0}
    lote, _ = lote_sintetico(s, extra=extra)
    out = services.monitorar(s, lote, date.today())
    regras = {a["regra"] for a in out["alertas"]}
    assert "ACP-M06" not in regras                      # 2 amostras não fazem média de 3 meses
    assert out["fatos"]["laudo.ccs_tendencia"]["valor"] == "subindo"
    lote2, _ = lote_sintetico(s, extra={(39, "laudo_ccs"): 120.0, (20, "laudo_ccs"): 100.0, (39, "laudo_lactose"): 4.25})
    out2 = services.monitorar(s, lote2, date.today())
    assert "laudo.ccs_tendencia" not in out2["fatos"] and "ACP-M05" not in {a["regra"] for a in out2["alertas"]}


def test_resposta_ao_concentrado_desconta_a_curva(sessao_memoria):
    s = sessao_memoria
    extra = {(i, "concentrado_kg_vaca"): 4.5 for i in range(30, 40)}
    lote, _ = lote_sintetico(s, del0=200, extra=extra, eventos=[(30, "mudanca_concentrado")])
    out = services.monitorar(s, lote, date.today())
    assert abs(out["fatos"]["mon.resposta_marginal"]["valor"]) < 0.1


def test_leitura_isolada_nao_dispara_regras_semanais(sessao_memoria):
    s = sessao_memoria
    lote, _ = lote_sintetico(s, extra={(39, "ms_silagem"): 41.0, (25, "ecc"): 3.0, (32, "ecc"): 3.75, (39, "ecc"): 3.0})
    regras = {a["regra"] for a in services.monitorar(s, lote, date.today())["alertas"]}
    assert not regras & {"ACP-S01", "ACP-S02", "ACP-09"}
