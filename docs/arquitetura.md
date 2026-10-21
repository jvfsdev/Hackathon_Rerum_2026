# Arquitetura

Tudo roda em localhost. O motor de inferência é o único componente que decide. Calculadora, otimizador e monitor de séries são ferramentas que ele chama ou que alimentam a memória de trabalho. Fontes externas só trazem dados (clima, preços, composição de alimentos); nunca conclusões.

```
 React (Vite) ─ desktop + modo campo (celular, fila offline) ──/api──▶ FastAPI
                                                                       │
        ┌──────────────────────────────────────────────────────────────┼──────────────────┐
        │                                                              ▼                  │
        │   services.py — monta a memória de trabalho de cada fluxo (lote, dieta,         │
        │                 registros, laudos, clima, preços da fazenda, catálogo)          │
        │          │                                                                      │
        │          ▼                                                                      │
        │   Memória de trabalho (fatos + CF + origem)                                     │
        │          │  ▲                                                                   │
        │          ▼  │                                                                   │
        │   MOTOR DE INFERÊNCIA ── lê ──▶ BASE DE CONHECIMENTO (YAML, versionada)         │
        │   match → conflito → disparo     153 regras · 114 parâmetros · 13 alimentos     │
        │   forward + backward + CF        perguntas · versão + changelog                 │
        │          │                                                                      │
        │          ├── chama ──▶ calc/ (CMS, ELl, PM, ITU, curva, DCAD, R$, bonificação)  │
        │          ├── metas ──▶ optimizer/ (PL de custo mínimo, PuLP + HiGHS)            │
        │          ├── traço ──▶ explain ("como?" / "por quê?")                           │
        │          └── alertas ─▶ alertas.py (episódios: aberto → aceito/recusado →       │
        │                                     resolvido/expirado, com histórico)          │
        │                                                                                 │
        │   monitor/      registros → séries → fatos mon.* / laudo.*                      │
        │   importacao.py planilhas CSV (controle leiteiro, laudo) com prévia             │
        │   referencias/  preços de referência diários (Cepea, IPEADATA)                  │
        │   SQLite        fazendas, lotes, insumos, preços, dietas versionadas,           │
        │                 registros, eventos, alertas + histórico, sessões (traço)        │
        └─────────────────────────────────────────────────────────────────────────────────┘
   Fontes externas (opcionais; sem internet tudo continua funcionando):
   Open-Meteo (clima → ITU) · Cepea/Esalq-USP (milho, leite MG) · IPEADATA/Deral-PR (farelo de soja)
   CQBAL 4.0 (composição dos alimentos, importada para foods.yaml por script)
```

## Fluxo

1. **Classificação (A · CLS):** fatos brutos (DEL, estado, grupo genético, sistema, ITU) → fato derivado `perfil.*` (fase, equação de consumo, gestação, crescimento, pastejo, estresse térmico).
2. **Exigências (B · EXG):** CMS (NRC 2001, NASEM 2021 com ECC ou BR-Leite conforme o grupo; teto pela fibra), ELl = mantença + leite + gestação + crescimento + atividade ± ECC, PB alvo e metas de fibra/FDND/CNF/gordura/ureia/DCAD.
3. **Verificação (C · VER):** composição da dieta (MN → MS, minerais e DCAD quando todos os itens têm Na/K/Cl/S), oferta × exigência, restrições, parecer (adequada / ajustar / bloqueada).
4. **Formulação (F · FOR):** as regras montam as restrições do PL. O PuLP + HiGHS minimiza o custo com os preços da fazenda. Se for inviável, um diagnóstico relaxa grupos de restrições e as regras explicam o que falta. A dieta resultante volta para o módulo C.
5. **Acompanhamento (D1–D3 · ACP):** cada registro diário/semanal/mensal vira fatos datados. O esperado vem da curva de lactação (Cobuci) × escala da fazenda − perda por ITU. Detectores com persistência (Shewhart, corrida, EWMA, queda de 7 dias) se combinam por CF e geram alertas com causa provável. Leitura de cocho diária por escore 1–5 (ou pesagem), MS da silagem, ECC, fezes, altura do pasto, laudo do laticínio (NUL, G:P, CCS, lactose, crioscopia), economia (custo de concentrado, IOFC, bonificação).
6. **Meta-regras (M · META):**
   - "mastite primeiro" suprime os alertas de dieta;
   - "calor explica" rebaixa os alertas de dieta motivados pela queda;
   - movimentação de vacas ou correção da MS suprime os alertas de queda por 48 h.

