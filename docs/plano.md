# Plano — CochoCerto, sistema especialista de dietas por lote (Hackathon UFJF 2026, Tema T2)

> **Documento de planejamento (21/10), mantido como registro do processo.** O estado atual do sistema está em
> [arquitetura.md](arquitetura.md) e no [README](../README.md). Diferenças em relação ao plano: o solver é o HiGHS
> (o PuLP 4 não traz o CBC); a composição dos alimentos vem do CQBAL 4.0, não das tabelas da Embrapa de 2006;
> foram acrescentados preços por fazenda e de referência, insumos próprios, alertas como episódios com histórico,
> modo campo no celular e DCAD. Ficou de fora a destinação econômica como objetivo do lote.


## Contexto

O repositório está vazio (só `README.md` e 4 documentos de referência). Precisamos construir, até **quinta 22/10 às 20h**, uma aplicação em localhost que oriente e acompanhe lotes de vacas leiteiras em **dieta e comportamento alimentar**, seguindo as exigências do edital ([requisitos-hackathon-ufjf-2026.md](requisitos-hackathon-ufjf-2026.md)):
- **base de conhecimento explícita** (regras + CF, versionada) + **motor de inferência** determinístico. A LLM **não decide**.
- memória de trabalho, interface, explicação "por quê?/como?", aquisição de conhecimento, testes com casos conhecidos validando cada versão da base.

O domínio já está levantado em [dossie.md](dossie.md) (regras CLS/EXG/VER/ACP, equações, testes T1–T18), [dados.md](dados.md) (o que cada porte de fazenda registra e com que frequência) e [Inferências de dados leiteiros por lote.md](Inferências%20de%20dados%20leiteiros%20por%20lote.md) (curva esperada, detecção de quedas, economia do concentrado, 43 regras de alerta com força de evidência A–D).

**Decisões tomadas:** Python (FastAPI) + React/Vite; escopo = MVP **com PL de custo mínimo obrigatório** + acompanhamento; 3 pessoas.

**Ideia central do produto:** funciona com 3–4 números por lote por dia (nº de vacas, litros, kg de concentrado, dieta/piquete). Todo o resto (MS da silagem, sobras, ECC, laudo do laticínio, bromatologia) é opcional e entra com valor padrão de tabela e **rótulo de confiança** que vira CF.

---

## 0. Primeiro passo da implementação: criar `CLAUDE.md` na raiz

Conteúdo a gravar em `/Users/jvfs/Documents/repos/Hackathon/CLAUDE.md`. Ele vale para os 3 integrantes e para os agentes de IA que eles usarem:

````markdown
# Sistema especialista de dietas por lote — Hackathon UFJF 2026 (T2)

Aplicação local que orienta e acompanha lotes de vacas leiteiras em dieta e comportamento alimentar.
Entrega: quinta 22/10 às 20h. Demo: sexta 23/10 às 9h, rodando em localhost.

## Regra de ouro (exigência do edital)
- **Quem decide é a base de conhecimento + o motor de inferência**, de forma determinística e auditável.
- Nunca use LLM para gerar números, conclusões ou alertas dentro do sistema.
- A IA só ajuda a construir o código e a extrair regras.

## Documentos de referência (ler antes de mexer em regras)
- `requisitos-hackathon-ufjf-2026.md`: o que o edital exige e os critérios de avaliação.
- `dossie.md`: regras CLS/EXG/VER/ACP, equações e casos de teste T1–T18.
- `Inferências de dados leiteiros por lote.md`: curva esperada, detecção de quedas, economia do concentrado, 43 regras de alerta com força de evidência A–D e lista de valores conflitantes.
- `dados.md`: o que cada porte de fazenda registra e com que frequência.

## Stack
Python 3.11+ · FastAPI · SQLModel/SQLite · PuLP (CBC) · pytest | React + Vite + TS + Tailwind + Recharts.
O motor de inferência é próprio. Não usar Experta: quebra em Python ≥3.10.

## Estrutura
```
backend/app/engine/     motor: fatos, memória de trabalho, agenda, conflito, CF, traço, explicação
backend/app/calc/       funções PURAS (CMS, energia, proteína, ITU, curva, economia, conversões)
backend/app/optimizer/  PL de custo mínimo (metas/restrições vêm do motor)
backend/app/monitor/    séries: esperado, resíduo, EWMA/CUSUM, médias móveis
backend/app/api/        rotas FastAPI
backend/app/db/         modelos + seed (fazenda demo com 60 dias)
backend/kb/             BASE DE CONHECIMENTO: rules/*.yaml, params.yaml, foods.yaml, CHANGELOG.md
backend/tests/          cases.yaml (casos conhecidos) + testes unitários
frontend/               interface React
docs/                   processo-ia.md, arquitetura.md, regras.md, apresentação
```

