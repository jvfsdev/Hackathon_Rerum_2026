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
                      preco_leite=2.45, preco_concentrado=1.90, latitude=-21.58, longitude=-43.26)
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
                    dias_gestacao_ref=150, fracao_primiparas=0.1, distancia_km=1.5, relevo="ondulado",
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
                if lote.sistema != "pasto":
                    sobra = (3.5 + rnd.uniform(-0.4, 0.4)) if n == 3 else (3.0 + rnd.uniform(-0.8, 0.8))
                    if n == 3 and i >= 57:
                        sobra = 0.0                                  # cocho vazio
                    reg(lote, i, "sobras_pct", sobra)
                if i % 7 == 0 or (n == 1 and i in (41, 44, 48)):
                    if n in (1, 3):
                        ms = 26.0 + rnd.uniform(-0.4, 0.4) if (n == 1 and i >= 41) else 31.0 + rnd.uniform(-0.6, 0.6)
                        reg(lote, i, "ms_silagem", ms, "micro-ondas")
                    if n == 2:
                        reg(lote, i, "ms_silagem", 30.8 + rnd.uniform(-0.6, 0.6), "micro-ondas")
                if i % 7 == 3:
                    ecc = {1: 2.75, 2: 3.0, 3: max(2.25, 3.5 - 0.035 * (i - 20)), 4: 3.25}[n]
                    reg(lote, i, "ecc", ecc)
                    reg(lote, i, "escore_fezes", 3.0)
            # laudos mensais (controle leiteiro por lote)
        laudos = {
            1: [(2, dict(gordura=3.75, proteina=3.2, lactose=4.6, nul=14.0, ccs=230, cbt=65)),
                (20, dict(gordura=3.7, proteina=3.2, lactose=4.6, nul=14.5, ccs=240, cbt=60)),
                (50, dict(gordura=3.3, proteina=3.22, lactose=4.55, nul=21.0, ccs=260, cbt=55))],
            2: [(2, dict(gordura=3.9, proteina=3.3, lactose=4.6, nul=12.2, ccs=290, cbt=75)),
                (20, dict(gordura=3.9, proteina=3.3, lactose=4.6, nul=12.0, ccs=300, cbt=70)),
                (50, dict(gordura=3.85, proteina=3.3, lactose=4.6, nul=12.5, ccs=310, cbt=65))],
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

        for lote in lotes.values():
            services.reprocessar(s, lote, dia0, hoje)
    print(f"Fazenda demo criada em {DB_PATH} ({DIAS} dias, {len(lotes)} lotes).")


if __name__ == "__main__":
    gerar()
