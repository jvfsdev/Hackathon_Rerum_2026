# Hackathon UFJF 2026 — T2 Dietas: dossiê de domínio

Oct 20, 2026 · @JVFS

## Resumo executivo

O sistema proposto tem três módulos que compartilham a mesma base de conhecimento: **classificar o lote**, **verificar/formular a dieta** e **acompanhar a dieta ao longo do tempo**. Os dois primeiros respondem "o que dar"; o terceiro responde "está funcionando?" e é o que diferencia o projeto de uma calculadora.

- **Equações (cálculo)**: estimam exigências (CMS, energia, proteína) a partir de peso, produção, gordura, semana de lactação. São funções puras chamadas pelas regras, não são o sistema especialista em si.
- **Regras de produção (decisão)**: SE fatos do lote/dieta/indicadores ENTÃO conclusão + fator de certeza (CF) + explicação. É aqui que mora o conhecimento do nutricionista.
- **Motor de inferência**: encadeamento progressivo (dados → alertas e recomendações) e, opcionalmente, regressivo para perguntar ao usuário só o que falta.
- **Acompanhamento**: cada visita/registro (ECC, sobras de cocho, produção, gordura/proteína, NUL, escore de fezes) vira fatos novos; o motor dispara regras de alerta e sugere ajustes, sempre com o "por quê".

As variáveis do edital (raça, peso, idade, estado produtivo, destinação econômica, produção) são exemplos; o conjunto usado aqui foi escolhido pelo peso que cada variável tem nas equações e na prática de campo (seção *Variáveis que mais pesam*). Regra do edital que guia tudo: a LLM ajuda a construir e extrair regras, mas a decisão sai da base explícita + motor, de forma determinística e auditável.

Aviso: os valores numéricos deste dossiê são referências de literatura para uma prova de conceito; um sistema real precisaria de validação por zootecnista/nutricionista (a RERUM oferece técnicos para orientação).

## Contexto de negócio

