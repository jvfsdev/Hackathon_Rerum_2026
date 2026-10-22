"""Ciclo de vida dos alertas: episódio, aceite/recusa, ação registrada, resolução automática e histórico."""
from datetime import date, datetime, timedelta

import pytest
from sqlmodel import select
from test_auditoria import DIETA as DIETA_TESTE, lote_sintetico, sessao_memoria  # noqa: F401 (fixture)

from app import alertas, services
from app.db.models import AlertaDB, Dieta, Evento, HistoricoAlerta


def eps(s, lote_id, regra=None):
    q = select(AlertaDB).where(AlertaDB.lote_id == lote_id)
    if regra:
        q = q.where(AlertaDB.regra == regra)
    return s.exec(q).all()


def tipos(s, ep):
    """Tipos do histórico na ordem em que foram registrados (o teste simula dias passados para o automático)."""
    return [h.tipo for h in sorted(alertas.historico_do(s, ep.id), key=lambda h: h.id)]


def queda_e_recuperacao(s, eventos=()):
    """Queda de 12% nos dias 28–33 e recuperação a partir do 34 (40 dias, terminando hoje)."""
    lote, d0 = lote_sintetico(s, efeitos={i: 0.88 for i in range(28, 34)}, eventos=eventos)
    return lote, d0


def test_um_episodio_por_problema_e_resolucao_automatica_explicada(sessao_memoria):
    s = sessao_memoria
    lote, d0 = queda_e_recuperacao(s)
    services.reprocessar(s, lote, d0, date.today())
    [ep] = eps(s, lote.id, "ACP-D04")
    assert ep.ocorrencias > 1 and ep.aberto_em >= d0 + timedelta(days=28)
    assert ep.estado == "resolvido" and ep.estado_em is not None
    assert "deixou de valer" in ep.resolucao and "mon.residuo" in ep.resolucao
    assert tipos(s, ep)[0] == "aberto" and tipos(s, ep)[-1] == "resolvido"


def test_aceitar_leva_para_a_tela_e_acao_entra_no_historico_e_na_resolucao(sessao_memoria):
    s = sessao_memoria
    lote, d0 = queda_e_recuperacao(s)
    services.reprocessar(s, lote, d0, d0 + timedelta(days=31))      # problema em andamento
    [ep] = eps(s, lote.id, "ACP-D04")
    assert ep.estado == "aberto"
    destino = alertas.aceitar(s, ep, "vou conferir a ordenha")
    assert destino == f"/lotes/{lote.id}/registro?evento=conferencia&alerta={ep.id}"
    ev = Evento(lote_id=lote.id, data_hora=datetime.combine(d0 + timedelta(days=32), datetime.min.time()),
                tipo="conferencia", descricao="teteiras trocadas")
    s.add(ev)
    s.commit()
    alertas.registrar_acao(s, ep.id, lote.id, "Evento conferência: teteiras trocadas", {"evento_id": ev.id})
    services.reprocessar(s, lote, d0 + timedelta(days=32), date.today())
    s.refresh(ep)
    assert tipos(s, ep)[:3] == ["aberto", "aceito", "acao_registrada"]
    assert ep.estado == "resolvido" and "teteiras trocadas" in ep.resolucao


def test_recusa_exige_motivo_e_nao_insiste(sessao_memoria):
    s = sessao_memoria
    lote, d0 = queda_e_recuperacao(s)
    services.reprocessar(s, lote, d0, d0 + timedelta(days=30))
    [ep] = eps(s, lote.id, "ACP-D04")
    with pytest.raises(ValueError):
        alertas.recusar(s, ep, "  ")
    alertas.recusar(s, ep, "queda já explicada: vacas vendidas")
    services.reprocessar(s, lote, d0 + timedelta(days=31), d0 + timedelta(days=32))
    s.refresh(ep)
    assert ep.estado == "recusado" and len(eps(s, lote.id, "ACP-D04")) == 1


