# Regras de produção — base v1.1.0

114 regras · 82 parâmetros · 12 alimentos. Gerado automaticamente de `backend/kb/` (não editar à mão).

Formato: **SE** condições **ENTÃO** ações [CF da regra]. Limiares `@params.*` estão na tabela de parâmetros no fim.
Força da evidência: A = norma/meta-análise; B = estudo revisado ou extensão com dados; C = extensão sem dados ou população diferente; D = escolha de engenharia.

## A — Classificação do lote (CLS)

| ID | Descrição | SE | ENTÃO | CF | Força | Fonte |
|---|---|---|---|---|---|---|
| CLS-01 | Lote em lactação com DEL até 21 dias é recém-parido | `lote.estado` = lactacao E `lote.del` <= @params.del_recem_parida_max | concluir `perfil.fase` = recem_parida | 1.0 | C | Dossiê CLS-01 |
| CLS-02 | Lote em lactação com DEL entre 22 e 100 dias está no início/pico | `lote.estado` = lactacao E `lote.del` > @params.del_recem_parida_max E `lote.del` <= @params.del_inicio_max | concluir `perfil.fase` = inicio | 1.0 | C | Dossiê CLS-02 |
| CLS-03 | Lote em lactação com DEL entre 101 e 200 dias está no meio da lactação | `lote.estado` = lactacao E `lote.del` > @params.del_inicio_max E `lote.del` <= @params.del_meio_max | concluir `perfil.fase` = meio | 1.0 | C | Dossiê CLS-03 |
| CLS-04 | Lote em lactação com DEL acima de 200 dias está no final da lactação | `lote.estado` = lactacao E `lote.del` > @params.del_meio_max | concluir `perfil.fase` = final | 1.0 | C | Dossiê CLS-04 |
| CLS-05 | Vaca seca a até 21 dias do parto está no pré-parto (transição) | `lote.estado` = seca E `lote.dias_para_parto` <= @params.preparto_dias | concluir `perfil.fase` = pre_parto | 1.0 | B | Dossiê CLS-05; Santos et al. 2019 |
| CLS-05B | Vaca seca a mais de 21 dias do parto é vaca seca (fase inicial do período seco) | `lote.estado` = seca E `lote.dias_para_parto` > @params.preparto_dias | concluir `perfil.fase` = seca | 1.0 | C | Dossiê CLS-05 |
| CLS-06 | Gestação com 190 dias ou mais soma exigência de gestação | `lote.dias_gestacao` >= @params.gestacao_dias_exigencia | concluir `perfil.gestacao_avancada` = True | 1.0 | B | NRC 2001 via AgModel |
| CLS-07 | Lote em lactação com primíparas soma exigência de crescimento | `lote.estado` = lactacao E `lote.fracao_primiparas` > 0 | concluir `perfil.crescimento` = True | 0.9 | B | RBZ (primíparas perdem mais peso e ainda crescem) |
| CLS-08 | Zebuínos e cruzados em lactação usam a equação de consumo BR-Leite | `lote.estado` = lactacao E `lote.grupo_genetico` in @params.grupos_zebuinos | concluir `perfil.equacao_cms` = brleite | 0.8 | B | BR-Leite 2024 (Embrapa) |
| CLS-08B | Holandês e Jersey em lactação usam a equação de consumo NRC 2001 | `lote.estado` = lactacao E `lote.grupo_genetico` nao_in @params.grupos_zebuinos | concluir `perfil.equacao_cms` = nrc2001 | 1.0 | B | NRC 2001 |
| CLS-09 | Lote em pasto tem gasto de energia com atividade de pastejo | `lote.sistema` = pasto | concluir `perfil.atividade_pastejo` = True | 0.8 | B | NRC 2001 via eOrganic |
| CLS-ITU | Calcular o ITU a partir de temperatura e umidade | `lote.temp` existe E `lote.ur` existe | calcular `clima.itu` = itu(…) | 1.0 | B | IFSULDEMINAS |
| CLS-10 | ITU entre 72 e 78 indica estresse térmico brando (consumo esperado menor) | `clima.itu` > @params.itu_alerta E `clima.itu` <= @params.itu_forte | concluir `perfil.estresse_termico` = brando; alerta **atencao** (calor): Risco de estresse térmico (ITU {clima.itu:.1f}) | 0.7 | B | Embrapa COT42 |
| CLS-11 | ITU acima de 78 indica estresse térmico acima do brando | `clima.itu` > @params.itu_forte | concluir `perfil.estresse_termico` = forte; alerta **critico** (calor): Estresse térmico forte (ITU {clima.itu:.1f}) | 0.8 | B | Embrapa COT42 |
| CLS-12 | Mestiças em pasto tropical têm predição de consumo pouco confiável | `lote.sistema` = pasto E `lote.grupo_genetico` in @params.grupos_zebuinos | concluir `perfil.cms_baixa_confianca` = True | 0.6 | B | Embrapa 2012 (NRC com R² 0,029 em pasto tropical) |
| CLS-13 | Calcular a semana de lactação a partir do DEL | `lote.estado` = lactacao E `lote.del` existe | calcular `perfil.semana_lactacao` = semana_lactacao(…) | 1.0 | B | NRC 2001 |

## B — Exigências e metas (EXG)

