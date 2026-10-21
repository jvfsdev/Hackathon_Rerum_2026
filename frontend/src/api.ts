// Cliente da API. O contrato está em backend/app/api/schemas.py.
export type Nivel = 'critico' | 'atencao' | 'informativo'

export interface Fato { nome: string; valor: any; cf: number; origem: string; regra: string | null; nota?: string | null }
export type EstadoAlerta = 'aberto' | 'aceito' | 'recusado' | 'resolvido' | 'expirado'
export interface Alerta {
  id?: number; regra: string; nivel: Nivel; titulo: string; causa: string; acao: string; categoria: string
  cf: number; fonte: string; forca: string; status: 'ativo' | 'suprimido'; nota?: string | null
  data?: string; lote_id?: number; sessao_id?: number; modulo?: string
  // episódio (alertas persistidos)
  estado?: EstadoAlerta; aberto_em?: string; ultima_ocorrencia?: string; ocorrencias?: number
  estado_em?: string | null; resolucao?: string | null; destino?: string; origem?: string
  // mesmos fatos em linguagem do produtor (vazio = usar o texto técnico)
  titulo_produtor?: string; causa_produtor?: string; acao_produtor?: string; problema?: string; tambem?: string[]
  contexto?: { fato: string; valor: any }[]
}
export interface ItemHistorico {
  id: number; alerta_id: number; lote_id: number; data_hora: string; tipo: string; descricao: string
  automatico: boolean; ref?: Record<string, any> | null
  alerta?: { id: number; regra: string; titulo: string; titulo_produtor?: string; nivel: Nivel; estado: EstadoAlerta; categoria: string }
}
export interface Premissa { fato: string; op: string; esperado: any; valor: any; cf: number }
export interface EntradaTraco {
  ciclo: number; regra: string; descricao: string; modulo: string; cf_regra: number; cf: number
  premissas: Premissa[]; acoes: any[]; fonte: string; forca: string; concorrentes: string[]
}
export interface NoComo {
  fato: string; valor?: any; cf?: number; origem?: string; nota?: string | null; conhecido?: boolean; op?: string; esperado?: any
  regras?: { regra: string; descricao: string; cf_regra: number; fonte: string; forca: string; premissas: NoComo[]; calculo?: any }[]
}
export interface Resultado {
  kb_version: string; fatos: Record<string, Fato>; traco: EntradaTraco[]; alertas: Alerta[]
  supressoes: Record<string, any>; explicacoes: Record<string, NoComo>; sessao_id?: number
  episodios?: Record<string, { id: number; estado: EstadoAlerta }>
}

/** Junta aos alertas de uma execução o id/estado do episódio persistido (para aceitar/recusar). */
export function comEpisodios(r: Resultado): Alerta[] {
  return r.alertas.map((a) => (r.episodios?.[a.regra] ? { ...a, ...r.episodios[a.regra] } : a))
}
export const dataBR = (d?: string | null) => (d ? new Date(d.slice(0, 10) + 'T12:00').toLocaleDateString('pt-BR') : '—')
export interface ItemDieta { alimento: string; kg_mn: number }
export interface Alimento { id: string; nome: string; tipo: string; ms: number; pb: number; fdn: number; ndt: number; ee: number; preco_kg_mn: number; fonte: string; forca: string; cf: number; preco_origem?: string
  da_fazenda?: boolean; ativo?: boolean; origem_dado?: string; mm?: number; pastejo?: boolean; max_pct_ms?: number | null
  preco_ref?: { fonte: string; data: string | null; praca?: string; url?: string; valor_original?: number; unidade_original?: string } }
export interface Lote {
  id: number; fazenda_id: number; nome: string; finalidade: string; estado: string; sistema: string; grupo_genetico: string
  n_vacas: number; pv: number; del_ref: number | null; dias_para_parto_ref: number | null; dias_gestacao_ref: number | null
  fracao_primiparas: number | null; ecc: number | null; distancia_km: number | null; relevo: string | null; forrageira?: string | null
  leite: number | null; gordura: number | null; proteina: number | null
}
export interface EtapaTransicao { dia: number; data: string; pct_nova: number; itens: ItemDieta[] }
export interface Transicao { dias: number; de_versao: number | null; plano: EtapaTransicao[]; alerta?: Alerta | null }
export interface Dieta { id: number; lote_id: number; versao: number; itens: ItemDieta[]; origem: string; motivo: string; inicio: string; ativa: boolean; parecer?: any
  transicao?: Transicao | null }