## Comandos
```
cd backend && pip install -e ".[dev]"      # dependências
cd backend && pytest -q                     # TODOS os testes devem passar antes de commitar
cd backend && python -m app.db.seed         # recria a fazenda demo
cd backend && uvicorn app.main:app --reload # API em :8000
cd frontend && npm install && npm run dev   # UI em :5173
```

## Convenções da base de conhecimento
- Formato da regra:
  `id, versao, modulo, descricao, prioridade, se: [{fato, op, valor}], entao: [...], cf, fonte, forca`.
- IDs por módulo:
  - `CLS-` classificação
  - `EXG-` exigências
  - `VER-` verificação
  - `FOR-` formulação/PL
  - `ACP-` acompanhamento
  - `META-` resolução de conflito/supressão
- **Nunca coloque número fixo dentro da regra.** Limiares vão em `params.yaml`, com `valor, unidade, fonte, forca (A–D), editavel`, e são referenciados como `@params.nome`.
- Todo alimento em `foods.yaml` tem `fonte` e `forca`. Valor de tabela entra com CF 0,6, medição com <30 dias com CF 0,8, medição recente com CF 1,0.
- Mudou regra ou parâmetro: suba `kb_version`, anote em `kb/CHANGELOG.md` e adicione ou ajuste o caso em `tests/cases.yaml`.
- Valores ⚠ NV ou conflitantes (ver a última seção de `Inferências...md`) viram parâmetro com força explícita, nunca constante escondida.

## Convenções do motor e do cálculo
- `calc/` não acessa banco nem motor: entra número, sai número. Cada função tem um teste com valor publicado.
- Toda conclusão precisa aparecer no traço com a regra, os fatos usados, o CF e a fonte. Sem traço, não vai para a UI.
- CF no estilo MYCIN: `cf_regra × min(cf_premissas)`. Para a mesma conclusão vinda de regras diferentes: `cf1 + cf2·(1−cf1)`.
- Resolução de conflito: módulo → prioridade → especificidade → recência. Há refração: a mesma regra não dispara duas vezes com os mesmos fatos.
- Dia sem registro gera lembrete, nunca alerta zootécnico. Movimentação de vacas ou correção de MS suprime alertas de queda por 48 h.
- "Mastite primeiro": lactose baixa com CCS subindo suprime recomendação de dieta. "Calor explica": queda de leite com ITU alto rebaixa os alertas de dieta.

## Divisão do time
- P1 · Conhecimento e testes: `kb/`, `tests/cases.yaml`, seed, `docs/regras.md`.
- P2 · Motor, cálculo e PL: `engine/`, `calc/`, `monitor/`, `optimizer/`, API de inferência.
- P3 · Interface e entrega: `frontend/`, API de CRUD, docs, slides, roteiro da demo.
- Contrato da API: os schemas Pydantic em `backend/app/api/schemas.py` são a fonte da verdade. Mudou o schema, avise o time.

## Git
- Branch por pessoa ou feature (`p1/regras-acp`, `p2/motor`, `p3/tela-dieta`). PR curto para `main`, com `pytest` verde.
- Registre prompts relevantes usados com a IA em `docs/processo-ia.md` (vira material da apresentação).

## Fora do escopo
KPIs reprodutivos, sensores individuais, aminoácidos/minerais detalhados, NASEM completo, ML.
````

Em seguida, a implementação segue as seções abaixo, começando pelo esqueleto do repositório (§3).

## 1. Fluxo geral do sistema