| ID | Descrição | SE | ENTÃO | CF | Força | Fonte |
|---|---|---|---|---|---|---|
| EXG-00 | Calcular a composição da dieta informada (MS, PB, FDN, FDNf, CNF, EE, ELl, ureia, custo) | `dieta.itens` existe | calcular `dieta` = composicao_dieta(…) | 1.0 | B | Conversão MN→MS; ELl = 0,0245·NDT − 0,12 (NRC 2001 Eq. 2-3) |
| EXG-01A | CMS pela equação NRC 2001 (Holandês/Jersey em lactação) | `perfil.equacao_cms` = nrc2001 | calcular `exig.cms_equacao` = cms_nrc2001(…) | 1.0 | B | NRC 2001 (coeficientes confirmados em fonte secundária) |
| EXG-01B | CMS pela equação BR-Leite Eq. 1.1 (zebuínos e cruzados) | `perfil.equacao_cms` = brleite E (`dieta.cana_unico_volumoso` ausente OU `dieta.cana_unico_volumoso` = False) | calcular `exig.cms_equacao` = cms_brleite(…) | 1.0 | B | BR-Leite 2024, cap. 3, Eq. 1.1 (Embrapa) |
| EXG-01C | CMS pela equação BR-Leite Eq. 1.2 quando a cana é o volumoso | `perfil.equacao_cms` = brleite E `dieta.cana_unico_volumoso` = True | calcular `exig.cms_equacao` = cms_brleite_cana(…) | 1.0 | B | BR-Leite 2024, cap. 3, Eq. 1.2 (Embrapa) |
| EXG-01D | Teto de consumo pelo enchimento (consumo de FDN ≤ 1,25% do PV) | `dieta.fdn_pct` > 0 E `exig.cms_equacao` existe | calcular `exig.cms_teto_fibra` = teto_fibra(…) | 1.0 | B | Mertens via Epagri |
| EXG-01E | CMS esperado é o menor entre a equação e o teto de fibra | `exig.cms_equacao` existe E `perfil.cms_baixa_confianca` ausente | calcular `exig.cms` = minimo(…) | 1.0 | B | NRC 2001; Mertens |
| EXG-01P | Em pasto com mestiças o CMS é estimado com confiança reduzida | `exig.cms_equacao` existe E `perfil.cms_baixa_confianca` = True | calcular `exig.cms` = minimo(…); alerta **informativo** (dieta): Consumo em pasto estimado com baixa confiança | 0.6 | B | Embrapa 2012 (Jardim et al.) |
| EXG-03 | Vacas secas e pré-parto consomem cerca de 1,8–2% do PV | `perfil.fase` in ['pre_parto', 'seca'] | calcular `exig.cms` = cms_preparto(…) | 1.0 | B | NASEM 2021 via Drackley 2021 |
| EXG-02A | Energia de mantença = k × PV^0,75 | `lote.pv` existe E `perfil.fase` existe | calcular `exig.ell_mantenca` = mantenca(…) | 1.0 | B | NRC 2001 (NASEM 2021: 0,10) |
| EXG-02B | Energia para produção de leite pela composição do leite | `lote.estado` = lactacao | calcular `exig.ell_leite` = ell_leite(…) | 1.0 | B | NRC 2001 |
| EXG-02C | Energia de gestação (a partir de 190 dias) | `perfil.gestacao_avancada` = True | calcular `exig.ell_gestacao` = ell_gestacao(…); calcular `exig.pm_gestacao` = pm_gestacao(…) | 1.0 | B | NRC 2001 (Bell & Ehrhardt); confere com tabela de Drackley 2021 |
| EXG-02D | Energia de crescimento das primíparas | `perfil.crescimento` = True E `exig.ell_mantenca` existe | calcular `exig.ell_crescimento` = ell_crescimento(…) | 0.9 | D | NRC 1989 (+20% de mantença na 1ª lactação) |
| EXG-02E | Energia de atividade de pastejo por peso, distância e relevo | `perfil.atividade_pastejo` = True | calcular `exig.ell_atividade` = ell_atividade(…) | 0.8 | B | NRC 2001 via eOrganic (reproduz valores tabelados) |
| EXG-06A | ECC abaixo do mínimo no meio da lactação — somar energia para recuperar | `perfil.fase` = meio E `lote.ecc` < @params.ecc_min_meio | calcular `exig.ell_ecc` = ell_ajuste_ecc(…) | 0.8 | B | Penn State (417 Mcal por ponto de ECC) |
| EXG-06B | ECC abaixo do mínimo no final da lactação — somar energia para recuperar antes da secagem | `perfil.fase` = final E `lote.ecc` < @params.ecc_min_final | calcular `exig.ell_ecc` = ell_ajuste_ecc(…) | 0.8 | B | Penn State |
| EXG-06C | ECC abaixo do mínimo no início da lactação — somar energia para recuperar | `perfil.fase` in ['recem_parida', 'inicio'] E `lote.ecc` < @params.ecc_min_inicio | calcular `exig.ell_ecc` = ell_ajuste_ecc(…) | 0.8 | B | Penn State |
| EXG-07 | Início de lactação com ECC adequado pode mobilizar reserva — tolerar oferta de energia um pouco menor | `perfil.fase` in ['recem_parida', 'inicio'] E `lote.ecc` >= @params.ecc_min_inicio | concluir `meta.fator_energia_min` = @params.fator_energia_mobilizacao | 0.8 | B | Penn State; USC |
| EXG-02Z | Exigência total de ELl = mantença + leite + gestação + crescimento + atividade ± ECC | `exig.ell_mantenca` existe | calcular `exig.ell_total` = soma(…) | 1.0 | B | NRC 2001 |
| EXG-PB1 | PB alvo por produção — Holandês/Jersey | `perfil.equacao_cms` = nrc2001 | calcular `exig.pb_pct_alvo` = pb_alvo(…); calcular `exig.pm_leite` = pm_leite(…) | 1.0 | B | MSD Vet Manual; NRC 2001 |
| EXG-PB2 | PB alvo por produção — zebuínos e cruzados | `perfil.equacao_cms` = brleite | calcular `exig.pb_pct_alvo` = pb_alvo(…); calcular `exig.pm_leite` = pm_leite(…) | 1.0 | B | MSD Vet Manual (raças pequenas) |
| EXG-PB3 | PB alvo no pré-parto | `perfil.fase` = pre_parto | concluir `exig.pb_pct_alvo` = @params.pb_preparto | 1.0 | C | Dossiê (pré-parto 13–15% PB) |
| EXG-PB4 | PB alvo para vacas secas | `perfil.fase` = seca | concluir `exig.pb_pct_alvo` = @params.pb_seca | 1.0 | D | Prática de campo |
| EXG-04 | Metas fixas de fibra de forragem, gordura e ureia da dieta | `perfil.fase` existe | concluir `meta.fdnf_min` = @params.fdnf_min; concluir `meta.ee_max` = @params.ee_max; concluir `meta.ureia_max` = @params.ureia_max | 1.0 | B | NRC 2001; Cultivar; Semadesc-MS |
| EXG-04B | Sem dieta informada, metas de FDN e CNF ficam no valor base | `perfil.fase` existe E `dieta.fdnf_pct` ausente | concluir `meta.fdn_min` = @params.fdn_min; concluir `meta.cnf_max` = @params.cnf_max | 1.0 | B | NRC 2001 |
| EXG-05 | Cada ponto de FDNf abaixo de 19% sobe o FDN mínimo em 2 e baixa o CNF máximo em 2 | `dieta.fdnf_pct` existe E `perfil.fase` existe | calcular `meta` = metas_fibra(…) | 1.0 | B | NRC 2001 via CompreRural |
| EXG-09 | Calcular CMS como % do PV para checagem de plausibilidade | `exig.cms` existe E `lote.estado` = lactacao | calcular `perfil.cms_pct_pv` = cms_pct_pv(…) | 1.0 | C | Dossiê (CMS de lactação entre 2,5 e 4% do PV) |

