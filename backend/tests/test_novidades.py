"""Simulador, contrafactual, ajuste mínimo, sensibilidade, transição, trato, estoque, revisão, relatório e textos
em linguagem do produtor."""
from datetime import date, timedelta

import pytest
from sqlmodel import select
from test_auditoria import lote_sintetico, sessao_memoria  # noqa: F401 (fixture)

from app import estoque, relatorio, revisao, services
from app.calc.energy import leite_permitido
from app.db.models import AlertaDB, Dieta, HistoricoAlerta
from app.engine.engine import Motor
from app.engine.explain import contrafactual
from app.optimizer import lp

KB = services.kb()
LOTE = {"lote.estado": "lactacao", "lote.del": 120, "lote.grupo_genetico": "girolando", "lote.sistema": "confinado",
        "lote.pv": 550, "lote.leite": 22, "lote.gordura": 3.6, "lote.proteina": 3.2}
POBRE = [{"alimento": "silagem_milho", "kg_mn": 30}, {"alimento": "milho_moido", "kg_mn": 1}]


# ------------------------------------------------------------------ linguagem do produtor
def test_todo_alerta_tem_texto_do_produtor_e_numeros_no_padrao_brasileiro():
    sem = [r["id"] for r in KB.regras for a in r.get("entao", []) if "alerta" in a and r["id"] != "ACP-D00"   # lembrete
           and not all(a["alerta"].get(k) for k in ("titulo_produtor", "causa_produtor", "acao_produtor"))]
    assert sem == []
    assert [f for f, p in KB.perguntas.items() if not p.get("texto_produtor") or not p.get("ajuda_produtor")] == []
    # o "não sei" também tem fonte: os valores padrão das perguntas vêm de params.yaml
    assert [f for f, p in KB.perguntas.items() if isinstance(p.get("padrao"), (int, float)) and "padrao_param" not in p] == []
    assert KB.perguntas["lote.del"]["padrao"] == KB.params["padrao_del"]["valor"]
    r = services.avaliar(LOTE, POBRE)
    ver01 = next(a for a in r["alertas"] if a["regra"] == "VER-01")
    assert "%" in ver01["titulo_produtor"] and "Mcal" not in ver01["titulo_produtor"]
    acp = Motor(KB, ["acompanhamento_diario"]).executar(services.memoria(
        {"mon.z": -4.0, "mon.litros_vaca": 18.25, "mon.esperado_vaca": 21.5}, origem="medido"))
    d01 = next(a for a in acp.alertas if a.regra == "ACP-D01")
    assert "18,2" in d01.titulo_produtor and "18.2" in d01.titulo     # vírgula para o produtor, ponto no técnico


# ------------------------------------------------------------------ leite permitido e simulador
def test_leite_permitido_pela_energia():
    # sobra 2 Mcal; cada kg de leite custa 0,7 Mcal (14 Mcal / 20 kg) → +2,86 kg
    assert leite_permitido(30, 28, 14, 20) == pytest.approx(22.857, abs=0.01)
    assert leite_permitido(20, 28, 14, 20) == pytest.approx(8.571, abs=0.01)
    assert leite_permitido(5, 28, 14, 20) == 0.0
    r = services.avaliar(LOTE, POBRE)["fatos"]
    assert r["ver.leite_permitido"]["valor"] < LOTE["lote.leite"]       # dieta pobre não sustenta a meta


def test_simulador_mais_concentrado_aumenta_custo_e_leite_previsto_respeita_a_energia(sessao_memoria):
    s = sessao_memoria
    lote, _ = lote_sintetico(s)
    atual = services.dieta_ativa(s, lote.id).itens
    mais = [i | {"kg_mn": i["kg_mn"] + 1.5} if i["alimento"] == "milho_moido" else i for i in atual]
    out = services.simular(s, lote, mais)
    a, b = out["atual"], out["simulado"]
    assert b["custo_vaca_dia"] > a["custo_vaca_dia"] and b["leite_permitido"] > a["leite_permitido"]
    assert b["leite_previsto"] == pytest.approx(min(b["leite_meta"], b["leite_permitido"]))
    caro = services.simular(s, lote, atual, preco_leite=3.0)["simulado"]
    assert caro["receita_vaca_dia"] == pytest.approx(caro["leite_previsto"] * 3.0)


