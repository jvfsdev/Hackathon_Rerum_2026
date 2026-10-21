import { useEffect, useState, type ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, dataBR, fmt, rotulo, UNIDADES, type Alerta, type EstadoAlerta, type ItemHistorico, type NoComo, type Nivel } from '../api'

const COR_NIVEL: Record<Nivel, string> = {
  critico: 'bg-red-50 text-critico ring-red-200',
  atencao: 'bg-amber-50 text-atencao ring-amber-200',
  informativo: 'bg-blue-50 text-info ring-blue-200',
}
const NOME_NIVEL: Record<Nivel, string> = { critico: 'Crítico', atencao: 'Atenção', informativo: 'Informativo' }

export function NivelBadge({ nivel }: { nivel: Nivel }) {
  return <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold ring-1 ${COR_NIVEL[nivel]}`}>{NOME_NIVEL[nivel]}</span>
}

export function ForcaBadge({ forca }: { forca?: string }) {
  if (!forca) return null
  const titulo: Record<string, string> = {
    A: 'Norma legal, meta-análise ou estudo grande', B: 'Estudo revisado ou extensão com dados',
    C: 'Extensão sem dados próprios ou população diferente', D: 'Escolha de engenharia, sem validação',
  }
  return <span title={titulo[forca]} className="inline-flex h-5 min-w-5 items-center justify-center rounded bg-stone-100 px-1 text-[11px] font-bold text-stone-600 ring-1 ring-stone-200">Evid. {forca}</span>
}

export function CfBarra({ cf, rotulo: r = 'CF' }: { cf: number; rotulo?: string }) {
  const pct = Math.round(Math.max(0, Math.min(1, cf)) * 100)
  const cor = cf >= 0.8 ? 'bg-campo-500' : cf >= 0.6 ? 'bg-amber-500' : 'bg-stone-400'
  return (
    <span className="inline-flex items-center gap-1.5" title="Fator de certeza (0 a 1)">
      <span className="text-[11px] font-medium text-stone-500">{r}</span>
      <span className="h-1.5 w-14 overflow-hidden rounded-full bg-stone-200"><span className={`block h-full ${cor}`} style={{ width: `${pct}%` }} /></span>
      <span className="num text-xs font-semibold text-stone-700">{cf.toFixed(2)}</span>
    </span>
  )
}

export function Carregando({ texto = 'Consultando a base de conhecimento…' }: { texto?: string }) {
  return <div className="flex items-center gap-2 p-6 text-sm text-stone-500"><span className="h-4 w-4 animate-spin rounded-full border-2 border-campo-500 border-t-transparent" />{texto}</div>
}

export function Erro({ msg }: { msg: string }) {
  return <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-critico">{msg}</div>
}

export function Painel({ titulo, subtitulo, acoes, children, className = '' }: { titulo?: ReactNode; subtitulo?: ReactNode; acoes?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={`card p-4 sm:p-5 ${className}`}>
      {(titulo || acoes) && (
        <div className="mb-3 flex flex-wrap items-start justify-between gap-2">
          <div>
            {titulo && <h2 className="text-base font-semibold text-stone-900">{titulo}</h2>}
            {subtitulo && <p className="mt-0.5 text-sm text-stone-500">{subtitulo}</p>}
          </div>
          {acoes}
        </div>
      )}
      {children}
    </section>
  )
}

export function Gaveta({ aberta, onFechar, titulo, children }: { aberta: boolean; onFechar: () => void; titulo: ReactNode; children: ReactNode }) {
  useEffect(() => {
    const esc = (e: KeyboardEvent) => e.key === 'Escape' && onFechar()
    window.addEventListener('keydown', esc)
    return () => window.removeEventListener('keydown', esc)
  }, [onFechar])
  if (!aberta) return null
  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="absolute inset-0 bg-stone-900/30" onClick={onFechar} />
      <aside className="relative flex h-full w-full max-w-2xl flex-col bg-white shadow-xl">
        <header className="flex items-center justify-between border-b border-stone-200 px-5 py-3">
          <h3 className="font-semibold text-stone-900">{titulo}</h3>
          <button className="btn-secundario px-2 py-1" onClick={onFechar} aria-label="Fechar">✕</button>
        </header>
        <div className="flex-1 overflow-y-auto p-5">{children}</div>
      </aside>
    </div>
  )
}

const ORIGEM: Record<string, string> = { usuario: 'informado', medido: 'medido', tabela: 'tabela', padrao: 'valor padrão', sistema: 'sistema', regra: 'concluído' }

/** Árvore "Como?" — derivação de uma conclusão a partir do traço de inferência. */
export function ComoArvore({ no, nivel = 0 }: { no: NoComo; nivel?: number }) {
  const [aberto, setAberto] = useState(nivel < 2)
  if (no.conhecido === false) return <div className="text-sm text-stone-400">{rotulo(no.fato)}: não conhecido</div>
  const temFilhos = !!no.regras?.length
  return (
    <div className={nivel ? 'ml-3 border-l border-stone-200 pl-3' : ''}>
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1 py-1">
        {temFilhos ? (
          <button onClick={() => setAberto(!aberto)} className="w-4 text-stone-400 hover:text-stone-700">{aberto ? '▾' : '▸'}</button>
        ) : <span className="w-4" />}
        <span className="text-sm font-medium text-stone-800">{rotulo(no.fato)}</span>
        <span className="num text-sm text-stone-900">= {fmt(no.valor, no.fato)} {UNIDADES[no.fato] ?? ''}</span>
        {no.op && no.op !== 'existe' && no.op !== 'ref' && no.esperado !== null && no.esperado !== undefined && (
          <span className="rounded bg-stone-100 px-1.5 text-xs text-stone-500">condição: {no.op} {fmt(no.esperado)}</span>
        )}
        <span className="rounded bg-campo-50 px-1.5 text-[11px] text-campo-700">{ORIGEM[no.origem ?? ''] ?? no.origem}</span>
        {no.cf !== undefined && <CfBarra cf={no.cf} />}
        {no.nota && <span className="text-xs text-amber-700">{no.nota}</span>}
      </div>
      {aberto && no.regras?.map((r) => (
        <div key={r.regra} className="ml-4 mb-1">
          <div className="flex flex-wrap items-center gap-2 rounded-md bg-stone-50 px-2 py-1 text-xs text-stone-600">
            <span className="font-mono font-semibold text-campo-700">{r.regra}</span>
            <span>{r.descricao}</span>
            <ForcaBadge forca={r.forca} />
            <span className="text-stone-400">fonte: {r.fonte}</span>
          </div>
          {r.calculo?.funcao && (
            <div className="ml-2 mt-1 font-mono text-[11px] text-stone-500">
              {r.calculo.funcao}({Object.entries(r.calculo.args ?? {}).map(([k, v]) => `${k}=${typeof v === 'object' ? '…' : v}`).join(', ')})
            </div>
          )}
          {r.premissas.map((p, i) => <ComoArvore key={p.fato + i} no={p} nivel={nivel + 1} />)}
        </div>
      ))}
    </div>
  )
}

export function BotaoComo({ no, titulo }: { no?: NoComo; titulo?: string }) {
  const [aberto, setAberto] = useState(false)
  if (!no) return null
  return (
    <>
      <button onClick={() => setAberto(true)} className="text-xs font-medium text-campo-600 underline-offset-2 hover:underline">Como?</button>
      <Gaveta aberta={aberto} onFechar={() => setAberto(false)} titulo={`Como o sistema chegou a: ${titulo ?? rotulo(no.fato)}`}>
        <p className="mb-3 text-sm text-stone-500">Cada nível mostra a regra que concluiu o valor, a fonte e a força da evidência, e os fatos usados (com seu fator de certeza).</p>
        <ComoArvore no={no} />
      </Gaveta>
    </>
  )
}

/** Explicação completa de um alerta salvo: regra disparada + derivação das premissas. */
export function ExplicacaoAlerta({ alerta: inicial }: { alerta: Alerta }) {
  const [alerta, setAlerta] = useState<Alerta>(inicial)
  const [dados, setDados] = useState<any>(null)
  const [hist, setHist] = useState<ItemHistorico[] | null>(null)
  const [erro, setErro] = useState('')
  const carregarHist = () => {
    if (inicial.id && inicial.estado) api.get<any>(`/alertas/${inicial.id}`).then((a) => { setAlerta(a); setHist(a.historico) })
  }
  useEffect(() => {
    carregarHist()
    if (!inicial.sessao_id) return
    api.get(`/inferencia/sessoes/${inicial.sessao_id}/regra/${inicial.regra}`).then(setDados).catch((e) => setErro(e.message))
  }, [inicial])  // eslint-disable-line react-hooks/exhaustive-deps
  return (
    <div className="space-y-4">
      <AlertaCorpo alerta={alerta} />
      <AlertaAcoes alerta={alerta} onMudou={carregarHist} />
      {hist && (
        <div>
          <h4 className="mb-2 text-sm font-semibold text-stone-800">Histórico do alerta e ações</h4>
          <LinhaDoTempo itens={hist} />
        </div>
      )}
      {erro && <Erro msg={erro} />}
      {!dados && !erro && alerta.sessao_id && <Carregando />}
      {dados && (
        <>
          <RegraCartao regra={dados.regra_def} />
          <div>
            <h4 className="mb-1 text-sm font-semibold text-stone-800">Por quê? — fatos que satisfizeram a regra</h4>
            <p className="mb-2 text-xs text-stone-500">Base v{dados.kb_version} · ciclo {dados.ciclo} do motor · regras concorrentes no ciclo: {dados.concorrentes?.length ?? 0}</p>
            {dados.arvores.map((a: NoComo, i: number) => <ComoArvore key={i} no={a} />)}
          </div>
        </>
      )}
    </div>
  )
}

const ESTADO: Record<EstadoAlerta, [string, string]> = {
  aberto: ['Aberto', 'bg-white text-stone-700 ring-stone-300'], aceito: ['Aceito — em andamento', 'bg-campo-50 text-campo-700 ring-campo-100'],
  recusado: ['Recusado', 'bg-stone-100 text-stone-600 ring-stone-200'], resolvido: ['Resolvido', 'bg-campo-600 text-white ring-campo-600'],
  expirado: ['Expirado', 'bg-stone-200 text-stone-600 ring-stone-300'],
}

export function EstadoBadge({ estado }: { estado?: EstadoAlerta }) {
  if (!estado) return null
  const [nome, cor] = ESTADO[estado]
  return <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold ring-1 ${cor}`}>{nome}</span>
}