## F — Formulação por programação linear (FOR)

| ID | Descrição | SE | ENTÃO | CF | Força | Fonte |
|---|---|---|---|---|---|---|
| FOR-01 | Faixa de matéria seca total do PL (CMS ± 5%) | `formulacao.solicitada` = True E `exig.cms` existe | calcular `pl.folga_ms` = produto(…) | 1.0 | D | Inferências (CMS ± 5%) |
| FOR-02 | Energia mínima do PL = exigência × fator de tolerância | `formulacao.solicitada` = True E `exig.ell_total` existe | calcular `pl.ell_min` = produto(…) | 1.0 | D | Dossiê VER-01 |
| FOR-03 | Faixa de PB do PL = alvo até alvo + folga | `formulacao.solicitada` = True E `exig.pb_pct_alvo` existe | concluir `pl.pb_min` = $exig.pb_pct_alvo; calcular `pl.pb_max` = soma(…) | 1.0 | D | MSD Vet Manual |
| FOR-04 | Teto de consumo de FDN (kg/dia) = 1,25% do PV | `formulacao.solicitada` = True E `lote.pv` existe | calcular `pl.fdn_max_kg` = pct_de(…) | 1.0 | B | Mertens via Epagri |
| FOR-05 | Lote acima de 15 kg/vaca não pode ter cana como único volumoso — limitar a cana no PL | `formulacao.solicitada` = True E `lote.leite` > @params.leite_max_cana | concluir `pl.cana_max_pct_volumoso` = @params.cana_max_pct_volumoso | 1.0 | C | Semadesc-MS (mesma base da VER-07) |
| FOR-06 | Lote confinado não pasteja — excluir forragens de pastejo do PL | `formulacao.solicitada` = True E `lote.sistema` = confinado | concluir `pl.excluir_pastejo` = True | 1.0 | A | Definição do sistema de produção |
| FOR-10 | PL inviável por energia — faltam alimentos energéticos | `pl.status` = inviavel E `pl.restricoes_violadas` contem energia | alerta **critico** (formulacao): Energia não atingível com os alimentos escolhidos | 1.0 | D | Dossiê (diagnóstico de inviabilidade) |
| FOR-11 | PL inviável por proteína | `pl.status` = inviavel E `pl.restricoes_violadas` contem proteina | alerta **critico** (formulacao): Proteína fora da faixa com os alimentos escolhidos | 1.0 | D | Dossiê (diagnóstico de inviabilidade) |
| FOR-12 | PL inviável por fibra mínima | `pl.status` = inviavel E `pl.restricoes_violadas` contem fibra | alerta **critico** (formulacao): Fibra mínima não atingível | 1.0 | D | NRC 2001 |
| FOR-13 | PL inviável por enchimento (FDN demais para o consumo) | `pl.status` = inviavel E `pl.restricoes_violadas` contem enchimento | alerta **critico** (formulacao): Volumoso muito fibroso limita o consumo | 1.0 | B | Mertens via Epagri |
| FOR-14 | PL inviável por CNF ou gordura máximos | `pl.status` = inviavel E (`pl.restricoes_violadas` contem cnf OU `pl.restricoes_violadas` contem gordura) | alerta **critico** (formulacao): Limites de CNF ou gordura impedem a solução | 1.0 | D | NRC 2001 |
| FOR-15 | PL inviável porque falta volumoso além da cana | `pl.status` = inviavel E `pl.restricoes_violadas` contem cana | alerta **critico** (formulacao): Falta volumoso além da cana para esta produção | 1.0 | C | Semadesc-MS |
| FOR-20 | PL encontrou a dieta de menor custo | `pl.status` = otimo | alerta **informativo** (formulacao): Dieta de custo mínimo: R$ {pl.custo:.2f}/vaca/dia | 1.0 | B | Programação linear (PuLP + HiGHS) |

## C — Verificação da dieta (VER)