```
 ┌──────────────┐   ┌────────────────────┐   ┌────────────────────────────┐   ┌────────────────────┐
 │ 1. Cadastro  │──▶│ 2. Classificação   │──▶│ 3. Exigências e metas      │──▶│ 4. Dieta           │
 │ fazenda/lote │   │ (Módulo A · CLS)   │   │ (Módulo B · EXG)           │   │ 4a verificar (VER) │
 │ alimentos    │   │ → PerfilLote       │   │ CMS, ELl, PM, FDN/CNF...   │   │ 4b sugerir PL (FOR)│
 └──────────────┘   └────────────────────┘   └────────────────────────────┘   └─────────┬──────────┘
                                                                                         │ parecer + CF
                                                                                         ▼ + "como?"
 ┌──────────────────────────────────────────────────────────────────────────┐   ┌────────────────────┐
 │ 6. Acompanhamento (Módulo D · ACP) — ciclo contínuo                      │◀──│ 5. Dieta ativa     │
 │ registro diário/semanal/mensal → esperado vs observado → alertas         │   │ (versionada)       │
 │ hierarquizados (Crítico/Atenção/Info) com causa provável + ação + porquê │──▶│ ajuste aceito =    │
 └──────────────────────────────────────────────────────────────────────────┘   │ nova versão+motivo │
                                                                                 └────────────────────┘
```

Em toda etapa: as respostas do usuário e as conclusões vão para a **memória de trabalho**; cada disparo de regra vai para o **traço**, que alimenta "por quê?" (por que o sistema está perguntando isto) e "como?" (como chegou nesta conclusão).

---

## 2. Arquitetura (mapeada ao modelo conceitual do edital)

```
React (Vite, mobile-first)  ──HTTP/JSON──▶  FastAPI
                                              ├─ api/            rotas
                                              ├─ engine/         MOTOR DE INFERÊNCIA (próprio)
                                              │    working_memory, agenda, conflito, CF, traço,
                                              │    forward + backward (perguntas), explicação
                                              ├─ kb/             BASE DE CONHECIMENTO (YAML versionado no git)
                                              │    rules/*.yaml, params.yaml, foods.yaml, tests/cases.yaml
                                              ├─ calc/           funções puras chamadas pelas regras
                                              │    cms, energia, proteína, itu, curva, economia, ms
                                              ├─ optimizer/      PL custo mínimo (PuLP + CBC)
                                              ├─ monitor/        séries: esperado, resíduo, EWMA/CUSUM, médias móveis
                                              └─ db/             SQLite (SQLModel)
```

| Componente do edital | Onde fica |
|---|---|
| Base de conhecimento (regras, variáveis, CF, versionada) | `backend/kb/` em YAML + campo `kb_version`; cada regra com `id, versao, fonte, forca_evidencia` |
| Motor de inferência (casamento, conflito, encadeamento, incerteza) | `backend/engine/` |
| Memória de trabalho | `engine/working_memory.py` (fatos com valor, CF, origem, timestamp) persistida por sessão |
| Interface | `frontend/` React |
| Módulo de explicação | `engine/explain.py` + painel "Por quê? / Como?" na UI |
| Aquisição de conhecimento | Tela "Base de conhecimento" (lê regras/parâmetros, mostra fonte e força) + edição dos YAML no git + botão "rodar casos de teste desta versão" |
| Fontes externas (opcional) | Open-Meteo (temperatura/umidade → ITU) com fallback manual; importação CSV do controle leiteiro/laudo |

**Por que motor próprio e não Experta:** Experta depende de `frozendict` antigo e quebra em Python ≥3.10; um motor próprio de ~300 linhas é fácil de explicar aos avaliadores e dá controle total sobre traço e CF.

---

## 3. Estrutura do repositório

```
backend/
  app/main.py                FastAPI
  app/api/                   farms.py, lots.py, diets.py, records.py, inference.py, kb.py
  app/engine/                facts.py, working_memory.py, conditions.py, rules_loader.py,
                             agenda.py, engine.py, cf.py, explain.py
  app/calc/                  intake.py, energy.py, protein.py, climate.py, lactation_curve.py,
                             economics.py, conversions.py
  app/optimizer/lp.py
  app/monitor/series.py      esperado, resíduo padronizado, MAD, EWMA, CUSUM, MM3
  app/db/models.py, seed.py  SQLite + fazenda demo com 60 dias de histórico sintético
  kb/rules/{cls,exg,ver,for,acp_diario,acp_semanal,acp_mensal,meta}.yaml
  kb/params.yaml             limiares com valor, fonte, força, editável
  kb/foods.yaml              alimentos (CQBAL/NRC)
  kb/CHANGELOG.md            histórico de versões da base
  tests/cases.yaml           casos conhecidos (T1–T18 + novos)
  tests/test_calc.py, test_engine.py, test_rules.py, test_lp.py, test_monitor.py
frontend/                    Vite + React + TS + Tailwind + Recharts
docs/                        processo-ia.md, arquitetura.md, regras.md (gerado dos YAML), apresentacao/
```

