/** Modo campo (celular): registro rápido do dia e avisos pendentes. Funciona sem conexão: o registro fica numa
 * fila no aparelho e é enviado quando a API volta a responder. */
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, NavLink, Route, Routes, useNavigate, useSearchParams } from 'react-router-dom'
import { api, dataBR, ErroApi, numero, peso, textoAlerta, type Alerta, type Lote } from '../api'
import { EscalaEscore } from '../components/Escala'
import { AlertaCorpo, BORDA_NIVEL, Brinco, Icone, NivelBadge } from '../components/ui'

// ------------------------------------------------------------------ fila offline (localStorage)
interface Pendente { id: string; caminho: string; corpo: any; descricao: string; criado: string }
const CHAVE_FILA = 'campo_fila'
const CHAVE_LOTES = 'campo_lotes'

function lerJSON<T>(chave: string, padrao: T): T {
  try { return JSON.parse(localStorage.getItem(chave) ?? '') as T } catch { return padrao }
}
function gravarJSON(chave: string, valor: unknown) {
  try { localStorage.setItem(chave, JSON.stringify(valor)) } catch { /* armazenamento indisponível */ }
}
/** Falha de rede (fetch não completou) ou API inalcançável: o registro vai para a fila do aparelho. */
const semConexao = (e: any) => e instanceof TypeError || (e instanceof ErroApi && e.semConexao)

/** Envia já; se a API não responder, guarda na fila do aparelho. */
async function enviarOuEnfileirar(caminho: string, corpo: any, descricao: string): Promise<{ enviado: boolean; resposta?: any }> {
  try {
    return { enviado: true, resposta: await api.post(caminho, corpo) }
  } catch (e: any) {
    if (!semConexao(e)) throw e
    const fila = lerJSON<Pendente[]>(CHAVE_FILA, [])
    fila.push({ id: `${Date.now()}-${Math.random()}`, caminho, corpo, descricao, criado: new Date().toISOString() })
    gravarJSON(CHAVE_FILA, fila)
    return { enviado: false }
  }
}

function useFila() {
  const [fila, setFila] = useState<Pendente[]>(() => lerJSON(CHAVE_FILA, []))
  const [enviando, setEnviando] = useState(false)
  const sincronizar = useCallback(async () => {
    const atual = lerJSON<Pendente[]>(CHAVE_FILA, [])
    if (!atual.length) { setFila([]); return }
    setEnviando(true)
    const restantes: Pendente[] = []
    for (const p of atual) {     // em ordem: registros retroativos reprocessam os dias seguintes
      try { await api.post(p.caminho, p.corpo) } catch (e: any) { if (semConexao(e)) restantes.push(p) }
    }
    gravarJSON(CHAVE_FILA, restantes)
    setFila(restantes)
    setEnviando(false)
  }, [])
  useEffect(() => {
    sincronizar()
    window.addEventListener('online', sincronizar)
    const t = setInterval(sincronizar, 60_000)
    return () => { window.removeEventListener('online', sincronizar); clearInterval(t) }
  }, [sincronizar])
  return { fila, enviando, sincronizar, recarregar: () => setFila(lerJSON(CHAVE_FILA, [])) }
}