| ID | Descrição | SE | ENTÃO | CF | Força | Fonte |
|---|---|---|---|---|---|---|
| VER-00A | Energia efetivamente consumida (a vaca não come mais que o CMS previsto) | `dieta.ms_kg` > 0 E `exig.cms` existe | calcular `ver.ell_consumida` = energia_consumida(…); calcular `ver.razao_ms` = razao(…) | 1.0 | B | NRC 2001 |
| VER-00B | Razão entre energia consumida e exigida | `ver.ell_consumida` existe E `exig.ell_total` existe | calcular `ver.razao_energia` = razao(…) | 1.0 | B | NRC 2001 |
| VER-00C | Razão entre PB da dieta e PB alvo | `dieta.pb_pct` existe E `exig.pb_pct_alvo` existe | calcular `ver.razao_pb` = razao(…) | 1.0 | B | MSD Vet Manual |
| VER-01 | Energia consumida abaixo da exigência — déficit energético | `ver.razao_energia` < $meta.fator_energia_min\|@params.fator_energia_min | concluir `ver.deficit_energetico` = True; alerta **atencao** (dieta): Déficit energético: a dieta cobre {ver.razao_energia:.0%} da exigência | 0.9 | B | Dossiê VER-01; NRC 2001 |
| VER-02 | PB da dieta abaixo do alvo — déficit proteico | `ver.razao_pb` < @params.fator_pb_min | concluir `ver.deficit_proteico` = True; alerta **atencao** (dieta): Déficit proteico: PB {dieta.pb_pct:.1f}% contra alvo de {exig.pb_pct_alvo:.1f}% | 0.85 | B | Dossiê VER-02; MSD Vet Manual |
| VER-02B | PB muito acima do alvo — desperdício de proteína | `ver.razao_pb` > @params.fator_pb_max | alerta **informativo** (economia): Proteína acima do necessário ({dieta.pb_pct:.1f}% contra {exig.pb_pct_alvo:.1f}%) | 0.7 | C | Penn State (NUL) |
| VER-03 | FDN da dieta abaixo da meta — risco de acidose ruminal | `dieta.fdn_pct` < $meta.fdn_min | concluir `ver.risco_acidose` = True | 0.85 | B | NRC 2001 (FDN ≥ 25% MS) |
| VER-03B | CNF acima do máximo — risco de acidose ruminal | `dieta.cnf_pct` > $meta.cnf_max | concluir `ver.risco_acidose` = True | 0.8 | B | NRC 2001 (CNF ≤ 44% MS) |
| VER-03C | FDN de forragem abaixo de 19% — pouca fibra efetiva | `dieta.fdnf_pct` < $meta.fdnf_min | concluir `ver.risco_acidose` = True | 0.7 | B | NRC 2001 (FDNf ≥ 19% MS) |
| VER-03Z | Emitir alerta de acidose com o CF combinado das evidências | `ver.risco_acidose` = True | alerta **atencao** (dieta): Risco de acidose ruminal | 1.0 | B | NRC 2001 |
| VER-04 | Ureia acima de 1% da MS — dieta bloqueada | `dieta.ureia_pct` > $meta.ureia_max | concluir `parecer.bloqueio` = True; alerta **critico** (dieta): Ureia acima do limite: {dieta.ureia_pct:.2f}% da MS (máx. {meta.ureia_max}%) | 1.0 | B | Semadesc-MS |
| VER-05 | Gordura da dieta acima de 6% da MS | `dieta.ee_pct` > $meta.ee_max | concluir `ver.excesso_gordura` = True; alerta **atencao** (dieta): Gordura excessiva: EE {dieta.ee_pct:.1f}% da MS | 0.8 | C | Cultivar |
| VER-06 | MS ofertada muito acima do CMS previsto — dieta não será consumida | `ver.razao_ms` > @params.fator_oferta_max | concluir `ver.oferta_excessiva` = True; alerta **atencao** (dieta): Oferta acima do consumo previsto ({dieta.ms_kg:.1f} kg MS contra {exig.cms:.1f}) | 0.7 | D | Dossiê VER-06 |
| VER-06B | MS ofertada abaixo do CMS possível — subalimentação | `ver.razao_ms` < @params.fator_oferta_min | concluir `ver.subalimentacao` = True; alerta **atencao** (dieta): Oferta abaixo do consumo possível ({dieta.ms_kg:.1f} kg MS contra {exig.cms:.1f}) | 0.7 | D | Escolha de engenharia |
| VER-07 | Cana como único volumoso limita lotes de produção mais alta | `dieta.cana_unico_volumoso` = True E `lote.leite` > @params.leite_max_cana | concluir `ver.volumoso_limitante` = True; alerta **atencao** (dieta): Cana como único volumoso para {lote.leite:.0f} kg/vaca | 0.7 | C | Semadesc-MS |
| VER-09 | CMS fora de 2,5–4% do PV — conferir dados de entrada | (`perfil.cms_pct_pv` < @params.cms_pct_pv_min OU `perfil.cms_pct_pv` > @params.cms_pct_pv_max) | alerta **informativo** (dados): Consumo previsto incomum ({perfil.cms_pct_pv:.1f}% do PV) | 0.8 | C | Dossiê |
| VER-90 | Parecer — dieta bloqueada | `parecer.bloqueio` = True | concluir `parecer.dieta` = bloqueada | 1.0 | B | Dossiê VER-04 |
| VER-91 | Parecer — dieta precisa de ajustes | `parecer.bloqueio` ausente E (`ver.deficit_energetico` existe OU `ver.deficit_proteico` existe OU `ver.risco_acidose` existe OU `ver.excesso_gordura` existe OU `ver.oferta_excessiva` existe OU `ver.subalimentacao` existe OU `ver.volumoso_limitante` existe) | concluir `parecer.dieta` = ajustar | 1.0 | C | Dossiê VER-08 |
| VER-08 | Parecer — dieta adequada (nenhuma regra crítica disparou) | `dieta.ms_kg` > 0 E `ver.razao_energia` existe E `parecer.dieta` ausente | concluir `parecer.dieta` = adequada | 1.0 | C | Dossiê VER-08 |

## D1 — Acompanhamento diário (ACP)

| ID | Descrição | SE | ENTÃO | CF | Força | Fonte |
|---|---|---|---|---|---|---|
| ACP-D00 | Dia sem registro gera lembrete, nunca alerta zootécnico | `mon.sem_registro_hoje` = True | alerta **informativo** (registro): Sem registro de hoje | 1.0 | D | de Mol et al. 2012 (dado faltante não é alerta) |
| ACP-D01 | Queda brusca de um dia (resíduo abaixo de −3σ) sem queda sustentada em curso | `mon.z` < @params.shewhart_z E `hipotese.queda_sustentada` ausente | alerta **atencao** (producao): Queda brusca hoje: {mon.litros_vaca:.1f} L/vaca contra {mon.esperado_vaca:.1f} esperados | 0.7 | D | SPC (Shewhart) sobre resíduo padronizado |
| ACP-D02 | Corrida de dias abaixo do esperado com ao menos um dia abaixo de −10% | `mon.corrida_dias` >= @params.corrida_dias_min E `mon.corrida_pior` <= @params.corrida_queda_min E `mon.residuo` < @params.residuo_queda_atual | concluir `hipotese.queda_sustentada` = True | 0.8 | B | Frontiers in Genetics 2022 (perturbação de lactação) |
| ACP-D03 | EWMA do resíduo abaixo do limite inferior (queda sustentada de 3–5%) | `mon.ewma` < $mon.ewma_limite_inf E `mon.residuo` < @params.residuo_queda_atual | concluir `hipotese.queda_sustentada` = True | 0.6 | C | Archiv Tierzucht 2009; SPC |
| ACP-D03B | Queda de mais de 10% em 7 dias | `mon.queda_7d` <= @params.queda_7d | concluir `hipotese.queda_sustentada` = True | 0.6 | C | Dossiê ACP-08/ACP-10 |
| ACP-D04 | Alerta de queda sustentada de produção (CF combinado das evidências) | `hipotese.queda_sustentada` = True | alerta **critico** (producao): Queda sustentada de produção: {mon.litros_vaca:.1f} L/vaca ({mon.residuo:.0%} do esperado) | 1.0 | B | Frontiers in Genetics 2022; de Mol 2012 (persistência) |
| ACP-08 | Queda logo após troca de volumoso — causa provável é o novo volumoso | `hipotese.queda_sustentada` = True E `mon.dias_desde_troca_volumoso` <= @params.janela_troca_volumoso | concluir `hipotese.causa_volumoso` = True; alerta **atencao** (dieta_queda): Causa provável da queda: troca de volumoso há {mon.dias_desde_troca_volumoso} dia(s) | 0.6 | C | Dossiê ACP-08; Inferências (assinatura de troca de silagem) |
| ACP-10 | Queda de produção com ITU alto nos 2 dias anteriores — causa provável é calor, não a dieta | (`hipotese.queda_sustentada` = True OU `mon.queda_7d` <= @params.queda_7d) E `mon.itu_2d` > $mon.itu_limiar E (`mon.dias_desde_troca_volumoso` ausente OU `mon.dias_desde_troca_volumoso` > @params.janela_troca_volumoso) E `hipotese.mastite` ausente | concluir `hipotese.causa_calor` = True; alerta **atencao** (calor): Calor explica a queda (ITU médio de 2 dias = {mon.itu_2d:.1f}) | 0.6 | B | Dossiê ACP-10; Negri 2021; LUME UFRGS |
| ACP-D05 | Menos de 2 litros por kg de concentrado | `mon.litros_por_kg_conc` < @params.litros_por_kg_conc_min | alerta **atencao** (economia): Baixa eficiência do concentrado: {mon.litros_por_kg_conc:.1f} L/kg | 0.6 | D | Inferências (C/D) |
| ACP-D06 | Resposta ao último aumento de concentrado não paga o custo | `mon.resposta_marginal` existe E `mon.resposta_marginal` < $mon.razao_precos | alerta **atencao** (economia): Concentrado extra não se paga: {mon.resposta_marginal:+.2f} L por kg | 0.8 | B | de Abreu, Lana et al. 2013 (resposta marginal 0,15–0,97 kg/kg) |
| ACP-D07 | Custo de concentrado por litro acima da mediana de 30 dias | `mon.custo_conc_litro` existe E `mon.custo_conc_litro_ref` existe E `mon.custo_conc_razao` > @params.custo_conc_litro_tolerancia | alerta **informativo** (economia): Custo de concentrado subiu: R$ {mon.custo_conc_litro:.2f}/L (ref. R$ {mon.custo_conc_litro_ref:.2f}) | 0.6 | D | Penn State (IOFC); Inferências |