## Garantias verificadas por teste

- **Formulação × verificação:** cada restrição do PL tem a mesma definição numérica da regra de verificação
  correspondente. Por exemplo, a energia consumida = min(MS, CMS) × densidade é linearizada em duas restrições.
  O teste de consistência roda 300 perfis × conjuntos de alimentos e exige que toda dieta "ótima" seja aprovada
  pelas regras. Numa medição com 1.500 cenários: 0 reprovadas.
- **Ponto fixo:** se a dieta escolhida muda o próprio CMS (teto de fibra, equação com cana), o PL é refeito com o
  novo CMS até ficar estável.
- **Melhor dieta possível:** se só energia e/ou proteína são inatingíveis, o PL entra em modo de metas com folgas
  penalizadas e entrega a dieta que mais se aproxima, com o déficit explícito.
- **Manutenção de verdade:** continuar uma sessão recalcula todas as conclusões a partir das entradas.
- **Validação estática da base:** o carregamento falha com operador, função, argumento, ação, nível ou fato
  desconhecido, inclusive dentro dos textos de alerta.
- **Acompanhamento:** um dia isolado nunca vira queda sustentada; registro retroativo reprocessa os dias seguintes.

## Alertas e ações (`backend/app/alertas.py`)

Cada problema detectado vira um **episódio** por lote, enquanto a condição durar. Regras que medem o mesmo
problema em graus diferentes (ex.: perda de ECC moderada × severa; cocho vazio × sobras baixas) declaram a mesma
chave `problema`: viram um alerta só (o mais grave, citando os demais) e um único episódio que **agrava** ou **atenua**.

- **Aceitar** leva à tela da ação: dieta, registro ou evento de manejo de calor, manejo sanitário, conferência,
  secagem ou manejo do pasto. O que for salvo nela fica no histórico do alerta.
- **Recusar** exige motivo e está disponível em todos os avisos (inclusive os já aceitos). Um alerta recusado só
  reabre se o problema se agravar.
- **Resolução automática:** quando a regra para de disparar por alguns dias (parâmetro `resolucao_dias`, por módulo),
  o episódio é encerrado com a data, o que mudou nos fatos que o sustentavam e as mudanças do período
  (ações registradas, novas dietas, eventos, laudos). Isso vale mesmo quando a solução não passou pelo aceite.
- **Expirado:** se o laudo que sustentava o alerta vence sem um novo, o episódio é encerrado como "expirado".
- Os alertas da verificação da **dieta ativa** também são episódios, resolvidos quando uma nova versão passa na regra.
- Reprocessar dias desfaz só o que é automático; ações do usuário nunca são apagadas.

## Motor de inferência (`backend/app/engine/`)

- **Fatos** (`facts.py`): valor, CF, origem (usuário, medido, tabela, padrão, regra) e ciclo (recência).
- **Ciclo** (`engine.py`): monta o conjunto de conflito, ordena por **módulo → prioridade → especificidade → recência** e dispara uma regra por ciclo. A **refração** faz cada regra disparar uma vez por execução. Cada entrada do traço registra as regras concorrentes. Uma premissa com CF abaixo do limiar (0,2) não sustenta conclusão.
- **Incerteza** (`cf.py`): CF da conclusão = CF da regra × menor CF das premissas. A mesma conclusão vinda de regras diferentes combina como CF1 + CF2·(1−CF1). Exemplo: G:P baixa (0,7) + fezes fluidas (0,6) → acidose com CF 0,88.
- **Encadeamento regressivo** (`faltantes`): parte do objetivo, percorre as regras que o concluem, poda as que têm condição já falsa ou inalcançável e pergunta só os fatos perguntáveis que faltam. A cadeia de regras percorrida é o "por quê". É o que move a **consulta guiada**, cujas respostas podem virar um lote novo.
- **Explicação** (`explain.py`): "como?" é a árvore de derivação a partir do traço (regra, fonte, força, premissas, cálculo com as entradas); "por quê?" é a cadeia do dado até o objetivo. As sessões ficam salvas, então qualquer alerta antigo pode ser explicado.
- **Valores no texto**: regras nunca têm número fixo; limiares vêm de `@params.*` e fatos de `$fato`.