def test_reprocessamento_retroativo_preserva_acoes_do_usuario(sessao_memoria):
    s = sessao_memoria
    lote, d0 = queda_e_recuperacao(s)
    services.reprocessar(s, lote, d0, d0 + timedelta(days=31))
    [ep] = eps(s, lote.id, "ACP-D04")
    alertas.aceitar(s, ep)
    services.reprocessar(s, lote, d0 + timedelta(days=29), date.today())   # ex.: registro retroativo
    s.refresh(ep)
    assert "aceito" in tipos(s, ep) and len(eps(s, lote.id, "ACP-D04")) == 1


def test_laudo_vencido_expira_em_vez_de_resolver(sessao_memoria):
    s = sessao_memoria
    lote, d0 = lote_sintetico(s, dias=60, extra={(5, "laudo_nul"): 22.0})
    services.reprocessar(s, lote, d0, date.today())
    [ep] = eps(s, lote.id, "ACP-01R")
    assert ep.estado == "expirado" and "venceu" in ep.resolucao


def test_alertas_da_dieta_ativa_sao_resolvidos_pela_nova_versao(sessao_memoria):
    s = sessao_memoria
    lote, _ = lote_sintetico(s, dias=10)
    ruim = [{"alimento": "silagem_milho", "kg_mn": 35}, {"alimento": "milho_moido", "kg_mn": 3},
            {"alimento": "nucleo_mineral", "kg_mn": 0.2}]                     # sem fonte proteica
    for d in s.exec(select(Dieta).where(Dieta.lote_id == lote.id)).all():
        d.itens = ruim
        s.add(d)
    s.commit()
    services.avaliar_lote(s, lote)
    [ep] = eps(s, lote.id, "VER-02")
    assert ep.origem == "verificacao" and ep.estado == "aberto"
    assert alertas.aceitar(s, ep).startswith(f"/lotes/{lote.id}/dieta")
    for d in s.exec(select(Dieta).where(Dieta.lote_id == lote.id)).all():
        d.ativa = False
        s.add(d)
    corrigida = [{"alimento": "silagem_milho", "kg_mn": 35}, {"alimento": "milho_moido", "kg_mn": 2.5},
                 {"alimento": "farelo_soja", "kg_mn": 4.5}, {"alimento": "nucleo_mineral", "kg_mn": 0.2}]
    nova = Dieta(lote_id=lote.id, versao=2, itens=corrigida, motivo="mais farelo de soja", inicio=date.today())
    s.add(nova)
    s.commit()
    alertas.registrar_acao(s, ep.id, lote.id, "Nova dieta v2: mais farelo de soja", {"dieta_id": nova.id})
    services.avaliar_lote(s, lote)
    s.refresh(ep)
    assert ep.estado == "resolvido" and "dieta ativa v2" in ep.resolucao
    assert s.exec(select(HistoricoAlerta).where(HistoricoAlerta.alerta_id == ep.id,
                                                HistoricoAlerta.automatico == False)).all()  # noqa: E712


def test_reanalisar_hoje_preserva_abertura_de_alerta_ja_aceito(sessao_memoria):
    s = sessao_memoria
    lote, d0 = lote_sintetico(s, efeitos={i: 0.88 for i in range(32, 40)})
    services.reprocessar(s, lote, d0, date.today())
    [ep] = eps(s, lote.id, "ACP-D04")
    alertas.aceitar(s, ep)
    services.monitorar(s, lote, date.today())          # ex.: novo registro no mesmo dia
    s.refresh(ep)
    assert tipos(s, ep)[:2] == ["aberto", "aceito"] and ep.estado == "aceito"
    assert all(c["fato"].startswith(("mon.", "ver.", "laudo.", "clima.", "dieta.", "exig.", "meta.")) for c in ep.contexto)