---

## 4. Modelo de dados (SQLite)

- **Fazenda**: nome, município, porte (pequeno/médio/grande → define quais campos a UI mostra), preço do leite, tabela de bonificação do laticínio (opcional).
- **Lote**: nome, finalidade, sistema (pasto/semiconfinado/confinado), grupo genético, nº de vacas, PV médio, DEL médio (ou datas de parto), dias de gestação médios, ordem de parto (fração de primíparas), ECC, distância/relevo (pasto), objetivo.
- **Alimento**: `id, nome, tipo, ms, pb, pdr, fdn, fdnd, fdnf_fator, cnf, ee, ndt, ell, ca, p, preco_kg_mn, fonte, versao`; valores da fazenda sobrescrevem a tabela.
- **Dieta** (versionada): lote, versão, itens (alimento, kg MN/vaca/dia), origem (usuário/PL), motivo, data de início, parecer da inferência anexado.
- **Registro** `(lote, data, indicador, valor, método, confiança)`; indicadores: `vacas, litros, concentrado_kg, dieta_id/piquete, sobras_pct|escore_cocho, ms_silagem, ecc, escore_fezes, altura_pasto, ruminacao_media, temp, ur, gordura, proteina, lactose, nul|ureia, ccs, cbt`.
- **Evento de lote**: troca de dieta/silo, movimentação de vacas, mudança de concentrado (abrem janelas de supressão e de medição de resposta).
- **SessaoInferencia**: kb_version, fatos de entrada, conclusões, traço (JSON) — auditável e reproduzível.
- **Alerta**: lote, data, regra_id, nível, CF, causa, ação sugerida, status (novo/visto/aceito/rejeitado).

---

## 5. Base de conhecimento

### 5.1 Formato de regra (YAML)

```yaml
- id: ACP-03
  versao: 1
  modulo: acompanhamento_mensal
  descricao: Relação gordura:proteína baixa sugere acidose subaguda
  prioridade: 50                 # salience para resolução de conflito
  se:
    - {fato: leite.gp_ratio, op: "<", valor: "@params.gp_sara_max"}
  entao:
    - concluir: {fato: hipotese.acidose_subaguda, valor: true}
    - alerta: {nivel: atencao, acao: "Aumentar fibra efetiva (FDNfe), checar partícula e amido"}
  cf: 0.7
  fonte: "Penn State; UNH 2025"
  forca: C
```

- Operadores: `= != < <= > >= in entre existe ausente tendencia_queda`; valores podem referenciar `@params.x` (limiares editáveis) ou outros fatos.
- Ações: `concluir` (novo fato), `calcular` (chama função de `calc/` registrada por nome e grava o resultado como fato), `alerta`, `perguntar` (para backward), `suprimir` (meta-regra), `meta` (alvo/restrição de dieta usada pelo PL).
- **params.yaml**: cada limiar com `valor, unidade, fonte, forca, editavel`. Conflitos de literatura (NUL, G:P, ITU por raça, mantença 0,08 vs 0,10) viram parâmetros/flags, com a escolha padrão justificada.
- **Versionamento**: `kb_version` semântico no topo; `CHANGELOG.md`; cada sessão grava a versão usada; suíte de casos roda por versão.

### 5.2 Módulos de regras (≈70 regras no planejamento; a base final tem 172)