// ------------------------------------------------------------------ layout
export default function CampoPagina() {
  const fila = useFila()
  const [lotes, setLotes] = useState<Lote[]>(() => lerJSON(CHAVE_LOTES, []))
  const [pendentes, setPendentes] = useState<Alerta[]>([])
  const carregar = useCallback(() => {
    api.get<Lote[]>('/lotes').then((l) => { setLotes(l); gravarJSON(CHAVE_LOTES, l) }).catch(() => {})
    api.get<Alerta[]>('/alertas?estado=pendentes&incluir_suprimidos=false').then(setPendentes).catch(() => {})
  }, [])
  useEffect(carregar, [carregar])
  const importantes = pendentes.filter((a) => a.nivel !== 'informativo').length
  const aba = ({ isActive }: { isActive: boolean }) =>
    `relative flex flex-1 flex-col items-center gap-1 pt-2.5 pb-2 text-xs font-semibold ${isActive ? 'text-campo-700 before:absolute before:inset-x-6 before:top-0 before:h-[3px] before:rounded-b before:bg-brinco' : 'text-stone-500'}`
  return (
    <div className="min-h-screen pb-[calc(5rem+env(safe-area-inset-bottom,0px))]">
      <header className="sticky top-0 z-20 bg-campo-900 pt-[env(safe-area-inset-top,0px)] text-white">
        <div className="flex items-center justify-between px-4 py-3">
          <span className="flex items-center gap-2">
            <svg viewBox="0 0 40 50" className="h-7 w-[22px]" aria-hidden="true"><path d="M20 1.5c-4.6 0-8 3-8.6 7.2L6.2 41.4C5.6 45.3 8.6 48.5 12.6 48.5h14.8c4 0 7-3.2 6.4-7.1L28.6 8.7C28 4.5 24.6 1.5 20 1.5z" fill="var(--color-brinco)" /><circle cx="20" cy="10" r="3.2" fill="var(--color-campo-900)" /></svg>
            <span className="titulo text-xl font-bold tracking-wide">CochoCerto</span>
            <span className="rounded bg-white/10 px-1.5 py-0.5 text-[11px] font-semibold text-campo-100">campo</span>
          </span>
          <Link to="/?completo=1" className="text-[13px] text-campo-100/80 underline underline-offset-2">versão completa</Link>
        </div>
      </header>
      {fila.fila.length > 0 && (
        <div className="flex items-center justify-between gap-2 border-b border-brinco/60 bg-brinco-claro px-4 py-2.5 text-sm text-stone-800">
          <span>{fila.fila.length} registro(s) guardado(s) no aparelho, aguardando conexão.</span>
          <button className="font-semibold underline" onClick={fila.sincronizar} disabled={fila.enviando}>{fila.enviando ? 'enviando…' : 'enviar agora'}</button>
        </div>
      )}
      <main className="mx-auto max-w-lg px-4 py-4">
        <Routes>
          <Route index element={<Registrar lotes={lotes} onEnviado={() => { fila.recarregar(); carregar() }} />} />
          <Route path="avisos" element={<Avisos alertas={pendentes} lotes={lotes} onMudou={carregar} />} />
          <Route path="trato" element={<Trato lotes={lotes} onEnviado={fila.recarregar} />} />
        </Routes>
      </main>
      <nav className="fixed inset-x-0 bottom-0 z-20 flex border-t border-stone-200 bg-white pb-[env(safe-area-inset-bottom,0px)]">
        <NavLink end to="/campo" className={aba}><Icone nome="lapis" className="h-6 w-6" />Registrar</NavLink>
        <NavLink to="/campo/trato" className={aba}><Icone nome="trato" className="h-6 w-6" />Trato</NavLink>
        <NavLink to="/campo/avisos" className={aba}>
          <span className="relative"><Icone nome="sino" className="h-6 w-6" />{importantes > 0 && <span className="absolute -right-2.5 -top-1 min-w-[18px] rounded-full bg-critico px-1 text-center text-[10px] font-bold leading-[18px] text-white">{importantes}</span>}</span>Avisos
        </NavLink>
      </nav>
    </div>
  )
}

/** Botão de escolha do lote: o brinco com o número e o nome curto. */
function BotaoLote({ lote, ativo, onClick }: { lote: Lote; ativo: boolean; onClick: () => void }) {
  const [, desc] = lote.nome.split(' — ')
  return (
    <button onClick={onClick} aria-pressed={ativo}
      className={`flex min-w-0 items-center gap-2.5 rounded-[10px] border px-2.5 py-2 text-left transition-colors ${ativo ? 'border-campo-600 bg-campo-600 text-white' : 'border-stone-300 bg-white text-stone-800'}`}>
      <Brinco nome={lote.nome} id={lote.id} tamanho="sm" />
      <span className="min-w-0 truncate text-sm font-semibold leading-tight">{desc ?? lote.nome}</span>
    </button>
  )
}

// ------------------------------------------------------------------ registrar
const EVENTOS: [string, string][] = [
  ['troca_volumoso', 'Troca de volumoso'], ['correcao_ms', 'Correção de MS'], ['movimentacao', 'Entrada/saída de vacas'],
  ['mudanca_concentrado', 'Mudança de concentrado'], ['manejo_calor', 'Manejo de calor'], ['manejo_sanitario', 'Manejo sanitário'],
  ['conferencia', 'Conferência de ordenha'], ['secagem', 'Secagem'], ['manejo_pasto', 'Manejo do pasto'], ['outro', 'Outro'],
]

