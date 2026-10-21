// Cliente da API. O contrato está em backend/app/api/schemas.py.
export type Nivel = 'critico' | 'atencao' | 'informativo'

export interface Fato { nome: string; valor: any; cf: number; origem: string; regra: string | null; nota?: string | null }
export interface Alerta {
  id?: number; regra: string; nivel: Nivel; titulo: string; causa: string; acao: string; categoria: string
  cf: number; fonte: string; forca: string; status: 'ativo' | 'suprimido'; nota?: string | null
  data?: string; lote_id?: number; sessao_id?: number; status_usuario?: string; modulo?: string
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
}
export interface ItemDieta { alimento: string; kg_mn: number }
export interface Alimento { id: string; nome: string; tipo: string; ms: number; pb: number; fdn: number; ndt: number; ee: number; preco_kg_mn: number; fonte: string; forca: string; cf: number }
export interface Lote {
  id: number; fazenda_id: number; nome: string; finalidade: string; estado: string; sistema: string; grupo_genetico: string
  n_vacas: number; pv: number; del_ref: number | null; dias_para_parto_ref: number | null; dias_gestacao_ref: number | null
  fracao_primiparas: number | null; ecc: number | null; distancia_km: number | null; relevo: string | null
  leite: number | null; gordura: number | null; proteina: number | null
}
export interface Dieta { id: number; lote_id: number; versao: number; itens: ItemDieta[]; origem: string; motivo: string; inicio: string; ativa: boolean; parecer?: any }

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
    throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg))
  }
  return r.json()
}

export const api = {
  get: <T,>(c: string) => req<T>('GET', c),
  post: <T,>(c: string, b?: unknown) => req<T>('POST', c, b ?? {}),
  put: <T,>(c: string, b: unknown) => req<T>('PUT', c, b),
  patch: <T,>(c: string, b: unknown) => req<T>('PATCH', c, b),
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
export const rotulo = (f: string) => ROTULOS[f] ?? f

export const UNIDADES: Record<string, string> = {
  'exig.cms': 'kg MS/d', 'exig.cms_equacao': 'kg MS/d', 'exig.cms_teto_fibra': 'kg MS/d', 'dieta.ms_kg': 'kg MS/d',
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
  nrc2001: 'NRC 2001', brleite: 'BR-Leite (Embrapa)', adequada: 'Adequada', ajustar: 'Precisa de ajustes', bloqueada: 'Bloqueada',
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
