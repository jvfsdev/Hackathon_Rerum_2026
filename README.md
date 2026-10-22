# CochoCerto — sistema especialista de dietas por lote

Hackathon UFJF 2026 (XXVIII Semana da Computação · RERUM), **Tema T2 — Dietas**.

Orienta e acompanha **lotes** de vacas leiteiras: classifica o lote, calcula exigências, verifica a dieta, sugere a dieta de **custo mínimo** e acompanha o dia a dia (produção × curva esperada, cocho, silagem, ECC, laudo do laticínio). Os alertas vêm com causa provável, ação sugerida e explicação **"por quê?/como?"**.

Quem decide é a **base de conhecimento (172 regras de produção com fator de certeza)** + **motor de inferência próprio** (encadeamento progressivo e regressivo, resolução de conflito, CF estilo MYCIN). Não há LLM no sistema: as decisões são determinísticas e auditáveis.

## Rodar (localhost)

Requisitos: Python 3.11+ e Node 20+.

```bash
# API
cd backend
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/python -m app.db.seed            # fazenda demo: 4 lotes, 60 dias de histórico
.venv/bin/uvicorn app.main:app --port 8000

# Interface (outro terminal)
cd frontend
npm install
npm run dev                                 # http://localhost:5173
```

No celular (mesma rede Wi-Fi): `npm run dev:rede` e abra `http://<ip-do-computador>:5173` — a página inicial vira o **modo campo** (registro rápido + avisos, funciona sem conexão e envia depois).

Testes: `cd backend && .venv/bin/pytest -q`, com 471 testes, entre eles 36 casos de resultado conhecido em `backend/tests/cases.yaml` (os mesmos rodam na tela **Base de conhecimento**).

Sem internet o sistema funciona por completo: o clima passa a ser digitado e os preços de referência ficam no último valor coletado. Para desligar a coleta diária de preços: `LEITE_SEM_COLETA=1`. Documentação interativa da API: `http://localhost:8000/docs`.

## Funcionalidades

- **Lotes:** cadastro (ou a partir da consulta guiada), perfil e exigências com "como?".
- **Dieta:** verificação com parecer e CF, sugestão de custo mínimo (PL) verificada pelas mesmas regras, editor, versões e restauração, quadrado de Pearson, DCAD no pré-parto.
- **Acompanhamento:** produção × curva esperada com eventos no gráfico, cocho diário por escore 1–5, MS da silagem, ECC e fezes com escalas descritas, laudo do laticínio, economia (custo de concentrado, IOFC, bonificação), importação CSV.
- **Alertas:** causa provável, ação sugerida, aceitar (leva à tela da ação) ou recusar com motivo, resolução automática explicada e histórico.
- **Insumos e preços:** preços por fazenda com histórico, insumos próprios com composição, preços de referência diários (Cepea, IPEADATA).
- **Base de conhecimento:** regras, parâmetros editáveis (sobe a versão e roda os casos), changelog.
- **Modo campo** no celular: registro rápido, clima automático, avisos e checklist do trato, com fila offline.
- **Visão do produtor × visão técnica:** o produtor vê avisos em linguagem de fazenda; o técnico vê regras, CF e traço.
- **"O que precisaria mudar?"** em cada aviso (explicação contrafactual) e **menor mudança na dieta** que a corrige.
- **Simulador "e se?"**: mais/menos concentrado, troca de volumoso, preços e meta de leite → custo, leite que a comida sustenta e sobra por vaca.
- **Até quanto vale pagar** em cada alimento (sensibilidade de preços da dieta de custo mínimo).
- **Planilha de trato** (vagão: kg por trato, ordem de carga, impressão) e **troca de dieta aos poucos** com plano dia a dia.
- **Previsão dos próximos 30 dias**: leite com faixa de incerteza, secagens, receita, custo e sobra por lote e da fazenda.
- **Estoque** (dias até acabar e quando comprar), **relatório semanal** para imprimir/PDF e **revisão da base pelo uso** (regras recusadas ou que somem sozinhas).

## Onde está cada coisa

| Componente do edital | Onde |
|---|---|
| Base de conhecimento (regras, CF, versionada) | `backend/kb/` (YAML + `CHANGELOG.md`) |
| Motor de inferência | `backend/app/engine/` |
| Memória de trabalho | `backend/app/engine/working_memory.py` |
| Módulo de explicação | `backend/app/engine/explain.py` + gavetas "Como?" / "Por que este alerta?" na UI |
| Aquisição de conhecimento | Tela **Base de conhecimento** (modo especialista) + edição dos YAML |
| Interface | `frontend/` (React) |
| Fontes externas | Open-Meteo (clima → ITU), Cepea e IPEADATA (preços), CQBAL 4.0 (composição dos alimentos), CSV do controle leiteiro/laudo |

## Documentação

- [docs/arquitetura.md](docs/arquitetura.md): arquitetura e fluxo.
- [docs/regras.md](docs/regras.md): regras de produção, parâmetros e alimentos (gerado da base).
- [docs/processo-ia.md](docs/processo-ia.md): processo de desenvolvimento com IA.
- [docs/plano.md](docs/plano.md): plano completo.
- Referências de domínio: `dossie.md`, `dados.md`, `Inferências de dados leiteiros por lote.md`.

## Fontes de dados

- Composição dos alimentos: VALADARES FILHO, S.C., LOPES, S.A. et al. **CQBAL 4.0**. Tabelas Brasileiras de Composição de Alimentos para Ruminantes. 2018. Disponível em: www.cqbal.com.br.
- Preços de referência: **Cepea/Esalq-USP** (milho, leite MG; CC BY-NC 4.0) e **Deral-PR via IPEADATA** (farelo de soja).
- Clima: **Open-Meteo**.
- Equações e limiares: NRC 2001, NASEM 2021, BR-Leite (Embrapa) e demais fontes citadas em cada regra e parâmetro ([docs/regras.md](docs/regras.md)).

> Os valores numéricos são referências de literatura para uma prova de conceito e precisam de validação por zootecnista.