/** Erro de resposta da API, com o status HTTP e o corpo (vazio quando o proxy não alcançou a API). */
export class ErroApi extends Error {
  status: number
  corpo: string
  constructor(status: number, corpo: string, mensagem: string) {
    super(mensagem)
    this.status = status
    this.corpo = corpo
  }
  /** A API não respondeu (fora do ar / sem rede): o proxy devolve 5xx sem corpo, ou 502–504. */
  get semConexao() { return (this.status >= 500 && !this.corpo.trim()) || [502, 503, 504].includes(this.status) }
}

async function req<T>(metodo: string, caminho: string, corpo?: unknown): Promise<T> {
  const r = await fetch(`/api${caminho}`, {
    method: metodo,
    headers: corpo ? { 'Content-Type': 'application/json' } : undefined,
    body: corpo ? JSON.stringify(corpo) : undefined,
  })
  if (!r.ok) {
    const txt = await r.text()
    let msg = txt
    try { msg = JSON.parse(txt).detail ?? txt } catch { /* texto puro */ }
    throw new ErroApi(r.status, txt, typeof msg === 'string' && msg ? msg : (txt ? JSON.stringify(msg) : `API indisponível (HTTP ${r.status})`))
  }
  return r.json()
}

export const api = {
  get: <T,>(c: string) => req<T>('GET', c),
  post: <T,>(c: string, b?: unknown) => req<T>('POST', c, b ?? {}),
  put: <T,>(c: string, b: unknown) => req<T>('PUT', c, b),
  patch: <T,>(c: string, b: unknown) => req<T>('PATCH', c, b),
  del: <T,>(c: string) => req<T>('DELETE', c),
}