def test_graus_do_mesmo_problema_sao_um_episodio_que_agrava_e_atenua(sessao_memoria):
    """ECC: ACP-09 (atenção) → ACP-05 (crítico) → ACP-09 de novo continuam no MESMO episódio (problema perda_ecc)."""
    from app.engine.engine import Resultado
    from app.engine.facts import Alerta
    from app.engine.working_memory import MemoriaTrabalho
    s = sessao_memoria
    lote, d0 = lote_sintetico(s)
    kb = services.kb()

    def dia(i, regra, nivel):
        r = Resultado(wm=MemoriaTrabalho())
        r.alertas.append(Alerta(regra=regra, nivel=nivel, titulo=f"{regra} dia {i}", causa="", acao="",
                                categoria="dieta", cf=0.8, problema="perda_ecc"))
        alertas.sincronizar(s, kb, lote.id, d0 + timedelta(days=i), r, None, "acompanhamento")

    dia(1, "ACP-09", "atencao")
    dia(8, "ACP-05", "critico")
    dia(15, "ACP-09", "atencao")
    [ep] = s.exec(select(AlertaDB).where(AlertaDB.lote_id == lote.id, AlertaDB.problema == "perda_ecc")).all()
    assert ep.regra == "ACP-09" and ep.nivel == "atencao" and ep.ocorrencias == 3
    assert tipos(s, ep) == ["aberto", "agravado", "atenuado"]


def test_registro_em_partes_nao_apaga_o_que_ja_foi_anotado_e_apagar_reprocessa(sessao_memoria, monkeypatch):
    """Cocho de manhã e leite à noite em envios separados: cada envio só toca nos seus indicadores."""
    from app.api import fazendas
    from app.api.schemas import RegistroIn
    from app.db.models import Registro
    s = sessao_memoria
    lote, _ = lote_sintetico(s)
    monkeypatch.setattr(fazendas, "sessao", lambda: _Mesma(s))
    hoje = date.today() + timedelta(days=1)
    fazendas.registrar(lote.id, RegistroIn(data=hoje, valores={"escore_cocho": 3}))
    fazendas.registrar(lote.id, RegistroIn(data=hoje, valores={"vacas": 18, "litros": 400}))
    dia = {r.indicador: r.valor for r in s.exec(select(Registro).where(Registro.lote_id == lote.id, Registro.data == hoje)).all()}
    assert dia == {"escore_cocho": 3, "vacas": 18, "litros": 400}
    # 2ª ordenha: soma ao total do dia, guardando as parcelas
    fazendas.registrar(lote.id, RegistroIn(data=hoje, valores={"litros": 350}, somar=["litros"]))
    litros = s.exec(select(Registro).where(Registro.lote_id == lote.id, Registro.data == hoje, Registro.indicador == "litros")).one()
    assert litros.valor == 750 and litros.texto == "400 + 350"
    fazendas.registrar(lote.id, RegistroIn(data=hoje, valores={"litros": 760}))          # correção do total
    s.refresh(litros)
    assert litros.valor == 760 and litros.texto is None
    with pytest.raises(Exception):
        fazendas.registrar(lote.id, RegistroIn(data=hoje, valores={"vacas": 2}, somar=["vacas"]))
    # valores impossíveis são recusados sem gravar nada (nem os valores válidos do mesmo envio)
    for ruim in ({"litros": -500}, {"vacas": 0}, {"vacas": 18.5}, {"escore_cocho": 7}, {"xyz": 1},
                 {"litros": 5000}, {"concentrado_kg_vaca": 3, "litros": -1}):
        with pytest.raises(Exception):
            fazendas.registrar(lote.id, RegistroIn(data=hoje, valores=ruim))
    assert not s.exec(select(Registro).where(Registro.lote_id == lote.id, Registro.data == hoje,
                                             Registro.indicador == "concentrado_kg_vaca")).first()
    fazendas.apagar_registro(lote.id, hoje, "escore_cocho")
    assert not s.exec(select(Registro).where(Registro.lote_id == lote.id, Registro.data == hoje,
                                             Registro.indicador == "escore_cocho")).first()
    with pytest.raises(Exception):
        fazendas.registrar(lote.id, RegistroIn(data=hoje, valores={}))


