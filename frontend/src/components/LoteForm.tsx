import { useState } from 'react'
import { api, OPCOES, type Lote } from '../api'
import { Erro } from './ui'
import { EscalaEscore } from './Escala'

/** Cadastro/edição de lote. DEL e dias de gestação são os valores de HOJE (avançam sozinhos com o tempo). */
export interface ValoresLote {
  nome: string; finalidade: string; estado: string; sistema: string; grupo_genetico: string; n_vacas: string; pv: string
  del_ref: string; dias_para_parto_ref: string; dias_gestacao_ref: string; fracao_primiparas: string; ecc: string
  distancia_km: string; relevo: string; forrageira: string; leite: string; gordura: string; proteina: string
}

const s = (v: any) => (v === null || v === undefined ? '' : String(Math.round(Number(v) * 100) / 100))

export function valoresIniciais(lote?: Lote, fatos?: Record<string, any>): ValoresLote {
  return {
    nome: lote?.nome ?? '', finalidade: lote?.finalidade ?? '', estado: lote?.estado ?? 'lactacao', sistema: lote?.sistema ?? 'confinado',
    grupo_genetico: lote?.grupo_genetico ?? 'girolando', n_vacas: s(lote?.n_vacas ?? 20), pv: s(lote?.pv ?? 500),
    del_ref: s(fatos?.['lote.del'] ?? lote?.del_ref ?? 100), dias_para_parto_ref: s(fatos?.['lote.dias_para_parto'] ?? lote?.dias_para_parto_ref),
    dias_gestacao_ref: s(fatos?.['lote.dias_gestacao'] ?? lote?.dias_gestacao_ref ?? 0), fracao_primiparas: s(lote?.fracao_primiparas ?? 0.3),
    ecc: s(lote?.ecc), distancia_km: s(lote?.distancia_km), relevo: lote?.relevo ?? 'plano', forrageira: lote?.forrageira ?? '', leite: s(fatos?.['lote.leite'] ?? lote?.leite),
    gordura: s(lote?.gordura ?? 3.5), proteina: s(lote?.proteina ?? 3.2),
  }
}

const num = (v: string) => (v.trim() === '' ? null : Number(v.replace(',', '.')))

