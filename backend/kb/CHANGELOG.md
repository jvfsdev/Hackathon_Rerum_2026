# Histórico da base de conhecimento

## 1.7.0 — 21/10/2026
Auditoria de todos os valores (10 subagentes, cada valor contra a fonte citada). Nenhum valor de composição ou equação
era inventado; correções:
- **Força e fonte** alinhadas ao que a fonte sustenta: corrida de 5 dias (D, adaptada de ≥10 d por vaca), ITU 72
  (Ravagnolo, ⚠ NV; Negri achou 74), secagem aos 220 d (C), DCAD de alerta 0 (D), MS 5 p.p. (D), sobras por fase (C),
  queda de gordura (D), validade do laudo (D), 417 Mcal/ponto de ECC (C: é energia de perda), VER-01/02, VER-15I, CLS-ITUL,
  CLS-07, EXG-01F/04/06A–C/07, FOR-20, ACP-D02/D04/S02/S03/S03A/S04/SEC/M03/M05/M06B, PRV-02, META-04, TRN-01/02/09.
- **Transição de dieta:** `transicao_dias_volumoso` 5 → 7 (extensão: 7–14 d) e `transicao_passo_conc` 1,0 → 0,5 kg MS/dia
  (NFACC: 0,5–0,7 kg/dia).
- **ACP-M06B:** CCS não suspende a coleta (só a CBT/CPP, IN 77); o limite de 500 mil é da IN 76, não do laticínio.
- **Acidose:** G:P baixa sozinha vira informativo (ACP-ACID0); atenção só com 2ª evidência (fezes: ACP-04; ruminação:
  ACP-S05R). ACP-S05 não conclui acidose com calor ou troca de volumoso recente.
- **ACP-EA1:** a referência de 1,3 kg ECM/kg MS é de Holandesas: não vale para Gir, Girolando e mestiças.
- **Sem número escondido:** textos usam `{@params.x}`; parâmetros novos para janelas e limites que estavam no código
  (`mad_janela_dias`, `sigma_piso`, `ewma_z_cap`, `resposta_marginal_dias` = 5–7 d como nas Inferências, `ccs_tendencia_fator`
  = +25% em 3 meses, `cocho_vazio_sobra_pct`, `custo_conc_*`, `silo_novo_dias`, `sobras_dias`, `sobras_ajuste_pct`,
  `ecc_validade_dias`, `ruminacao_dias`, `laudo_mg3_dias`, `transicao_extensao_dias`, `ea_del_faixa`, `atividade_ondulado`,
  `pl_margem_dcad`, `tolerancia_inclusao_pct`) e para os valores padrão da consulta guiada (`padrao_*`).
- Perda de ECC medida em `dias_mobilizacao` (5 semanas), como diz a ACP-05. Ureia com a PB do CQBAL (281,87).
- Casos N13–N15 (acidose com uma e duas evidências; ruminação com calor).

## 1.6.1 — 21/10/2026
- ACP-01 e ACP-01R (NUL alto) compartilham o problema `nul_alto`: um aviso só, o mais grave (caso T8 ajustado).
- Meta-regras do acompanhamento (ex.: META-01 "mastite primeiro") passam a valer também para os avisos da verificação
  da dieta ativa (`alertas.aplicar_meta_na_verificacao`).

## 1.6.0 — 21/10/2026
- Módulo **P (previsão)**: projeção de 7 a 90 dias (app/previsao.py) pela curva ajustada ao lote, com faixa de 90%
  (`@params.prev_z_faixa` × sigma robusto dos desvios), calor previsto (Open-Meteo, 16 dias), secagem em
  `@params.dias_gestacao_secagem`, dieta do dia e preços vigentes. Regras PRV-01 (queda projetada), PRV-02 (secagem no
  horizonte), PRV-03 (dieta mais cara que o leite), PRV-04 (energia sobrando para a produção projetada), PRV-10 (receita da
  fazenda caindo), PRV-11 (margem da fazenda negativa).

## 1.5.0 — 21/10/2026
- **Linguagem do produtor**: todo alerta ganha `titulo_produtor`, `causa_produtor` e `acao_produtor` (mesmos fatos,
  sem jargão, números com vírgula). A interface mostra esses textos na "visão do produtor" e os técnicos na "visão técnica".
- VER-00D: leite que a energia consumida sustenta (`ver.leite_permitido`, NRC 2001) — usado no simulador "e se?".
- Módulo **T (transição)**: TRN-01 (troca de volumoso → `@params.transicao_dias_volumoso`), TRN-02 (aumento de
  concentrado em passos de `@params.transicao_passo_conc`), TRN-03 (mudança grande da MS), TRN-09 (duração = maior).
  Adaptação no acompanhamento: ACP-TR1 (rejeição/sobras altas, problema `cocho_alto` junto com ACP-S04), ACP-TR2 (fezes
  moles), ACP-TR3 (queda durante a adaptação).
- Módulo **E (estoque)**: EST-01 (crítico até `@params.estoque_dias_critico`), EST-02 (programar compra até
  `@params.estoque_dias_atencao`), EST-03 (contagem desatualizada).