## Base de conhecimento (`backend/kb/`)

- `rules/*.yaml`: uma lista de regras por módulo (`id, versao, modulo, descricao, prioridade, se, entao, cf, fonte, forca`).
- `params.yaml`: cada limiar com `valor, unidade, fonte, forca (A–D), editavel`. Valores conflitantes na literatura (NUL, G:P, ITU por raça, mantença 0,08 vs 0,10) ficam aqui como escolha explícita.
- `foods.yaml`: alimentos com composição do **CQBAL 4.0** (Valadares Filho et al., 2018), incluindo minerais para a DCAD, preço de demonstração e limites de inclusão. Atualizado por `backend/scripts/importar_cqbal.py`.
- `perguntas.yaml`: fatos que o sistema pode perguntar, com texto, ajuda, escala (ECC, fezes) e valor padrão.
- `kb.yaml` + `CHANGELOG.md`: versão. Editar um parâmetro pela interface sobe a versão, registra o motivo e roda os casos de teste.

## Dados da fazenda

- **Catálogo de alimentos** = base (`foods.yaml`, só leitura) + insumos cadastrados pela fazenda (`AlimentoFazenda`, com composição, minerais e CF pela origem: laboratório 1,0 / tabela 0,8 / estimado 0,6).
- **Preços** por fazenda com histórico (`PrecoAlimento`); o vigente é o mais recente e é o que a verificação, a formulação e o painel usam. Os **preços de referência** (Cepea milho e leite MG, Deral-PR farelo de soja via IPEADATA) são coletados uma vez por dia por um agendador; falha de fonte nunca apaga valor.
- **Bonificação do laticínio** por faixas de qualidade entra no preço efetivo do leite e no IOFC.
- **Dietas versionadas**: sugerida pelo PL, editada à mão ou restaurada de uma versão anterior; cada versão guarda origem e motivo.
- **Registros e eventos**: digitados, importados de CSV (com prévia e faixa plausível por indicador) ou enviados pelo modo campo.

## Interface (`frontend/`)

| Tela | O que faz |
|---|---|
| Painel | Cards por lote (leite × esperado, custo, alerta mais grave) e avisos do dia com aceitar/recusar. |
| Lote | Abas: perfil e exigências ("como?"), dieta (verificar, sugerir custo mínimo, editor, versões, Pearson), acompanhamento (gráfico observado × esperado com eventos), registro (diário/semanal/mensal com escalas descritas, importação CSV), alertas e histórico. |
| Novo lote | Cadastro; também pode vir preenchido pela consulta guiada. |
| Consulta guiada | Encadeamento regressivo: pergunta só o que falta, com "por que estou perguntando?" e memória de trabalho visível. |
| Insumos e preços | Preços da fazenda, insumos próprios com composição, bonificação, preços de referência com fonte. |
| Base de conhecimento | Regras, parâmetros (editáveis no modo especialista), changelog e "rodar casos de teste". |
| Modo campo (`/campo`) | Celular: registro rápido, clima automático, avisos; sem conexão, guarda numa fila e envia quando a API volta. |

## API

Documentação interativa em `http://localhost:8000/docs`. Grupos de rotas:
`/fazendas` (painel, preços, insumos, bonificação), `/lotes` (CRUD, dietas, registros, eventos, série, importação),
`/alertas` e `/historico`, `/inferencia` (avaliar, formular, acompanhar, consulta guiada, sessões, como, por quê),
`/kb` (regras, parâmetros, perguntas, testes), `/referencias`, `/clima/{fazenda}`, `/ferramentas/pearson`.

## Tecnologias

Python 3.11+ (desenvolvido em 3.14) · FastAPI · SQLModel/SQLite · PuLP + HiGHS · pytest | React 19 · Vite · TypeScript · Tailwind 4 · Recharts.