// ---------- rótulos legíveis ----------
export const ROTULOS: Record<string, string> = {
  'perfil.fase': 'Fase do lote', 'perfil.equacao_cms': 'Equação de consumo', 'perfil.semana_lactacao': 'Semana de lactação',
  'perfil.estresse_termico': 'Estresse térmico', 'perfil.gestacao_avancada': 'Gestação ≥ 190 dias', 'perfil.crescimento': 'Primíparas em crescimento',
  'perfil.atividade_pastejo': 'Gasto com pastejo', 'perfil.cms_baixa_confianca': 'Consumo com baixa confiança', 'perfil.cms_pct_pv': 'CMS (% do PV)',
  'clima.itu': 'ITU', 'exig.cms': 'Consumo de MS previsto', 'exig.cms_equacao': 'CMS pela equação', 'exig.cms_teto_fibra': 'Teto de consumo pela fibra',
  'exig.ell_total': 'Energia exigida (ELl)', 'exig.ell_mantenca': 'Mantença', 'exig.ell_leite': 'Produção de leite', 'exig.ell_gestacao': 'Gestação',
  'exig.ell_crescimento': 'Crescimento (primíparas)', 'exig.ell_atividade': 'Atividade de pastejo', 'exig.ell_ecc': 'Recuperação de ECC',
  'exig.pb_pct_alvo': 'Proteína bruta alvo', 'exig.pm_leite': 'Proteína metabolizável p/ leite', 'exig.pm_gestacao': 'PM de gestação',
  'meta.fdn_min': 'FDN mínimo', 'meta.fdnf_min': 'FDN de forragem mínimo', 'meta.cnf_max': 'CNF máximo', 'meta.ee_max': 'Gordura máxima',
  'meta.ureia_max': 'Ureia máxima', 'meta.fator_energia_min': 'Tolerância de energia',
  'dieta.ms_kg': 'MS ofertada', 'dieta.pb_pct': 'PB da dieta', 'dieta.fdn_pct': 'FDN da dieta', 'dieta.fdnf_pct': 'FDN de forragem',
  'dieta.cnf_pct': 'CNF da dieta', 'dieta.ee_pct': 'Gordura da dieta', 'dieta.ell_mcal': 'ELl ofertada', 'dieta.ell_mcal_kg': 'ELl por kg MS',
  'dieta.ureia_pct': 'Ureia da dieta', 'dieta.custo_vaca_dia': 'Custo/vaca/dia', 'dieta.itens': 'Dieta informada', 'dieta.forragem_pct': 'Volumoso na MS',
  'ver.razao_energia': 'Energia consumida / exigida', 'ver.razao_pb': 'PB dieta / alvo', 'ver.razao_ms': 'MS ofertada / CMS', 'ver.ell_consumida': 'ELl consumida',
  'ver.risco_acidose': 'Risco de acidose', 'ver.deficit_energetico': 'Déficit energético', 'ver.deficit_proteico': 'Déficit proteico',
  'parecer.dieta': 'Parecer da dieta', 'parecer.bloqueio': 'Dieta bloqueada',
  'lote.estado': 'Estado', 'lote.del': 'Dias em lactação', 'lote.dias_para_parto': 'Dias para o parto', 'lote.dias_gestacao': 'Dias de gestação',
  'lote.grupo_genetico': 'Grupo genético', 'lote.sistema': 'Sistema', 'lote.pv': 'Peso vivo', 'lote.leite': 'Leite/vaca', 'lote.gordura': 'Gordura do leite',
  'lote.proteina': 'Proteína do leite', 'lote.lactose': 'Lactose', 'lote.fracao_primiparas': 'Fração de primíparas', 'lote.ecc': 'ECC',
  'lote.distancia_km': 'Distância caminhada', 'lote.relevo': 'Relevo', 'lote.temp': 'Temperatura', 'lote.ur': 'Umidade',
  'exig.cms_ajuste_fdnd': 'Ajuste pela digestibilidade da FDN', 'dieta.dcad_meq_kg': 'DCAD da dieta', 'perfil.dias_gestacao': 'Dias de gestação', 'dieta.fdnd_forragem': 'FDND do volumoso',
  'mon.iofc': 'Receita − custo da dieta (IOFC)', 'mon.alimento_pct_receita': 'Alimentação / receita', 'mon.ea': 'Eficiência alimentar',
  'mon.ecm': 'Leite corrigido para energia', 'mon.cms_medido': 'Consumo medido (oferta − sobras)', 'mon.custo_dieta_vaca': 'Custo da dieta/vaca/dia',
  'mon.bonificacao_rs_l': 'Bonificação do laticínio', 'mon.preco_leite_efetivo': 'Preço efetivo do leite', 'laudo.crioscopia': 'Crioscopia',
  'mon.altura_entrada': 'Altura na entrada', 'mon.altura_saida': 'Altura na saída', 'mon.altura_media': 'Altura média do pasto',
  'mon.distancia_delta': 'Aumento da caminhada', 'mon.dias_para_parto_previsto': 'Dias para o parto (previsto)',
  'hipotese.queda_sustentada': 'Queda sustentada', 'hipotese.causa_calor': 'Causa: calor', 'hipotese.causa_volumoso': 'Causa: novo volumoso',
  'hipotese.acidose': 'Acidose subaguda', 'hipotese.mastite': 'Mastite', 'hipotese.ben_severo': 'BEN severo', 'hipotese.dgl': 'Depressão de gordura',
  'mon.litros_vaca': 'Litros/vaca hoje', 'mon.esperado_vaca': 'Esperado pela curva', 'mon.residuo': 'Desvio do esperado', 'mon.z': 'Desvio padronizado',
  'mon.corrida_dias': 'Dias seguidos abaixo', 'mon.corrida_pior': 'Pior dia da corrida', 'mon.ewma': 'EWMA do desvio', 'mon.ewma_limite_inf': 'Limite do EWMA',
  'mon.queda_7d': 'Variação em 7 dias', 'mon.itu_2d': 'ITU médio 2 dias', 'mon.itu_limiar': 'Limiar de ITU do grupo',
  'mon.dias_desde_troca_volumoso': 'Dias desde a troca de volumoso', 'mon.horas_desde_movimentacao': 'Horas desde a movimentação',
  'mon.horas_desde_correcao_ms': 'Horas desde a correção de MS', 'mon.litros_por_kg_conc': 'Litros por kg de concentrado',
  'mon.resposta_marginal': 'Resposta ao concentrado extra', 'mon.razao_precos': 'Razão de preços conc./leite', 'mon.sobras_mm3': 'Sobras (média 3 dias)',
  'mon.dias_cocho_vazio': 'Leituras com cocho vazio', 'mon.ms_silagem_atual': 'MS da silagem (atual)', 'mon.ms_silagem_formulacao': 'MS da silagem (formulação)',
  'mon.ms_delta_abs': 'Variação da MS', 'mon.ms_leituras_confirmadas': 'Leituras confirmando', 'mon.ecc_perda': 'Perda de ECC', 'mon.fezes': 'Escore de fezes',
  'laudo.nul': 'NUL', 'laudo.ureia': 'Ureia no leite', 'laudo.gp': 'Gordura : proteína', 'laudo.gordura': 'Gordura (laudo)', 'laudo.proteina': 'Proteína (laudo)',
  'laudo.lactose': 'Lactose (laudo)', 'laudo.ccs': 'CCS', 'laudo.ccs_mg3': 'CCS (média geom. 3 m)', 'laudo.cbt_mg3': 'CBT (média geom. 3 m)',
  'laudo.ccs_tendencia': 'Tendência da CCS', 'laudo.gordura_delta': 'Variação da gordura',
}