class _Mesma:
    """Usa a sessão do teste dentro das rotas (with sessao() as s)."""
    def __init__(self, s):
        self.s = s

    def __enter__(self):
        return self.s

    def __exit__(self, *a):
        return False


def test_mastite_primeiro_tambem_suprime_os_avisos_da_verificacao_da_dieta(sessao_memoria):
    s = sessao_memoria
    lote, _ = lote_sintetico(s)
    hoje = date.today()
    ep = AlertaDB(lote_id=lote.id, regra="VER-01", problema="VER-01", origem="verificacao", nivel="atencao",
                  titulo="Déficit energético", categoria="dieta", aberto_em=hoje, ultima_ocorrencia=hoje, modulo="verificacao")
    s.add(ep)
    s.commit()
    sup = {"dieta": {"tipo": "suprimir", "regra": "META-01", "motivo": "tratar mastite antes de mudar a dieta", "para": "informativo"}}
    alertas.aplicar_meta_na_verificacao(s, lote.id, sup)
    s.refresh(ep)
    assert ep.suprimido and ep.nota.startswith("META-01")
    alertas.aplicar_meta_na_verificacao(s, lote.id, {})          # mastite resolvida: volta ao primeiro plano
    s.refresh(ep)
    assert not ep.suprimido and ep.nota is None


def _episodio(s, lote, ajuste, regra="ACP-06"):
    ep = AlertaDB(lote_id=lote.id, regra=regra, problema=regra, modulo="acompanhamento_diario", nivel="critico",
                  titulo="t", categoria="cocho", aberto_em=date.today(), ultima_ocorrencia=date.today(), ajuste=ajuste)
    s.add(ep)
    s.commit()
    return ep


def test_regra_de_cocho_vazio_carrega_a_proposta_de_mais_oferta():
    from app.engine.engine import Motor
    r = Motor(services.kb(), ["classificacao", "acompanhamento_diario"]).executar(
        services.memoria({"lote.estado": "lactacao", "lote.del": 10, "mon.dias_cocho_vazio": 3}, origem="medido"))
    [a] = [a for a in r.alertas if a.regra == "ACP-06"]
    assert a.ajuste == {"tipo": "oferta", "pct": services.kb().params["sobras_ajuste_pct"]["valor"]}


def test_aviso_de_cocho_propoe_mais_oferta_e_nao_desfaz_a_troca_de_dieta_em_andamento(sessao_memoria, monkeypatch):
    """Lote no meio de uma troca gradual aceita o aviso de cocho vazio: a dieta nova é a atual +5% e a troca continua,
    com os dias que faltam também +5% (o ajuste soma, não substitui a troca)."""
    from app.api import fazendas
    from app.api.schemas import DietaIn, ItemDieta
    s = sessao_memoria
    lote, _ = lote_sintetico(s)
    monkeypatch.setattr(fazendas, "sessao", lambda: _Mesma(s))
    nova = [{"alimento": "silagem_sorgo", "kg_mn": 35}] + [i for i in DIETA_TESTE if i["alimento"] != "silagem_milho"]
    v2 = fazendas.nova_dieta(lote.id, DietaIn(itens=[ItemDieta(**i) for i in nova], motivo="troca de silagem"))
    assert v2["transicao"] and v2["transicao"]["dias"] >= 2
    ep = _episodio(s, lote, {"tipo": "oferta", "pct": 5.0})
    p = services.proposta_ajuste(s, ep)
    assert p["em_transicao"] and p["nota"]
    mais5 = [{"alimento": i["alimento"], "kg_mn": services.arredondar_kg(i["kg_mn"] * 1.05)} for i in nova]
    v3 = fazendas.nova_dieta(lote.id, DietaIn(itens=[ItemDieta(**i) for i in mais5], motivo=p["motivo"], alerta_id=ep.id))
    t2, t3 = v2["transicao"], v3["transicao"]
    assert t3["ajuste_oferta"]["fator"] == pytest.approx(1.05, abs=0.002) and t3["dias"] == t2["dias"] and t3["de_versao"] == t2["de_versao"]
    hoje = date.today().isoformat()
    antes = next(e for e in t2["plano"] if e["data"] == hoje)
    depois = next(e for e in t3["plano"] if e["data"] == hoje)
    for a, b in zip(antes["itens"], depois["itens"]):
        assert b["kg_mn"] == pytest.approx(a["kg_mn"] * 1.05, rel=0.02)