function Numero({ rotulo, un, valor, onChange, dica }: { rotulo: string; un: string; valor: string; onChange: (v: string) => void; dica?: string }) {
  return (
    <label className="block">
      <span className="mb-1 block text-sm font-medium text-stone-700">{rotulo} <span className="font-normal text-stone-400">({un})</span></span>
      <input className="input num titulo py-2.5 text-2xl font-semibold" inputMode="decimal" value={valor} onChange={(e) => onChange(e.target.value)} placeholder={dica} />
    </label>
  )
}

function Registrar({ lotes, onEnviado }: { lotes: Lote[]; onEnviado: () => void }) {
  const [params, setParams] = useSearchParams()
  const hoje = new Date().toISOString().slice(0, 10)
  const ontem = new Date(Date.now() - 864e5).toISOString().slice(0, 10)
  const [loteId, setLoteId] = useState<number | null>(() => Number(params.get('lote')) || lerJSON<number | null>('campo_lote', null))
  const [data, setData] = useState(hoje)
  const [v, setV] = useState<Record<string, string>>({})
  const [anterior, setAnterior] = useState<Record<string, number>>({})
  const [mais, setMais] = useState<'' | 'semanal' | 'laudo' | 'evento'>(params.get('evento') ? 'evento' : '')
  const [evento, setEvento] = useState({ tipo: params.get('evento') ?? 'outro', descricao: '' })
  const alertaId = params.get('alerta')
  const [confirmar, setConfirmar] = useState<string[]>([])
  const [resultado, setResultado] = useState<{ ok: boolean; texto: string; alertas?: Alerta[] } | null>(null)
  const [erro, setErro] = useState('')
  const lote = lotes.find((l) => l.id === loteId)
  const [clima, setClima] = useState<any>(null)
  const [climaManual, setClimaManual] = useState(false)     // digitou à mão: a meteorologia não sobrescreve
  const set = (k: string) => (x: string) => {
    if (k === 'temp' || k === 'ur') setClimaManual(true)
    setV({ ...v, [k]: x })
  }

  // temperatura e umidade médias do dia, da meteorologia, quando houver conexão
  useEffect(() => {
    if (!lote) return
    let cancelado = false
    setClima({ carregando: true })
    api.get<any>(`/clima/${lote.fazenda_id}?data=${data}`)
      .then((c) => {
        if (cancelado) return
        setClima(c)
        if (c.disponivel && !climaManual) setV((atual) => ({ ...atual, temp: String(c.temp), ur: String(c.ur) }))
      })
      .catch(() => { if (!cancelado) setClima({ disponivel: false, motivo: 'sem conexão com a meteorologia' }) })
    return () => { cancelado = true }
  }, [lote?.fazenda_id, data])  // eslint-disable-line react-hooks/exhaustive-deps
  const usarMeteorologia = () => { if (clima?.disponivel) { setClimaManual(false); setV({ ...v, temp: String(clima.temp), ur: String(clima.ur) }) } }

  useEffect(() => {   // último valor de cada indicador do lote: base para pré-preencher e conferir digitação
    if (!loteId) return
    gravarJSON('campo_lote', loteId)
    api.get<{ data: string; indicador: string; valor: number }[]>(`/lotes/${loteId}/registros?desde=${new Date(Date.now() - 10 * 864e5).toISOString().slice(0, 10)}`)
      .then((regs) => {
        const ult: Record<string, number> = {}
        regs.forEach((r) => { if (r.data < data) ult[r.indicador] = r.valor })
        setAnterior(ult)
        setV((atual) => ({ vacas: atual.vacas || (ult.vacas ? String(ult.vacas) : ''), ...atual }))
      }).catch(() => setAnterior({}))
  }, [loteId, data])

  const num = (x?: string) => (x && x.trim() !== '' ? Number(x.replace(',', '.')) : null)
  const valores = useMemo(() => Object.fromEntries(Object.entries(v).map(([k, x]) => [k, num(x)]).filter(([, x]) => x !== null && !Number.isNaN(x))), [v])

  /** Valores muito diferentes do último registro: provável erro de digitação, pedir confirmação. */
  const suspeitos = () => {
    const out: string[] = []
    const lv = valores.litros, va = valores.vacas ?? anterior.vacas
    if (lv && va && anterior.litros && anterior.vacas) {
      const hojeV = lv / va, antes = anterior.litros / anterior.vacas
      if (Math.abs(hojeV / antes - 1) > 0.3) out.push(`Litros/vaca ${hojeV.toFixed(1)} contra ${antes.toFixed(1)} no último registro`)
    }
    if (valores.vacas && anterior.vacas && Math.abs(valores.vacas / anterior.vacas - 1) > 0.3) out.push(`${valores.vacas} vacas contra ${anterior.vacas} no último registro`)
    if (valores.concentrado_kg_vaca && anterior.concentrado_kg_vaca && Math.abs(valores.concentrado_kg_vaca / anterior.concentrado_kg_vaca - 1) > 0.5)
      out.push(`Concentrado ${valores.concentrado_kg_vaca} kg contra ${anterior.concentrado_kg_vaca} kg`)
    return out
  }

  const enviar = async (confirmado = false) => {
    setErro(''); setResultado(null)
    if (!lote) { setErro('Escolha o lote.'); return }
    const temValores = Object.keys(valores).length > 0
    const temEvento = mais === 'evento' && evento.descricao.trim()
    if (!temValores && !temEvento) { setErro('Preencha ao menos um valor ou descreva o evento.'); return }
    if (!confirmado) {
      const s = suspeitos()
      if (s.length) { setConfirmar(s); return }
    }
    setConfirmar([])
    try {
      const partes: string[] = []
      let alertas: Alerta[] | undefined
      let offline = false
      if (temValores) {
        const r = await enviarOuEnfileirar(`/lotes/${lote.id}/registros`, { data, valores, alerta_id: alertaId && !temEvento ? Number(alertaId) : null },
          `${lote.nome} · ${dataBR(data)}`)
        offline ||= !r.enviado
        if (r.enviado) alertas = r.resposta?.alertas?.filter((a: Alerta) => a.status === 'ativo' && a.nivel !== 'informativo')
        partes.push(`${Object.keys(valores).length} valor(es)`)
      }
      if (temEvento) {
        const hora = data === hoje ? new Date().toTimeString().slice(0, 5) : '08:00'
        const r = await enviarOuEnfileirar(`/lotes/${lote.id}/eventos`, { data_hora: `${data}T${hora}:00`, ...evento, alerta_id: alertaId ? Number(alertaId) : null },
          `${lote.nome} · evento`)
        offline ||= !r.enviado
        partes.push('1 evento')
      }
      setResultado({ ok: true, alertas, texto: offline
        ? `Sem conexão: ${partes.join(' e ')} guardado(s) no aparelho. Será enviado quando a conexão voltar.`
        : `${partes.join(' e ')} registrado(s) para ${lote.nome}${alertaId ? ' e ligado(s) ao aviso aceito' : ''}.` })
      setV({ vacas: v.vacas ?? '', ...(clima?.disponivel ? { temp: String(clima.temp), ur: String(clima.ur) } : {}) })
      setClimaManual(false); setEvento({ tipo: 'outro', descricao: '' }); setMais('')
      if (alertaId) { params.delete('alerta'); params.delete('evento'); setParams(params, { replace: true }) }
      onEnviado()
    } catch (e: any) { setErro(e.message) }
  }

  return (
    <div className="space-y-4">
      {alertaId && <div className="rounded-[10px] border border-campo-500 border-l-[6px] border-l-campo-600 bg-campo-50 p-3 text-sm text-campo-900">Registrando a ação de um aviso aceito: descreva o que foi feito no evento abaixo.</div>}

      <div>
        <p className="titulo mb-2 text-lg font-semibold text-stone-900">Qual lote?</p>
        <div className="grid grid-cols-2 gap-2">
          {lotes.map((l) => (
            <BotaoLote key={l.id} lote={l} ativo={l.id === loteId} onClick={() => setLoteId(l.id)} />
          ))}
          {!lotes.length && <p className="text-sm text-stone-500">Sem lotes (conecte uma vez para carregar a lista).</p>}
        </div>
        
      </div>

      <div className="flex gap-2">
        {([[hoje, 'Hoje'], [ontem, 'Ontem']] as const).map(([d, r]) => (
          <button key={d} onClick={() => setData(d)} className={`flex-1 rounded-md border py-2.5 text-sm font-semibold ${data === d ? 'border-campo-600 bg-campo-600 text-white' : 'border-stone-300 bg-white text-stone-700'}`}>{r}</button>
        ))}
        <input type="date" className="input flex-1" value={data} max={hoje} onChange={(e) => setData(e.target.value)} />
      </div>

      <section className="card space-y-3 p-4">
        <div className="grid grid-cols-2 gap-3">
          <Numero rotulo="Vacas ordenhadas" un="nº" valor={v.vacas ?? ''} onChange={set('vacas')} />
          <Numero rotulo="Litros do lote" un="L" valor={v.litros ?? ''} onChange={set('litros')} dica={anterior.litros ? `último: ${anterior.litros.toLocaleString('pt-BR', { maximumFractionDigits: 0 })}` : ''} />
        </div>
        <Numero rotulo="Concentrado" un="kg/vaca" valor={v.concentrado_kg_vaca ?? ''} onChange={set('concentrado_kg_vaca')} dica={anterior.concentrado_kg_vaca ? `último: ${anterior.concentrado_kg_vaca}` : ''} />
        {lote?.sistema !== 'pasto' && <EscalaEscore tipo="cocho" valor={v.escore_cocho ?? ''} onChange={set('escore_cocho')} />}
        <div className="grid grid-cols-2 gap-3">
          <Numero rotulo="Temperatura média" un="°C" valor={v.temp ?? ''} onChange={set('temp')} />
          <Numero rotulo="Umidade média" un="%" valor={v.ur ?? ''} onChange={set('ur')} />
        </div>
        <p className="-mt-1 text-xs text-stone-500">
          {clima?.carregando ? 'Buscando a meteorologia…'
            : clima?.disponivel ? (
              climaManual
                ? <>Valores digitados. Meteorologia: {clima.temp} °C · {clima.ur}% — <button className="text-campo-600 underline" onClick={usarMeteorologia}>usar</button></>
                : <>🌤 Média do dia pela meteorologia ({clima.local}) · ITU {clima.itu}{clima.agora ? ` · agora ${clima.agora.temperature_2m} °C` : ''}</>
            ) : clima ? `${clima.motivo ?? 'Meteorologia indisponível'}: preencha se tiver termômetro.` : ''}
        </p>
      </section>

      <div className="grid grid-cols-3 gap-2">
        {([['semanal', 'Semanal'], ['laudo', 'Laudo'], ['evento', 'Evento']] as const).map(([k, r]) => (
          <button key={k} onClick={() => setMais(mais === k ? '' : k)} aria-pressed={mais === k} className={`rounded-md border py-2.5 text-sm font-semibold ${mais === k ? 'border-campo-600 bg-campo-50 text-campo-700' : 'border-stone-300 bg-white text-stone-600'}`}>{mais === k ? '−' : '+'} {r}</button>
        ))}
      </div>
      {mais === 'semanal' && (
        <section className="card space-y-4 p-4">
          <EscalaEscore tipo="ecc" valor={v.ecc ?? ''} onChange={set('ecc')} />
          <EscalaEscore tipo="fezes" valor={v.escore_fezes ?? ''} onChange={set('escore_fezes')} />
          <div className="grid grid-cols-2 gap-3">
            <Numero rotulo="MS da silagem" un="%" valor={v.ms_silagem ?? ''} onChange={set('ms_silagem')} />
            <Numero rotulo="Sobras pesadas" un="%" valor={v.sobras_pct ?? ''} onChange={set('sobras_pct')} />
            {(lote?.sistema === 'pasto' || lote?.sistema === 'semiconfinado') && <>
              <Numero rotulo="Altura entrada" un="cm" valor={v.altura_entrada ?? ''} onChange={set('altura_entrada')} />
              <Numero rotulo="Altura saída" un="cm" valor={v.altura_saida ?? ''} onChange={set('altura_saida')} />
              <Numero rotulo="Altura média" un="cm" valor={v.altura_media ?? ''} onChange={set('altura_media')} />
              <Numero rotulo="Caminhada" un="km/dia" valor={v.distancia_km ?? ''} onChange={set('distancia_km')} />
            </>}
          </div>
        </section>
      )}
      {mais === 'laudo' && (
        <section className="card grid grid-cols-2 gap-3 p-4">
          <Numero rotulo="Gordura" un="%" valor={v.laudo_gordura ?? ''} onChange={set('laudo_gordura')} />
          <Numero rotulo="Proteína" un="%" valor={v.laudo_proteina ?? ''} onChange={set('laudo_proteina')} />
          <Numero rotulo="Lactose" un="%" valor={v.laudo_lactose ?? ''} onChange={set('laudo_lactose')} />
          <Numero rotulo="NUL" un="mg/dL" valor={v.laudo_nul ?? ''} onChange={set('laudo_nul')} />
          <Numero rotulo="CCS" un="mil/mL" valor={v.laudo_ccs ?? ''} onChange={set('laudo_ccs')} />
          <Numero rotulo="CBT" un="mil UFC/mL" valor={v.laudo_cbt ?? ''} onChange={set('laudo_cbt')} />
        </section>
      )}
      {mais === 'evento' && (
        <section className="card space-y-3 p-4">
          <div className="flex flex-wrap gap-1.5">
            {EVENTOS.map(([k, r]) => (
              <button key={k} onClick={() => setEvento({ ...evento, tipo: k })}
                className={`rounded-full border px-2.5 py-1 text-xs ${evento.tipo === k ? 'border-campo-600 bg-campo-600 text-white' : 'border-stone-300 bg-white text-stone-700'}`}>{r}</button>
            ))}
          </div>
          <textarea className="input h-20" placeholder="O que foi feito (ex.: abri o silo 3; 5 vacas entraram do lote 2)" value={evento.descricao}
            onChange={(e) => setEvento({ ...evento, descricao: e.target.value })} />
        </section>
      )}

      {confirmar.length > 0 && (
        <div className="rounded-[10px] border border-brinco border-l-[6px] bg-brinco-claro p-3 text-sm">
          <p className="font-semibold text-stone-900">Conferir antes de enviar:</p>
          <ul className="ml-4 list-disc text-stone-800">{confirmar.map((c) => <li key={c}>{c}</li>)}</ul>
          <div className="mt-2 flex gap-2">
            <button className="btn-primario flex-1" onClick={() => enviar(true)}>Está certo, enviar</button>
            <button className="btn-secundario flex-1" onClick={() => setConfirmar([])}>Corrigir</button>
          </div>
        </div>
      )}
      {erro && <p className="rounded-lg bg-red-50 p-3 text-sm text-critico">{erro}</p>}
      {resultado && (
        <div className={`rounded-xl p-3 text-sm ${resultado.texto.startsWith('Sem conexão') ? 'bg-amber-50 text-amber-900' : 'bg-campo-50 text-campo-900'}`}>
          <p className="font-medium">{resultado.texto}</p>
          {resultado.alertas && resultado.alertas.length > 0 && (
            <div className="mt-2 space-y-1">
              {resultado.alertas.map((a) => <p key={a.regra} className="flex items-start gap-2"><NivelBadge nivel={a.nivel} /><span>{textoAlerta(a).titulo}</span></p>)}
              <Link to="/campo/avisos" className="font-semibold underline">ver avisos</Link>
            </div>
          )}
        </div>
      )}
      <button className="btn-primario titulo w-full py-4 text-xl" onClick={() => enviar()}>Enviar registro</button>
    </div>
  )
}