export default function LoteForm({ lote, fatos, onSalvo }: { lote?: Lote; fatos?: Record<string, any>; onSalvo: (l: Lote) => void }) {
  const [v, setV] = useState<ValoresLote>(valoresIniciais(lote, fatos))
  const [erro, setErro] = useState('')
  const [salvando, setSalvando] = useState(false)
  const set = (k: keyof ValoresLote) => (e: { target: { value: string } }) => setV({ ...v, [k]: e.target.value })
  const lactacao = v.estado === 'lactacao'
  const pasto = v.sistema === 'pasto' || v.sistema === 'semiconfinado'

  const salvar = async () => {
    if (!v.nome.trim()) { setErro('Dê um nome ao lote.'); return }
    if (!num(v.pv) || !num(v.n_vacas)) { setErro('Informe nº de vacas e peso vivo.'); return }
    if (lactacao && num(v.del_ref) === null) { setErro('Informe os dias em lactação.'); return }
    if (!lactacao && num(v.dias_para_parto_ref) === null) { setErro('Informe os dias para o parto.'); return }
    const corpo = {
      fazenda_id: lote?.fazenda_id ?? 1, nome: v.nome.trim(), finalidade: v.finalidade, estado: v.estado, sistema: v.sistema,
      grupo_genetico: v.grupo_genetico, n_vacas: num(v.n_vacas), pv: num(v.pv),
      del_ref: lactacao ? num(v.del_ref) : null, dias_para_parto_ref: lactacao ? null : num(v.dias_para_parto_ref),
      dias_gestacao_ref: num(v.dias_gestacao_ref) ?? 0, fracao_primiparas: num(v.fracao_primiparas), ecc: num(v.ecc),
      distancia_km: pasto ? num(v.distancia_km) : null, relevo: pasto ? v.relevo : null, forrageira: pasto && v.forrageira ? v.forrageira : null, leite: lactacao ? num(v.leite) : null,
      gordura: num(v.gordura), proteina: num(v.proteina),
    }
    setSalvando(true); setErro('')
    try { onSalvo(await (lote ? api.put<Lote>(`/lotes/${lote.id}`, corpo) : api.post<Lote>('/lotes', corpo))) }
    catch (e: any) { setErro(e.message) }
    setSalvando(false)
  }

  const campo = (k: keyof ValoresLote, rotulo: string, un = '', ajuda = '') => (
    <label title={ajuda}>
      <span className="rotulo">{rotulo}{un && ` (${un})`}</span>
      <input className="input num" inputMode="decimal" value={v[k]} onChange={set(k)} />
    </label>
  )
  const opcao = (k: keyof ValoresLote, rotulo: string, opcoes: string[]) => (
    <label>
      <span className="rotulo">{rotulo}</span>
      <select className="input" value={v[k]} onChange={set(k)}>{opcoes.map((o) => <option key={o} value={o}>{OPCOES[o] ?? o}</option>)}</select>
    </label>
  )

  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2">
        <label><span className="rotulo">Nome</span><input className="input" value={v.nome} onChange={set('nome')} placeholder="Ex.: Lote 5 — Primíparas" /></label>
        <label><span className="rotulo">Finalidade</span><input className="input" value={v.finalidade} onChange={set('finalidade')} /></label>
      </div>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        {opcao('estado', 'Estado', ['lactacao', 'seca'])}
        {opcao('sistema', 'Sistema', ['confinado', 'semiconfinado', 'pasto'])}
        {opcao('grupo_genetico', 'Grupo genético', ['holandes', 'jersey', 'girolando', 'gir', 'mestica'])}
        {campo('n_vacas', 'Nº de vacas')}
        {campo('pv', 'Peso vivo médio', 'kg')}
        {lactacao ? campo('del_ref', 'Dias em lactação hoje', 'dias') : campo('dias_para_parto_ref', 'Dias para o parto', 'dias')}
        {campo('dias_gestacao_ref', 'Dias de gestação hoje', 'dias', '0 se vazias')}
        {campo('fracao_primiparas', 'Fração de primíparas', '0–1')}
      </div>
      <EscalaEscore tipo="ecc" valor={v.ecc} onChange={(x) => setV({ ...v, ecc: x })} />
      {lactacao && (
        <div className="grid grid-cols-3 gap-3">
          {campo('leite', 'Leite/vaca', 'kg/d', 'referência; o diário vem dos registros')}
          {campo('gordura', 'Gordura', '%')}
          {campo('proteina', 'Proteína', '%')}
        </div>
      )}
      {pasto && (
        <div className="grid grid-cols-3 gap-3">
          {campo('distancia_km', 'Distância caminhada', 'km/d')}
          {opcao('relevo', 'Relevo', ['plano', 'ondulado', 'acidentado'])}
          <label><span className="rotulo">Forrageira</span>
            <select className="input" value={v.forrageira} onChange={set('forrageira')}>
              <option value="">não informada</option><option value="mombaca">Mombaça</option><option value="tanzania">Tanzânia</option>
              <option value="decumbens">Braquiária decumbens</option><option value="marandu">Marandu</option><option value="outra">Outra</option>
            </select></label>
        </div>
      )}
      <p className="text-xs text-stone-500">DEL e dias de gestação são os valores de hoje; o sistema os avança automaticamente a cada dia.</p>
      {erro && <Erro msg={erro} />}
      <button className="btn-primario" onClick={salvar} disabled={salvando}>{salvando ? 'Salvando…' : lote ? 'Salvar alterações' : 'Criar lote'}</button>
    </div>
  )
}