## D3 — Acompanhamento mensal / laudo (ACP)

| ID | Descrição | SE | ENTÃO | CF | Força | Fonte |
|---|---|---|---|---|---|---|
| ACP-M00 | Laudo em ureia — converter para NUL (× 0,4667) | `laudo.ureia` existe E `laudo.nul` ausente | calcular `laudo.nul` = ureia_para_nul(…) | 1.0 | B | Magalhães, UFV 2003 |
| ACP-M01 | Calcular a relação gordura:proteína do leite | `laudo.gordura` existe E `laudo.proteina` existe | calcular `laudo.gp` = razao(…) | 1.0 | B | Penn State |
| ACP-01 | NUL alto — excesso de proteína ou falta de energia fermentável | `laudo.nul` > @params.nul_max | alerta **atencao** (dieta): NUL alto: {laudo.nul:.1f} mg/dL | 0.7 | B | Penn State; Embrapa Pedroso 2011 |
| ACP-01R | NUL acima de ~19,5 mg/dL reduz a chance de prenhez | `laudo.nul` >= @params.nul_reprodutivo | alerta **critico** (reproducao): NUL {laudo.nul:.1f} mg/dL: risco reprodutivo | 0.9 | A | Raboisson et al. 2017 (meta-análise) |
| ACP-02 | NUL baixo junto com produção abaixo do esperado — proteína possivelmente insuficiente | `laudo.nul` < @params.nul_min E (`hipotese.queda_sustentada` = True OU `mon.residuo` < -0.05) | alerta **atencao** (dieta_queda): NUL baixo ({laudo.nul:.1f} mg/dL) com produção abaixo do esperado | 0.6 | B | Magalhães UFV 2003; Meyer et al. 2006 (alvo único de NUL não vale) |
| ACP-03 | G:P abaixo de 1,0 — suspeita de acidose subaguda | `laudo.gp` < @params.gp_sara_max | concluir `hipotese.acidose` = True | 0.7 | C | Dossiê ACP-03; UNH 2025 |
| ACP-04 | G:P baixa com fezes fluidas reforça a suspeita de acidose | `laudo.gp` < @params.gp_sara_max E `mon.fezes` <= @params.fezes_acidose_max | concluir `hipotese.acidose` = True | 0.6 | C | Dossiê ACP-04 |
| ACP-ACID | Alerta de acidose subaguda com o CF combinado das evidências | `hipotese.acidose` = True | alerta **atencao** (dieta): Suspeita de acidose ruminal subaguda | 1.0 | C | Dossiê; MYCIN (combinação de CFs) |
| ACP-M03 | G:P acima de 1,4 em recém-paridas — balanço energético negativo / cetose subclínica | `perfil.fase` in ['recem_parida', 'inicio'] E `lote.del` <= 40 E `laudo.gp` > @params.gp_ben_min | alerta **atencao** (dieta): G:P {laudo.gp:.2f} em recém-paridas: risco de cetose subclínica | 0.7 | B | Penn State (cetose subclínica) |
| ACP-M04 | Queda de gordura com proteína estável — depressão da gordura do leite | `laudo.gordura_delta` <= @params.gordura_queda_pp E `laudo.proteina_delta_abs` < @params.proteina_estavel_pp | concluir `hipotese.dgl` = True; alerta **atencao** (dieta): Gordura do leite caiu {laudo.gordura_delta:.2f} p.p. com proteína estável | 0.7 | C | eXtension (gordura do leite) |
| ACP-M05 | Lactose baixa com CCS subindo — mastite primeiro, não dieta | `laudo.lactose` < @params.lactose_min E (`laudo.ccs_tendencia` = subindo OU `laudo.ccs` > @params.ccs_pre_regulatorio) | concluir `hipotese.mastite` = True; alerta **critico** (qualidade): Mastite primeiro: lactose {laudo.lactose:.2f}% com CCS subindo | 0.8 | A | IN 76/2018; Inferências |
| ACP-M06 | CCS do tanque acima do limite regulatório (média geométrica de 3 meses) | `laudo.ccs_mg3` > @params.ccs_regulatorio | calcular `mon.perda_ccs` = perda_ccs(…); alerta **critico** (qualidade): CCS {laudo.ccs_mg3:.0f} mil acima do limite da IN 76 (500 mil) | 1.0 | A | IN 76/2018; eXtension (perdas por CCS) |
| ACP-M06B | CCS do tanque em faixa pré-regulatória | `laudo.ccs_mg3` > @params.ccs_pre_regulatorio E `laudo.ccs_mg3` <= @params.ccs_regulatorio | alerta **atencao** (qualidade): CCS {laudo.ccs_mg3:.0f} mil: perto do limite regulatório | 0.8 | A | IN 76/2018 |
| ACP-M07 | CBT acima do limite — higiene e resfriamento, não dieta | `laudo.cbt_mg3` > @params.cbt_regulatorio | alerta **critico** (qualidade): CBT {laudo.cbt_mg3:.0f} mil UFC/mL acima do limite (300 mil) | 1.0 | A | IN 76/2018 |
| ACP-M05B | Queda de produção com mastite em curso — causa provável é a mastite | `hipotese.queda_sustentada` = True E `hipotese.mastite` = True | alerta **atencao** (qualidade): Causa provável da queda: mastite | 0.7 | C | Inferências (assinatura de surto de mastite) |