| Módulo | Regras | Papel |
|---|---|---|
| **A · CLS** classificação | CLS-01..12 do dossiê (fase da lactação, pré-parto, gestação ≥190 d, primípara, grupo genético → conjunto de equações, pasto → atividade, ITU 72/78, pasto+mestiça → CF menor) | Gera o fato derivado `PerfilLote` (encadeamento visível) |
| **B · EXG** exigências/metas | EXG-01..09 + seleção de equação de CMS: Holandês → NRC 2001; Girolando/mestiça confinada → BR-Leite Eq 1.1; cana → Eq 1.2; pasto → rótulo baixa confiança + teto FDN 1,2–1,3% PV; presets FDN/CNF por produção | Calcula CMS, ELl (mantença+leite+gestação+crescimento+atividade±ECC), PM/PB-alvo, restrições |
| **C · VER** verificação | VER-01..08 (déficit ELl/PM, FDN baixo, ureia >1% bloqueante, EE >6%, oferta > CMS, cana única, adequada) + correção MN↔MS | Parecer da dieta proposta pelo usuário |
| **F · FOR** formulação (PL) | Regras que montam metas/restrições para o PL; regras de diagnóstico de inviabilidade ("energia não atingível → incluir fonte energética ou reduzir meta"); verificação do resultado pelo Módulo C | Sugestão de dieta de custo mínimo |
| **D1 · ACP diário** | resíduo L/vaca vs curva (Shewhart −3σ), corrida ≥5 d com 1 d < −10%, EWMA; queda com ITU̅2d alto → calor (ACP-10); degrau após troca de silo/dieta (ACP-08); L/kg concentrado < 2; resposta marginal ΔL/Δkg < P_conc/P_leite; custo/L e margem sobre concentrado; movimentação → suprimir 48 h; dia sem registro → só lembrete | "Está funcionando?" e "o concentrado se paga?" |
| **D2 · ACP semanal** | MS silagem: Δ≥2 p.p. em 2 leituras → recalcular MN; Δ≥5 p.p. ou silo novo → reformular; sobras MM3 fora da faixa por fase (±2–3%, esperar 3 d); cocho vazio ≥2 d (crítico); ECC: perda >0,5–0,75 ponto, ACP-05/09; escore de fezes (reforço ACP-04); ruminação média do lote em queda (opcional) | Comportamento alimentar e ajuste de oferta |
| **D3 · ACP mensal** | NUL (normaliza ureia×0,4667): alto vs alvo por produção, ≥19–20 → risco reprodutivo (crítico), baixo só se leite/proteína abaixo; G:P <1,0–1,1 (SARA) e >1,4 em recém-paridas (BEN); queda de gordura ≥0,2–0,3 p.p. (DGL) cruzada com mudanças recentes; CCS/CBT média geométrica 3 m + R$ perdido; lactose/ESD baixos + CCS ↑ | Laudo do laticínio que toda fazenda já tem |
| **M · META** resolução de conflito | "Mastite primeiro": lactose baixa + CCS ↑ suprime recomendações de dieta; "Calor explica": queda + ITU alto rebaixa alertas de dieta; janelas de supressão (movimentação, correção de MS); deduplicação e limite de alertas por semana priorizado por R$ | Demonstra resolução de conflitos e combate à fadiga de alertas |

Fora do escopo (citar na apresentação como evolução): KPIs reprodutivos (TP21 etc.), sensores individuais, aminoácidos/minerais detalhados, NASEM completo, consumo de pasto por massa de forragem, ML.

---

## 6. Motor de inferência (`backend/app/engine/`)

- **Fatos**: `Fato(nome, valor, cf, origem: usuario|tabela|calculado|regra:<id>, t)`. CF de entrada vem do rótulo de confiança: medido recente = 1,0; medição <30 d = 0,8; valor de tabela/padrão = 0,6 (parâmetros em `params.yaml`).
- **Ciclo forward (match → resolve → act)**: a cada ciclo, monta o conjunto de conflito (regras cujas condições casam e ainda não dispararam com esse mesmo conjunto de fatos — refração), escolhe por **prioridade do módulo → salience → especificidade (nº de condições) → recência dos fatos**, dispara, registra no traço; repete até não haver regra aplicável. Ordem de módulos: CLS → EXG → FOR/VER → ACP → META.
- **Incerteza (MYCIN)**: CF da conclusão = CF_regra × min(CF das premissas); mesma conclusão por regras diferentes → CF = CF1 + CF2·(1−CF1) (positivos), com fórmula geral para negativos. Exemplo de demo: ACP-03 (0,7) + ACP-04 (0,6) → 0,88.
- **Backward (perguntas)**: dado um objetivo (ex.: `parecer_dieta`), o motor procura regras que o concluem e, para premissas ausentes e marcadas `perguntavel`, gera perguntas — só pergunta o que falta. A UI mostra "Por que estou perguntando?" = cadeia regra → objetivo.
- **Explicação**: "Como?" = árvore de derivação da conclusão (regras, fatos usados com valores e CF, fonte e força da evidência); "Por quê?" = regra que precisa do fato perguntado. Texto gerado por templates determinísticos.
- Funções de `calc/` são chamadas pelas regras via ação `calcular`; números nunca vêm da LLM.

---

## 7. Cálculo (`backend/app/calc/`) — funções puras testadas