// ---------- visão do produtor × visão técnica ----------
/** "produtor": linguagem de fazenda, sem códigos de regra nem fator de certeza. "tecnico": tudo o que o motor mostra. */
export type Modo = 'produtor' | 'tecnico'
let modoAtual: Modo = (() => {
  const daUrl = new URLSearchParams(window.location.search).get('visao')     // ?visao=tecnico abre direto na visão técnica
  if (daUrl === 'tecnico' || daUrl === 'produtor') { try { localStorage.setItem('modo', daUrl) } catch { /* */ } return daUrl }
  try { return localStorage.getItem('modo') === 'tecnico' ? 'tecnico' : 'produtor' } catch { return 'produtor' }
})()
export const getModo = () => modoAtual
export function setModoGlobal(m: Modo) {
  modoAtual = m
  try { localStorage.setItem('modo', m) } catch { /* sem armazenamento */ }
}
export const tecnico = () => modoAtual === 'tecnico'

/** Nomes dos fatos em linguagem do produtor (os que aparecem em explicações e no "o que precisaria mudar"). */
export const ROTULOS_PRODUTOR: Record<string, string> = {
  'perfil.fase': 'Fase do lote', 'perfil.estresse_termico': 'Calor', 'perfil.gestacao_avancada': 'Prenhez avançada',
  'clima.itu': 'Índice de calor', 'mon.itu_2d': 'Índice de calor (2 dias)', 'mon.itu_limiar': 'Calor que o lote aguenta',
  'exig.cms': 'Quanto a vaca consegue comer (matéria seca)', 'exig.ell_total': 'Energia que o lote precisa',
  'exig.pb_pct_alvo': 'Proteína que o lote precisa', 'ver.ell_consumida': 'Energia que a dieta dá',
  'ver.razao_energia': 'Energia da dieta (do necessário)', 'ver.razao_pb': 'Proteína da dieta (do necessário)',
  'ver.razao_ms': 'Comida oferecida (do que a vaca come)', 'ver.leite_permitido': 'Leite que a comida sustenta',
  'dieta.ms_kg': 'Comida oferecida (matéria seca)', 'dieta.pb_pct': 'Proteína da dieta', 'dieta.fdn_pct': 'Fibra da dieta',
  'dieta.fdnf_pct': 'Fibra do volumoso', 'dieta.cnf_pct': 'Amido e açúcares', 'dieta.ee_pct': 'Gordura da dieta',
  'dieta.ureia_pct': 'Ureia na dieta', 'dieta.custo_vaca_dia': 'Custo da comida por vaca/dia', 'dieta.forragem_pct': 'Volumoso na dieta',
  'dieta.dcad_meq_kg': 'DCAD (dieta aniônica)', 'dieta.mineral_kg_ms': 'Núcleo mineral',
  'meta.fdn_min': 'Fibra mínima', 'meta.fdnf_min': 'Fibra mínima do volumoso', 'meta.cnf_max': 'Amido e açúcares (máximo)',
  'meta.ee_max': 'Gordura máxima', 'meta.ureia_max': 'Ureia máxima', 'meta.sobras.max': 'Sobra máxima no cocho', 'meta.sobras.min': 'Sobra mínima no cocho',
  'lote.del': 'Dias de lactação', 'lote.pv': 'Peso médio', 'lote.leite': 'Leite por vaca', 'lote.ecc': 'Escore corporal',
  'lote.dias_para_parto': 'Dias para o parto', 'lote.fracao_primiparas': 'Fração de novilhas', 'lote.estado': 'Situação',
  'lote.sistema': 'Sistema', 'lote.grupo_genetico': 'Raça', 'lote.gordura': 'Gordura do leite', 'lote.proteina': 'Proteína do leite',
  'lote.temp': 'Temperatura', 'lote.ur': 'Umidade', 'lote.distancia_km': 'Caminhada por dia',
  'mon.litros_vaca': 'Leite por vaca hoje', 'mon.esperado_vaca': 'Leite esperado por vaca', 'mon.residuo': 'Diferença para o esperado',
  'mon.corrida_dias': 'Dias seguidos abaixo do esperado', 'mon.corrida_pior': 'Pior dia (diferença)', 'mon.queda_7d': 'Variação do leite em 7 dias',
  'mon.z': 'Sinal de queda brusca', 'mon.ewma': 'Sinal de queda lenta', 'mon.ewma_limite_inf': 'Limite do sinal de queda lenta',
  'mon.sobras_mm3': 'Sobra no cocho (3 dias)', 'mon.sobras_min3': 'Menor sobra dos 3 dias', 'mon.sobras_max3': 'Maior sobra dos 3 dias',
  'mon.dias_cocho_vazio': 'Leituras com cocho vazio', 'mon.ecc_perda': 'Escore corporal perdido', 'mon.fezes': 'Escore de fezes',
  'mon.litros_por_kg_conc': 'Litros por kg de concentrado', 'mon.resposta_marginal': 'Leite a mais por kg de concentrado extra',
  'mon.razao_precos': 'Litros para pagar 1 kg de concentrado', 'mon.custo_conc_litro': 'Concentrado por litro (R$)',
  'mon.custo_conc_razao': 'Concentrado por litro (do normal)', 'mon.alimento_pct_receita': 'Comida / dinheiro do leite (%)',
  'mon.iofc': 'Sobra por vaca depois da comida (R$)', 'mon.ea': 'Leite por kg de comida', 'mon.ms_delta_abs': 'Mudança na umidade da silagem',
  'mon.ms_leituras_confirmadas': 'Leituras confirmando', 'mon.ms_silagem_atual': 'Matéria seca da silagem hoje',
  'mon.dias_desde_troca_volumoso': 'Dias desde a troca de volumoso', 'mon.horas_desde_movimentacao': 'Horas desde a mudança de vacas',
  'mon.dias_dieta_nova': 'Dias desde a troca de dieta', 'mon.em_adaptacao_dieta': 'Em adaptação à dieta nova',
  'mon.altura_media': 'Altura do pasto', 'mon.altura_entrada': 'Altura do pasto na entrada', 'mon.altura_saida': 'Altura do pasto na saída',
  'mon.distancia_delta': 'Caminhada a mais', 'mon.bonificacao_rs_l': 'Bonificação (R$/L)', 'mon.dias_para_parto_previsto': 'Dias para o parto',
  'laudo.nul': 'Ureia do leite (NUL)', 'laudo.ureia': 'Ureia do leite', 'laudo.gp': 'Gordura ÷ proteína do leite', 'laudo.lactose': 'Lactose',
  'laudo.ccs': 'CCS', 'laudo.ccs_mg3': 'CCS (média de 3 meses)', 'laudo.cbt_mg3': 'CBT (média de 3 meses)', 'laudo.gordura_delta': 'Queda da gordura do leite',
  'laudo.crioscopia': 'Crioscopia', 'laudo.ccs_tendencia': 'CCS subindo',
  'hipotese.queda_sustentada': 'Leite caindo há vários dias', 'hipotese.acidose': 'Suspeita de acidose', 'hipotese.mastite': 'Suspeita de mastite',
  'hipotese.ben_severo': 'Emagrecimento forte', 'hipotese.causa_calor': 'Calor como causa', 'hipotese.dgl': 'Queda da gordura do leite',
  'estoque.dias_restantes': 'Dias de estoque', 'estoque.saldo_kg': 'Estoque (kg)',
}
export const rotulo = (f: string) => (modoAtual === 'produtor' && ROTULOS_PRODUTOR[f]) || ROTULOS[f] || f