## D2 — Acompanhamento semanal (ACP)

| ID | Descrição | SE | ENTÃO | CF | Força | Fonte |
|---|---|---|---|---|---|---|
| ACP-S01 | MS da silagem mudou 2 p.p. ou mais (confirmado) — recalcular kg de matéria natural | `mon.ms_delta_abs` >= @params.ms_delta_recalcular E `mon.ms_leituras_confirmadas` >= 2 | calcular `mon.silagem_kg_mn_novo` = ms_para_mn(…); alerta **atencao** (dieta): MS da silagem mudou: {mon.ms_silagem_formulacao:.1f}% → {mon.ms_silagem_atual:.1f}% | 0.8 | C | Penn State (determinação de MS); heurística de 2 p.p. |
| ACP-S02 | MS mudou 5 p.p. ou mais, ou silo novo — reformular e pedir bromatologia | (`mon.ms_delta_abs` >= @params.ms_delta_reformular OU `mon.silo_novo` = True) | alerta **atencao** (dieta): Volumoso mudou muito: reformular a dieta | 0.8 | B | OSU Buckeye Dairy News |
| ACP-S03A | Faixa-alvo de sobras para a fase do lote | `perfil.fase` existe E `mon.sobras_mm3` existe | calcular `meta.sobras` = faixa(…) | 1.0 | B | eXtension (feed bunk management) |
| ACP-S03 | Sobras (média de 3 dias) abaixo da faixa — aumentar oferta | `mon.sobras_mm3` < $meta.sobras.min | alerta **atencao** (cocho): Sobras baixas: {mon.sobras_mm3:.1f}% (meta {meta.sobras.min:.0f}–{meta.sobras.max:.0f}%) | 0.7 | B | eXtension; SDSU |
| ACP-S04 | Sobras (média de 3 dias) acima da faixa — reduzir oferta ou investigar seleção | `mon.sobras_mm3` > $meta.sobras.max | alerta **atencao** (cocho): Sobras altas: {mon.sobras_mm3:.1f}% (meta {meta.sobras.min:.0f}–{meta.sobras.max:.0f}%) | 0.7 | B | eXtension; SDSU; Dossiê ACP-07 |
| ACP-06 | Cocho vazio por 2+ leituras em lote de alta ou recém-paridas | `mon.dias_cocho_vazio` >= @params.cocho_vazio_dias E `perfil.fase` in ['recem_parida', 'inicio'] | alerta **critico** (cocho): Cocho vazio há {mon.dias_cocho_vazio} leituras | 0.8 | C | Dossiê ACP-06; DeVries 2023 |
| ACP-06B | Cocho vazio por 2+ leituras nos demais lotes | `mon.dias_cocho_vazio` >= @params.cocho_vazio_dias E `perfil.fase` nao_in ['recem_parida', 'inicio'] | alerta **atencao** (cocho): Cocho vazio há {mon.dias_cocho_vazio} leituras | 0.7 | C | Dossiê ACP-06 |
| ACP-05 | Perda de mais de 1 ponto de ECC no início da lactação — balanço energético negativo severo | `perfil.fase` in ['recem_parida', 'inicio'] E `mon.ecc_perda` > @params.ecc_perda_severa | concluir `hipotese.ben_severo` = True; alerta **critico** (dieta): Balanço energético negativo severo: perdeu {mon.ecc_perda:.2f} ponto(s) de ECC | 0.8 | B | Dossiê ACP-05; Carvalho et al. 2014 |
| ACP-09 | Perda de ECC acima de 0,5 ponto | `mon.ecc_perda` > @params.ecc_perda_atencao E `hipotese.ben_severo` ausente | alerta **atencao** (dieta): Lote perdendo condição corporal ({mon.ecc_perda:.2f} ponto) | 0.7 | B | OMAFRA |
| ACP-S05 | Ruminação média do lote caiu — falta de fibra efetiva, troca de dieta ou calor | `mon.ruminacao_queda` >= @params.ruminacao_queda | concluir `hipotese.acidose` = True | 0.5 | C | Paudyal 2018 (queda coletiva = causa coletiva) |

## M — Meta-regras (resolução de conflito)

| ID | Descrição | SE | ENTÃO | CF | Força | Fonte |
|---|---|---|---|---|---|---|
| META-01 | Mastite primeiro — suprime recomendações de dieta | `hipotese.mastite` = True | suprimir alertas de dieta, dieta_queda | 1.0 | C | Inferências (lactose/ESD baixos com CCS = mastite primeiro) |
| META-02 | Calor explica — rebaixa a informativos os alertas de dieta motivados pela queda | `hipotese.causa_calor` = True | rebaixar alertas de dieta_queda | 1.0 | B | Dossiê ACP-10 |
| META-03 | Reagrupamento recente — suprime alertas de queda de produção por 48 h | `mon.horas_desde_movimentacao` <= @params.janela_supressao_h | suprimir alertas de producao | 1.0 | B | UBC/Farmwest |
| META-04 | Correção recente da MS — suprime alertas de queda de produção por 48 h | `mon.horas_desde_correcao_ms` <= @params.janela_supressao_h | suprimir alertas de producao | 1.0 | D | Inferências |

## Parâmetros

