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
   - Composição de 12 alimentos tirada das tabelas da Embrapa (depois substituída pelo CQBAL 4.0, etapa 13).
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

8. **Funcionalidades a partir do uso (21–22/10).** O integrante testava a interface e pedia ajustes; cada pedido
   virou código + teste, sem "remendo" pontual:
   - cadastro e edição de lotes e sugestão de dieta visível no lote;
   - preços editáveis por fazenda, com histórico (antes eram fixos na base);
   - eventos numerados no gráfico de acompanhamento;
   - editor de dieta (a sugestão vai para o editor), versões com "voltar para esta versão";
   - cadastro de insumos próprios com composição e CF pela origem do dado.
9. **Alertas como episódios.** Pedido: "aceitar leva à tela da ação; recusar fica registrado; se o problema se
   resolver por outro caminho, o alerta vai para o histórico dizendo o que o resolveu". O agente modelou o ciclo
   aberto → aceito/recusado → resolvido/expirado, com contexto do que mudou e das ações do período, e testes que
   garantem que reprocessar dias não apaga ações do usuário.
10. **Preços de referência confiáveis.** Um subagente pesquisou fontes públicas de preço com atualização diária e
    licença. Escolhidas: Cepea/Esalq-USP (milho, leite MG; CC BY-NC, citar a fonte) e Deral-PR via IPEADATA (farelo
    de soja). Agendador diário, validação de faixa plausível e nunca apagar o último valor bom.
11. **Lacunas do plano e dos documentos de referência.** O agente comparou o plano e os três documentos com o código
    e implementou o que faltava: importação CSV com prévia, bonificação do laticínio e IOFC, NASEM 2021 com ECC,
    FDND, secagem/pré-parto, altura do pasto, crioscopia, eficiência alimentar.
12. **Campo e celular.** Leitura de cocho diária por escore 1–5 (com a regra de 3 dias fora da meta), escalas de
    ECC e fezes com a descrição de cada nível, modo campo no celular (registro rápido + avisos) com fila offline,
    clima preenchido pela Open-Meteo e "Recusar" em todos os avisos.
13. **CQBAL 4.0.** Um integrante encontrou o CQBAL. Um subagente verificou a API pública do site, a ausência de
    licença publicada e a forma de citação. O agente escreveu `backend/scripts/importar_cqbal.py`, que atualiza
    `foods.yaml` com fonte e nº de amostras (NDT observado só com n ≥ 10), e acrescentou minerais, cálculo da DCAD
    e as regras do pré-parto (VER-15, FOR-07), com a mesma restrição no PL (base 1.4.0).
14. **Consulta guiada → lote.** As respostas da consulta (encadeamento regressivo) passaram a preencher o cadastro
    de um lote novo, ligando a demonstração do motor ao fluxo real.
15. **Revisão contra o edital.** O agente conferiu cada requisito no sistema rodando (instalação limpa, testes,
    build, casos pela API, alertas da demo). Achou avisos duplicados para o mesmo problema (perda de ECC moderada e
    severa abertos juntos) e a causa sistêmica: um episódio por regra. Correção: chave `problema` compartilhada
    entre regras do mesmo problema, um episódio que agrava ou atenua (base 1.4.1).

## O que os testes pegaram

- Casos que o agente escreveu com expectativa errada: perda por CCS interpolada linearmente em vez de em escala logarítmica, e soma da MS da dieta. Foi corrigida a expectativa, não o código, e o motivo ficou registrado.
- A poda do encadeamento regressivo perguntava a distância caminhada para lote confinado. A correção foi podar regras cujas condições dependem de fatos inalcançáveis.
- Importação do CQBAL: a conferência dos valores importados mostrou matéria mineral de 95,7% no farelo de soja.
  Era um erro no importador (o valor de outro campo entrava no lugar). Corrigido e reimportado a partir do backup.
- Com minerais reais nos alimentos, dois testes de DCAD passaram a falhar porque supunham alimentos sem minerais;
  foram reescritos com alimentos que de fato não têm Cl no CQBAL.
- O teste de consistência PL × verificação (300 cenários) passou a rodar a cada mudança: uma regra nova de
  verificação sem a restrição correspondente no PL faz o teste falhar. A DCAD do pré-parto tem teste próprio
  (`test_dcad.py`) que formula com sal aniônico e exige o parecer "adequada".
- Mudanças de API em bibliotecas novas (PuLP 4 sem solver embutido, SQLModel exigindo fuso horário, Tailwind 4), documentadas no CLAUDE.md.

## Prompts principais (resumo)

- "Monte um plano completo do sistema para que eu veja todo o fluxo e funcionalidades antes da implementação; se faltar informação, designe um subagente."
- Subagente: "Confirme em fonte (com URL) a composição de 12 alimentos, os coeficientes do NRC 2001 e a Eq. 1.1 do BR-Leite; diga CONFIRMADO, DIVERGENTE ou NÃO ENCONTRADO; não invente valores."
- "Com base nesse plano, crie o CLAUDE.md para que os outros integrantes consigam trabalhar aqui também."
- "Fiz um teste no lote 1… ele continua com o aviso. Não devemos ficar tapando buraco; se precisar designe subagentes, procure os problemas, falhas e pontos fracos." (origem da auditoria da etapa 7)
- "Nas ações sugeridas, tem que ter as opções para aceitar e recusar… deve existir um histórico de alertas e ações…" (etapa 9)
- "Procure uma fonte de dados de preço para atualizar esses valores de referência diariamente." (etapa 10)
- "Foque em implementar o que está faltando, os 2 tópicos do plano, e o que ficou de fora dos documentos de referência." (etapa 11)
- "Sobre o mobile, essa é a parte que deveria ir para lá, o registro rápido… além de informações sucintas como os avisos." (etapa 12)
- "Um integrante encontrou o CQBAL 4.0, lá parece ter informações valiosas, usamos ele já?" (etapa 13)
- "Analise novamente, veja se cumprimos os requisitos da Hackathon e se o sistema está correto e completo." (etapa 15)

## O que aprendemos com o processo

- **Planejar antes de codificar** com a IA (plano completo + CLAUDE.md) manteve três pessoas e seus agentes no mesmo padrão.
- **Pedir a causa, não o remendo:** os maiores ganhos vieram de medir em massa (34% de dietas reprovadas → 0) e de corrigir a definição comum, não o caso visto.
- **Subagentes para pesquisa e auditoria** (fontes de preço, licença do CQBAL, revisão do motor) trouxeram evidência com URL e reprodutores, que o agente principal transformou em código e testes.
- **A IA não decide no sistema:** ela escreveu regras e código; cada número tem fonte e força de evidência na base, e cada conclusão tem traço.