# ------------------------------------------------------------------ contrafactual
def test_contrafactual_aponta_o_limite_de_cada_premissa_e_desce_nas_conclusoes():
    r = services.avaliar(LOTE, POBRE)
    res = services.alertas_resultado(r)
    cf = contrafactual(res, "VER-01")
    lim = next(o for o in cf["opcoes"] if o["fato"] == "ver.razao_energia")
    assert lim["op"] == ">=" and lim["valor"] < lim["limite"]
    # queda sustentada: a premissa hipotese.queda_sustentada vira grupo com as regras que a concluíram
    acp = Motor(KB, ["acompanhamento_diario"]).executar(services.memoria(
        {"mon.corrida_dias": 6, "mon.corrida_pior": -0.15, "mon.residuo": -0.12, "mon.litros_vaca": 15.0,
         "mon.queda_7d": -0.12}, origem="medido"))
    cf2 = contrafactual(acp, "ACP-D04")
    grupo = next(o for o in cf2["opcoes"] if o["tipo"] == "conclusao")
    assert {g["regra"] for g in grupo["grupos"]} >= {"ACP-D02", "ACP-D03B"}
    assert all(g["opcoes"] for g in grupo["grupos"])


# ------------------------------------------------------------------ ajuste mínimo e sensibilidade
def test_ajuste_minimo_corrige_a_dieta_mexendo_pouco(sessao_memoria):
    s = sessao_memoria
    lote, _ = lote_sintetico(s)
    out = services.ajustar_dieta_lote(s, lote, POBRE + [{"alimento": "farelo_soja", "kg_mn": 1.0},
                                                         {"alimento": "nucleo_mineral", "kg_mn": 0.2}])
    assert out["pl"]["status"] == "otimo"
    assert out["verificacao"]["fatos"]["parecer.dieta"]["valor"] == "adequada"
    mexidos = {m["alimento"] for m in out["mudancas"]}
    # prefere mexer no que o lote já come: nenhum alimento novo quando os atuais resolvem
    assert mexidos and mexidos <= {"silagem_milho", "milho_moido", "farelo_soja", "nucleo_mineral"}


def test_sensibilidade_preco_acima_do_limite_tira_o_alimento_e_abaixo_do_limite_entra():
    alimentos = [KB.alimentos[a] for a in ("silagem_milho", "milho_moido", "farelo_soja", "polpa_citrica", "ureia",
                                           "nucleo_mineral")]
    out = services.formular(LOTE, [a["id"] for a in alimentos])
    r = out["pl"]["restricoes"]
    sens = lp.sensibilidade(alimentos, r)
    assert sens["status"] == "otimo"
    por = {a["alimento"]: a for a in sens["alimentos"]}
    soja = por["farelo_soja"]
    if soja["na_dieta"] and soja["sai_acima"]:
        caro = lp._kg_ms(lp._com_preco(alimentos, "farelo_soja", soja["sai_acima"] * 1.05), r)
        assert caro.get("farelo_soja", 0) <= 0.02 * (soja["kg_mn"] * 0.886) + 1e-6
    fora = [a for a in sens["alimentos"] if not a["na_dieta"] and a.get("entra_abaixo")]
    for a in fora:
        barato = lp._kg_ms(lp._com_preco(alimentos, a["alimento"], a["entra_abaixo"] * 0.95), r)
        assert barato.get(a["alimento"], 0) > 0.05
    assert {m["meta"] for m in sens["metas"]} == {"energia", "proteina", "fibra"}
    assert all(m["economia"] >= -1e-6 for m in sens["metas"])