/** Título, causa e ação do alerta na linguagem da visão atual. */
export function textoAlerta(a: Alerta) {
  const p = modoAtual === 'produtor'
  return { titulo: (p && a.titulo_produtor) || a.titulo, causa: (p && a.causa_produtor) || a.causa, acao: (p && a.acao_produtor) || a.acao }
}
/** Certeza em palavras (para o produtor), a partir do fator de certeza. */
export const certeza = (cf: number) => (cf >= 0.75 ? 'certeza alta' : cf >= 0.5 ? 'certeza média' : 'certeza baixa')
export const reais = (v?: number | null, casas = 2) =>
  v === null || v === undefined || Number.isNaN(v) ? '—' : v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', minimumFractionDigits: casas, maximumFractionDigits: casas })
export const numero = (v?: number | null, casas = 1) =>
  v === null || v === undefined || Number.isNaN(v) ? '—' : v.toLocaleString('pt-BR', { minimumFractionDigits: 0, maximumFractionDigits: casas })
/** kg em kg ou toneladas (estoque, trato). */
export const peso = (kg?: number | null) =>
  kg === null || kg === undefined ? '—' : Math.abs(kg) >= 2000 ? `${numero(kg / 1000, 1)} t` : `${numero(kg, kg < 10 ? 2 : 0)} kg`