- `conversions`: MN↔MS, LCG4% `= leite × (0,4 + 0,15 × %G)`, ECM `12,82G + 7,13P + 0,323L`, ureia→NUL ×0,4667, NDT→ELl.
- `intake`: CMS NRC 2001; BR-Leite Eq 1.1/1.2; pré-parto (1,8–2% PV / fórmula NRC); teto por fibra `1,25 × PV ÷ %FDN`; checagem de plausibilidade 2,5–4% PV.
- `energy`: mantença `k × PV^0,75` (k = 0,08 ou 0,10 por flag); ELl do leite pela composição; gestação (≥190 d); crescimento de primípara; atividade de pastejo (tabela NRC com interpolação por PV, distância, relevo); ajuste de ECC `417 × ΔECC ÷ dias`; balanço energético.
- `protein`: PM leite `10 × kg × %P / 0,67` e PB-alvo por produção (tabela MSD).
- `climate`: ITU (fórmula do dossiê e a fórmula Negri usada no Brasil — uma escolhida como padrão), média de 2 dias.
- `lactation_curve`: Cobuci como padrão (consistente), Wood alternativo; esperado do lote `N × f(DEL̄) × k_fazenda × correção ITU`; ajuste do fator k nas primeiras semanas.
- `economics`: L/kg concentrado, custo de concentrado/L, margem sobre concentrado, IOFC, resposta marginal após mudança, perda por CCS (interp. log), custo da dieta/vaca/dia.
- `monitor/series`: resíduo padronizado `(obs−esp)/esp ÷ (MAD×1,4826)`, EWMA, CUSUM, regra de corrida, médias móveis de 3 d.

### 7.1 Valores conferidos pelo subagente de pesquisa (entram em `foods.yaml` / `params.yaml`)

**Equações**
- **Confirmadas:**
  - BR-Leite Eq 1.1 na fonte primária (Embrapa 2024, Tab. 2). O PDF omite o sinal de menos no expoente; o correto é `e^(−0,0134·(DEL+92,4786))`. O LCG4% é o mesmo do NRC (`0,4·L + 15·kg gordura`).
  - NDT→ELl: `ELl = 0,0245·NDT% − 0,12` (NRC 2001, Eq. 2-3). Serve para calcular a ELl dos alimentos, porque nenhuma tabela traz esse valor.
- **Confirmadas só em fonte secundária (força B/C):**
  - CMS do NRC 2001 (0,372 / 0,0968 / 0,192 / 3,67).
  - Mantença `0,08·PV^0,75`.
  - Gestação, para D ≥ 190: `ELl = (0,00318·D − 0,0352)·(PBz/45)/0,218` e `PM = (0,69·D − 69,2)·(PBz/45)/0,33`. Com bezerro de ~44 kg, as duas reproduzem a tabela NRC de Drackley (ELl 2,7/3,4/3,8 Mcal e PM 199/306/357 g aos 200/250/275 d). **Esses valores viram casos de teste.**
- **Não usar:**
  - "+20% de mantença na 1ª lactação": é do NRC 1989. CLS-07 passa a somar o crescimento como parâmetro configurável, com força D.
  - Fórmula exponencial de CMS pré-parto: não foi verificada. EXG-03 fica com 1,8–2% do PV (NASEM/Drackley).

**Alimentos (% da MS)** — fontes: Embrapa Gado de Leite, *Planejamento alimentar* (Valadares Filho 2006), e Embrapa RO Doc 167:

| Alimento | MS | PB | FDN | NDT | EE |
|---|---|---|---|---|---|
| Silagem de milho | 30,9 | 7,3 | 55,4 | 64,3 | – |
| Silagem de sorgo | 30,8 | 6,7 | 61,4 | 57,2 | – |
| Capim-elefante 46–60 d | 19,9 | 9,2 | 72,3 | 52* | – |
| B. decumbens | 31,0 | 6,7 | 74,6 | 58,2 | – |
| B. brizantha | 36,7 | 7,4 | 79,2 | 49,3 | – |
| Cana-de-açúcar | 28,5 | 2,7 | 57,7 | 62,7 | – |
| Milho grão moído | 87,6 | 9,1 | 14,0 | 87,2 | 4,0 |
| Farelo de soja | 88,6 | 48,8 | 14,6 | 81,5 | 1,7 |
| Caroço de algodão | 91,0 | 22,6 | 46,0 | 81,9 | 18,9 |
| Farelo de trigo | 88,0 | 16,6 | 44,3 | 72,4 | 3,5 |
| Polpa cítrica | 87,9 | 7,2 | 24,3 | 65,2 | 3,3 |
| Ureia | 97,5 | 282 | – | – | – |