# ------------------------------------------------------------------ transição e trato
def test_troca_de_volumoso_gera_transicao_gradual_e_o_trato_usa_a_mistura_do_dia(sessao_memoria):
    s = sessao_memoria
    lote, _ = lote_sintetico(s)
    cat = services.catalogo(s, lote.fazenda_id)
    velha = [{"alimento": "silagem_sorgo", "kg_mn": 30}, {"alimento": "milho_moido", "kg_mn": 3}]
    nova = [{"alimento": "silagem_milho", "kg_mn": 30}, {"alimento": "milho_moido", "kg_mn": 3}]
    t = services.planejar_transicao(lote, velha, nova, cat, date.today(), 1)
    assert t["dias"] == KB.params["transicao_dias_volumoso"]["valor"] and "TRN-01" in t["regras"]
    pcts = [e["pct_nova"] for e in t["plano"]]
    assert pcts == sorted(pcts) and 0 < pcts[0] < pcts[-1] < 100
    assert services.planejar_transicao(lote, velha, [i | {"kg_mn": i["kg_mn"] * 1.03} for i in velha], cat,
                                       date.today()) is None     # ajuste pequeno não precisa de transição
    for d in s.exec(select(Dieta).where(Dieta.lote_id == lote.id)).all():
        d.ativa = False
        s.add(d)
    s.add(Dieta(lote_id=lote.id, versao=2, itens=nova, inicio=date.today(), ativa=True, transicao=t))
    s.commit()
    plano = services.plano_trato(s, lote, tratos=2)
    kg = {l["alimento"]: l["kg_vaca"] for l in plano["linhas"]}
    assert set(kg) == {"silagem_sorgo", "silagem_milho", "milho_moido"} and plano["transicao"]["dia"] == 1
    assert plano["linhas"][-1]["categoria"] == "volumoso_umido"        # silagem por último no vagão
    assert sum(plano["total_por_trato"]) == pytest.approx(plano["total"])
    assert plano["total"] == pytest.approx(sum(l["kg_vaca"] for l in plano["linhas"]) * plano["vacas"])
    with pytest.raises(services.EntradaInvalida):
        services.plano_trato(s, lote, tratos=2, divisao=[0.7, 0.2])


def test_rejeicao_na_adaptacao_vira_um_alerta_so_com_as_sobras_altas():
    acp = Motor(KB, ["classificacao", "acompanhamento_diario"]).executar(services.memoria(
        LOTE | {"mon.em_adaptacao_dieta": True, "mon.dias_dieta_nova": 2, "mon.sobras_min3": 9.0,
                "mon.sobras_max3": 11.0, "mon.sobras_texto": "9%"}, origem="medido"))
    regras = {a.regra for a in acp.alertas}
    assert "ACP-TR1" in regras and "ACP-S04" not in regras


# ------------------------------------------------------------------ estoque
def test_estoque_desconta_o_consumo_das_dietas_e_avisa_pelas_regras(sessao_memoria):
    s = sessao_memoria
    lote, _ = lote_sintetico(s)
    dieta = services.dieta_ativa(s, lote.id)
    item = dieta.itens[0]
    consumo_dia = item["kg_mn"] * 20
    estoque.registrar(s, lote.fazenda_id, item["alimento"], "contagem", consumo_dia * 10, date.today() - timedelta(days=4))
    sit = estoque.situacao(s, lote.fazenda_id)
    linha = next(i for i in sit["itens"] if i["item"] == item["alimento"])
    assert linha["saldo_kg"] == pytest.approx(consumo_dia * 6)
    assert linha["dias_restantes"] == pytest.approx(6, abs=0.01)
    assert [a["regra"] for a in linha["alertas"]] == ["EST-01"]
    estoque.registrar(s, lote.fazenda_id, item["alimento"], "entrada", consumo_dia * 6, date.today())
    linha = next(i for i in estoque.situacao(s, lote.fazenda_id)["itens"] if i["item"] == item["alimento"])
    assert [a["regra"] for a in linha["alertas"]] == ["EST-02"]
    with pytest.raises(services.EntradaInvalida):
        estoque.registrar(s, lote.fazenda_id, "nao_existe", "contagem", 10, date.today())


# ------------------------------------------------------------------ revisão da base e relatório
def test_revisao_sugere_rever_regra_muito_recusada(sessao_memoria):
    s = sessao_memoria
    lote, _ = lote_sintetico(s)
    hoje = date.today()
    for i in range(3):
        ep = AlertaDB(lote_id=lote.id, regra="ACP-D06", problema="ACP-D06", nivel="atencao", titulo="x",
                      aberto_em=hoje - timedelta(days=10 + i), ultima_ocorrencia=hoje, estado="recusado")
        s.add(ep)
        s.commit()
        s.add(HistoricoAlerta(alerta_id=ep.id, lote_id=lote.id, data_hora=__import__("datetime").datetime.now(),
                              tipo="recusado", descricao=f"motivo {i}", automatico=False))
    s.commit()
    r = revisao.revisar(s, KB)
    sug = next(x for x in r["sugestoes"] if x["regra"] == "ACP-D06")
    assert sug["tipo"] == "muitas_recusas" and "razao_precos" not in sug["parametros"] and len(sug["motivos"]) == 3


