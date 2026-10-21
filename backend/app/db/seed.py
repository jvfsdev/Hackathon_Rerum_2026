"""Fazenda de demonstração com 60 dias de histórico e cenários roteirizados.

Lote 1  Girolando confinado: troca de silagem no dia 40 (MS 31 → 26%), queda, correção da MS no dia 50, laudo com NUL alto.
Lote 2  Girolando semiconfinado: aumento de concentrado no dia 30 que não se paga; onda de calor nos dias 46–51.
Lote 3  Holandês pós-parto: perda de ECC (3,5 → 2,25), cocho vazio nos últimos dias, G:P alta no laudo.
Lote 4  Mestiças a pasto: lactose caindo com CCS subindo (mastite primeiro) e reagrupamento de vacas no dia 57.
Uso: python -m app.db.seed
"""
import random
from datetime import date, datetime, time, timedelta

from sqlmodel import SQLModel

from ..calc.lactation_curve import cobuci
from .. import services
from .models import DB_PATH, Dieta, Evento, Fazenda, Lote, Registro, criar_tabelas, engine, sessao

DIAS = 60


def gerar():
    if DB_PATH.exists():
        DB_PATH.unlink()
    SQLModel.metadata.drop_all(engine)
    criar_tabelas()
    rnd = random.Random(42)
    hoje = date.today()
    dia0 = hoje - timedelta(days=DIAS - 1)
    dia = lambda i: dia0 + timedelta(days=i)  # noqa: E731
    quando = lambda i, h=8: datetime.combine(dia(i), time(h, 0))  # noqa: E731

    with sessao() as s:
        faz = Fazenda(nome="Sítio Boa Vista", municipio="Coronel Pacheco — MG", porte="medio",
                      preco_leite=2.45, preco_concentrado=1.90, latitude=-21.58, longitude=-43.26,
                      bonificacao={  # tabela do laticínio (exemplo): faixas em R$/L
                          "ccs": [{"min": None, "max": 200, "rs_l": 0.03}, {"min": 200.01, "max": 400, "rs_l": 0.0},
                                  {"min": 400.01, "max": None, "rs_l": -0.04}],
                          "cbt": [{"min": None, "max": 100, "rs_l": 0.02}, {"min": 100.01, "max": None, "rs_l": -0.03}],
                          "gordura": [{"min": 3.8, "max": None, "rs_l": 0.02}],
                          "proteina": [{"min": 3.3, "max": None, "rs_l": 0.02}]})
        s.add(faz)
        s.commit()
        s.refresh(faz)

        lotes = {
            1: Lote(fazenda_id=faz.id, nome="Lote 1 — Alta produção", finalidade="Vacas de alta produção",
                    sistema="confinado", grupo_genetico="girolando", n_vacas=40, pv=560, data_ref=dia0, del_ref=45,
                    dias_gestacao_ref=0, fracao_primiparas=0.25, gordura=3.7, proteina=3.2),
            2: Lote(fazenda_id=faz.id, nome="Lote 2 — Média produção", finalidade="Meio de lactação",
                    sistema="semiconfinado", grupo_genetico="girolando", n_vacas=30, pv=520, data_ref=dia0, del_ref=91,
                    dias_gestacao_ref=30, fracao_primiparas=0.2, gordura=3.9, proteina=3.3),
            3: Lote(fazenda_id=faz.id, nome="Lote 3 — Pós-parto", finalidade="Recém-paridas e início de lactação",
                    sistema="confinado", grupo_genetico="holandes", n_vacas=15, pv=620, data_ref=dia0, del_ref=-19,
                    dias_gestacao_ref=0, fracao_primiparas=0.3, gordura=3.6, proteina=3.1),
            4: Lote(fazenda_id=faz.id, nome="Lote 4 — Final de lactação", finalidade="Baixa produção a pasto",
                    sistema="pasto", grupo_genetico="mestica", n_vacas=20, pv=480, data_ref=dia0, del_ref=181,
                    dias_gestacao_ref=150, fracao_primiparas=0.1, distancia_km=1.5, relevo="ondulado", forrageira="decumbens",
                    gordura=4.0, proteina=3.4),
        }
        for lote in lotes.values():
            s.add(lote)
        s.commit()
        for lote in lotes.values():
            s.refresh(lote)

        def dieta(lote, versao, itens, inicio, motivo, ms_ref=None, ativa=True, origem="usuario"):
            s.add(Dieta(lote_id=lote.id, versao=versao, itens=itens, inicio=inicio, motivo=motivo,
                        ms_silagem_ref=ms_ref, ativa=ativa, origem=origem))

        dieta(lotes[1], 1, [{"alimento": "silagem_milho", "kg_mn": 32}, {"alimento": "milho_moido", "kg_mn": 4},
                            {"alimento": "farelo_soja", "kg_mn": 2.6}, {"alimento": "nucleo_mineral", "kg_mn": 0.2}],
              dia0, "Dieta inicial", ms_ref=30.9, ativa=False)
        dieta(lotes[1], 2, [{"alimento": "silagem_milho", "kg_mn": 38}, {"alimento": "milho_moido", "kg_mn": 4},
                            {"alimento": "farelo_soja", "kg_mn": 2.6}, {"alimento": "nucleo_mineral", "kg_mn": 0.2}],
              dia(50), "Correção da MS da silagem nova (31 → 26%): 32 → 38 kg MN", ms_ref=26.0)
        dieta(lotes[2], 1, [{"alimento": "silagem_sorgo", "kg_mn": 25}, {"alimento": "milho_moido", "kg_mn": 3},
                            {"alimento": "farelo_soja", "kg_mn": 1.5}, {"alimento": "nucleo_mineral", "kg_mn": 0.15}],
              dia0, "Dieta inicial", ms_ref=30.8)
        dieta(lotes[3], 1, [{"alimento": "silagem_milho", "kg_mn": 35}, {"alimento": "milho_moido", "kg_mn": 6},
                            {"alimento": "farelo_soja", "kg_mn": 3.5}, {"alimento": "caroco_algodao", "kg_mn": 1.5},
                            {"alimento": "nucleo_mineral", "kg_mn": 0.25}], dia0, "Dieta de pós-parto", ms_ref=30.9)
        dieta(lotes[4], 1, [{"alimento": "braquiaria", "kg_mn": 30}, {"alimento": "milho_moido", "kg_mn": 1.5},
                            {"alimento": "farelo_soja", "kg_mn": 0.5}, {"alimento": "nucleo_mineral", "kg_mn": 0.1}],
              dia0, "Pasto + suplemento")

        eventos = [
            Evento(lote_id=lotes[1].id, data_hora=quando(40), tipo="troca_volumoso", descricao="Abertura do silo 2"),
            Evento(lote_id=lotes[1].id, data_hora=quando(40), tipo="silo_novo", descricao="Silo 2 (milho, safrinha)"),
            Evento(lote_id=lotes[1].id, data_hora=quando(50, 7), tipo="correcao_ms", descricao="Silagem 32 → 38 kg MN"),
            Evento(lote_id=lotes[2].id, data_hora=quando(30), tipo="mudanca_concentrado", descricao="Concentrado 3,0 → 4,5 kg/vaca"),
            Evento(lote_id=lotes[4].id, data_hora=quando(57, 7), tipo="movimentacao", descricao="Entrada de 5 vacas do Lote 2"),
        ]
        for e in eventos:
            s.add(e)

        k = {1: 1.32, 2: 0.89, 3: 1.80, 4: 0.69}
        conc = {1: 4.0, 2: 3.0, 3: 6.0, 4: 1.5}
        regs = []

        def reg(lote, i, ind, valor, metodo=None):
            regs.append(Registro(lote_id=lote.id, data=dia(i), indicador=ind, valor=round(valor, 3), metodo=metodo))

        for i in range(DIAS):
            calor = 46 <= i <= 51
            temp = 31.0 + rnd.uniform(-0.5, 0.5) if calor else 21.5 + rnd.uniform(-1.5, 1.5)
            ur = 72 + rnd.uniform(-2, 2) if calor else 65 + rnd.uniform(-4, 4)
            for n, lote in lotes.items():
                del_ = lote.del_ref + i
                if del_ < 1:
                    continue
                efeito = 1.0
                vacas = lote.n_vacas
                c = conc[n]
                if n == 1 and 41 <= i <= 49:
                    efeito -= 0.11                                   # silagem úmida não corrigida
                if n == 1 and 50 <= i <= 53:
                    efeito -= 0.11 - 0.025 * (i - 49)               # recuperação após correção
                if n == 2 and i >= 30:
                    c = 4.5
                    efeito += 0.02                                   # resposta fraca ao concentrado extra
                if n in (2, 3) and 47 <= i <= 53:
                    efeito -= 0.10 if n == 2 else 0.07               # calor (com atraso de 1 dia)
                if n == 4 and i >= 40:
                    efeito -= 0.004 * (i - 40)                       # mastite subclínica avançando
                if n == 4 and i >= 57:
                    vacas += 5
                    efeito -= 0.08 if i <= 58 else 0.03              # reagrupamento
                y = cobuci(del_) * k[n] * efeito * (1 + rnd.uniform(-0.02, 0.02))
                reg(lote, i, "vacas", vacas)
                reg(lote, i, "litros", y * vacas)
                reg(lote, i, "concentrado_kg_vaca", c)
                reg(lote, i, "temp", temp)
                reg(lote, i, "ur", ur)
                if n == 1:                                           # fazenda pesa as sobras do lote 1 (vagão)
                    reg(lote, i, "sobras_pct", 3.0 + rnd.uniform(-0.8, 0.8))
                elif lote.sistema != "pasto":                        # demais: leitura de cocho 1–5 antes do 1º trato
                    escore = rnd.choice([3, 3, 3, 3, 3, 3, 2, 4])
                    if n == 3 and i >= 57:
                        escore = 1                                   # cocho vazio
                    reg(lote, i, "escore_cocho", escore)
                if i % 7 == 0 or (n == 1 and i in (41, 44, 48)):
                    if n in (1, 3):
                        ms = 26.0 + rnd.uniform(-0.4, 0.4) if (n == 1 and i >= 41) else 31.0 + rnd.uniform(-0.6, 0.6)
                        reg(lote, i, "ms_silagem", ms, "micro-ondas")
                    if n == 2:
                        reg(lote, i, "ms_silagem", 30.8 + rnd.uniform(-0.6, 0.6), "micro-ondas")
                if n == 4 and i % 7 == 5:          # régua no pasto (lotação contínua): altura média caindo
                    reg(lote, i, "altura_media", 27 - 0.15 * i)
                if i % 7 == 3:
                    ecc = {1: 2.75, 2: 3.0, 3: max(2.25, 3.5 - 0.035 * (i - 20)), 4: 3.25}[n]
                    reg(lote, i, "ecc", ecc)
                    reg(lote, i, "escore_fezes", 3.0)
            # laudos mensais (controle leiteiro por lote)
        laudos = {
            1: [(2, dict(gordura=3.75, proteina=3.2, lactose=4.6, nul=14.0, ccs=230, cbt=65)),
                (20, dict(gordura=3.7, proteina=3.2, lactose=4.6, nul=14.5, ccs=240, cbt=60, crioscopia=-0.540)),
                (50, dict(gordura=3.3, proteina=3.22, lactose=4.55, nul=21.0, ccs=260, cbt=55, crioscopia=-0.541))],
            2: [(2, dict(gordura=3.9, proteina=3.3, lactose=4.6, nul=12.2, ccs=290, cbt=75)),
                (20, dict(gordura=3.9, proteina=3.3, lactose=4.6, nul=12.0, ccs=300, cbt=70)),
                (50, dict(gordura=3.85, proteina=3.3, lactose=4.6, nul=12.5, ccs=310, cbt=65, crioscopia=-0.521))],
            3: [(50, dict(gordura=4.6, proteina=3.0, lactose=4.7, nul=13.0, ccs=180, cbt=50))],
            4: [(2, dict(gordura=4.0, proteina=3.4, lactose=4.45, nul=14.8, ccs=330, cbt=85)),
                (20, dict(gordura=4.0, proteina=3.4, lactose=4.4, nul=15.0, ccs=380, cbt=90)),
                (50, dict(gordura=4.1, proteina=3.35, lactose=4.1, nul=17.5, ccs=520, cbt=95))],
        }
        for n, lista in laudos.items():
            for i, vals in lista:
                for ind, v in vals.items():
                    reg(lotes[n], i, f"laudo_{ind}", v, "laboratório RBQL")
        s.add_all(regs)
        s.commit()

        # insumo cadastrado pela fazenda, com análise do laboratório (silo novo do Lote 1)
        services.criar_alimento(s, faz, dict(nome="Silagem de milho — silo 2 (laudo)", tipo="volumoso", ms=26.0, pb=7.8,
                                             fdn=52.0, ndt=63.0, ee=2.8, mm=4.6, origem_dado="laboratorio",
                                             fonte="Laudo bromatológico 1043 (silo 2)", fdnd=55.0, preco_kg_mn=0.24))
        # preços informados pela fazenda (os demais ficam no valor de referência)
        services.registrar_precos(s, faz, {"milho_moido": 1.30, "farelo_soja": 2.70}, dia(20), "cotação da cooperativa")
        services.registrar_precos(s, faz, {"milho_moido": 1.45, "leite": 2.45}, dia(55), "nota fiscal / extrato do laticínio")

        # acompanhamento dia a dia, com ações de usuário simuladas nas datas do roteiro
        from sqlmodel import select
        from .. import alertas
        from .models import AlertaDB

        def episodio(n, regra):
            return s.exec(select(AlertaDB).where(AlertaDB.lote_id == lotes[n].id, AlertaDB.regra == regra,
                                                 AlertaDB.estado.in_(alertas.ATIVOS))).first()

        def acoes_do_dia(i):
            if i == 44 and (ep := episodio(1, "ACP-S01")):
                alertas.aceitar(s, ep, "silo novo mais úmido", quando(44, 14))
            if i == 50 and (ep := episodio(1, "ACP-S01")):
                v2 = s.exec(select(Dieta).where(Dieta.lote_id == lotes[1].id, Dieta.versao == 2)).one()
                alertas.registrar_acao(s, ep.id, lotes[1].id, "Nova dieta v2: silagem 32 → 38 kg MN (MS 26%)",
                                       {"dieta_id": v2.id}, quando(50, 7))
            if i == 36 and (ep := episodio(2, "ACP-D06")):
                alertas.recusar(s, ep, "aumento de concentrado é um teste planejado de 3 semanas", quando(36, 9))
            if i == 51 and (ep := episodio(4, "ACP-M05")):
                alertas.aceitar(s, ep, "", quando(51, 7))
                ev = Evento(lote_id=lotes[4].id, data_hora=quando(51, 9), tipo="manejo_sanitario",
                            descricao="CMT no lote: 3 vacas positivas tratadas; pré-dipping revisado")
                s.add(ev)
                s.commit()
                alertas.registrar_acao(s, ep.id, lotes[4].id, f"Evento manejo sanitário: {ev.descricao}",
                                       {"evento_id": ev.id}, quando(51, 9))
            if i == 59 and (ep := episodio(3, "ACP-06")):
                alertas.aceitar(s, ep, "aumentar oferta no próximo trato", quando(59, 7))

        historicos = {n: services.historico(s, lote.id) for n, lote in lotes.items()}
        for i in range(DIAS):
            for n, lote in lotes.items():
                if lote.estado != "lactacao" or (lote.del_ref + i) >= 1:
                    services.monitorar(s, lote, dia(i), historicos[n])
            acoes_do_dia(i)
        for lote in lotes.values():
            services.avaliar_lote(s, lote)        # alertas da dieta ativa
    print(f"Fazenda demo criada em {DB_PATH} ({DIAS} dias, {len(lotes)} lotes).")


if __name__ == "__main__":
    gerar()
