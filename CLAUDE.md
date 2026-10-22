# CochoCerto — sistema especialista de dietas por lote · Hackathon UFJF 2026 (T2)

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
backend/app/services.py monta a memória de trabalho de cada fluxo (catálogo, preços, avaliação, formulação, monitor)
backend/app/alertas.py  ciclo de vida dos alertas (episódios + histórico)
backend/app/importacao.py  importação CSV;  backend/app/referencias/  preços de referência diários
backend/app/estoque.py  saldo e dias de estoque;  app/revisao.py  revisão da base pelo uso;  app/relatorio.py  relatório semanal
backend/scripts/        gerar_regras_md.py (docs/regras.md), importar_cqbal.py (foods.yaml)
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
cd backend && python -m scripts.importar_cqbal    # reimporta a composição do CQBAL para kb/foods.yaml
LEITE_SEM_COLETA=1 pytest -q                # desliga a coleta diária de preços (testes, sem internet)
cd frontend && npm install && npm run dev   # UI em :5173  (npm run dev:rede para abrir no celular)
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
- Composição dos alimentos da base vem do **CQBAL 4.0** (`scripts/importar_cqbal.py`, a partir dos relatórios JSON do site; NDT observado só com n ≥ 10, senão BR-CORTE 2016; minerais Ca/P/Mg/K/Na/Cl/S quando o CQBAL os tem). Cite sempre: "VALADARES FILHO, S.C., LOPES, S.A. et al. CQBAL 4.0. Tabelas Brasileiras de Composição de Alimentos para Ruminantes. 2018. www.cqbal.com.br". Não há licença publicada: antes de redistribuir a base fora do hackathon, peça autorização (polyana.silva@ufv.br). DCAD só é calculada quando todos os itens da dieta têm Na, K, Cl e S.
- Todo alimento em `foods.yaml` tem `fonte`, `forca` e `cf` (0,8 = tabela publicada; 0,6 = estimado/padrão). Resposta "não sei" do usuário entra com `@params.cf_padrao` (0,6); medição com `@params.cf_medido_recente`. Premissa com CF abaixo de `@params.cf_limiar` não dispara regra.
- **Catálogo de alimentos da fazenda** = base (`foods.yaml`, só leitura) + insumos cadastrados (`AlimentoFazenda`, código `f{fazenda}_{slug}`, CF pela origem do dado: laboratório 1,0 / tabela 0,8 / estimado 0,6). Em fluxo de fazenda use `services.catalogo(s, fazenda_id)`, nunca `kb().alimentos`. Insumo desativado sai das listas, mas dietas antigas continuam válidas.
- **Preços de referência** vêm de fontes públicas (`app/referencias/fontes.py`: Cepea milho e leite MG, Deral-PR/IPEADATA farelo de soja), coletados 1x/dia pelo agendador (desligue com `LEITE_SEM_COLETA=1`). Falha de fonte nunca apaga valor; valor implausível é descartado. Cepea é CC BY-NC 4.0: sempre exibir "Fonte: Cepea/Esalq-USP". Itens sem fonte pública ficam com o valor de demonstração de `foods.yaml`.
- **Modo campo** (`frontend/src/pages/Campo.tsx`, rota `/campo`): registro rápido + avisos para o celular; no celular a página inicial redireciona para ele. Sem conexão, registros/eventos vão para a fila `campo_fila` no localStorage e são reenviados em ordem quando a API volta (evento `online` e a cada 60 s). "Sem conexão" = falha de fetch ou 5xx sem corpo (`ErroApi.semConexao`).
- **Fila offline** (`frontend/src/lib/fila.ts`): ordem garantida, para no primeiro item sem conexão, recusa do servidor
  vai para "recusados" (nunca some), uma sincronização por vez. Mudou a fila? Rode `npm run test:fila` (7 cenários).
- **Datas no front:** nunca `toISOString().slice(0, 10)` (é UTC: às 21h em Brasília já é amanhã). Use `hojeLocal()`,
  `diasAtras()` e `somarDias()` de `src/api.ts`.
- **Registro diário:** valores validados pelas mesmas faixas da importação (`importacao.FAIXAS`, `problema_valor`) e
  litros/vaca ≤ `LITROS_VACA_MAX`; só os indicadores enviados são tocados; litros e trato podem ser **somados**
  (`somar: ["litros"]`, 2ª ordenha) e guardam as parcelas em `Registro.texto`.
- **Meta-regras valem para a verificação:** "mastite primeiro" (META-01) também põe em segundo plano os avisos da dieta
  ativa (`alertas.aplicar_meta_na_verificacao`).
- **Importação CSV** (`app/importacao.py`): nomes de coluna em `ALIASES`, faixa plausível por indicador em `FAIXAS`; sempre prévia antes de gravar. **Bonificação do laticínio**: `Fazenda.bonificacao` (faixas por parâmetro, R$/L), entra no preço efetivo do leite e no IOFC.
- Preço em `foods.yaml` é só **referência de demonstração**. O preço que vale é o da fazenda (`PrecoAlimento`, histórico com data e fonte; vigente = mais recente), aplicado por `services.alimento_com_preco` na verificação, na formulação e no painel. Nunca leia `preco_kg_mn` direto da base num fluxo de fazenda.
- **Linguagem do produtor:** todo alerta novo traz `titulo_produtor`, `causa_produtor` e `acao_produtor` (sem jargão; números
  saem com vírgula). A interface tem "visão do produtor" (padrão: sem IDs de regra, CF ou traço) e "visão técnica" (`?visao=tecnico`).
  `tests/test_novidades.py` falha se um alerta ficar sem texto do produtor.
- Módulos T (transição, `rules/transicao.yaml`) e E (estoque, `rules/estoque.yaml`) rodam fora do acompanhamento: a transição ao
  salvar uma dieta nova (`services.planejar_transicao`), o estoque em `app/estoque.py`. Durante a troca, o que vai no cocho é
  `services.itens_do_dia` (trato e estoque usam isso).
- Ajuste mínimo e sensibilidade usam o MESMO modelo do PL (`lp._modelo`) só trocando o objetivo: o contrato com a verificação vale para eles.
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
- **Alertas são episódios** (`app/alertas.py`), um por `problema` e lote (regras do mesmo problema em graus diferentes
  declaram `problema:` no alerta e viram um episódio que agrava/atenua): aberto → aceito (ação registrada) | recusado (motivo obrigatório) →
  resolvido (a condição deixou de valer, com o que mudou e as mudanças do período) | expirado (laudo venceu).
  Telas que registram ações (dieta, evento, registro) recebem `alerta_id` e chamam `alertas.registrar_acao`.
  Reprocessar dias desfaz só o automático; ações do usuário nunca são apagadas. Testes em `tests/test_alertas.py`.
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
KPIs reprodutivos, sensores individuais, aminoácidos, balanço mineral completo (só DCAD), NASEM completo, ML, destinação econômica do lote como objetivo do PL.

## Plano completo
Fluxo, modelo de dados, módulos de regras, telas, testes e cronograma: `docs/plano.md`.