export const UNIDADES: Record<string, string> = {
  'exig.cms': 'kg MS/d', 'exig.cms_equacao': 'kg MS/d', 'exig.cms_ajuste_fdnd': 'kg MS/d', 'exig.cms_teto_fibra': 'kg MS/d', 'dieta.ms_kg': 'kg MS/d',
  'exig.ell_total': 'Mcal/d', 'exig.ell_mantenca': 'Mcal/d', 'exig.ell_leite': 'Mcal/d', 'exig.ell_gestacao': 'Mcal/d', 'exig.ell_crescimento': 'Mcal/d',
  'exig.ell_atividade': 'Mcal/d', 'exig.ell_ecc': 'Mcal/d', 'dieta.ell_mcal': 'Mcal/d', 'ver.ell_consumida': 'Mcal/d', 'exig.pm_leite': 'g/d',
  'exig.pb_pct_alvo': '% MS', 'dieta.pb_pct': '% MS', 'dieta.fdn_pct': '% MS', 'dieta.fdnf_pct': '% MS', 'dieta.cnf_pct': '% MS', 'dieta.ee_pct': '% MS',
  'meta.fdn_min': '% MS', 'meta.fdnf_min': '% MS', 'meta.cnf_max': '% MS', 'meta.ee_max': '% MS', 'meta.ureia_max': '% MS', 'dieta.ureia_pct': '% MS',
  'lote.pv': 'kg', 'lote.leite': 'kg/d', 'lote.del': 'dias', 'lote.gordura': '%', 'lote.proteina': '%', 'laudo.nul': 'mg/dL', 'lote.temp': '°C', 'lote.ur': '%',
}

export const FASES: Record<string, string> = {
  recem_parida: 'Recém-parida', inicio: 'Início / pico', meio: 'Meio de lactação', final: 'Final de lactação', pre_parto: 'Pré-parto', seca: 'Seca',
}
export const OPCOES: Record<string, string> = {
  lactacao: 'Lactação', seca: 'Seca', holandes: 'Holandês', jersey: 'Jersey', girolando: 'Girolando', gir: 'Gir', mestica: 'Mestiça',
  confinado: 'Confinado', semiconfinado: 'Semiconfinado', pasto: 'Pasto', plano: 'Plano', ondulado: 'Ondulado', acidentado: 'Acidentado',
  nrc2001: 'NRC 2001', nasem2021: 'NASEM 2021 (com ECC)', brleite: 'BR-Leite (Embrapa)', adequada: 'Adequada', ajustar: 'Precisa de ajustes', bloqueada: 'Bloqueada',
  brando: 'Brando', forte: 'Forte', subindo: 'Subindo', ...FASES,
}