// ------------------------------------------------------------------ avisos
function Avisos({ alertas, lotes, onMudou }: { alertas: Alerta[]; lotes: Lote[]; onMudou: () => void }) {
  const navegar = useNavigate()
  const [verInformativos, setVerInformativos] = useState(false)
  const [aberto, setAberto] = useState<number | null>(null)
  const [recusando, setRecusando] = useState<number | null>(null)
  const [motivo, setMotivo] = useState('')
  const [erro, setErro] = useState('')
  const ordem = { critico: 0, atencao: 1, informativo: 2 }
  const lista = [...alertas].filter((a) => verInformativos || a.nivel !== 'informativo').sort((a, b) => ordem[a.nivel] - ordem[b.nivel])
  const nomeLote = (id?: number) => lotes.find((l) => l.id === id)?.nome.replace(/ — .*/, '') ?? ''

  const aceitar = async (a: Alerta) => {
    setErro('')
    try {
      const r = await api.post<{ destino: string }>(`/alertas/${a.id}/aceitar`, {})
      // ação registrada no campo (evento/registro): fica no modo campo; dieta: tela completa
      const url = new URL(r.destino, location.origin)
      if (url.pathname.endsWith('/registro')) {
        navegar(`/campo?lote=${a.lote_id}&alerta=${a.id}${url.searchParams.get('evento') ? `&evento=${url.searchParams.get('evento')}` : '&evento=outro'}`)
      } else navegar(r.destino)
    } catch (e: any) { setErro(semConexao(e) ? 'Sem conexão: aceite o aviso quando a conexão voltar.' : e.message) }
  }
  const recusar = async (a: Alerta) => {
    try { await api.post(`/alertas/${a.id}/recusar`, { motivo }); setRecusando(null); setMotivo(''); onMudou() }
    catch (e: any) { setErro(e.message) }
  }

  return (
    <div className="space-y-3">
      <div className="flex items-baseline justify-between">
        <h1 className="titulo text-2xl font-semibold text-stone-900">Avisos pendentes</h1>
        <button className="text-xs text-campo-600 underline" onClick={() => setVerInformativos(!verInformativos)}>{verInformativos ? 'ocultar informativos' : 'mostrar informativos'}</button>
      </div>
      {erro && <p className="rounded-lg bg-red-50 p-3 text-sm text-critico">{erro}</p>}
      {lista.length === 0 && <p className="rounded-[10px] border border-campo-100 bg-campo-50 p-4 text-sm text-campo-800">Nenhum aviso pendente. Os lotes estão dentro do esperado.</p>}
      {lista.map((a) => (
        <article key={a.id} className={`card border-l-4 p-3.5 ${BORDA_NIVEL[a.nivel]}`}>
          <p className="flex items-center gap-1.5 text-[13px] font-medium text-stone-500"><Brinco nome={nomeLote(a.lote_id)} id={a.lote_id} tamanho="sm" />{nomeLote(a.lote_id)}{a.estado === 'aceito' && ' · aceito, aguardando ação'}</p>
          <button className="mt-0.5 w-full text-left" onClick={() => setAberto(aberto === a.id ? null : a.id!)}>
            <p className="font-semibold leading-snug text-stone-900">{textoAlerta(a).titulo}</p>
            <p className="mt-1 text-sm text-campo-700">{textoAlerta(a).acao}</p>
          </button>
          {aberto === a.id && <div className="mt-2 border-t border-stone-100 pt-2"><AlertaCorpo alerta={a} /></div>}
          {recusando === a.id ? (
            <div className="mt-2 space-y-2">
              <input autoFocus className="input" placeholder="Motivo da recusa" value={motivo} onChange={(e) => setMotivo(e.target.value)} />
              <div className="flex gap-2">
                <button className="btn-secundario flex-1" disabled={!motivo.trim()} onClick={() => recusar(a)}>Confirmar recusa</button>
                <button className="flex-1 text-sm text-stone-500" onClick={() => setRecusando(null)}>cancelar</button>
              </div>
            </div>
          ) : (
            <div className="mt-2 flex gap-2">
              <button className="btn-primario flex-1 py-2.5" onClick={() => (a.estado === 'aceito' && a.destino ? aceitarDeNovo(a) : aceitar(a))}>
                {a.estado === 'aceito' ? 'Registrar a ação' : 'Aceitar'}
              </button>
              <button className="btn-secundario flex-1 py-2.5" onClick={() => setRecusando(a.id!)}>Recusar</button>
            </div>
          )}
        </article>
      ))}
    </div>
  )

  function aceitarDeNovo(a: Alerta) {
    const url = new URL(a.destino!, location.origin)
    if (url.pathname.endsWith('/registro')) navegar(`/campo?lote=${a.lote_id}&alerta=${a.id}&evento=${url.searchParams.get('evento') ?? 'outro'}`)
    else navegar(a.destino!)
  }
}