\* NDT do capim-elefante sem idade informada (Doc 167).

**Lacunas tratadas como padrão de baixa confiança:**
- EE dos volumosos: padrão de 2–3%, com força D.
- CNF: calculado como `100 − (PB + FDN + EE + MM)`, com MM padrão por tipo de alimento.
- Núcleo mineral: composição informada pelo usuário a partir do rótulo do produto.
- Ca e P do farelo de trigo: parecem trocados na fonte, ficam marcados para conferir.
- Cada linha guarda `fonte` e `forca`.

## 8. Otimizador (`backend/app/optimizer/lp.py`)

PuLP + CBC. Variáveis xᵢ = kg MS/vaca/dia. Minimiza Σ custo·xᵢ s.a. ΣMS ∈ CMS ±5%, ELl ≥ exigência, PB entre mín/máx, FDN ≥ meta, FDNf ≥ meta, CNF ≤ meta, EE ≤ 6%, ureia ≤ 1%, consumo de FDN ≤ 1,25% PV, limites de inclusão por alimento. Restrições de razão linearizadas (Σ(FDNᵢ − meta)·xᵢ ≥ 0). Metas/restrições **vêm das conclusões do motor**; se inviável, roda relaxações uma a uma para identificar a restrição que quebra e passa isso às regras de diagnóstico. Saída convertida para kg MN e verificada pelo Módulo C antes de virar parecer.

---

## 9. Interface (React) — telas e fluxos

1. **Painel da fazenda**: cards por lote (L/vaca hoje vs esperado, custo de concentrado/L, alerta mais grave, CF). Lista de alertas do dia por nível.
2. **Cadastro de lote (assistente)**: perguntas em etapas; campos obrigatórios mínimos e opcionais conforme o porte; botão "Por que perguntamos?" em cada campo.
3. **Perfil do lote**: `PerfilLote` + exigências calculadas (CMS, ELl, PM, metas de fibra) com "Como?".
4. **Dieta**: (a) montar dieta com alimentos (kg MN) → **Verificar** → parecer oferta × exigência em barras, alertas com CF; (b) **Sugerir dieta de custo mínimo** → resultado do PL ou diagnóstico de inviabilidade; aceitar = nova versão da dieta com motivo.
5. **Registro rápido** (mobile, <30 s): vacas, litros, concentrado, dieta/piquete; seções recolhíveis para semanal (MS, sobras/escore, ECC, fezes, pasto) e mensal (laudo: gordura, proteína, lactose, NUL/ureia, CCS, CBT; importação CSV).
6. **Acompanhamento do lote**: gráfico observado × esperado com faixa, marcadores de eventos (troca de silo, movimentação, ITU alto), séries de NUL, G:P, sobras, ECC; linha do tempo de versões da dieta.
7. **Alerta / explicação**: causa provável, ação sugerida, regras disparadas em árvore, fatos com origem e confiança, fonte e força; aceitar/rejeitar.
8. **Base de conhecimento**: lista de regras por módulo (filtro, fonte, força, versão), parâmetros editáveis em modo "especialista", changelog e botão **Rodar casos de teste** (mostra passou/falhou por caso na versão atual).

## 10. API (FastAPI)

`/farms`, `/lots`, `/foods`, `/diets` (CRUD + versões), `/records` (POST diário/semanal/mensal, import CSV), `POST /inference/classify|requirements|verify|formulate|monitor/{lot}`, `POST /inference/session` + `/answer` (backward), `GET /inference/{session}/explain?fact=`, `/alerts` (listar/atualizar status), `/kb/rules`, `/kb/params`, `POST /kb/run-tests`, `/weather/{farm}` (Open-Meteo com fallback manual).

---

## 11. Testes com casos conhecidos