export function AlertaCorpo({ alerta }: { alerta: Alerta }) {
  const encerrado = alerta.estado === 'resolvido' || alerta.estado === 'expirado' || alerta.estado === 'recusado'
  return (
    <div className={alerta.status === 'suprimido' || encerrado ? 'opacity-80' : ''}>
      <div className="flex flex-wrap items-center gap-2">
        <NivelBadge nivel={alerta.nivel} />
        <EstadoBadge estado={alerta.estado} />
        {alerta.status === 'suprimido' && <span className="rounded-full bg-stone-200 px-2 py-0.5 text-xs font-semibold text-stone-600">Suprimido</span>}
        <span className="font-mono text-xs text-stone-500">{alerta.regra}</span>
        <ForcaBadge forca={alerta.forca} />
        <CfBarra cf={alerta.cf} />
        {alerta.aberto_em ? (
          <span className="text-xs text-stone-400">
            desde {dataBR(alerta.aberto_em)}{alerta.ultima_ocorrencia && alerta.ultima_ocorrencia !== alerta.aberto_em && ` · última ${dataBR(alerta.ultima_ocorrencia)}`}
            {(alerta.ocorrencias ?? 1) > 1 && ` · ${alerta.ocorrencias} ocorrências`}
          </span>
        ) : alerta.data && <span className="text-xs text-stone-400">{dataBR(alerta.data)}</span>}
      </div>
      <p className="mt-1.5 font-medium text-stone-900">{alerta.titulo}</p>
      {alerta.causa && <p className="mt-1 text-sm text-stone-600"><span className="font-medium text-stone-700">Causa provável: </span>{alerta.causa}</p>}
      {alerta.acao && <p className="mt-1 text-sm text-stone-600"><span className="font-medium text-campo-700">Ação sugerida: </span>{alerta.acao}</p>}
      {alerta.nota && <p className="mt-1 rounded bg-stone-100 px-2 py-1 text-xs text-stone-600">Meta-regra {alerta.nota}</p>}
      {alerta.resolucao && (
        <p className={`mt-1.5 rounded-lg px-2 py-1.5 text-sm ${alerta.estado === 'resolvido' ? 'bg-campo-50 text-campo-900' : 'bg-stone-100 text-stone-700'}`}>
          <b>{alerta.estado === 'resolvido' ? 'Resolvido' : 'Encerrado'} em {dataBR(alerta.estado_em)}:</b> {alerta.resolucao}
        </p>
      )}
    </div>
  )
}