// ------------------------------------------------------------------ trato do dia (checklist do tratador)
function Trato({ lotes, onEnviado }: { lotes: Lote[]; onEnviado: () => void }) {
  const hoje = new Date().toISOString().slice(0, 10)
  const [loteId, setLoteId] = useState<number | null>(() => lerJSON<number | null>('campo_lote', null))
  const [p, setP] = useState<any>(null)
  const [aviso, setAviso] = useState('')
  const chave = `campo_trato_${loteId}_${hoje}`
  const [feitos, setFeitos] = useState<number[]>([])
  useEffect(() => { if (!loteId && lotes.length) setLoteId(lotes[0].id) }, [loteId, lotes])
  useEffect(() => {
    if (!loteId) return
    setFeitos(lerJSON(chave, []))
    const cache = `campo_trato_plano_${loteId}`
    setAviso('')
    api.get<any>(`/lotes/${loteId}/trato?tratos=2`).then((x) => { setP(x); gravarJSON(cache, x) })
      .catch(() => { const c = lerJSON<any>(cache, null); setP(c); setAviso(c ? `Sem conexão: mostrando a planilha de ${dataBR(c.data)}.` : 'Sem conexão e sem planilha guardada.') })
  }, [loteId])  // eslint-disable-line react-hooks/exhaustive-deps
  const marcar = async (k: number) => {
    const novos = feitos.includes(k) ? feitos.filter((x) => x !== k) : [...feitos, k]
    setFeitos(novos); gravarJSON(chave, novos)
    if (p && novos.length === p.tratos && !feitos.includes(k)) {      // todos os tratos do dia feitos: registra o total fornecido
      const r = await enviarOuEnfileirar(`/lotes/${loteId}/registros`, { data: hoje, valores: { trato_kg: Math.round(p.total) } }, `${p.lote.nome} · trato`)
      setAviso(r.enviado ? `Trato do dia registrado: ${peso(p.total)}.` : 'Sem conexão: trato guardado no aparelho.')
      onEnviado()
    }
  }
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-2">
        {lotes.map((l) => (
          <BotaoLote key={l.id} lote={l} ativo={l.id === loteId} onClick={() => setLoteId(l.id)} />
        ))}
      </div>
      {aviso && <p className="rounded-md border-l-4 border-l-brinco bg-brinco-claro p-2.5 text-sm text-stone-800">{aviso}</p>}
      {!loteId && <p className="text-sm text-stone-500">Escolha o lote.</p>}
      {p && (
        <>
          <p className="text-sm text-stone-600">{p.lote.nome} · {numero(p.vacas, 0)} vacas · carregue nesta ordem:</p>
          {p.observacoes.map((o: string) => <p key={o} className="rounded-md border-l-4 border-l-brinco bg-brinco-claro p-2.5 text-[13px] text-stone-800">{o}</p>)}
          {p.total_por_trato.map((total: number, k: number) => (
            <section key={k} className={`card p-3 ${feitos.includes(k) ? 'opacity-60' : ''}`}>
              <div className="mb-2 flex items-center justify-between">
                <h2 className="titulo text-xl font-semibold text-stone-900">Trato {k + 1} <span className="num ml-1 text-stone-500">{peso(total)}</span></h2>
                <button className={`rounded-lg px-3 py-1.5 text-sm font-medium ${feitos.includes(k) ? 'bg-campo-600 text-white' : 'border border-stone-300 bg-white'}`} onClick={() => marcar(k)}>
                  {feitos.includes(k) ? 'Feito ✓' : 'Marcar feito'}
                </button>
              </div>
              <ol className="space-y-1">
                {p.linhas.map((l: any, i: number) => (
                  <li key={l.alimento} className="flex justify-between gap-2 text-base"><span><span className="mr-2 text-stone-400">{i + 1}.</span>{l.nome}</span><b className="num">{peso(l.por_trato[k])}</b></li>
                ))}
              </ol>
            </section>
          ))}
        </>
      )}
    </div>
  )
}