`tests/cases.yaml` declara fatos de entrada → conclusões e IDs de regras esperados; `pytest` roda tudo, e a tela de KB roda o mesmo conjunto.
- **Cálculo**: T1 (CMS NRC ≈ 21,2), T2 (ELl leite, mantença, PM), BR-Leite (550 kg, 15 kg, 4%, 150 DEL → ≈16,9), gestação 250 d com bezerro de 44 kg (≈3,4 Mcal, ≈306 g PM), NDT 64,3 → ELl ≈ 1,46 Mcal/kg, T12 (atividade ≈ 5,5 Mcal), T13 (ITU ≈ 81,3), T16 (teto fibra 18,75), T17 (ECC ≈ +2,1 Mcal/d), Cobuci (pico ≈ dia 40, 16,7 kg).
- **Regras**: T3–T11, T14, T15, T18 do dossiê.
- **Novos**: MS caiu 35→32% em 2 leituras → recalcular MN; sobras MM3 6% em lote de alta → reduzir 2–3%; cocho vazio 2 d → crítico; ureia 450 mg/L → NUL 21 → alerta reprodutivo; NUL 7 em lote de 10 kg sem queda → **nenhum** alerta; lactose 4,1 + CCS ↑ + queda de leite → "mastite primeiro", dieta suprimida; movimentação → queda de 8% suprimida 48 h; dia sem registro → lembrete, não alerta; resposta marginal 0,4 L/kg com R = 0,8 → "concentrado não se paga"; PL viável (lote médio Girolando) e inviável (só cana + núcleo para 30 kg).
- **Motor**: combinação de CF, refração, ordem de resolução de conflito, backward pergunta só o que falta.

---

## 12. Divisão de trabalho e cronograma (hoje é quarta 21/10)

| Pessoa | Responsabilidade |
|---|---|
| **P1 · Conhecimento & testes** | `kb/*.yaml` (regras, params com fonte/força, alimentos), `tests/cases.yaml`, `docs/regras.md`, seed da fazenda demo com cenários roteirizados |
| **P2 · Motor, cálculo, PL** | `engine/`, `calc/`, `monitor/`, `optimizer/`, testes unitários, API de inferência |
| **P3 · Interface & entrega** | React (telas 1–8), API de CRUD/registros, docs de processo e arquitetura, slides, roteiro da demo |

- **Quarta 21/10 (tarde/noite)**: esqueleto do repo e do contrato da API (todos, 1 h); P1 escreve CLS/EXG/VER + params + alimentos; P2 motor + calc com T1–T7 verdes; P3 telas de cadastro, dieta e parecer contra mocks.
- **Quinta 22/10 (manhã)**: P2 PL + monitor (curva, resíduo, EWMA) + backward/explicação; P1 regras ACP diário/semanal/mensal + META + casos novos + seed com 60 dias (troca de silo no dia 40, onda de calor, NUL alto, mastite); P3 registro rápido, acompanhamento com gráficos, tela de KB.
- **Quinta 22/10 (tarde)**: integração, todos os testes verdes, ensaio da demo; documentação (processo com IA, arquitetura, regras geradas dos YAML) e apresentação; **enviar até 20h** para carlos.lima@rerum.com.br com nome e telefone de todos.
- Corte de escopo se atrasar (nesta ordem): ruminação → CCS/CBT em R$ → EWMA/CUSUM (fica só corrida + Shewhart) → importação CSV.

## 13. Roteiro da demo (sexta 23/10, 9h)

1. Lote "Alta produção Girolando" → assistente pergunta só o que falta → PerfilLote → exigências com "Como?".
2. Dieta do produtor → verificação acusa FDN baixo e ureia acima → parecer com CF e regras.
3. "Sugerir custo mínimo" → PL → dieta mais barata verificada; caso inviável explicado.
4. Histórico de 60 dias: troca de silagem → queda detectada → causa provável + "medir MS e recalcular MN"; onda de calor → "calor explica, não mude a dieta"; laudo com NUL 21 → alerta reprodutivo; lactose baixa + CCS → "mastite primeiro".
5. Tela da base: mudar um parâmetro → nova versão → rodar casos → resultado por versão.

---

## 14. Verificação end-to-end

- `cd backend && pytest -q` — todos os casos de `tests/cases.yaml` + unitários de calc/motor/PL/monitor passam.
- `uvicorn app.main:app` + `cd frontend && npm run dev`; abrir `localhost:5173`, rodar o roteiro da demo acima sobre a fazenda semeada (`python -m app.db.seed`), conferir alertas esperados em cada cenário.
- Conferir em `GET /inference/{session}/explain` que toda conclusão exibida tem traço com regras, fatos, CF e fonte.
- Desligar a internet e confirmar que tudo funciona (ITU cai para entrada manual).