/** Aceitar (vai para a tela da ação) ou recusar (com motivo) a recomendação de um alerta persistido. */
export function AlertaAcoes({ alerta, onMudou }: { alerta: Alerta; onMudou?: (a: Alerta) => void }) {
  const navegar = useNavigate()
  const [recusando, setRecusando] = useState(false)
  const [motivo, setMotivo] = useState('')
  const [erro, setErro] = useState('')
  if (!alerta.id || !alerta.estado || alerta.estado === 'resolvido' || alerta.estado === 'expirado') return null
  const aceitar = async () => {
    setErro('')
    try {
      const r = await api.post<{ destino: string }>(`/alertas/${alerta.id}/aceitar`, {})
      navegar(r.destino)
    } catch (e: any) { setErro(e.message) }
  }
  const recusar = async () => {
    setErro('')
    try { const a = await api.post<Alerta>(`/alertas/${alerta.id}/recusar`, { motivo }); setRecusando(false); onMudou?.(a) }
    catch (e: any) { setErro(e.message) }
  }
  return (
    <div className="mt-2">
      <div className="flex flex-wrap items-center gap-2">
        {alerta.estado === 'aceito' ? (
          <button className="btn-primario px-3 py-1.5" onClick={() => alerta.destino && navegar(alerta.destino)}>Registrar a ação →</button>
        ) : (
          <button className="btn-primario px-3 py-1.5" onClick={aceitar}>{alerta.estado === 'recusado' ? 'Aceitar agora' : 'Aceitar e registrar ação'}</button>
        )}
        {alerta.estado !== 'recusado' && !recusando && <button className="btn-secundario px-3 py-1.5" onClick={() => setRecusando(true)}>Recusar</button>}
      </div>
      {recusando && (
        <div className="mt-2 flex flex-wrap gap-2">
          <input autoFocus className="input max-w-md flex-1" placeholder="Motivo da recusa (obrigatório)" value={motivo}
            onChange={(e) => setMotivo(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && motivo.trim() && recusar()} />
          <button className="btn-secundario" disabled={!motivo.trim()} onClick={recusar}>Confirmar recusa</button>
          <button className="text-sm text-stone-500 hover:underline" onClick={() => setRecusando(false)}>cancelar</button>
        </div>
      )}
      {erro && <div className="mt-2"><Erro msg={erro} /></div>}
    </div>
  )
}

const TIPO_HIST: Record<string, [string, string]> = {
  aberto: ['Alerta aberto', 'bg-amber-500'], agravado: ['Agravou', 'bg-red-600'], atenuado: ['Atenuou', 'bg-amber-400'], reaberto: ['Reaberto', 'bg-red-600'],
  aceito: ['Recomendação aceita', 'bg-campo-500'], acao_registrada: ['Ação registrada', 'bg-campo-700'],
  recusado: ['Recusado', 'bg-stone-500'], resolvido: ['Resolvido', 'bg-campo-600'], expirado: ['Expirado', 'bg-stone-400'],
}

/** Linha do tempo de um alerta (ou de vários, com `mostrarAlerta`). */
export function LinhaDoTempo({ itens, mostrarAlerta = false, onAbrirAlerta }: { itens: ItemHistorico[]; mostrarAlerta?: boolean; onAbrirAlerta?: (id: number) => void }) {
  if (!itens.length) return <p className="text-sm text-stone-500">Sem registros.</p>
  return (
    <ol className="relative ml-2 border-l border-stone-200">
      {itens.map((h) => {
        const [nome, cor] = TIPO_HIST[h.tipo] ?? [h.tipo, 'bg-stone-400']
        return (
          <li key={h.id} className="mb-3 ml-4">
            <span className={`absolute -left-[5px] mt-1.5 h-2.5 w-2.5 rounded-full ${cor}`} />
            <div className="flex flex-wrap items-baseline gap-x-2 text-xs text-stone-500">
              <span className="num font-medium text-stone-700">{new Date(h.data_hora).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })}</span>
              <span className="font-semibold text-stone-800">{nome}</span>
              <span>{h.automatico ? 'sistema' : 'usuário'}</span>
              {mostrarAlerta && h.alerta && (
                <button className="text-campo-600 hover:underline" onClick={() => onAbrirAlerta?.(h.alerta!.id)}>
                  <span className="font-mono">{h.alerta.regra}</span> {h.alerta.titulo.slice(0, 70)}
                </button>
              )}
            </div>
            <p className="mt-0.5 text-sm text-stone-700">{h.descricao}</p>
          </li>
        )
      })}
    </ol>
  )
}

