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

16. **Mais valor para o produtor e linguagem clara (21/10).** O time achou o sistema "simples" e técnico demais para
    o fazendeiro. O agente propôs 11 ideias; o time escolheu oito: explicação contrafactual ("o que precisaria mudar"),
    revisão da base pelo uso, sensibilidade de preços, simulador "e se?", planilha de trato, estoque, plano de transição
    de dieta e relatório semanal. Junto, cada um dos 73 avisos ganhou textos em linguagem do produtor, com uma visão do
    produtor (padrão) e uma visão técnica. Tudo continua decidido pelas regras: transição (módulo T) e estoque (módulo E)
    viraram regras novas; ajuste mínimo e sensibilidade usam o mesmo PL, com o mesmo contrato de verificação (base 1.5.0).

17. **Auditoria de cada valor (21/10).** Dez subagentes conferiram, em paralelo e só lendo, cada número do sistema contra
    a fonte citada (documentos de referência e literatura na web): parâmetros, alimentos (baixados de novo, ao vivo, do
    CQBAL: bateram 100%), equações, regras, constantes no código, textos, frontend e seed. Nenhum valor de composição ou
    equação era inventado; os achados foram força de evidência maior que a da fonte, fontes erradas ou vagas, números
    escritos à mão em textos e código (agora `{@params.x}` e parâmetros novos), duas recomendações de transição de dieta
    fora da literatura (5 → 7 dias; 1,0 → 0,5 kg/dia), uma afirmação errada sobre a IN 77 (CCS não suspende a coleta) e
    incoerências do seed (dietas sem energia para o leite produzido, NUL subindo com proteína em falta). Base 1.7.0.

18. **Testes finais com o sistema na mão (22/10).** O time usou o sistema como produtor, no computador e no celular, e
    trouxe problemas concretos; o agente procurou a causa de cada um em vez do remendo:
    - nomes internos de fatos (`mon.bonificacao_perda_rs_mes`) na visão do produtor: faltavam 127 rótulos; agora um teste
      lê o frontend e exige nome para todo fato, e o histórico/resolução ganharam texto do produtor;
    - "registrar a ação" do cocho vazio não ajustava a dieta: os avisos passaram a carregar uma proposta decidida pela
      regra (oferta ± x%, proteína − x p.p.), que não desfaz troca de dieta em andamento. O agente pegou um erro na
      própria primeira versão (a proposta de "baixar proteína" subia a ureia quando a PB já estava no mínimo) e cobrou
      no teste que a proposta nunca suba a proteína;
    - a proposta de +5% gerava "comida demais" e a dieta acusava "falta energia": a causa comum era a equação de consumo
      vencendo a medição (cocho vazio). Regra nova EXG-01V: o consumo observado é o piso (base 1.9.0);
    - gráfico "item por item" com todos os traços na mesma posição (era razão normalizada): cada linha ganhou escala;
    - movimentação de vacas era só texto: agora atualiza o cadastro dos lotes;
    - fila do celular presa após reinícios da API: reenvio ganhou prazo e a faixa mostra o que está guardado;
    - texto afirmando que "a entrega leva uns 5 dias" (escolha de engenharia, sem fonte): reescrito como prazo configurado;
    - a Base de conhecimento passou a aparecer só na visão técnica.
    Junto, o agente gerou um guia de estudo do sistema inteiro (artefato) para a preparação da apresentação.

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
- O teste de rótulos do produtor pegou na hora os dois fatos novos da regra EXG-01V sem nome na tela.
- O teste da proposta de proteína exige que ela nunca suba a PB: foi assim que a primeira versão (que subia a ureia) foi barrada.
- O teste da proposta de cocho falhou pelo motivo certo num lote sem leitura de cocho vazio: sem a evidência, +5% de fato
  passa do consumo previsto, e a proposta corrige isso. O teste foi separado em dois cenários (com e sem a evidência).

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
- "Sem implementar nada ainda, sugira ideias de coisas novas… implemente 1, 2, 5, 6, 7, 8, 9 e 10; o sistema está muito técnico, o fazendeiro precisa de linguagem clara." (etapa 16)
- "Analise novamente, veja se cumprimos os requisitos da Hackathon e se o sistema está correto e completo." (etapa 15)
- "Designe um exército de subagentes para verificar cada valor do sistema, incluindo do seed; nenhum valor pode ser inventado." (etapa 17)
- "No cocho 3, quando aperto para registrar ação do cocho vazio, ele aumenta a dieta que está ruim e ainda fala que está dando mais comida que o lote consegue comer; seria bom juntar esses avisos de dieta." (etapa 18)
- "De onde tirou que a entrega leva uns 5 dias?" (etapa 18)

## O que aprendemos com o processo

- **Planejar antes de codificar** com a IA (plano completo + CLAUDE.md) manteve três pessoas e seus agentes no mesmo padrão.
- **Pedir a causa, não o remendo:** os maiores ganhos vieram de medir em massa (34% de dietas reprovadas → 0) e de corrigir a definição comum, não o caso visto.
- **Subagentes para pesquisa e auditoria** (fontes de preço, licença do CQBAL, revisão do motor) trouxeram evidência com URL e reprodutores, que o agente principal transformou em código e testes.
- **A IA não decide no sistema:** ela escreveu regras e código; cada número tem fonte e força de evidência na base, e cada conclusão tem traço.