def test_aviso_de_ureia_do_leite_propoe_menos_proteina_sem_faltar_para_o_lote(sessao_memoria):
    s = sessao_memoria
    lote, _ = lote_sintetico(s)
    ep = _episodio(s, lote, {"tipo": "proteina", "pp": 1.0}, regra="ACP-01R")
    p = services.proposta_ajuste(s, ep)
    assert p["tipo"] == "proteina" and p["itens"]
    assert p["mudancas"] or p["nota"]          # ou muda a dieta, ou explica por que não dá para baixar mais
    cat = services.catalogo(s, lote.fazenda_id)
    pb = lambda itens: services.composicao_itens(itens, {}, cat)["pb_pct"]  # noqa: E731
    dieta = services.dieta_ativa(s, lote.id)
    assert pb(p["itens"]) < pb(dieta.itens) if p["mudancas"] else p["itens"] == dieta.itens   # nunca sobe a proteína
    parecer = services.avaliar_lote(s, lote, p["itens"])["fatos"]["parecer.dieta"]["valor"]
    assert parecer != "bloqueada"


def test_movimentacao_atualiza_o_numero_de_vacas_dos_dois_lotes(sessao_memoria, monkeypatch):
    from app.api import fazendas
    from app.api.schemas import EventoIn
    s = sessao_memoria
    lote, _ = lote_sintetico(s)
    outro, _ = lote_sintetico(s)
    monkeypatch.setattr(fazendas, "sessao", lambda: _Mesma(s))
    ev = fazendas.registrar_evento(lote.id, EventoIn(data_hora=datetime.now(), tipo="movimentacao", vacas=5, outro_lote_id=outro.id))
    s.refresh(lote)
    s.refresh(outro)
    assert (lote.n_vacas, outro.n_vacas) == (25, 15) and "20 → 25" in ev["descricao"]
    assert s.exec(select(Evento).where(Evento.lote_id == outro.id, Evento.tipo == "movimentacao")).first()
    with pytest.raises(Exception):
        fazendas.registrar_evento(lote.id, EventoIn(data_hora=datetime.now(), tipo="movimentacao", vacas=-100))


def test_historico_e_resolucao_tem_texto_do_produtor(sessao_memoria):
    from app.engine.engine import Resultado
    from app.engine.facts import Alerta
    from app.engine.working_memory import MemoriaTrabalho
    s = sessao_memoria
    lote, _ = lote_sintetico(s)
    d0 = date.today() - timedelta(days=10)
    r = Resultado(wm=MemoriaTrabalho())
    r.alertas.append(Alerta(regra="ACP-09", nivel="atencao", titulo="técnico", causa="", acao="a", categoria="dieta", cf=0.8,
                            titulo_produtor="As vacas estão emagrecendo", acao_produtor="Dê mais energia"))
    alertas.sincronizar(s, services.kb(), lote.id, d0, r, None, "acompanhamento")
    alertas.sincronizar(s, services.kb(), lote.id, d0 + timedelta(days=9), Resultado(wm=MemoriaTrabalho()), None, "acompanhamento")
    ep = s.exec(select(AlertaDB).where(AlertaDB.lote_id == lote.id)).one()
    hist = alertas.historico_do(s, ep.id)
    assert [h.descricao_produtor for h in hist][0] == "As vacas estão emagrecendo"
    assert ep.estado == "resolvido" and ep.resolucao_produtor.startswith("O problema não aparece mais")