def test_relatorio_semanal_traz_producao_custo_e_proximos_passos(sessao_memoria):
    s = sessao_memoria
    lote, _ = lote_sintetico(s, efeitos={i: 0.85 for i in range(33, 40)})
    services.reprocessar(s, lote, date.today() - timedelta(days=10), date.today())
    rel = relatorio.gerar(s, lote.fazenda_id)
    l = rel["lotes"][0]
    assert l["leite_vaca"] < l["leite_vaca_anterior"] and l["variacao_pct"] < 0
    assert l["custo_vaca_dia"] > 0 and l["margem_vaca_dia"] is not None
    assert l["pendentes"] and all(p["titulo"] for p in l["pendentes"])


# ------------------------------------------------------------------ previsão
def test_previsao_segue_a_curva_seca_o_lote_e_avisa_pelas_regras(sessao_memoria):
    from app import previsao
    s = sessao_memoria
    lote, _ = lote_sintetico(s, del0=200)
    lote.dias_gestacao_ref = 160            # 160 + 39 dias de registro = 199 hoje → secagem (220) em ~21 dias
    s.add(lote)
    s.commit()
    p = previsao.projetar_lote(s, lote, 30)
    prod = [x for x in p["serie"] if x["produzindo"]]
    assert 15 <= len(prod) <= 25 and all(x["leite_vaca"] is None for x in p["serie"] if not x["produzindo"])
    assert prod[-1]["leite_vaca"] < prod[0]["leite_vaca"]                       # final de lactação: curva cai
    assert all(x["baixo"] < x["leite_vaca"] < x["alto"] for x in prod)
    assert any(m["tipo"] == "secagem" for m in p["marcos"])
    assert "PRV-02" in {a["regra"] for a in p["alertas"]}
    tot = p["totais"]
    assert tot["margem"] == pytest.approx(tot["receita"] - tot["custo"])
    # calor previsto acima do limiar reduz o leite projetado
    quente = {date.today() + timedelta(days=i): 85.0 for i in range(0, 31)}
    p2 = previsao.projetar_lote(s, lote, 30, itu_futuro=quente)
    assert p2["totais"]["leite"] < tot["leite"]


def test_regras_de_previsao_da_fazenda():
    res = Motor(KB, ["previsao"]).executar(services.memoria(
        {"prev.dias": 30, "prev.fazenda.variacao_receita_pct": -22.0, "prev.fazenda.margem_total": -100.0}, origem="sistema"))
    assert {a.regra for a in res.alertas} == {"PRV-10", "PRV-11"}


def test_todo_fato_que_aparece_na_tela_tem_nome_para_o_produtor():
    """A visão do produtor nunca mostra nome interno (ex.: mon.bonificacao_perda_rs_mes): todo fato citado ou concluído
    pelas regras, perguntado ou produzido pelo monitor/serviços tem rótulo em ROTULOS_PRODUTOR (frontend/src/api.ts)."""
    import re
    from pathlib import Path
    from app.engine.rules_loader import fatos_concluidos, fatos_requeridos
    raiz = Path(__file__).resolve().parents[1]
    ts = (raiz.parent / "frontend" / "src" / "api.ts").read_text(encoding="utf-8")
    bloco = ts[ts.index("ROTULOS_PRODUTOR"):]
    bloco = bloco[:bloco.index("\n}\n")]
    rotulados = set(re.findall(r"'([a-z_]+(?:\.[\w.]+)?)'\s*:", bloco))
    fatos = set(KB.perguntas)
    for r in KB.regras:
        fatos |= set(fatos_requeridos(r)) | set(fatos_concluidos(r))
    for arq in ("app/monitor/fatos.py", "app/services.py", "app/previsao.py", "app/estoque.py"):
        fatos |= set(re.findall(r'["\']((?:mon|laudo|prev|estoque|lote|exig|ver|dieta|meta|perfil|clima)\.[a-z_][\w.]*)["\']',
                                (raiz / arq).read_text(encoding="utf-8")))
    assert sorted(f for f in fatos if f not in rotulados) == []
