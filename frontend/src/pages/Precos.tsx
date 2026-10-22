import { Fragment, useEffect, useState } from 'react'
import { api, type Alimento, hojeLocal } from '../api'
import { Carregando, Erro, Painel } from '../components/ui'

interface Linha {
  id: string; nome?: string; tipo?: string; ms?: number; preco: number; preco_referencia: number | null; da_fazenda?: boolean
  origem: 'fazenda' | 'referencia'; data: string | null; fonte: string; historico: { data: string; preco: number; fonte: string }[]
}
interface Dados { leite: Linha; concentrado: Linha; alimentos: Linha[] }

const TIPO: Record<string, string> = { volumoso: 'Volumoso', concentrado: 'Concentrado', ureia: 'Ureia', mineral: 'Mineral' }
const dataBR = (d: string | null | undefined) => (d ? new Date(d + 'T12:00').toLocaleDateString('pt-BR') : '—')
const brl = (v: number) => v.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

const ORIGEM_DADO: Record<string, string> = { laboratorio: 'análise de laboratório', tabela: 'tabela publicada', estimado: 'estimativa' }
const MINERAIS: [string, string][] = [['ca', 'Ca'], ['p', 'P'], ['mg', 'Mg'], ['k', 'K'], ['na', 'Na'], ['cl', 'Cl'], ['s', 'S']]
const VAZIO = { nome: '', tipo: 'concentrado', origem_dado: 'tabela', fonte: '', ms: '', pb: '', fdn: '', ndt: '', ee: '', mm: '', fdnd: '', max_pct_ms: '', pastejo: false, preco_kg_mn: '',
  ca: '', p: '', mg: '', k: '', na: '', cl: '', s: '' }
type FormInsumo = typeof VAZIO

const PARAMS_BONIF: Record<string, [string, string]> = {
  ccs: ['CCS', 'mil cél/mL'], cbt: ['CBT/CPP', 'mil UFC/mL'], gordura: ['Gordura', '%'], proteina: ['Proteína', '%'],
}
type Faixa = { min: string; max: string; rs_l: string }