export function fmt(v: any, fato?: string): string {
  if (v === null || v === undefined) return '—'
  if (typeof v === 'boolean') return v ? 'Sim' : 'Não'
  if (typeof v === 'number') {
    if (fato && (fato.startsWith('ver.razao') || fato === 'mon.residuo' || fato === 'mon.queda_7d' || fato === 'mon.corrida_pior')) return `${(v * 100).toFixed(0)}%`
    const casas = Math.abs(v) >= 100 ? 0 : Math.abs(v) >= 10 ? 1 : 2
    return v.toLocaleString('pt-BR', { maximumFractionDigits: casas, minimumFractionDigits: 0 })
  }
  if (typeof v === 'string') return OPCOES[v] ?? v
  if (Array.isArray(v)) return v.map((x) => (typeof x === 'object' ? `${x.alimento} ${x.kg_mn} kg` : String(x))).join(', ')
  return JSON.stringify(v)
}

// ---------- registros do lote ----------
export interface Registro { id: number; lote_id: number; data: string; indicador: string; valor: number; metodo?: string | null; atualizado_em?: string
  texto?: string | null }
export const NOME_INDICADOR: Record<string, string> = {
  vacas: 'Vacas', litros: 'Litros', concentrado_kg_vaca: 'Concentrado/vaca', escore_cocho: 'Cocho', sobras_pct: 'Sobras pesadas',
  temp: 'Temperatura', ur: 'Umidade', ms_silagem: 'MS da silagem', ecc: 'Escore corporal', escore_fezes: 'Fezes',
  ruminacao: 'Ruminação', distancia_km: 'Caminhada', altura_entrada: 'Pasto (entrada)', altura_saida: 'Pasto (saída)',
  altura_media: 'Pasto (média)', trato_kg: 'Trato fornecido', laudo_gordura: 'Gordura', laudo_proteina: 'Proteína',
  laudo_lactose: 'Lactose', laudo_ureia: 'Ureia', laudo_nul: 'NUL', laudo_ccs: 'CCS', laudo_cbt: 'CBT', laudo_crioscopia: 'Crioscopia',
}
const UN_INDICADOR: Record<string, string> = {
  litros: ' L', concentrado_kg_vaca: ' kg', sobras_pct: '%', temp: ' °C', ur: '%', ms_silagem: '%', distancia_km: ' km',
  altura_entrada: ' cm', altura_saida: ' cm', altura_media: ' cm', trato_kg: ' kg', laudo_gordura: '%', laudo_proteina: '%',
  laudo_lactose: '%', laudo_ureia: ' mg/dL', laudo_nul: ' mg/dL', laudo_ccs: ' mil', laudo_cbt: ' mil', ruminacao: ' min',
}
export const valorIndicador = (ind: string, v: number, partes?: string | null) =>
  `${v.toLocaleString('pt-BR', { maximumFractionDigits: ind === 'laudo_crioscopia' ? 3 : 2 })}${UN_INDICADOR[ind] ?? ''}${partes ? ` (${partes.replace(/\./g, ',')})` : ''}`
/** Registros agrupados por data (mais recente primeiro): {data: {indicador: registro}}. */
export function porDia(regs: Registro[]): [string, Record<string, Registro>][] {
  const m = new Map<string, Record<string, Registro>>()
  for (const r of regs) m.set(r.data, { ...(m.get(r.data) ?? {}), [r.indicador]: r })
  return [...m.entries()].sort((a, b) => (a[0] < b[0] ? 1 : -1))
}
/** Valor gravado como texto de formulário (até 2 casas) e "mudou?" com tolerância desse arredondamento. */
export const paraCampo = (v: number) => String(Math.round(v * 100) / 100)
export const mudou = (gravado: number | undefined, novo: number) => gravado === undefined || Math.abs(gravado - novo) > 0.006
export const hora = (iso?: string) => (iso ? new Date(iso).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }) : '')