def test_cocho_vazio_junta_os_avisos_da_dieta_numa_proposta_so(sessao_memoria):
    """Lote comendo tudo (cocho vazio) com dieta fraca: a proposta aumenta a oferta e já corrige o resto, e a dieta
    proposta não é acusada de "mais comida do que o lote come" (o consumo medido vence a equação: EXG-01V)."""
    from app.db.models import Registro
    s = sessao_memoria
    extra = {(i, "escore_cocho"): 1 for i in range(37, 40)}
    lote, _ = lote_sintetico(s, extra=extra)
    fatos = services.fatos_lote(lote, date.today(), services.historico(s, lote.id), s)
    assert fatos["mon.dias_cocho_vazio"] >= 2 and fatos["mon.ms_ofertada_cocho"] > 0
    ep = _episodio(s, lote, {"tipo": "oferta", "pct": 5.0})
    p = services.proposta_ajuste(s, ep)
    r = services.avaliar_lote(s, lote, p["itens"])
    regras = {a["regra"] for a in r["alertas"] if a["status"] == "ativo"}
    assert "VER-06" not in regras                             # não reclama de oferta acima do consumo
    assert r["fatos"]["exig.cms"]["valor"] >= fatos["mon.ms_ofertada_cocho"]   # medição é o piso do consumo
    if p.get("corrige"):                                      # havia outros problemas: a proposta os resolve junto
        assert r["fatos"]["parecer.dieta"]["valor"] in ("adequada", "ajustar") and "VER-01" not in regras


def test_proposta_do_aviso_nao_se_repete_depois_de_aplicada(sessao_memoria, monkeypatch):
    """Salvar a dieta proposta pelo aviso de cocho e reabrir não soma outro +5%: só propõe de novo se o cocho
    continuar vazio COM a dieta nova (leituras posteriores a ela)."""
    from app.api import fazendas
    from app.api.schemas import DietaIn, ItemDieta
    from app.db.models import Registro
    s = sessao_memoria
    lote, _ = lote_sintetico(s, extra={(i, "escore_cocho"): 1 for i in range(37, 40)})
    monkeypatch.setattr(fazendas, "sessao", lambda: _Mesma(s))
    ep = _episodio(s, lote, {"tipo": "oferta", "pct": 5.0})
    p1 = services.proposta_ajuste(s, ep)
    assert not p1.get("ja_aplicado")
    fazendas.nova_dieta(lote.id, DietaIn(itens=[ItemDieta(**i) for i in p1["itens"]], motivo=p1["motivo"], alerta_id=ep.id))
    p2 = services.proposta_ajuste(s, ep)
    assert p2["ja_aplicado"] and p2["itens"] == services.dieta_ativa(s, lote.id).itens   # não aumenta de novo
    a = fazendas.obter_alerta(ep.id)
    assert a["acao_em"]                                       # a tela mostra que a ação já foi registrada
    for k in (1, 2):                                          # cocho continua vazio com a dieta nova
        s.add(Registro(lote_id=lote.id, data=date.today() + timedelta(days=k), indicador="escore_cocho", valor=1))
    s.commit()
    assert not services._evidencia_nova(s, lote, "oferta", date.today(), date.today())    # hoje ainda sem leitura nova
    assert services._evidencia_nova(s, lote, "oferta", date.today(), date.today() + timedelta(days=2))


def test_excluir_lote_apaga_o_que_e_dele(sessao_memoria, monkeypatch):
    from app.api import fazendas
    from app.db.models import Lote, Registro
    s = sessao_memoria
    lote, _ = lote_sintetico(s)
    monkeypatch.setattr(fazendas, "sessao", lambda: _Mesma(s))
    services.monitorar(s, lote, date.today())
    fazendas.excluir_lote(lote.id)
    assert s.get(Lote, lote.id) is None
    for modelo in (Registro, Dieta, Evento, AlertaDB, HistoricoAlerta):
        assert not s.exec(select(modelo).where(modelo.lote_id == lote.id)).first()