/** Tabela de bonificação/penalização do laticínio por qualidade (faixas por parâmetro, R$/L). */
function Bonificacao({ fazendaId }: { fazendaId: number }) {
  const [tabela, setTabela] = useState<Record<string, Faixa[]>>({})
  const [aberto, setAberto] = useState(false)
  const [msg, setMsg] = useState('')
  const [erro, setErro] = useState('')
  const txt = (v: any) => (v === null || v === undefined ? '' : String(v))
  useEffect(() => {
    api.get<{ tabela: Record<string, any[]> }>(`/fazendas/${fazendaId}/bonificacao`).then((r) =>
      setTabela(Object.fromEntries(Object.entries(r.tabela).map(([k, fs]) => [k, fs.map((f) => ({ min: txt(f.min), max: txt(f.max), rs_l: txt(f.rs_l) }))]))))
  }, [fazendaId])
  const n = (v: string) => (v.trim() === '' ? null : Number(v.replace(',', '.')))
  const salvar = async () => {
    setErro(''); setMsg('')
    const corpo = Object.fromEntries(Object.entries(tabela).map(([k, fs]) => [k, fs.filter((f) => f.rs_l.trim() !== '').map((f) => ({ min: n(f.min), max: n(f.max), rs_l: n(f.rs_l) }))]))
    try { await api.put(`/fazendas/${fazendaId}/bonificacao`, { tabela: corpo }); setMsg('Tabela salva. Vale no próximo acompanhamento (preço efetivo do leite, IOFC e alerta de bonificação).') }
    catch (e: any) { setErro(e.message) }
  }
  const muda = (p: string, i: number, campo: keyof Faixa, v: string) =>
    setTabela({ ...tabela, [p]: (tabela[p] ?? []).map((f, j) => (j === i ? { ...f, [campo]: v } : f)) })
  const total = Object.values(tabela).reduce((t, fs) => t + fs.length, 0)
  return (
    <Painel titulo="Bonificação do laticínio por qualidade" subtitulo={total ? `${total} faixa(s) cadastrada(s). Entra no preço efetivo do leite, no IOFC e no alerta de quanto a qualidade está custando.` : 'Cadastre as faixas do seu laticínio (cada um tem a sua): ex.: CCS até 200 mil = +R$ 0,03/L; acima de 400 mil = −R$ 0,03/L.'}
      acoes={<button className="btn-secundario py-1.5" aria-expanded={aberto} onClick={() => setAberto(!aberto)}>{aberto ? 'Fechar' : 'Editar faixas'}</button>}>
      {aberto && (
        <div className="space-y-4">
          {Object.entries(PARAMS_BONIF).map(([p, [nome, un]]) => (
            <div key={p}>
              <p className="mb-1 text-sm font-semibold text-stone-800">{nome} <span className="font-normal text-stone-400">({un})</span></p>
              {(tabela[p] ?? []).map((f, i) => (
                <div key={i} className="mb-1 flex flex-wrap items-center gap-2 text-sm">
                  de <input className="input num w-20 py-1" placeholder="—" value={f.min} onChange={(e) => muda(p, i, 'min', e.target.value)} />
                  até <input className="input num w-20 py-1" placeholder="—" value={f.max} onChange={(e) => muda(p, i, 'max', e.target.value)} />
                  → R$ <input className="input num w-20 py-1" placeholder="+0,02" value={f.rs_l} onChange={(e) => muda(p, i, 'rs_l', e.target.value)} />/L
                  <button className="text-stone-400 hover:text-critico" onClick={() => setTabela({ ...tabela, [p]: tabela[p].filter((_, j) => j !== i) })}>✕</button>
                </div>
              ))}
              <button className="text-xs text-campo-600 hover:underline" onClick={() => setTabela({ ...tabela, [p]: [...(tabela[p] ?? []), { min: '', max: '', rs_l: '' }] })}>+ faixa</button>
            </div>
          ))}
          <p className="text-xs text-stone-500">Deixe "de" ou "até" vazio para faixa aberta. Valores negativos são penalização.</p>
          {erro && <Erro msg={erro} />}
          {msg && <div className="rounded-lg bg-campo-50 p-2 text-sm text-campo-700">{msg}</div>}
          <button className="btn-primario" onClick={salvar}>Salvar tabela</button>
        </div>
      )}
    </Painel>
  )
}

const SITUACAO: Record<string, string> = {
  atual: 'bg-campo-100 text-campo-700', desatualizado: 'bg-amber-50 text-atencao ring-1 ring-amber-200',
  'aguardando coleta': 'bg-stone-100 text-stone-600', 'sem fonte pública': 'bg-stone-100 text-stone-500',
}