export function AlertaItem({ alerta, onAbrir, onMudou }: { alerta: Alerta; onAbrir?: () => void; onMudou?: (a: Alerta) => void }) {
  return (
    <div className="border-b border-stone-100 py-3 last:border-0">
      <AlertaCorpo alerta={alerta} />
      <AlertaAcoes alerta={alerta} onMudou={onMudou} />
      {onAbrir && <button onClick={onAbrir} className="mt-1.5 text-xs font-medium text-campo-600 hover:underline">Por que este alerta? · histórico</button>}
    </div>
  )
}

function condicaoTexto(c: any): string {
  if (c.qualquer) return `( ${c.qualquer.map(condicaoTexto).join('  OU  ')} )`
  if (c.todos) return `( ${c.todos.map(condicaoTexto).join('  E  ')} )`
  const v = Array.isArray(c.valor) ? `[${c.valor.join(', ')}]` : c.valor ?? ''
  return `${c.fato} ${c.op ?? 'existe'} ${v}`.trim()
}

function acaoTexto(a: any): string {
  if (a.concluir) return `concluir ${a.concluir.fato} = ${a.concluir.valor}`
  if (a.calcular) return `calcular ${a.calcular.fato} = ${a.calcular.funcao}(…)`
  if (a.alerta) return `alerta ${a.alerta.nivel}: "${a.alerta.titulo}"`
  if (a.suprimir) return `suprimir alertas de ${a.suprimir.categorias.join(', ')}`
  if (a.rebaixar) return `rebaixar alertas de ${a.rebaixar.categorias.join(', ')}`
  return JSON.stringify(a)
}

export function RegraCartao({ regra }: { regra: any }) {
  if (!regra) return null
  return (
    <div className="rounded-lg border border-stone-200 bg-stone-50 p-3 font-mono text-xs leading-relaxed text-stone-700">
      <div className="mb-1 flex flex-wrap items-center gap-2 font-sans">
        <span className="font-mono font-bold text-campo-700">{regra.id}</span>
        <span className="text-sm text-stone-800">{regra.descricao}</span>
        <ForcaBadge forca={regra.forca} />
      </div>
      <div><span className="font-bold text-stone-900">SE</span> {regra.se?.map(condicaoTexto).join('  E  ') || '—'}</div>
      <div><span className="font-bold text-stone-900">ENTÃO</span> {regra.entao?.map(acaoTexto).join('; ')}</div>
      <div className="mt-1 font-sans text-stone-500">CF da regra {regra.cf} · prioridade {regra.prioridade} · módulo {regra.modulo} · v{regra.versao} · fonte: {regra.fonte}</div>
    </div>
  )
}