Alimentação é o maior custo controlável da fazenda leiteira: levantamentos da Embrapa Gado de Leite apontam que 40 a 60% do custo do litro vem da alimentação ([Embrapa, 1995](https://www.infoteca.cnptia.embrapa.br/infoteca/bitstream/doc/591500/1/2032.pdf)). No índice de custos ICPLeite/Embrapa, os grupos *alimentação concentrada* e *produção e compra de volumosos* têm as maiores ponderações e lideraram a inflação de custos nos últimos anos ([Agrolink/Embrapa](https://www.agrolink.com.br/noticias/custo-de-producao-de-leite-tem-alta-de-quase-3-_451722.html)). Um sistema que erra para mais desperdiça dinheiro; que erra para menos derruba produção, reprodução e saúde.

**Quem usa o sistema**

| Perfil | O que precisa | Implicação no design |
| --- | --- | --- |
| Produtor / gerente | Saber quanto dar a cada lote e se algo está errado | Linguagem simples, alertas priorizados |
| Técnico de campo | Registrar visitas e ajustar a dieta | Formulário rápido, histórico por lote |
| Zootecnista / nutricionista | Validar e editar regras | Base de regras legível e versionada |

**Particularidades do Brasil que o sistema deve tratar**

- Rebanho muito mestiço (Girolando, Holandês × Gir) e zebuíno leiteiro, com exigências diferentes das tabelas americanas; por isso a Embrapa publicou o [BR-Leite](https://www.alice.cnptia.embrapa.br/alice/handle/doc/1169399) (exigências de zebuínos leiteiros e cruzados).
- Sistemas de produção variados: pasto, semiconfinamento, compost barn, free stall. Em pasto o consumo real é estimado, não medido.
- Volumosos tropicais (capim-elefante, braquiárias, cana) e silagem de milho/sorgo; composição muda muito entre fazendas, por isso existem tabelas nacionais (CQBAL) e a recomendação de usar análise bromatológica própria quando houver.

**Fluxo real de trabalho (o que o sistema imita)**: separar o rebanho em lotes → definir exigências do lote → montar/checar a dieta com os alimentos disponíveis → fornecer → observar cocho, fezes, ECC, leite → ajustar.

## Fundamentos de nutrição (glossário para a base de conhecimento)

Tudo é calculado sobre a **matéria seca (MS)**: o alimento "como fornecido" tem água, e a vaca precisa de nutrientes, não de água. Converter MN ↔ MS é a primeira função utilitária do sistema (kg MS = kg MN × %MS / 100).

| Sigla | Nome | Para que serve na dieta | Unidade usual |
| --- | --- | --- | --- |
| CMS | Consumo de matéria seca | Teto físico de quanto a vaca come; tudo é proporcional a ele | kg MS/dia |
| NDT / ELl (NEL) | Nutrientes digestíveis totais / energia líquida de lactação | Energia para manutenção, leite, gestação e ganho | % MS ou Mcal/kg MS |
| PB | Proteína bruta | Proteína total da dieta | % MS |
| PDR / PNDR | Proteína degradável / não degradável no rúmen | PDR alimenta os micróbios; PNDR chega ao intestino | % PB ou % MS |
| PM | Proteína metabolizável | O que de fato é absorvido (microbiana + PNDR digerida) | g/dia |
| FDN / FDNf | Fibra em detergente neutro / FDN de forragem | Saúde do rúmen, ruminação, gordura do leite; em excesso limita consumo | % MS |
| FDNfe | FDN fisicamente efetiva | Fibra que estimula mastigação (depende do tamanho de partícula) | % MS |
| CNF / amido | Carboidratos não fibrosos | Energia rápida; em excesso causa acidose | % MS |
| EE | Extrato etéreo (gordura) | Energia densa; em excesso prejudica fermentação | % MS |
| Ca, P, Mg, Na, K... | Minerais | Ossos, leite, metabolismo; fornecidos via núcleo/sal mineral | g/dia ou % MS |

**Lógica de causa e efeito que vira regra**

- Pouca fibra efetiva → menos ruminação e saliva → pH ruminal cai → acidose subclínica → gordura do leite cai.
- Muita fibra → rúmen enche antes → consumo cai → energia insuficiente.
- Proteína degradável sem energia fermentável suficiente → amônia sobra → vira ureia → NUL alto (desperdício e efeito na reprodução).
- Energia insuficiente no início da lactação → vaca mobiliza gordura corporal → perde ECC → risco de cetose.
- Água: consumo livre é algumas vezes o CMS; o NASEM 2021 traz equações de consumo de água em função de CMS, temperatura e produção ([Merck Vet Manual](https://www.merckvetmanual.com/multimedia/table/free-water-intake-equations-for-dairy-cows)).

## Variáveis que mais pesam

A literatura aponta **peso vivo, produção e composição do leite, estágio da lactação e gestação** como os motores das equações de exigência; **ECC, qualidade do volumoso, sistema de produção (pastejo) e ambiente (ITU)** são os modificadores que mais mudam o resultado na prática brasileira. Raça e idade, citadas no edital, entram melhor como *grupo genético* e *ordem de parto*.

**Nível 1 — entram nas equações (obrigatórias no MVP)**

| Variável | Por que pesa (evidência) | Como entra no sistema | Como o usuário obtém |
| --- | --- | --- | --- |
| Peso vivo médio do lote (kg) | Usado em quase toda equação; responde por cerca de 50% da predição de consumo ([AgModel/CNCPS](https://agmodelsystems.com/?p=525)) | PV^0,75 na manutenção e no CMS | Balança ou fita de pesagem |
| Produção de leite (kg/d) | Define a exigência de energia e de proteína metabolizável ([AgModel](https://agmodelsystems.com/?p=525)) | EL leite × kg; PM leite | Controle leiteiro / tanque ÷ vacas |
| Gordura e proteína do leite (%) | Energia do leite depende da composição; também alimentam LCG 4% ([MDPI, 2022](https://www.mdpi.com/2077-0472/12/5/654)) | Equação de EL leite, LCG | Análise do laticínio (mensal) |
| Dias em lactação (DEL) | Consumo é menor nas primeiras semanas; no NASEM 2021 a depressão pós-parto dura 31 dias ([Hoard's](https://hoards.com/article-30897-feeding-strategies-get-a-top-to-bottom-review.html)) | Termo de semana de lactação no CMS; classificação de fase | Data do parto |
| Dias de gestação | Exigências de gestação passam a contar a partir de cerca de 191 dias ([AgModel](https://agmodelsystems.com/?p=525)) | Soma exigência de gestação; para secas, semana até o parto define CMS | Data da cobertura/IA |
| Ordem de parto | Primíparas perdem proporcionalmente mais peso no início (−8,4 vs −6,6 kg/100 kg) ([RBZ](https://rbz.org.br/?p=5888)) e ainda crescem | Exigência de crescimento; ajuste de CMS | Registro do animal |

**Nível 2 — modificam exigência ou consumo (recomendadas; perguntadas só quando a regra precisa)**

| Variável | Por que pesa (evidência) | Como entra no sistema |
| --- | --- | --- |
| ECC (1–5) e sua variação | 1 ponto de ECC ≈ 56 kg de tecido ([Alberta](https://www1.agriculture.alberta.ca/$department/deptdocs.nsf/all/agdex9622/$FILE/body-condition-scoring-and-energy-balance.pdf)); uma vaca de \~650 kg com ECC 4 que perde 1 ponto libera cerca de 417 Mcal de ELl ([Penn State](https://extension.psu.edu/body-condition-scoring-as-a-tool-for-dairy-herd-management)) | Meta de ECC por fase → regra soma ou desconta energia para recuperar/permitir mobilização |
| Qualidade do volumoso (FDN e sua digestibilidade) | +1 ponto de digestibilidade da FDN → +0,17 kg de CMS e +0,25 kg de leite corrigido ([Oba & Allen, 1999](https://agris.fao.org/search/fr/records/65de3a467c7033e84bea2104)); consumo de FDN tende a se limitar perto de 1,25% do PV ([Epagri](https://casuar.epagri.sc.gov.br/index.php/1SEPLP/1SCPLP/paper/download/229/282)) | Teto de CMS pela fibra; alerta de volumoso ruim |
| Sistema de produção e pastejo (distância, relevo) | Atividade de pastejo custa de \~0,6 a \~5,5 Mcal ELl/d conforme peso, distância e relevo (NRC 2001, via [eOrganic](https://eorganic.org/node/219)); o NRC subestima exigências de vacas em pasto ([ADSA, 2019](https://m.adsa.org/2019/abs/t/79013)) e foi pouco preciso para mestiças em pastagens tropicais ([Embrapa, 2012](https://www.alice.cnptia.embrapa.br/alice/bitstream/doc/949021/1/Avaliacao-do-modelo-NRC-para-predicao-do-consumo-de-materia-seca.pdf)) | Acréscimo de manutenção; CF menor nas conclusões em pasto |
| Ambiente (ITU) | Acima de ITU 72 começa o estresse térmico; 72–78 é estresse brando, com queda de consumo e de leite ([Embrapa](https://www.infoteca.cnptia.embrapa.br/infoteca/bitstream/doc/594946/1/COT42Modificacoesambientais.pdf)) | ITU calculado de temperatura e umidade → regra reduz CMS esperado e emite alerta |
| Grupo genético | Mestiços Holandês × Zebu têm ITU crítico e exigências diferentes ([Embrapa](https://www.alice.cnptia.embrapa.br/alice/bitstream/doc/595010/1/Estimativa-de-niveis-criticos-superiores-do-indice-de-temperatura-e-umidade-para-vacas-leiteiras.pdf); [BR-Leite](https://www.alice.cnptia.embrapa.br/alice/handle/doc/1169399)) | Escolhe o conjunto de equações e faixas (ex.: NUL) |
| Preço do leite e dos alimentos | Indicador da Embrapa usa 1 kg de mistura 70% milho + 30% farelo de soja para 3 kg de leite como referência de margem ([Embrapa, Anuário](https://ainfo.cnptia.embrapa.br/digital/bitstream/doc/1143702/1/Precos-e-custos-na-producao-de-leite-Brasil.pdf)) | Função objetivo do PL; regra de viabilidade econômica |

**Nível 3 — indicadores de resposta** (NUL, gordura:proteína, sobras de cocho, escore de fezes, produção observada): não definem a dieta, mas dizem se ela funciona. Estão na seção de acompanhamento.

**O que muda em relação aos exemplos do edital**

| Exemplo do edital | Como fica no sistema |
| --- | --- |
| Raça | Grupo genético (Holandês, Jersey, Gir, Girolando por fração, mestiça) |
| Peso médio por lote | Mantido (nível 1) |
| Idade | Ordem de parto + dias de gestação; idade em meses só para novilhas |
| Estado produtivo | DEL + dias de gestação → fato derivado `PerfilLote` |
| Destinação econômica | Objetivo do lote + preços (leite, alimentos) |
| Produção | Produção + gordura + proteína |
| (não citados) | ECC, qualidade do volumoso, sistema/pastejo, ITU |

**Fato `Lote` mínimo**: `grupo_genetico, peso_kg, leite_kg, gordura_pct, proteina_pct, del, dias_gestacao, ordem_parto, ecc, sistema, distancia_km, relevo, temp_c, umidade_pct, objetivo`. As regras de classificação transformam esses fatos brutos no fato derivado `PerfilLote`, que as demais regras usam: um bom ponto para mostrar encadeamento aos avaliadores.

## Sistemas de exigências e equações de referência

Recomendação para a PoC: usar as equações do **NRC 2001** (simples, públicas, fáceis de explicar) e citar o **NASEM 2021** e o **BR-Leite** como evolução/ajuste para mestiços.

| Sistema | O que é | Uso no projeto |
| --- | --- | --- |
| [NRC 2001](https://nap.nationalacademies.org/read/9825/chapter/3) | 7ª edição das exigências de gado de leite (EUA); base clássica | Equações de CMS, energia e proteína do MVP |
| [NASEM 2021](https://www.agproud.com/articles/56402-notable-changes-to-the-nasem-dairy-nutrient-requirements-software) | 8ª edição (dez/2021); revisou consumo, digestão e aminoácidos; tem software gratuito com código em R | Referência para limites e para discutir na apresentação |
| [BR-Leite (Embrapa)](https://www.alice.cnptia.embrapa.br/alice/handle/doc/1169399) | Exigências de zebuínos leiteiros e cruzados, com equações próprias de CMS para confinados | Ajuste por raça (Gir, Girolando) |
| [CQBAL](https://locus.ufv.br/items/c98d4285-1356-41d9-b2ec-3c3e16d68479) | Tabelas brasileiras de composição de alimentos (UFV) | Base de alimentos |

No NASEM 2021, a queda de consumo pós-parto passou a durar 31 dias e há duas abordagens de CMS (só animal, ou animal + dieta) ([Hoard's](https://hoards.com/article-30897-feeding-strategies-get-a-top-to-bottom-review.html); [Penn State](https://extension.psu.edu/dairy-sense-predicting-dry-matter-intake-comparing-new-versus-old-approaches)).

**1. Consumo de matéria seca (NRC 2001, vacas em lactação)**

```latex
\mathrm{CMS}\ (\mathrm{kg/d}) = (0{,}372 \cdot \mathrm{LCG_{4\%}} + 0{,}0968 \cdot PV^{0{,}75}) \cdot \left(1 - e^{-0{,}192\,(SL + 3{,}67)}\right)
```

LCG₄% = leite corrigido para 4% de gordura = leite × (0,4 + 0,15 × %gordura); PV = peso vivo (kg); SL = semana de lactação. Exemplo publicado: vaca de 650 kg, 35 kg de leite a 3,8%, semana 6 → ≈ 21,2 kg MS/dia ([calculator.academy](https://calculator.academy/dry-matter-intake-calculator/)). Bom caso de teste unitário.

**2. Energia líquida para leite (NRC 2001)**

```latex
\mathrm{EL_{leite}}\ (\mathrm{Mcal/kg}) = 0{,}0929 \cdot \%G + 0{,}0547 \cdot \%PB_{leite} + 0{,}0395 \cdot \%Lact
```

Sem lactose medida, a variante usada é 0,0929 × %G + 0,0547 × %PB + 0,192 ([MDPI, 2022](https://www.mdpi.com/2077-0472/12/5/654)). Exigência diária de leite = EL\_leite × kg de leite.

**3. Energia de manutenção**: os sistemas europeus e americanos usam algo em torno de 0,30–0,35 MJ ELl por kg de PV^0,75 ([Gruber et al.](https://www.uni-hohenheim.de/organisation/publikation/evaluation-of-the-german-net-energy-system-and-estimation-of-the-energy-requirement-of-cows-on-the-basis-of-an-extensive-data-set-from-feeding-trials)); no NRC 2001 isso equivale a 0,08 Mcal × PV^0,75 (valor de memória, conferir no capítulo 2 do NRC), com acréscimo de atividade para animais em pastejo ([Weiss, UF](https://animal.ifas.ufl.edu/apps/dairymedia/rns/2002/weiss.pdf)).

**4. Proteína metabolizável para leite**: PM (g/d) = 10 × kg leite × %proteína / 0,67, onde 0,67 é a eficiência PM → proteína do leite ([AgModel/NRC 2001](https://agmodelsystems.com/?p=589)).

**5. Vacas secas e pré-parto (NASEM 2021)**: o CMS pré-parto usa a semana até o parto e o FDN da dieta, e tende a ficar entre 1,8 e 2% do PV; para novilhas, multiplica-se a equação de vacas por 0,88 ([Drackley, 2021](https://balchem.com/animal-nutrition-health/wp-content/uploads/sites/3/2021/09/Drackley-2021-NRC-Dry-Cows-Calves-and-Heifers.pdf)).

**6. Gestação**: a exigência extra entra a partir de \~190 dias de gestação ([AgModel](https://agmodelsystems.com/?p=525)); antes disso o termo é zero. Para a PoC, tratar como uma parcela adicional de ELl e PM tirada da tabela do NRC/NASEM (a implementar com o valor do livro).

**7. Variação de ECC**: cada ponto de ECC equivale a \~56 kg de tecido ([Alberta](https://www1.agriculture.alberta.ca/$department/deptdocs.nsf/all/agdex9622/$FILE/body-condition-scoring-and-energy-balance.pdf)) e, numa vaca de \~650 kg com ECC 4, a perda de 1 ponto libera \~417 Mcal de ELl ([Penn State](https://extension.psu.edu/body-condition-scoring-as-a-tool-for-dairy-herd-management)). Regra prática: energia/dia para mudar ECC ≈ 417 × Δ ECC ÷ dias até a meta (recuperar custa mais que mobilizar; usar o valor como aproximação).

**8. Atividade de pastejo (NRC 2001)**: soma à manutenção conforme peso, distância diária e relevo. Valores tabelados: vaca de \~450 kg em terreno plano andando \~0,4 km/d gasta \~0,6 Mcal; vaca de \~635 kg em terreno acidentado andando \~3,2 km/d gasta \~5,5 Mcal ELl/d ([eOrganic/NRC 2001](https://eorganic.org/node/219)). Implementar como tabela de consulta com interpolação.

**9. Índice de temperatura e umidade**

```latex
\mathrm{ITU} = 0{,}8\,T + \frac{UR}{100}\,(T - 14{,}4) + 46{,}4
```

T em °C e UR em % ([IFSULDEMINAS](https://memoriajornada.ifsuldeminas.edu.br/index.php/jcinc/jcinc/paper/download/40/53)). Faixas usadas pela Embrapa: até 70 normal, 70–72 alerta, 72–78 estresse acima do crítico para produção ([Embrapa](https://www.infoteca.cnptia.embrapa.br/infoteca/bitstream/doc/594946/1/COT42Modificacoesambientais.pdf)). O quanto o CMS cai por ponto de ITU não foi levantado aqui; a PoC só sinaliza o risco e reduz o CF.

**10. Teto de consumo pela fibra**: consumo de FDN ≈ 1,25% do PV no máximo, logo CMS\_max\_fibra ≈ 1,25 × PV ÷ %FDN da dieta ([Epagri/Mertens](https://casuar.epagri.sc.gov.br/index.php/1SEPLP/1SCPLP/paper/download/229/282)). O CMS esperado é o menor entre a equação do NRC e esse teto.

**Equação alternativa de CMS com ECC e ordem de parto**: de Souza et al. (2019) usam energia do leite, peso, ECC, DEL e paridade e tiveram viés menor que o NRC no meio e fim da lactação ([Feedstuffs](https://informamarkets.turtl.co/story/feedstuffs-august-2023/page/13)). Boa candidata a segunda opção selecionável por regra quando o ECC for informado.

Manutenção: o NRC 2001 usa \~0,08 Mcal × PV^0,75; um estudo recente com Jersey mediu \~0,10 Mcal × PV^0,75 ([JDS, 2024](https://doaj.org/article/be8288d8427c42378442716527f92d27)). Deixar o coeficiente como parâmetro versionado da base.

Atalho de sanidade (regra de verificação, não de cálculo): CMS de vaca em lactação raramente sai da faixa de \~2,5 a 4% do PV; fora disso, o sistema deve pedir confirmação dos dados.

## Alimentos e composição

A fonte principal deve ser o **CQBAL** (Tabelas Brasileiras de Composição de Alimentos para Bovinos, UFV): a versão 2.0 cadastrou 1996 referências e 1911 derivados de alimentos, com média, n e desvio padrão de cada nutriente ([Magalhães/UFV](https://locus.ufv.br/items/c98d4285-1356-41d9-b2ec-3c3e16d68479)); há a versão web CQBAL 3.0 ([Embrapa, 2015](https://www.alice.cnptia.embrapa.br/alice/bitstream/doc/1037875/1/Cnpgl2015CadTecVetZootNutricao.pdf)). Para o Nordeste existem as [Tabelas Nordestinas](https://www.infoteca.cnptia.embrapa.br/infoteca/handle/doc/1007523) da Embrapa. A variabilidade é real: o milho fubá no CQBAL tem PB média de 9,01% com desvio de 0,78% ([Scot/Embrapa](https://www.infoteca.cnptia.embrapa.br/infoteca/bitstream/doc/1118538/1/InformacoesUteisFormulacao.pdf)), o que justifica permitir que o usuário sobrescreva valores com a análise da fazenda.

**Base mínima de alimentos para o MVP** (valores **aproximados**, de memória, só para semear o protótipo; substituir pelos do CQBAL antes da apresentação)

| Alimento | Tipo | MS (%) | PB (% MS) | FDN (% MS) | NDT (% MS) |
| --- | --- | --- | --- | --- | --- |
| Silagem de milho | Volumoso | 30–35 | 7–8 | 45–52 | 62–66 |
| Capim-elefante picado (\~60 d) | Volumoso | 18–22 | 6–9 | 65–72 | 50–56 |
| Braquiária em pastejo (águas) | Volumoso | 22–28 | 8–12 | 60–68 | 55–60 |
| Cana-de-açúcar | Volumoso | 26–30 | 2–4 | 45–55 | 58–62 |
| Milho grão moído (fubá) | Concentrado energético | 87–89 | 8–9 | 10–14 | 82–87 |
| Farelo de soja | Concentrado proteico | 88–90 | 45–50 | 13–16 | 80–84 |
| Caroço de algodão | Concentrado (gordura + fibra) | 90–92 | 20–24 | 40–48 | 85–95 |
| Núcleo mineral | Mineral | \~98 | — | — | — |

**Limites de inclusão que viram restrições/regras**

- Ureia: no máximo 1% da MS da dieta total, misturada ao volumoso ou concentrado ([Semadesc-MS](https://www.semadesc.ms.gov.br/wp-content/uploads/2023/11/Formulac¦o-Dietas-Vacas-Leiteiras.pdf)).
- Gordura total (EE): no máximo cerca de 6% da MS ([Cultivar](https://revistacultivar.com.br/index.php/artigos/manejo-nutricional-de-vacas-leiteiras-no-periodo-de-lactacao)).
- Cana como único volumoso: FDN de baixa digestibilidade (cerca de 25% digerido, contra 45% na forragem de milho) e restrição de consumo; regra de alerta para alta produção ([Semadesc-MS](https://www.semadesc.ms.gov.br/wp-content/uploads/2023/11/Formulac¦o-Dietas-Vacas-Leiteiras.pdf)).

**Modelo de dados do alimento**: `id, nome, tipo, ms, pb, pdr, fdn, fdnd, fdnf_fator, cnf, ee, ndt, ca, p, preco_kg_mn, fonte, versao`. O campo `fdnd` (digestibilidade da FDN) é opcional, mas é o que mais explica diferença de consumo entre volumosos com o mesmo teor de FDN.

## Formulação: métodos e onde o motor de inferência entra

A divisão de trabalho recomendada: **as regras definem as metas e restrições; um otimizador (ou checagem simples) encontra quantidades; as regras verificam e explicam o resultado.** Assim o otimizador é uma ferramenta chamada pelo sistema especialista, não o sistema especialista.

**Métodos de formulação**

| Método | Como funciona | Quando usar no projeto |
| --- | --- | --- |
| Quadrado de Pearson | Mistura 2 ingredientes para atingir 1 nutriente (ex.: concentrado com 18% PB) | Demo didática; calcular mistura de concentrado |
| Tentativa e verificação | Usuário propõe dieta; sistema calcula oferta vs exigência | Módulo "verificar dieta" (obrigatório no MVP) |
| Programação linear de mínimo custo | Minimiza custo sujeito a restrições de nutrientes e inclusão; ensinada em zootecnia como "formulação de rações de mínimo custo" ([UFV](https://pgp.ufv.br/wp-content/uploads/2021/11/Zootecnista.pdf)) | Módulo "sugerir dieta" (diferencial) |

**Formulação como PL**: variáveis xᵢ = kg MS do alimento i por vaca/dia.

```latex
\min \sum_i c_i x_i \quad \text{s.a.} \quad \sum_i x_i \le \mathrm{CMS},\quad \sum_i n_{ij} x_i \ge E_j,\quad \frac{\sum_i \mathrm{FDN}_i x_i}{\sum_i x_i} \ge 0{,}25,\quad x_i \ge 0
```

cᵢ = preço por kg MS; nᵢⱼ = teor do nutriente j no alimento i; Eⱼ = exigência. Restrições de razão (% da MS) ficam lineares multiplicando pelo total: Σ(FDNᵢ − 0,25)·xᵢ ≥ 0.

**Onde as regras entram em cada etapa**

1. **Antes**: regras transformam o perfil do lote em metas (ex.: "pré-parto → PB 13–15%, CMS \~1,8–2% PV") e restrições ("ureia ≤ 1% MS", "FDNf ≥ 19%").
2. **Durante**: se o PL for inviável, regras de diagnóstico explicam qual restrição falhou e sugerem relaxamento (ex.: "energia não atingível com estes alimentos → incluir fonte energética ou reduzir meta de leite").
3. **Depois**: regras de verificação conferem a dieta final e geram o parecer com CF e justificativa.

Isso atende literalmente ao edital ("formulação e verificação") e deixa a decisão auditável.

## Acompanhamento da dieta: indicadores e sinais de alerta

O acompanhamento transforma observações de campo em fatos datados (`Registro(lote, data, indicador, valor)`); as regras comparam com faixas-alvo e com o registro anterior (tendência). Os seis indicadores abaixo são baratos, usados na prática e cada um aponta para uma causa nutricional.

| Indicador | Faixa-alvo | Fora da faixa sugere | Frequência | Fonte |
| --- | --- | --- | --- | --- |
| NUL (nitrogênio ureico no leite) | \~10–18 mg/dL (varia com raça e sistema) | >18: excesso de PB/PDR ou falta de energia fermentável; muito baixo: proteína insuficiente | Mensal (controle leiteiro) | [Pubvet, 2019](https://doaj.org/article/bd606610132d47228b2cd89fc1d0b6f2); [UFGD](https://ojs.ufgd.edu.br/realizacao/article/download/21231/11709/78261) |
| Relação gordura:proteína do leite | \~1,0–1,4 (inferido; ver nota) | <1,0: sinal indireto de acidose ruminal subaguda; alta no início da lactação: mobilização de gordura/cetose | Mensal | [Lusófona](https://revistas.ulusofona.pt/index.php/rlcmv/article/view/11108/6200); [UTP](https://revistas.utp.br/index.php/GR1/article/download/1625/1373) |
| ECC (escala 1–5) | Parto 3,25–3,75; pico 2,5–3,0; meio 2,75–3,25; final 3,0–3,75 | Perda > 1 ponto nas 5 primeiras semanas atrasa a 1ª inseminação; gordura excessiva ao parto piora metabolismo | Por fase / mensal | [USC](https://libros-xestion.usc.gal/index.php/spic/catalog/view/1665/1642/10140-1); [Embrapa/IFRO](https://www.alice.cnptia.embrapa.br/alice/bitstream/doc/1143677/1/cpafro-18764.pdf) |
| Leitura de cocho (sobras) | Sobra fina e uniforme | Cocho vazio: subalimentação; sobra grossa: excesso/rejeição/seleção | Diária, \~1 h antes do trato | [CompreRural](https://comprerural.com/escore-de-cocho-tecnica-conhecida-mas-pouco-utilizada/) |
| Escore de fezes (1–5) | 3,0 alta produção; 2,5 recém-paridas; 3,5 secas e final de lactação | Fezes fluidas: excesso de proteína/amido; firmes: excesso de fibra; grãos inteiros: processamento ruim | Semanal | [Unicruz](<https://home.unicruz.edu.br/seminario/anais/anais-2018/XXIII%20SEMINARIO%20INTERINSTITUCIONAL/Ciencias%20Exatas,%20Agrarias%20e%20Engenharias/Mostra%20de%20Iniciacao%20Cientifica%20-%20RESUMO%20EXPANDIDO/CARACTERIZA%C3%87%C3%83O%20DE%20ESCORE%20FECAL%20EM%20BOVINOS%20REVIS%C3%83O%20DE%20LITERATURA%20(7151).pdf>) |
| Produção vs esperada | Dentro de ±10% da meta do lote (critério nosso, a validar) | Queda súbita após troca de silagem é um caso clássico | Diária/semanal | [CompreRural](https://comprerural.com/fibra-na-nutricao-de-ruminantes/) |

Notas: a faixa de NUL depende da raça (Jersey costuma ter NUL diferente de Holandesa) e do sistema (pastejo eleva NUL) ([Unijuí](https://www.publicacoeseventos.unijui.edu.br/index.php/salaoconhecimento/article/view/3514/2914)); em mestiças, estudo da UFV encontrou que só lotes acima de 20 kg/dia exigiam atenção a excesso de proteína ([UFV, 2003](https://locus.ufv.br/items/e03c398b-ddb1-4c88-9d84-801ca65f3aad)). O limite superior da relação gordura:proteína é uma convenção de campo, não sourced aqui; confirmar com um técnico. Para NUL, a Embrapa sugere amostrar pelo menos 4 vacas por dieta ([Embrapa, 2011](https://www.infoteca.cnptia.embrapa.br/infoteca/bitstream/doc/900587/1/PROCI-2011.00109.pdf)).

**Ciclo de acompanhamento**: registrar → motor compara com faixa e tendência → alertas com CF e explicação → sugestão de ajuste → usuário aceita/rejeita → nova versão da dieta é salva com motivo. Esse histórico versionado é o que o edital chama de "acompanhar".

## Banco de regras de produção candidatas

Regras no formato SE condições ENTÃO conclusão \[CF\], com fonte. Os CFs são **propostos pelo grupo** (0 a 1) para a PoC e devem ser revisados; a fonte justifica a condição, não o número do CF. Sugestão de ID: `MÓDULO-nn` para versionar e citar na explicação.

**Módulo A — Classificação do lote**

| ID | SE | ENTÃO | CF |
| --- | --- | --- | --- |
| CLS-01 | lactação E del ≤ 21 | perfil = recém-parida | 1,0 |
| CLS-02 | lactação E 22 ≤ del ≤ 100 | perfil = início/pico | 1,0 |
| CLS-03 | lactação E 101 ≤ del ≤ 200 | perfil = meio de lactação | 1,0 |
| CLS-04 | lactação E del > 200 | perfil = final de lactação | 1,0 |
| CLS-05 | seca E dias\_para\_parto ≤ 21 | perfil = pré-parto (transição) | 1,0 |
| CLS-06 | dias\_gestacao ≥ 190 | adicionar exigência de gestação | 1,0 |
| CLS-07 | ordem\_parto = 1 E lactação | adicionar exigência de crescimento | 0,9 |
| CLS-08 | grupo\_genetico ∈ {Gir, Girolando, mestiça} | usar ajustes BR-Leite quando disponíveis | 0,8 |
| CLS-09 | sistema = pasto | adicionar custo de atividade (tabela NRC por distância e relevo) | 0,8 |
| CLS-10 | ITU > 72 | risco de estresse térmico: CMS esperado menor | 0,7 |
| CLS-11 | ITU > 78 | estresse térmico acima do brando: alerta forte | 0,8 |
| CLS-12 | sistema = pasto E grupo mestiço | reduzir CF das predições de CMS (NRC pouco preciso nesse caso) | 0,6 |

**Módulo B — Exigências e metas**

| ID | SE | ENTÃO | Fonte |
| --- | --- | --- | --- |
| EXG-01 | perfil = lactação | CMS = min(equação NRC 2001; teto de fibra 1,25 × PV ÷ %FDN) | NRC 2001; Mertens |
| EXG-02 | perfil = lactação | ELl = manutenção + leite + gestação (CLS-06) + crescimento (CLS-07) + atividade (CLS-09) ± ajuste de ECC | NRC 2001 |
| EXG-03 | perfil = pré-parto | CMS ≈ 1,8–2% PV | NASEM 2021 (Drackley) |
| EXG-04 | perfil = lactação | meta FDN ≥ 25% MS E FDNf ≥ 19% MS E CNF ≤ 44% MS | NRC 2001 |
| EXG-05 | FDNf < 19% | para cada 1 ponto a menos de FDNf: FDN mínimo +2 e CNF máximo −2 | NRC 2001 ([CompreRural](https://comprerural.com/fibra-na-nutricao-de-ruminantes/)) |
| EXG-06 | ECC < meta da fase | somar energia para recuperar ≈ 417 Mcal × Δ ECC ÷ dias até a meta | Penn State |
| EXG-07 | perfil = início E ECC ≥ meta | permitir mobilização moderada (não exigir 100% da energia pela dieta) | Penn State; USC |
| EXG-08 | ECC informado E lactação | oferecer equação de CMS alternativa (de Souza 2019) | Feedstuffs |
| EXG-09 | fdnd do volumoso informada | ajustar CMS esperado em \~0,17 kg por ponto de FDND acima/abaixo da referência | Oba & Allen 1999 |

**Módulo C — Verificação da dieta**

| ID | SE | ENTÃO | CF |
| --- | --- | --- | --- |
| VER-01 | oferta\_ELl < 0,95 × exigência | déficit energético; alertar perda de ECC | 0,9 |
| VER-02 | oferta\_PM < 0,95 × exigência | déficit proteico | 0,85 |
| VER-03 | FDN\_dieta < meta EXG-04/05 | risco de acidose ruminal | 0,85 |
| VER-04 | ureia > 1% MS | inclusão de ureia acima do limite (bloqueante) | 1,0 |
| VER-05 | EE > 6% MS | gordura excessiva | 0,8 |
| VER-06 | MS\_ofertada > 1,05 × CMS\_previsto | dieta provavelmente não será consumida | 0,7 |
| VER-07 | volumoso = cana (único) E leite > \~15 kg (limite a validar) | volumoso limitante para essa produção | 0,7 |
| VER-08 | todas as regras críticas OK | dieta adequada | combinação dos CFs |

**Módulo D — Acompanhamento e alertas**

| ID | SE | ENTÃO | CF |
| --- | --- | --- | --- |
| ACP-01 | NUL > 18 mg/dL | excesso de proteína ou falta de energia fermentável; sugerir rever PB/PDR e CNF | 0,7 |
| ACP-02 | NUL < 10 mg/dL | proteína possivelmente insuficiente | 0,6 |
| ACP-03 | gordura/proteína < 1,0 | suspeita de acidose subaguda; aumentar fibra efetiva | 0,7 |
| ACP-04 | ACP-03 E escore\_fezes ≤ 2 | reforça suspeita de acidose (combina CFs) | 0,6 |
| ACP-05 | perfil = início E perda\_ECC > 1 ponto em 5 semanas | balanço energético negativo severo; elevar densidade energética | 0,8 |
| ACP-06 | sobras = cocho vazio por 2+ leituras | aumentar oferta \~5% (ajuste a validar) | 0,8 |
| ACP-07 | sobras ≥ "camada grossa" | reduzir oferta ou investigar rejeição/seleção | 0,7 |
| ACP-08 | queda de leite > 10% em 7 dias E troca recente de volumoso | causa provável: novo volumoso; pedir análise com FDND | 0,6 |
| ACP-09 | ECC fora da faixa da fase | ajustar energia conforme direção do desvio (EXG-06) | 0,7 |
| ACP-10 | queda de leite E ITU > 72 nos mesmos dias | causa provável: estresse térmico, não a dieta; sugerir manejo de sombra/água antes de mudar a dieta | 0,6 |
| ACP-11 | lote em pasto E perda de ECC E distância ou relevo aumentaram | gasto de atividade subestimado; rever CLS-09 | 0,5 |
| ACP-12 | dias\_gestacao chegou a 190 | recalcular exigências (entrou o termo de gestação) | 1,0 |

**Combinação de CF (estilo MYCIN)** para duas regras que concluem a mesma hipótese: CF = CF₁ + CF₂ × (1 − CF₁) quando ambos positivos. Exemplo: ACP-03 (0,7) + ACP-04 (0,6) → 0,88. Simples de implementar e de explicar na apresentação.

## Arquitetura, tecnologias e escopo para 3 dias

A arquitetura segue o modelo conceitual do edital (slide 14) e roda inteira em localhost; o motor de inferência é o único que decide.

&#91;embedded content: arquitetura proposta · 9 componentes, tudo em localhost\]

O motor chama a calculadora e o otimizador como funções, recebe números e decide com regras; cada disparo vai para o traço que alimenta o "por quê?".

**Stack open source sugerida**

| Camada | Recomendado | Alternativa / observação |
| --- | --- | --- |
| Motor de inferência | [Experta](https://pypi.org/project/experta/) (Python puro, RETE, inspirado no CLIPS) | clipspy (CLIPS real) ou motor forward-chaining próprio (\~150 linhas). Experta é antigo: testar a instalação na versão de Python do grupo logo no primeiro dia |
| Base de conhecimento | Regras em YAML/JSON no git (ID, condições, conclusão, CF, fonte, versão) | Carregadas e convertidas em regras do motor na inicialização |
| Cálculo de exigências | Python puro, funções testadas | — |
| Otimizador | PuLP + CBC (já embutido) | scipy.optimize.linprog (HiGHS) |
| Backend | FastAPI | Flask |
| Interface | Streamlit (mais rápido para PoC) | React/Vite se alguém do grupo já domina |
| Persistência | SQLite | JSON |
| Testes | pytest com os casos da seção de testes | — |

Vale escrever o motor próprio se o Experta der problema: um laço "enquanto alguma regra casar com fatos novos, dispare e registre no traço" já é encadeamento progressivo e é fácil de explicar aos avaliadores.

**Escopo**

- **Obrigatório (MVP)**: cadastro de lote com as variáveis de nível 1 + ECC → classificação (Módulo A) → exigências (B) → verificação de uma dieta informada pelo usuário (C) → parecer com explicação. Registro de acompanhamento com NUL, gordura/proteína, ECC, sobras, fezes, produção → alertas (D).
- **Diferencial**: variáveis de nível 2 (pastejo com tabela de atividade, ITU a partir de temperatura e umidade, FDND do volumoso, grupo genético); sugestão de dieta de mínimo custo via PL com diagnóstico de inviabilidade; histórico de versões da dieta com gráfico de indicadores por lote.
- **Fora do escopo**: minerais e vitaminas detalhados, aminoácidos, modelo completo NASEM, estimativa de consumo de pasto por massa de forragem.

**Plano por dia** (entrega quinta, 22/10, até 20h; apresentação sexta, 23/10, 9h)

1. **Terça, 20/10 (tarde/noite)**: fechar escopo, modelo de dados, carregar 8 alimentos, escrever regras em YAML com fonte; registrar os prompts usados com o agente (vira material da apresentação).
2. **Quarta, 21/10**: calculadora + motor + Módulos A, B e C com testes T1–T7; interface mínima de cadastro e parecer.
3. **Quinta, 22/10**: Módulo D (acompanhamento) + T8–T10; PL se der tempo; documentação (processo, arquitetura, regras) e slides; enviar a Carlos Lima até 20h.

Sugestão de divisão para 3 pessoas: uma na base de conhecimento e testes (domínio), uma no motor e cálculo, uma na interface, documentação e slides.

## Casos de teste com resultado esperado

O edital pede casos conhecidos para validar cada versão da base. Os dois primeiros testam equações (valores calculados aqui); os demais testam regras.

| # | Entrada | Resultado esperado | Testa |
| --- | --- | --- | --- |
| T1 | Vaca 650 kg, 35 kg leite, 3,8% gordura, semana 6 | CMS ≈ 21,2 kg MS/d | EXG-01 ([exemplo publicado](https://calculator.academy/dry-matter-intake-calculator/)) |
| T2 | Mesma vaca, proteína 3,2%, sem lactose | EL leite ≈ 0,72 Mcal/kg → ≈ 25,2 Mcal/d; manutenção ≈ 0,08 × 128,8 ≈ 10,3 Mcal/d; PM leite ≈ 1.672 g/d | EXG-02, PM |
| T3 | del = 10, lactação | perfil = recém-parida | CLS-01 |
| T4 | Seca, 15 dias para o parto | perfil = pré-parto; CMS ≈ 1,8–2% PV | CLS-05, EXG-03 |
| T5 | Dieta com FDN 22% MS, FDNf 19% | alerta de risco de acidose | VER-03 |
| T6 | Dieta com FDNf 17% | FDN mínimo vira 29% e CNF máximo 40% | EXG-05 |
| T7 | Ureia 1,4% MS | dieta bloqueada, explicação cita VER-04 | VER-04 |
| T8 | NUL 22 mg/dL | alerta de excesso de proteína/falta de energia | ACP-01 |
| T9 | Gordura 2,9%, proteína 3,3% (razão 0,88) + escore de fezes 2 | suspeita de acidose com CF ≈ 0,88 | ACP-03 + ACP-04 + combinação |
| T10 | ECC 3,5 ao parto → 2,25 na semana 5 | alerta de balanço energético negativo severo | ACP-05 |
| T11 | Alimentos sem fonte energética suficiente para a meta | PL inviável + explicação da restrição que falhou | diagnóstico de inviabilidade |
| T12 | Vaca de \~635 kg em pasto acidentado, \~3,2 km/d | atividade ≈ +5,5 Mcal ELl/d somada à manutenção | CLS-09 |
| T13 | T = 30 °C, UR = 70% | ITU ≈ 81,3 → alerta forte de estresse térmico | CLS-10, CLS-11 |
| T14 | Lactação, 200 dias de gestação | termo de gestação incluído; ACP-12 dispara na transição de 189 → 190 | CLS-06, ACP-12 |
| T15 | Primípara em lactação | exigência de crescimento incluída | CLS-07 |
| T16 | PV 600 kg, dieta com 40% FDN | teto de fibra ≈ 18,75 kg MS/d; CMS = menor valor entre NRC e teto | EXG-01 |
| T17 | ECC 2,5, meta 3,0 em 100 dias (vaca \~650 kg) | ≈ +2,1 Mcal ELl/d (aproximação) | EXG-06 |
| T18 | Leite caiu 12% em 7 dias, ITU > 72 no período, sem troca de volumoso | causa provável estresse térmico; não sugerir mudança de dieta primeiro | ACP-10 |

Automatizar como testes unitários (pytest): cada caso declara fatos, roda o motor e compara as conclusões e os IDs das regras disparadas.

## Fontes e referências

Prioridade de leitura para o grupo: NRC 2001 cap. 1 (consumo), BR-Leite (mestiços), CQBAL (alimentos), artigo de NUL da Pubvet.

- [NRC 2001 — Nutrient Requirements of Dairy Cattle, cap. 1 (National Academies, leitura online)](https://nap.nationalacademies.org/read/9825/chapter/3)
- [NASEM 2021 — mudanças no software (Progressive Dairy)](https://www.agproud.com/articles/56402-notable-changes-to-the-nasem-dairy-nutrient-requirements-software)
- [NASEM 2021 — vacas secas e transição (Progressive Dairy)](https://www.agproud.com/articles/54377)
- [Drackley 2021 — NASEM: vacas secas, bezerras e novilhas](https://balchem.com/animal-nutrition-health/wp-content/uploads/sites/3/2021/09/Drackley-2021-NRC-Dry-Cows-Calves-and-Heifers.pdf)
- [AgModel Systems — entradas mais importantes do modelo (peso, leite, gestação)](https://agmodelsystems.com/?p=525)
- [Hoard's Dairyman — revisão das estratégias de alimentação NASEM](https://hoards.com/article-30897-feeding-strategies-get-a-top-to-bottom-review.html)
- [Penn State — predição de CMS, nova vs antiga](https://extension.psu.edu/dairy-sense-predicting-dry-matter-intake-comparing-new-versus-old-approaches)
- [Feedstuffs 2023 — equações de CMS com ECC e paridade](https://informamarkets.turtl.co/story/feedstuffs-august-2023/page/13)
- [Weiss (UF) — sistema de energia do NRC 2001](https://animal.ifas.ufl.edu/apps/dairymedia/rns/2002/weiss.pdf)
- [MDPI 2022 — equações de energia do leite](https://www.mdpi.com/2077-0472/12/5/654)
- [JDS 2024 — energia de manutenção em Jersey com ECC diferente](https://doaj.org/article/be8288d8427c42378442716527f92d27)
- [Penn State — ECC como ferramenta (energia por ponto de ECC)](https://extension.psu.edu/body-condition-scoring-as-a-tool-for-dairy-herd-management)
- [Alberta Agriculture — ECC e balanço energético](https://www1.agriculture.alberta.ca/$department/deptdocs.nsf/all/agdex9622/$FILE/body-condition-scoring-and-energy-balance.pdf)
- [RBZ — perda de peso no início da lactação por ordem de parto](https://rbz.org.br/?p=5888)
- [Oba & Allen 1999 — digestibilidade da FDN, consumo e leite](https://agris.fao.org/search/fr/records/65de3a467c7033e84bea2104)
- [eOrganic — energia da atividade de pastejo (NRC 2001)](https://eorganic.org/node/219)
- [ADSA 2019 — exigência de atividade de vacas em pastejo](https://m.adsa.org/2019/abs/t/79013)
- [Embrapa 2012 — avaliação do NRC para CMS de mestiças em pastagens tropicais](https://www.alice.cnptia.embrapa.br/alice/bitstream/doc/949021/1/Avaliacao-do-modelo-NRC-para-predicao-do-consumo-de-materia-seca.pdf)
- [Embrapa — modificações ambientais e ITU](https://www.infoteca.cnptia.embrapa.br/infoteca/bitstream/doc/594946/1/COT42Modificacoesambientais.pdf)
- [Embrapa — ITU crítico para vacas 1/2, 3/4 e 7/8 Holandês-Zebu](https://www.alice.cnptia.embrapa.br/alice/bitstream/doc/595010/1/Estimativa-de-niveis-criticos-superiores-do-indice-de-temperatura-e-umidade-para-vacas-leiteiras.pdf)
- [IFSULDEMINAS — fórmula do ITU com temperatura e umidade](https://memoriajornada.ifsuldeminas.edu.br/index.php/jcinc/jcinc/paper/download/40/53)
- [Merck Vet Manual — consumo de água (NASEM 2021)](https://www.merckvetmanual.com/multimedia/table/free-water-intake-equations-for-dairy-cows)
- [Embrapa — BR-Leite: predição de CMS de zebuínos e cruzados](https://www.alice.cnptia.embrapa.br/alice/handle/doc/1169399)
- [Embrapa 2015 — Nutrição de precisão na pecuária leiteira (CQBAL 3.0)](https://www.alice.cnptia.embrapa.br/alice/bitstream/doc/1037875/1/Cnpgl2015CadTecVetZootNutricao.pdf)
- [UFV — Tabelas brasileiras de composição de alimentos (CQBAL 2.0)](https://locus.ufv.br/items/c98d4285-1356-41d9-b2ec-3c3e16d68479)
- [Embrapa — Tabelas nordestinas de composição de alimentos](https://www.infoteca.cnptia.embrapa.br/infoteca/handle/doc/1007523)
- [Embrapa — Anuário: preços e custos (relação concentrado:leite)](https://ainfo.cnptia.embrapa.br/digital/bitstream/doc/1143702/1/Precos-e-custos-na-producao-de-leite-Brasil.pdf)
- [Embrapa 1995 — Alimentos concentrados para bovinos de leite (custo)](https://www.infoteca.cnptia.embrapa.br/infoteca/bitstream/doc/591500/1/2032.pdf)
- [Epagri — consumo voluntário e limite de FDN](https://casuar.epagri.sc.gov.br/index.php/1SEPLP/1SCPLP/paper/download/229/282)
- [Pubvet 2019 — NUL e NUP de vacas em pastejo](https://doaj.org/article/bd606610132d47228b2cd89fc1d0b6f2)
- [Embrapa 2011 — uso dos valores de NUL](https://www.infoteca.cnptia.embrapa.br/infoteca/bitstream/doc/900587/1/PROCI-2011.00109.pdf)
- [CompreRural — fibra mínima (NRC 2001)](https://comprerural.com/fibra-na-nutricao-de-ruminantes/)
- [CompreRural — escore de cocho](https://comprerural.com/escore-de-cocho-tecnica-conhecida-mas-pouco-utilizada/)
- [USC — condição corporal por fase da lactação](https://libros-xestion.usc.gal/index.php/spic/catalog/view/1665/1642/10140-1)
- [Semadesc-MS — formulação de dietas para vacas leiteiras](https://www.semadesc.ms.gov.br/wp-content/uploads/2023/11/Formulac¦o-Dietas-Vacas-Leiteiras.pdf)
- [Experta — documentação](https://experta.readthedocs.io/en/latest/introduction.html)
