# Histórico da base de conhecimento

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
