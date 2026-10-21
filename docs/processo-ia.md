# Processo de desenvolvimento com IA

Agente usado: **Claude Code** (Anthropic), no VS Code. A IA ajudou a pesquisar, planejar, extrair regras e escrever código. Quem decide dentro do sistema é a base de conhecimento + o motor de inferência.

## Etapas

1. **Pesquisa de domínio (20/10).** Com o agente foram produzidos três documentos de referência:
   - `dossie.md`: nutrição, equações, banco de regras candidatas e casos de teste;
   - `dados.md`: o que fazendas de cada porte registram e com que frequência;
   - `Inferências de dados leiteiros por lote.md`: curva esperada, detecção de quedas, economia do concentrado, 43 regras de alerta com força de evidência A–D e a lista de valores conflitantes ou não verificados.
2. **Plano (21/10).** O agente leu os quatro documentos (requisitos + 3 de referência), fez três perguntas de escopo e montou o plano completo (`docs/plano.md`). As respostas foram: FastAPI + React, PL de custo mínimo obrigatório, equipe de 3.
3. **Verificação de lacunas por subagente.** Antes de codificar, um subagente de pesquisa conferiu em fontes os números que entrariam na base:
   - Confirmados: BR-Leite Eq. 1.1 (na fonte primária, achando um sinal de menos faltando no PDF) e NDT→ELl.
   - Confirmados em fonte secundária: NRC 2001 (CMS e mantença) e as fórmulas de gestação, que reproduzem a tabela NRC.
   - Composição de 12 alimentos tirada das tabelas da Embrapa.
   - Descartados: "+20% de mantença em primíparas" (é do NRC 1989; virou parâmetro de força D) e a fórmula exponencial de CMS pré-parto, que não foi verificada.
4. **CLAUDE.md** com as convenções do projeto, para que os três integrantes e seus agentes trabalhem do mesmo jeito.
5. **Implementação guiada por testes.**
   - Funções de cálculo testadas contra valores publicados (T1: CMS ≈ 21,2 kg; ITU ≈ 81,3; gestação 250 d ≈ 3,4 Mcal / 306 g PM).
   - Motor com testes de mecânica: ordem de conflito, refração, combinação de CF, poda do encadeamento regressivo.
   - 33 casos de resultado conhecido em `tests/cases.yaml`, rodando no pytest e na tela da base.
6. **Cenários de demonstração.** O seed gera 60 dias com eventos roteirizados. Ao rodar o acompanhamento sobre eles, apareceram problemas reais, corrigidos nas regras:
   - alertas falsos de MS por usar a dieta atual em datas passadas;
   - "queda sustentada" ainda ativa com o lote já recuperado;
   - "calor explica" rebaixando alertas do laudo sem relação com a queda;
   - queda atribuída ao calor quando havia mastite.

7. **Auditoria com subagentes (21/10).** Um teste manual mostrou o lote 3 recebendo uma dieta "ótima" que a própria
   verificação reprovava. Em vez de corrigir o caso:
   - medimos em massa: 34% das dietas ótimas eram reprovadas;
   - unificamos as definições do PL e da verificação;
   - três subagentes auditaram em paralelo, só lendo o código e entregando um relatório com reprodutores executados:
     o motor de inferência, a base de regras contra os documentos de referência, e o acompanhamento diário.
   - Os cerca de 35 achados viraram correções agrupadas por causa e testes de regressão (`tests/test_auditoria.py`).
   - Exemplos: um único dia digitado errado virava "queda sustentada" crítica; vaca seca sem os dias de gestação
     ficava com 26% menos energia; continuar uma sessão deixava conclusões obsoletas; o validador aceitava regra com
     operador inexistente.

## O que os testes pegaram

- Casos que o agente escreveu com expectativa errada: perda por CCS interpolada linearmente em vez de em escala logarítmica, e soma da MS da dieta. Foi corrigida a expectativa, não o código, e o motivo ficou registrado.
- A poda do encadeamento regressivo perguntava a distância caminhada para lote confinado. A correção foi podar regras cujas condições dependem de fatos inalcançáveis.
- Mudanças de API em bibliotecas novas (PuLP 4 sem solver embutido, SQLModel exigindo fuso horário, Tailwind 4), documentadas no CLAUDE.md.

## Prompts principais (resumo)

- "Monte um plano completo do sistema para que eu veja todo o fluxo e funcionalidades antes da implementação; se faltar informação, designe um subagente."
- Subagente: "Confirme em fonte (com URL) a composição de 12 alimentos, os coeficientes do NRC 2001 e a Eq. 1.1 do BR-Leite; diga CONFIRMADO, DIVERGENTE ou NÃO ENCONTRADO; não invente valores."
- "Com base nesse plano, crie o CLAUDE.md para que os outros integrantes consigam trabalhar aqui também."