/** Situação das cotações públicas usadas como preço de referência. */
function FontesReferencia({ onAtualizado }: { onAtualizado: () => void }) {
  const [d, setD] = useState<any>(null)
  const [rodando, setRodando] = useState(false)
  const [aberto, setAberto] = useState(false)
  const carregar = () => api.get('/referencias').then(setD).catch(() => setD(null))
  useEffect(() => { carregar() }, [])
  const atualizar = async () => {
    setRodando(true)
    try { await api.post('/referencias/atualizar', {}); await carregar(); onAtualizado() } finally { setRodando(false) }
  }
  if (!d) return null
  const ult = d.ultima_coleta
  const falhas = ult ? Object.entries(ult.resultado).filter(([, r]: any) => !r.ok) : []
  const comFonte = d.itens.filter((i: any) => i.fontes.length)
  return (
    <Painel titulo="Fontes de referência (atualização diária)"
      subtitulo={`${comFonte.length} de ${d.itens.length} itens têm cotação pública. Os demais ficam com valor de demonstração até a fazenda informar o seu preço.`}
      acoes={<div className="flex items-center gap-2">
        <button className="btn-secundario py-1.5" aria-expanded={aberto} onClick={() => setAberto(!aberto)}>{aberto ? 'Ocultar detalhes' : 'Ver detalhes'}</button>
        <button className="btn-secundario py-1.5" onClick={atualizar} disabled={rodando}>{rodando ? 'Coletando…' : 'Atualizar agora'}</button>
      </div>}>
      <p className="mb-1 text-xs text-stone-500">Cotações oficiais/reconhecidas, acessadas sem login: Cepea/Esalq-USP (milho, diário; leite ao produtor MG, mensal — licença CC BY-NC 4.0) e Seab/Deral-PR via IPEADATA (farelo de soja, mensal). Silagens, capins, cana, núcleo mineral, polpa, farelo de trigo, caroço de algodão e ureia pecuária não têm cotação pública confiável e diária.</p>
      <p className="text-sm text-stone-600">
        Última coleta: <b>{ult ? new Date(ult.inicio).toLocaleString('pt-BR') : 'nunca'}</b>
        {falhas.length > 0 && <span className="ml-2 text-atencao">· {falhas.length} fonte(s) indisponível(is) — mantidos os últimos valores válidos</span>}
      </p>
      {aberto && (
        <div className="mt-3 overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-xs text-stone-500"><tr><th className="py-1 pr-3">Item</th><th className="pr-3">Situação</th><th className="pr-3">Cotação</th><th className="pr-3">Data</th><th>Fonte</th></tr></thead>
            <tbody>
              {d.itens.map((i: any) => (
                <tr key={i.id} className="border-t border-stone-100">
                  <td className="py-1.5 pr-3 text-stone-800">{i.nome}</td>
                  <td className="pr-3"><span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${SITUACAO[i.situacao] ?? ''}`}>{i.situacao}</span></td>
                  <td className="num pr-3 text-xs">{i.vigente ? <>R$ {brl(i.vigente.preco)}/{i.id === 'leite' ? 'L' : 'kg'} <span className="text-stone-400">({i.vigente.valor_original.toLocaleString('pt-BR')} {i.vigente.unidade_original})</span></> : '—'}</td>
                  <td className="pr-3 text-xs text-stone-500">{i.vigente ? `${dataBR(i.vigente.data_cotacao)}${i.idade_dias ? ` (${i.idade_dias} d)` : ''}` : '—'}</td>
                  <td className="text-xs text-stone-500">{i.vigente ? (i.vigente.url ? <a className="text-campo-600 hover:underline" href={i.vigente.url} target="_blank" rel="noreferrer">{i.vigente.fonte}</a> : i.vigente.fonte) : (i.fontes.join(', ') || '—')}{i.vigente?.praca ? ` · ${i.vigente.praca}` : ''}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {falhas.length > 0 && <ul className="mt-2 text-xs text-stone-500">{falhas.map(([n, r]: any) => <li key={n}><b>{n}</b>: {r.erro}</li>)}</ul>}
        </div>
      )}
    </Painel>
  )
}

/** Cadastro/edição de insumo da fazenda, com prévia dos valores derivados para pegar erro de digitação. */
function FormularioInsumo({ fazendaId, inicial, codigo, onSalvo, onCancelar }: {
  fazendaId: number; inicial: FormInsumo; codigo?: string; onSalvo: () => void; onCancelar: () => void
}) {
  const [f, setF] = useState<FormInsumo>(inicial)
  const [erro, setErro] = useState('')
  const n = (v: string) => (v.trim() === '' ? null : Number(v.replace(',', '.')))
  const set = (k: keyof FormInsumo) => (e: any) => setF({ ...f, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value })
  const ndt = n(f.ndt), ms = n(f.ms), preco = n(f.preco_kg_mn)
  const soma = ['pb', 'fdn', 'ee', 'mm'].reduce((t, k) => t + (n((f as any)[k]) ?? 0), 0)
  const salvar = async () => {
    setErro('')
    const corpo = { nome: f.nome, tipo: f.tipo, origem_dado: f.origem_dado, fonte: f.fonte, ms: n(f.ms), pb: n(f.pb) ?? 0,
      fdn: n(f.fdn) ?? 0, ndt: n(f.ndt) ?? 0, ee: n(f.ee) ?? 0, mm: n(f.mm) ?? 0, fdnd: f.tipo === 'volumoso' ? n(f.fdnd) : null, max_pct_ms: n(f.max_pct_ms),
      pastejo: f.tipo === 'volumoso' && f.pastejo, preco_kg_mn: n(f.preco_kg_mn),
      ...Object.fromEntries(MINERAIS.map(([k]) => [k, n((f as any)[k])])) }
    if (corpo.ms === null) { setErro('Informe a matéria seca (MS).'); return }
    try {
      if (codigo) await api.put(`/fazendas/${fazendaId}/alimentos/${codigo}`, corpo)
      else await api.post(`/fazendas/${fazendaId}/alimentos`, corpo)
      onSalvo()
    } catch (e: any) { setErro(e.message) }
  }
  const campo = (k: keyof FormInsumo, rotulo: string, un: string) => (
    <label><span className="rotulo">{rotulo} <span className="text-stone-400">({un})</span></span>
      <input className="input num" inputMode="decimal" value={f[k] as string} onChange={set(k)} /></label>
  )
  return (
    <div className="space-y-3">
      <div className="grid gap-3 sm:grid-cols-4">
        <label className="sm:col-span-2"><span className="rotulo">Nome</span><input className="input" value={f.nome} onChange={set('nome')} placeholder="Ex.: Silagem de milho — silo 3" /></label>
        <label><span className="rotulo">Tipo</span>
          <select className="input" value={f.tipo} onChange={set('tipo')}>
            <option value="volumoso">Volumoso</option><option value="concentrado">Concentrado</option><option value="ureia">Ureia / NNP</option><option value="mineral">Mineral</option>
          </select></label>
        <label><span className="rotulo">Origem dos dados</span>
          <select className="input" value={f.origem_dado} onChange={set('origem_dado')}>
            {Object.entries(ORIGEM_DADO).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select></label>
      </div>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {campo('ms', 'Matéria seca', '% MN')}{campo('pb', 'Proteína bruta', '% MS')}{campo('fdn', 'FDN', '% MS')}{campo('ndt', 'NDT', '% MS')}
        {campo('ee', 'Gordura (EE)', '% MS')}{campo('mm', 'Matéria mineral', '% MS')}{campo('max_pct_ms', 'Inclusão máxima', '% MS, opcional')}
        {campo('preco_kg_mn', codigo ? 'Novo preço (opcional)' : 'Preço', 'R$/kg MN')}
        {f.tipo === 'volumoso' && campo('fdnd', 'Digestibilidade da FDN', '% da FDN, opcional')}
      </div>
      <details className="rounded-lg border border-stone-200 p-3" open={MINERAIS.some(([k]) => (f as any)[k])}>
        <summary className="cursor-pointer text-sm font-medium text-stone-700">Minerais (opcional, % da MS) — Na, K, Cl e S permitem verificar a DCAD do pré-parto</summary>
        <div className="mt-2 grid grid-cols-4 gap-3 sm:grid-cols-7">
          {MINERAIS.map(([k, r]) => <span key={k}>{campo(k as keyof FormInsumo, r, '% MS')}</span>)}
        </div>
      </details>
      <div className="grid gap-3 sm:grid-cols-[1fr_auto]">
        <label><span className="rotulo">Fonte</span><input className="input" value={f.fonte} onChange={set('fonte')} placeholder="Ex.: laudo bromatológico nº, tabela CQBAL, fornecedor" /></label>
        {f.tipo === 'volumoso' && (
          <label className="flex items-end gap-2 pb-2 text-sm text-stone-700"><input type="checkbox" className="accent-campo-600" checked={f.pastejo} onChange={set('pastejo')} />forragem de pastejo</label>
        )}
      </div>
      <p className="rounded-lg bg-stone-50 px-3 py-2 text-xs text-stone-600">
        Prévia: ELl ≈ <b>{ndt ? (0.0245 * ndt - 0.12).toFixed(2) : '—'}</b> Mcal/kg MS ·
        CNF ≈ <b className={soma > 100 ? 'text-critico' : ''}>{f.tipo === 'volumoso' || f.tipo === 'concentrado' ? (100 - soma).toFixed(1) : '—'}</b>% MS ·
        custo <b>{preco && ms ? `R$ ${(preco / (ms / 100)).toFixed(2)}` : '—'}</b>/kg MS ·
        confiança nas regras: <b>{f.origem_dado === 'laboratorio' ? 'alta (CF 1,0)' : f.origem_dado === 'tabela' ? 'média (CF 0,8)' : 'baixa (CF 0,6)'}</b>
      </p>
      {erro && <Erro msg={erro} />}
      <div className="flex gap-2">
        <button className="btn-primario" onClick={salvar}>{codigo ? 'Salvar alterações' : 'Cadastrar insumo'}</button>
        <button className="btn-secundario" onClick={onCancelar}>Cancelar</button>
      </div>
    </div>
  )
}

export default function PrecosPagina({ fazendaId = 1 }: { fazendaId?: number }) {
  const [refLeite, setRefLeite] = useState<any>(null)
  const [dados, setDados] = useState<Dados | null>(null)
  const [catalogo, setCatalogo] = useState<Record<string, Alimento>>({})
  const [formulario, setFormulario] = useState<{ codigo?: string; inicial: FormInsumo } | null>(null)
  const [novos, setNovos] = useState<Record<string, string>>({})
  const [fonte, setFonte] = useState('')
  const [data, setData] = useState(hojeLocal())
  const [aberto, setAberto] = useState<string | null>(null)
  const [erro, setErro] = useState('')
  const [ok, setOk] = useState('')

  const carregar = () => {
    api.get<any>('/referencias').then((r) => setRefLeite(r.itens.find((i: any) => i.id === 'leite')?.vigente ?? null)).catch(() => {})
    api.get<Dados>(`/fazendas/${fazendaId}/precos`).then(setDados).catch((e) => setErro(e.message))
    api.get<Alimento[]>(`/fazendas/${fazendaId}/alimentos?incluir_inativos=true`).then((l) => setCatalogo(Object.fromEntries(l.map((a) => [a.id, a]))))
  }
  useEffect(carregar, [fazendaId])  // eslint-disable-line react-hooks/exhaustive-deps
  const editar = (a: Alimento) => setFormulario({ codigo: a.id, inicial: {
    nome: a.nome, tipo: a.tipo, origem_dado: a.origem_dado ?? 'tabela', fonte: a.fonte ?? '', ms: String(a.ms), pb: String(a.pb),
    fdn: String(a.fdn), ndt: String(a.ndt), ee: String(a.ee), mm: String(a.mm ?? 0), fdnd: (a as any).fdnd != null ? String((a as any).fdnd) : '', max_pct_ms: a.max_pct_ms != null ? String(a.max_pct_ms) : '',
    pastejo: !!a.pastejo, preco_kg_mn: '',
    ...Object.fromEntries(MINERAIS.map(([k]) => [k, (a as any)[k] != null ? String((a as any)[k]) : ''])) as any } })
  const alternar = async (codigo: string, acao: 'desativar' | 'reativar') => {
    if (acao === 'desativar' && !window.confirm('Desativar este insumo? Ele sai das listas de escolha; dietas antigas continuam válidas.')) return
    await api.post(`/fazendas/${fazendaId}/alimentos/${codigo}/${acao}`, {}); carregar()
  }
  const desativados = Object.values(catalogo).filter((a) => a.da_fazenda && a.ativo === false)

  const alterados = Object.entries(novos).filter(([, v]) => v.trim() !== '')
  const salvar = async () => {
    setErro(''); setOk('')
    const precos = Object.fromEntries(alterados.map(([k, v]) => [k, Number(v.replace(',', '.'))]))
    if (Object.values(precos).some((v) => !(v > 0))) { setErro('Informe preços maiores que zero.'); return }
    try {
      setDados(await api.put<Dados>(`/fazendas/${fazendaId}/precos`, { precos, fonte, data }))
      setNovos({}); setOk(`${alterados.length} preço(s) atualizado(s). A verificação, a sugestão de dieta e o acompanhamento já usam os novos valores.`)
    } catch (e: any) { setErro(e.message) }
  }

  if (erro && !dados) return <Erro msg={erro} />
  if (!dados) return <Carregando texto="Carregando preços…" />

  const entrada = (id: string) => (
    <input className="input num w-24 py-1" inputMode="decimal" placeholder="novo" value={novos[id] ?? ''}
      onChange={(e) => setNovos({ ...novos, [id]: e.target.value })} />
  )
  const origem = (l: Linha) => l.origem === 'fazenda'
    ? <span className="rounded-full bg-campo-100 px-2 py-0.5 text-xs font-semibold text-campo-700">da fazenda</span>
    : <span className="rounded-full bg-amber-50 px-2 py-0.5 text-xs font-semibold text-atencao ring-1 ring-amber-200" title="Valor de demonstração, sem fonte">referência</span>

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3 border-b border-stone-300/70 pb-4">
        <div className="max-w-3xl">
          <h1 className="titulo text-[2rem] font-semibold leading-[1.05] text-stone-900">Insumos e preços</h1>
          <p className="mt-1 text-sm text-stone-500">
            Os alimentos da <b>base de conhecimento</b> têm composição do CQBAL 4.0. O preço de <b>referência</b> vem
            de cotação pública atualizada diariamente quando existe (Cepea/Esalq-USP, Deral-PR); nos demais itens é um valor
            de demonstração. Cadastre os insumos da fazenda e informe os preços dela: eles têm prioridade sobre a referência
            na verificação da dieta, na sugestão de custo mínimo e no acompanhamento.
          </p>
        </div>
        {!formulario && <button className="btn-primario" onClick={() => setFormulario({ inicial: { ...VAZIO } })}>Cadastrar insumo</button>}
      </div>
      {formulario && (
        <Painel titulo={formulario.codigo ? 'Editar insumo da fazenda' : 'Cadastrar insumo da fazenda'}
          subtitulo="MS em % da matéria natural; demais nutrientes em % da matéria seca (como vêm no laudo bromatológico).">
          <FormularioInsumo fazendaId={fazendaId} inicial={formulario.inicial} codigo={formulario.codigo}
            onSalvo={() => { setFormulario(null); setOk(formulario.codigo ? 'Insumo atualizado.' : 'Insumo cadastrado: já aparece nas dietas e na sugestão de custo mínimo.'); carregar() }}
            onCancelar={() => setFormulario(null)} />
        </Painel>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        {([['leite', 'Leite', 'R$/L', dados.leite], ['concentrado', 'Concentrado (mistura do cocho)', 'R$/kg', dados.concentrado]] as const).map(([id, nome, un, l]) => (
          <Painel key={id} titulo={nome} subtitulo={l.data ? `Atualizado em ${dataBR(l.data)}${l.fonte ? ` · ${l.fonte}` : ''}` : 'Valor inicial da fazenda'}>
            <div className="flex items-center justify-between gap-3">
              <span className="titulo num text-[2.2rem] font-semibold leading-none text-stone-900">R$ {brl(l.preco)}<span className="ml-1 text-sm font-normal text-stone-500">{un.replace('R$', '')}</span></span>
              {entrada(id)}
            </div>
            {id === 'leite' && refLeite && (
              <p className="mt-2 text-xs text-stone-500">
                Referência: <b className="num">R$ {brl(refLeite.preco)}/L</b> · {refLeite.praca} · {new Date(refLeite.data_cotacao + 'T12:00').toLocaleDateString('pt-BR', { month: 'short', year: 'numeric' })} ·{' '}
                <a className="text-campo-600 hover:underline" href={refLeite.url} target="_blank" rel="noreferrer">Fonte: Cepea/Esalq-USP</a>
              </p>
            )}
          </Painel>
        ))}
      </div>

      <Bonificacao fazendaId={fazendaId} />
      <FontesReferencia onAtualizado={carregar} />

      <Painel titulo="Alimentos" subtitulo="Preço por kg de matéria natural (como comprado). A sugestão de dieta compara o custo por kg de matéria seca.">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-xs text-stone-500">
              <tr><th className="py-1 pr-3">Alimento</th><th className="pr-3">Composição (% MS)</th><th className="pr-3">Preço atual (R$/kg MN)</th><th className="pr-3">R$/kg MS</th><th className="pr-3">Referência</th><th className="pr-3">Atualizado</th><th>Novo preço</th></tr>
            </thead>
            <tbody>
              {dados.alimentos.map((l) => (
                <Fragment key={l.id}>
                  <tr className="border-t border-stone-100 align-middle">
                    <td className="py-2 pr-3">
                      <div className="font-medium text-stone-800">{l.nome}
                        {l.da_fazenda && <span className="ml-1.5 rounded bg-campo-100 px-1.5 py-0.5 text-[10px] font-semibold text-campo-700">insumo da fazenda</span>}
                      </div>
                      <div className="text-xs text-stone-400">{TIPO[l.tipo ?? ''] ?? l.tipo} · MS {l.ms}%
                        {catalogo[l.id] && ` · ${l.da_fazenda ? ORIGEM_DADO[catalogo[l.id].origem_dado ?? ''] ?? '' : 'tabela CQBAL'}`}</div>
                      {l.da_fazenda && catalogo[l.id] && (
                        <div className="mt-0.5 flex gap-3 text-xs">
                          <button className="text-campo-600 hover:underline" onClick={() => editar(catalogo[l.id])}>editar</button>
                          <button className="text-stone-500 hover:text-critico hover:underline" onClick={() => alternar(l.id, 'desativar')}>desativar</button>
                        </div>
                      )}
                    </td>
                    <td className="num pr-3 text-xs text-stone-600">
                      {catalogo[l.id] ? <>PB {catalogo[l.id].pb} · FDN {catalogo[l.id].fdn}<br />NDT {catalogo[l.id].ndt} · EE {catalogo[l.id].ee}</> : '—'}
                    </td>
                    <td className="num pr-3"><span className="mr-2 font-semibold">{brl(l.preco)}</span>{origem(l)}</td>
                    <td className="num pr-3 text-stone-600">{l.ms ? brl(l.preco / (l.ms / 100)) : '—'}</td>
                    <td className="num pr-3 text-stone-400">
                      {l.preco_referencia !== null ? brl(l.preco_referencia) : '—'}
                      {catalogo[l.id]?.preco_ref && !l.da_fazenda && (
                        <div className="max-w-40 text-[11px] leading-tight">{catalogo[l.id].preco_ref!.data ? `${catalogo[l.id].preco_ref!.fonte} · ${dataBR(catalogo[l.id].preco_ref!.data)}` : 'demonstração'}</div>
                      )}
                    </td>
                    <td className="pr-3 text-xs text-stone-500">
                      {dataBR(l.data)}{l.fonte && <div>{l.fonte}</div>}
                      {l.historico.length > 1 && <button className="text-campo-600 hover:underline" onClick={() => setAberto(aberto === l.id ? null : l.id)}>histórico ({l.historico.length})</button>}
                    </td>
                    <td>{entrada(l.id)}</td>
                  </tr>
                  {aberto === l.id && (
                    <tr><td colSpan={7} className="bg-stone-50 px-3 py-2 text-xs text-stone-600">
                      {l.historico.map((h, i) => <span key={i} className="mr-4 num">{dataBR(h.data)}: <b>R$ {brl(h.preco)}</b>{h.fonte && ` (${h.fonte})`}</span>)}
                    </td></tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      </Painel>

      {desativados.length > 0 && (
        <Painel titulo="Insumos desativados" subtitulo="Fora das listas de escolha; dietas antigas que os usam continuam válidas.">
          {desativados.map((a) => (
            <div key={a.id} className="flex items-center justify-between border-b border-stone-100 py-2 text-sm last:border-0">
              <span className="text-stone-600">{a.nome}</span>
              <button className="text-campo-600 hover:underline" onClick={() => alternar(a.id, 'reativar')}>reativar</button>
            </div>
          ))}
        </Painel>
      )}

      <div className="card sticky bottom-3 flex flex-wrap items-end gap-3 border-campo-500/40 p-4 shadow-[0_8px_24px_-12px_rgba(20,42,26,0.35)]">
        <label><span className="rotulo">Data dos preços</span><input type="date" className="input" value={data} onChange={(e) => setData(e.target.value)} /></label>
        <label className="min-w-56 flex-1"><span className="rotulo">Fonte</span><input className="input" placeholder="Ex.: nota fiscal, cotação da cooperativa, Cepea" value={fonte} onChange={(e) => setFonte(e.target.value)} /></label>
        <button className="btn-primario" onClick={salvar} disabled={!alterados.length}>Salvar {alterados.length || ''} preço(s)</button>
        {erro && <div className="w-full"><Erro msg={erro} /></div>}
        {ok && <div className="w-full rounded-lg bg-campo-50 p-2 text-sm text-campo-700">{ok}</div>}
      </div>
    </div>
  )
}