| Parâmetro | Valor | Unidade | Força | Fonte | Descrição |
|---|---|---|---|---|---|
| `cf_medido_recente` | 1.0 | CF | D | Convenção do sistema | Medição recente na fazenda |
| `cf_medido_30d` | 0.8 | CF | D | Convenção do sistema | Medição com menos de 30 dias |
| `cf_tabela` | 0.8 | CF | D | Convenção do sistema | Valor de tabela publicada (Embrapa/CQBAL) |
| `cf_padrao` | 0.6 | CF | D | Convenção do sistema | Valor padrão quando o usuário não sabe |
| `del_recem_parida_max` | 21 | dias | C | Dossiê CLS-01 | Fim da fase recém-parida |
| `del_inicio_max` | 100 | dias | C | Dossiê CLS-02 | Fim do início/pico de lactação |
| `del_meio_max` | 200 | dias | C | Dossiê CLS-03 | Fim do meio de lactação |
| `preparto_dias` | 21 | dias | B | Dossiê CLS-05; Santos 2019 | Dias antes do parto que definem o pré-parto |
| `gestacao_dias_exigencia` | 190 | dias | B | NRC 2001 via AgModel | A partir daqui soma exigência de gestação |
| `itu_alerta` | 72 | ITU | B | Embrapa COT42 | Início do estresse térmico |
| `itu_forte` | 78 | ITU | B | Embrapa COT42 | Estresse acima do brando |
| `grupos_zebuinos` | ['girolando', 'gir', 'mestica'] | lista | B | BR-Leite 2024 | Grupos que usam equação BR-Leite |
| `k_mantenca` | 0.08 | Mcal/kg PV^0,75 | B | NRC 2001 (NASEM 2021 usa 0,10) | Coeficiente de mantença — flag 0,08 ou 0,10 |
| `peso_bezerro_kg` | 44 | kg | B | Calibrado na tabela NRC 2001 (Drackley 2021) | Peso do bezerro ao nascer para exigência de gestação |
| `acrescimo_primiparas` | 0.2 | fração | D | NRC 1989 (+20% de mantença na 1ª lactação) | Acréscimo de crescimento das primíparas |
| `teto_fdn_pct_pv` | 1.25 | % PV | B | Mertens via Epagri | Consumo máximo de FDN (enchimento) |
| `cms_preparto_pct_pv` | 1.9 | % PV | B | NASEM 2021 via Drackley (1,8–2%) | CMS de vacas secas/pré-parto |
| `cms_pct_pv_min` | 2.5 | % PV | C | Dossiê (checagem de sanidade) | CMS de lactação abaixo disso: conferir dados |
| `cms_pct_pv_max` | 4.0 | % PV | C | Dossiê (checagem de sanidade) | CMS de lactação acima disso: conferir dados |
| `mcal_por_ponto_ecc` | 417 | Mcal | B | Penn State | ELl por ponto de ECC (vaca ~650 kg) |
| `dias_recuperacao_ecc` | 100 | dias | D | Dossiê T17 | Prazo para levar o ECC à meta |
| `ecc_min_inicio` | 2.5 | 1-5 | B | USC; Embrapa/IFRO (pico 2,5–3,0) | ECC mínimo no início/pico |
| `ecc_meta_inicio` | 2.75 | 1-5 | B | USC; Embrapa/IFRO | ECC alvo no início/pico |
| `ecc_min_meio` | 2.75 | 1-5 | B | USC (meio 2,75–3,25) | ECC mínimo no meio da lactação |
| `ecc_meta_meio` | 3.0 | 1-5 | B | USC | ECC alvo no meio da lactação |
| `ecc_min_final` | 3.0 | 1-5 | B | USC (final 3,0–3,75) | ECC mínimo no final da lactação |
| `ecc_meta_final` | 3.25 | 1-5 | B | USC | ECC alvo no final da lactação |
| `eficiencia_pm` | 0.67 | fração | C | NRC 2001 via AgModel (⚠ NV) | Eficiência PM → proteína do leite |
| `pb_tabela_holandes` | [[10, 13.0], [27, 14.5], [55, 18.3]] | kg leite → % PB | B | MSD Vet Manual (ponto 10 kg: D) | PB alvo por produção — Holandês/Jersey |
| `pb_tabela_mestico` | [[8, 12.0], [18, 15.0], [36, 19.0]] | kg leite → % PB | B | MSD Vet Manual raças pequenas (ponto 8 kg: D) | PB alvo por produção — mestiças/zebuínas |
| `pb_preparto` | 14.0 | % MS | C | Dossiê (pré-parto 13–15%) | PB alvo pré-parto |
| `pb_seca` | 12.0 | % MS | D | Prática de campo | PB alvo vacas secas |
| `fdn_min` | 25 | % MS | B | NRC 2001 | FDN mínimo da dieta |
| `fdnf_min` | 19 | % MS | B | NRC 2001 | FDN de forragem mínimo |
| `cnf_max` | 44 | % MS | B | NRC 2001 | CNF máximo |
| `passo_fibra` | 2 | p.p. por p.p. | B | NRC 2001 via CompreRural | Ajuste de FDN/CNF por ponto de FDNf abaixo do mínimo |
| `ee_max` | 6 | % MS | C | Cultivar | Gordura máxima da dieta |
| `ureia_max` | 1.0 | % MS | B | Semadesc-MS | Ureia máxima da dieta (bloqueante) |
| `fator_energia_min` | 0.95 | fração | D | Dossiê VER-01 | Oferta mínima de ELl / exigência |
| `fator_energia_mobilizacao` | 0.9 | fração | D | Dossiê EXG-07; Penn State | Tolerância quando o lote pode mobilizar reserva |
| `fator_pb_min` | 0.95 | fração | D | Dossiê VER-02 | PB mínima / alvo |
| `fator_pb_max` | 1.15 | fração | D | Escolha de engenharia | PB acima disso = desperdício |
| `fator_oferta_max` | 1.05 | fração | D | Dossiê VER-06 | MS ofertada / CMS previsto acima disso não será consumida |
| `fator_oferta_min` | 0.9 | fração | D | Escolha de engenharia | MS ofertada / CMS abaixo disso = subalimentação |
| `cana_max_pct_volumoso` | 50 | % da MS de volumoso | D | Escolha de engenharia derivada de VER-07 (Semadesc-MS) | Teto de cana no volumoso do PL quando o lote produz acima de leite_max_cana |
| `leite_max_cana` | 15 | kg | C | Dossiê VER-07 (a validar) | Produção acima disso com cana como único volumoso |
| `pl_folga_cms` | 0.05 | fração | D | Inferências (CMS ± 5%) | Folga do total de MS no PL |
| `pl_pb_folga_max` | 3.0 | p.p. | D | Escolha de engenharia | PB máxima = alvo + folga |
| `shewhart_z` | -3.0 | sigma | D | SPC padrão | Queda de um dia |
| `corrida_dias_min` | 5 | dias | B | Frontiers Genet 2022 (adaptado ao lote) | Dias seguidos abaixo do esperado |
| `residuo_queda_atual` | -0.03 | fração | D | Escolha de engenharia (evita alerta com o lote já recuperado) | Resíduo de hoje precisa estar abaixo disso para manter a queda sustentada |
| `corrida_queda_min` | -0.1 | fração | B | Frontiers Genet 2022 | Ao menos um dia abaixo de −10% |
| `ewma_lambda` | 0.25 |  | C | Archiv Tierzucht 2009 (⚠ NV) | Suavização do EWMA |
| `ewma_L` | 2.75 | sigma | C | Archiv Tierzucht 2009 (⚠ NV) | Largura do limite do EWMA |
| `itu_limiar_holandes` | 72 | ITU | B | Negri 2021 (72–74) | Limiar de perda de leite — Holandês/Jersey |
| `itu_limiar_zebuino` | 76 | ITU | C | LUME UFRGS (sem limiar claro em Girolando) | Limiar de perda de leite — Girolando/mestiças |
| `perda_itu_holandes` | 0.2 | kg/unidade ITU | C | Ravagnolo 2000 (⚠ NV) | Perda de leite por unidade de ITU acima do limiar |
| `perda_itu_zebuino` | 0.04 | kg/unidade ITU | B | LUME UFRGS | Perda de leite por unidade de ITU — Girolando |
| `queda_7d` | -0.1 | fração | C | Dossiê ACP-08/ACP-10 | Queda de leite em 7 dias |
| `janela_troca_volumoso` | 7 | dias | C | Inferências (degrau 1–3 d após troca) | Janela para atribuir queda à troca de volumoso |
| `janela_supressao_h` | 48 | horas | B | UBC/Farmwest (−8,5% por 1–2 d) | Supressão de alertas após movimentação/correção de MS |
| `litros_por_kg_conc_min` | 2.0 | L/kg | D | Inferências (C/D) | Eficiência mínima do concentrado |
| `custo_conc_litro_tolerancia` | 1.1 | fração | D | Inferências (mediana 30 d + 10%) | Custo de concentrado/L acima da mediana |
| `ms_delta_recalcular` | 2.0 | p.p. | C | Heurística de campo (C) | Mudança de MS que exige recalcular kg MN |
| `ms_delta_reformular` | 5.0 | p.p. | B | OSU Buckeye Dairy News | Mudança de MS que exige reformular |
| `sobras_faixas` | {'recem_parida': [3, 5], 'inicio': [2, 4], 'meio': [2, 4], 'final': [1, 3], 'pre_parto': [2, 4], 'seca': [1, 3]} | % oferta | B | eXtension; SDSU | Faixa-alvo de sobras por fase |
| `cocho_vazio_dias` | 2 | dias | C | Dossiê ACP-06 | Leituras seguidas com cocho vazio |
| `ecc_perda_severa` | 1.0 | pontos | B | Dossiê ACP-05 (5 semanas) | Perda de ECC = BEN severo |
| `ecc_perda_atencao` | 0.5 | pontos | B | OMAFRA (0,5–0,75) | Perda de ECC que merece atenção |
| `fezes_acidose_max` | 2 | 1-5 | C | Dossiê ACP-04 | Fezes fluidas reforçam suspeita de acidose |
| `ruminacao_queda` | 30 | min/d | D | Coerente com HIS, não validado | Queda da ruminação média do lote |
| `nul_min` | 8 | mg/dL | B | Embrapa Pedroso 2011 (8–16) | NUL baixo (só alerta se produção/proteína também baixas) |
| `nul_max` | 16 | mg/dL | B | Embrapa (8–16); Penn State (10–14); conflito | NUL alto: excesso de PB ou falta de energia |
| `nul_reprodutivo` | 19.5 | mg/dL | A | Raboisson 2017 (meta-análise) | NUL com chance de prenhez −43% |
| `gp_sara_max` | 1.0 | razão | C | Dossiê ACP-03; UNH 2025 | G:P abaixo disso sugere acidose |
| `gp_ben_min` | 1.4 | razão | B | Penn State (≤40 DEL) | G:P acima disso em recém-paridas sugere BEN/cetose |
| `gordura_queda_pp` | -0.3 | p.p. | C | eXtension (0,2–0,3) | Queda de gordura vs linha de base |
| `proteina_estavel_pp` | 0.1 | p.p. | D | Escolha de engenharia | Variação de proteína considerada estável |
| `lactose_min` | 4.3 | % | A | IN 76/2018 | Lactose mínima |
| `ccs_regulatorio` | 500 | mil cél/mL | A | IN 76/2018 | CCS máxima (média geométrica 3 m) |
| `ccs_pre_regulatorio` | 400 | mil cél/mL | D | Inferências | Faixa pré-regulatória |
| `cbt_regulatorio` | 300 | mil UFC/mL | A | IN 76/2018 | CBT/CPP máxima (média geométrica 3 m) |