- Parâmetros novos: ajuste mínimo da dieta, sensibilidade, transição, ordem e notas do trato, estoque e revisão pelo uso.

## 1.4.1 — 21/10/2026
- Alertas ganham a chave `problema`: regras que medem o mesmo problema em graus diferentes viram um alerta só
  (o mais grave, citando os demais em `tambem`) e um único episódio que agrava ou atenua.
  `perda_ecc` = ACP-05 + ACP-09; `cocho_baixo` = ACP-06 + ACP-06B + ACP-S03.

## 1.4.0 — 21/10/2026
- Composição dos alimentos atualizada pelo **CQBAL 4.0** (Valadares Filho et al., 2018; www.cqbal.com.br) via
  scripts/importar_cqbal.py: MS, PB, EE, MM, FDN, CNF (medido), NDT (observado com n ≥ 10, senão BR-CORTE 2016),
  minerais Ca/P/Mg/K/Na/Cl/S quando disponíveis e n de amostras. Novo alimento: braquiária brizantha Marandu.
  Digestibilidade da FDN não importada (definição/n não confirmados).
- DCAD: composição calcula minerais e DCAD quando todos os itens têm Na/K/Cl/S; VER-15 (pré-parto com multíparas e
  DCAD > 0), VER-15N (novilhas), VER-15I (sem dados); FOR-07/FOR-18 levam a mesma restrição ao PL.
- Regras de 1.3.x: EXG-08 (NASEM com ECC), EXG-09 (FDND), ACP-11, ACP-12, secagem/pré-parto, altura do pasto,
  crioscopia, bonificação, IOFC, eficiência alimentar; leitura de cocho diária por escore.

## 1.3.0 — 21/10/2026 (auditoria: motor, base e acompanhamento)
- Exigências: gestação da vaca seca derivada dos dias para o parto (CLS-00A/B); total de energia exige o leite em
  lactação (EXG-02Z) e tem regra própria para vaca seca (EXG-02Y); tolerância de energia no pós-parto calculada pela
  mobilização aceitável de ECC (EXG-07 v2); sem "recuperar ECC" na recém-parida; energia por ponto de ECC escalada
  pelo PV; semiconfinado com gasto de atividade; Jersey na tabela de PB de raças menores; Gir/mestiças com CF menor
  na equação BR-Leite (fora da população); limiar de ITU por grupo genético (CLS-ITUL, CLS-10 v2).
- Verificação: FDNf < 15% bloqueia (VER-03D) e a meta de fibra não extrapola; excesso de energia (VER-10, e o PL
  respeita o teto), ECC acima da fase (VER-11), limites de inclusão (VER-12), pastejo em confinado (VER-13), falta de
  núcleo mineral (VER-14); plausibilidade do CMS sem o pós-parto (EXG-09 v2).
- Formulação: FOR-02B (teto de energia), FOR-16 (alimento excluído), FOR-17 (alimentos energéticos demais).
- Acompanhamento: curva calibrada só com dias válidos (ACP-D00B enquanto calibra); dias de transição fora dos
  detectores; EWMA com z limitado; corrida e variação de 7 dias por data e com resíduo atual; laudos com idade
  máxima e média geométrica só com 3 amostras; calor rebaixa a queda para atenção (META-02 v2).
- Parâmetros sem efeito removidos; números fixos de regras viraram parâmetros.

## 1.2.0 — 21/10/2026
- PL com o mesmo contrato da verificação: energia consumida = min(MS, CMS) × densidade (linearizada), oferta
  pelos mesmos fatores de VER-06/06B, PB máxima = alvo × fator_pb_max, margem de segurança `pl_margem` em todo
  limite. Mínimo de consumo em lactação = 95% do CMS OU rúmen cheio (teto de fibra), como a verificação.
- Formulação iterada até ponto fixo quando a dieta muda o próprio CMS (teto de fibra, equação com cana).
- FOR-21: quando só energia/proteína são inatingíveis, entrega a melhor dieta possível com o déficit explícito.
- Parâmetros `pl_folga_cms` e `pl_pb_folga_max` substituídos por `pl_fator_ms_min` e `pl_margem`.

## 1.1.0 — 21/10/2026
- FOR-05: o PL limita a cana a 50% do volumoso quando o lote produz acima de 15 kg/vaca (antes o PL podia sugerir
  cana como único volumoso e a própria verificação, VER-07, reprovava a dieta sugerida).
- FOR-15: diagnóstico quando falta volumoso além da cana. Novo parâmetro `cana_max_pct_volumoso`.
- FOR-06: lote confinado não recebe forragem de pastejo no PL (alimento com `pastejo: true`).

## 1.0.0 — 21/10/2026
- Versão inicial: módulos de classificação (CLS), exigências (EXG), verificação (VER), formulação (FOR),
  acompanhamento diário/semanal/mensal (ACP) e meta-regras (META).
- Alimentos semeados com valores da Embrapa (Valadares Filho 2006; Embrapa RO Doc 167), conferidos por pesquisa.
- Limiares conflitantes da literatura viraram parâmetros com fonte e força de evidência.
