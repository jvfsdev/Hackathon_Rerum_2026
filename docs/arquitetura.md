# Arquitetura

Tudo roda em localhost. O motor de inferência é o único componente que decide. Calculadora, otimizador e monitor de séries são ferramentas que ele chama ou que alimentam a memória de trabalho.

```
 React (Vite)  ──/api──▶  FastAPI
                           │
        ┌──────────────────┼──────────────────────────────────────────────┐
        │                  ▼                                              │
        │   Memória de trabalho  ◀── fatos do lote, dieta, registros,      │
        │   (fatos + CF + origem)    laudos, clima (Open-Meteo)            │
        │          │  ▲                                                    │
        │          ▼  │                                                    │
        │   MOTOR DE INFERÊNCIA ── lê ──▶ BASE DE CONHECIMENTO (YAML)      │
        │   match → conflito → disparo     111 regras · 81 parâmetros      │
        │   forward + backward + CF        12 alimentos · versão + changelog│
        │          │                                                       │
        │          ├── chama ──▶ calc/ (CMS, ELl, PM, ITU, curva, R$)     │
        │          ├── metas ──▶ optimizer/ (PL custo mínimo, HiGHS)      │
        │          └── traço ──▶ explain/ ("como?" / "por quê?")          │
        │                                                                  │
        │   monitor/ — registros → séries → fatos mon.* / laudo.*          │
        │   SQLite — lotes, dietas versionadas, registros, eventos,        │
        │            alertas, sessões de inferência (traço completo)       │
        └──────────────────────────────────────────────────────────────────┘
```

## Fluxo

1. **Classificação (A · CLS):** fatos brutos (DEL, estado, grupo genético, sistema, ITU) → fato derivado `perfil.*` (fase, equação de consumo, gestação, crescimento, pastejo, estresse térmico).
2. **Exigências (B · EXG):** CMS (NRC 2001 ou BR-Leite conforme o grupo; teto pela fibra), ELl = mantença + leite + gestação + crescimento + atividade ± ECC, PB alvo e metas de fibra/CNF/gordura/ureia.
3. **Verificação (C · VER):** composição da dieta (MN → MS), oferta × exigência, restrições, parecer (adequada / ajustar / bloqueada).
4. **Formulação (F · FOR):** as regras montam as restrições do PL. O PuLP + HiGHS minimiza o custo. Se for inviável, um diagnóstico relaxa grupos de restrições e as regras explicam o que falta. A dieta resultante volta para o módulo C.
5. **Acompanhamento (D1–D3 · ACP):** cada registro diário/semanal/mensal vira fatos datados. O esperado vem da curva de lactação (Cobuci) × escala da fazenda − perda por ITU. Detectores com persistência (Shewhart, corrida, EWMA, queda de 7 dias) se combinam por CF e geram alertas com causa provável.
6. **Meta-regras (M · META):**
   - "mastite primeiro" suprime os alertas de dieta;
   - "calor explica" rebaixa os alertas de dieta motivados pela queda;
   - movimentação de vacas ou correção da MS suprime os alertas de queda por 48 h.

## Motor de inferência (`backend/app/engine/`)

- **Fatos** (`facts.py`): valor, CF, origem (usuário, medido, tabela, padrão, regra) e ciclo (recência).
- **Ciclo** (`engine.py`): monta o conjunto de conflito, ordena por **módulo → prioridade → especificidade → recência** e dispara uma regra por ciclo. A **refração** vale na sessão: cada regra dispara uma vez. Cada entrada do traço registra as regras concorrentes.
- **Incerteza** (`cf.py`): CF da conclusão = CF da regra × menor CF das premissas. A mesma conclusão vinda de regras diferentes combina como CF1 + CF2·(1−CF1). Exemplo: G:P baixa (0,7) + fezes fluidas (0,6) → acidose com CF 0,88.
- **Encadeamento regressivo** (`faltantes`): parte do objetivo, percorre as regras que o concluem, poda as que têm condição já falsa ou inalcançável e pergunta só os fatos perguntáveis que faltam. A cadeia de regras percorrida é o "por quê".
- **Explicação** (`explain.py`): "como?" é a árvore de derivação a partir do traço (regra, fonte, força, premissas, cálculo); "por quê?" é a cadeia do dado até o objetivo. As sessões ficam salvas, então qualquer alerta antigo pode ser explicado.
- **Valores no texto**: regras nunca têm número fixo; limiares vêm de `@params.*` e fatos de `$fato`.

## Base de conhecimento (`backend/kb/`)

- `rules/*.yaml`: uma lista de regras por módulo (`id, versao, modulo, descricao, prioridade, se, entao, cf, fonte, forca`).
- `params.yaml`: cada limiar com `valor, unidade, fonte, forca (A–D), editavel`. Valores conflitantes na literatura (NUL, G:P, ITU por raça, mantença 0,08 vs 0,10) ficam aqui como escolha explícita.
- `foods.yaml`: alimentos com composição da Embrapa (Valadares Filho 2006; Doc 167), preço e limites de inclusão.
- `perguntas.yaml`: fatos que o sistema pode perguntar, com texto, ajuda e valor padrão.
- `kb.yaml` + `CHANGELOG.md`: versão. Editar um parâmetro pela interface sobe a versão, registra o motivo e roda os casos de teste.

## Tecnologias

Python 3.14 · FastAPI · SQLModel/SQLite · PuLP + HiGHS · pytest | React 19 · Vite · TypeScript · Tailwind 4 · Recharts.
