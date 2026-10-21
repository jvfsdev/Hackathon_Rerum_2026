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
Python 3.11+ · FastAPI · SQLModel/SQLite · PuLP + HiGHS (highspy) · pytest | React + Vite + TS + Tailwind + Recharts.
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
cd backend && uvicorn app.main:app --reload # API em :8000 (docs em /docs)
cd backend && python -m scripts.gerar_regras_md   # regenera docs/regras.md a partir dos YAML
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
- Todo alimento em `foods.yaml` tem `fonte`, `forca` e `cf` (0,8 = tabela publicada; 0,6 = estimado/padrão). Resposta "não sei" do usuário entra com `@params.cf_padrao` (0,6); medição com `@params.cf_medido_recente`. Premissa com CF abaixo de `@params.cf_limiar` não dispara regra.
- Pergunta sem valor padrão seguro (peso vivo, temperatura) não tem `padrao`; se for dispensável, é `opcional: true` ("não sei" pula as regras que dependem dela).
- Mudou regra ou parâmetro: suba `kb_version`, anote em `kb/CHANGELOG.md` e adicione ou ajuste o caso em `tests/cases.yaml`.
- Valores ⚠ NV ou conflitantes (ver a última seção de `Inferências...md`) viram parâmetro com força explícita, nunca constante escondida.

## Garantias que os testes cobram (não quebre)
- **Contrato PL × verificação:** toda restrição do PL (`optimizer/lp.py`) é a MESMA definição da regra VER
  correspondente, apertada por `@params.pl_margem`. Criou regra VER que reprova dieta? Crie a restrição no PL.
  `tests/test_consistencia.py` roda 300 perfis × conjuntos de alimentos: dieta "otimo" ⇒ parecer "adequada".
- **Dieta que muda o próprio CMS** (teto de fibra, equação com cana): a formulação itera até ponto fixo
  (`services._formular_ate_ponto_fixo`). **Só energia/proteína inatingíveis** ⇒ status "parcial" (melhor dieta possível).
- **Manutenção de verdade:** continuar sessão (`executar(wm, resultado)`) descarta conclusões e recalcula do zero.
- **Validador da base** (`rules_loader.validar`) falha ao carregar com operador, função/argumento, ação, nível,
  fato desconhecido (que nenhuma regra conclui e não é pergunta/entrada) ou `@params` inexistente — inclusive em textos.
- **Acompanhamento:** um dia isolado nunca vira queda sustentada; reanalisar um dia substitui os alertas dele;
  registro retroativo reprocessa os dias seguintes. Regressões em `tests/test_auditoria.py`.

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

## Armadilhas conhecidas
- PuLP 4 não traz solver: usamos HiGHS via `highspy`; variáveis com `prob.add_variable(...)` e status por `stats.status == LpSolveStatus.Optimal`.
- SQLModel 0.0.48 exige datetime com fuso: campos naive usam `pydantic.NaiveDatetime`.
- Tailwind 4: classes próprias (`card`, `btn-primario`, `input`…) são `@utility` em `src/index.css`; não encadear `@apply` de uma utility em outra.
- O Vite escuta em `localhost` (IPv6); o frontend chama a API por `/api` (proxy para :8000).

## Fora do escopo
KPIs reprodutivos, sensores individuais, aminoácidos/minerais detalhados, NASEM completo, ML.

## Plano completo
Fluxo, modelo de dados, módulos de regras, telas, testes e cronograma: `docs/plano.md`.