## Alimentos

| ID | Nome | MS | PB | FDN | NDT | EE | R$/kg MN | Fonte |
|---|---|---|---|---|---|---|---|---|
| silagem_milho | Silagem de milho | 30.9 | 7.3 | 55.4 | 64.3 | 2.5 | 0.25 | [A] VF 2006 |
| silagem_sorgo | Silagem de sorgo | 30.8 | 6.7 | 61.4 | 57.2 | 2.5 | 0.22 | [A] VF 2006 |
| capim_elefante | Capim-elefante picado (46–60 d) | 19.9 | 9.2 | 72.3 | 52.0 | 2.0 | 0.12 | [A] VF 2006; NDT [B] |
| braquiaria | Braquiária decumbens (pastejo) | 31.0 | 6.7 | 74.6 | 58.2 | 2.0 | 0.05 | [B] Tab. 1 |
| cana | Cana-de-açúcar | 28.5 | 2.7 | 57.7 | 62.7 | 1.0 | 0.1 | [A] VF 2006 |
| milho_moido | Milho grão moído (fubá) | 87.6 | 9.1 | 14.0 | 87.2 | 4.0 | 1.4 | [A] Tab. 2 |
| farelo_soja | Farelo de soja | 88.6 | 48.8 | 14.6 | 81.5 | 1.7 | 2.6 | [A] Tab. 3 |
| caroco_algodao | Caroço de algodão | 91.0 | 22.6 | 46.0 | 81.9 | 18.9 | 1.6 | [A] Tab. 3 |
| farelo_trigo | Farelo de trigo | 88.0 | 16.6 | 44.3 | 72.4 | 3.5 | 1.3 | [A] Tab. 2 (Ca/P a conferir) |
| polpa_citrica | Polpa cítrica | 87.9 | 7.2 | 24.3 | 65.2 | 3.3 | 1.2 | [A] Tab. 2 |
| ureia | Ureia pecuária | 97.5 | 282 | 0 | 0 | 0 | 3.5 | [A] Tab. 3 |
| nucleo_mineral | Núcleo mineral (conforme rótulo) | 98.0 | 0 | 0 | 0 | 0 | 4.0 | Rótulo do produto |
