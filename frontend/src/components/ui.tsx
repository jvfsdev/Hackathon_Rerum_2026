import { useEffect, useState, type ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, certeza, dataBR, fmt, numero, reais, rotulo, tecnico, textoAlerta, UNIDADES, type Alerta, type EstadoAlerta, type ItemDieta, type ItemHistorico, type NoComo, type Nivel } from '../api'

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
      <button onClick={() => setAberto(true)} className="text-xs font-medium text-campo-600 underline-offset-2 hover:underline">{tecnico() ? 'Como?' : 'De onde vem?'}</button>
      <Gaveta aberta={aberto} onFechar={() => setAberto(false)} titulo={`${tecnico() ? 'Como o sistema chegou a' : 'De onde vem'}: ${titulo ?? rotulo(no.fato)}`}>
        {tecnico() ? (
          <>
            <p className="mb-3 text-sm text-stone-500">Cada nível mostra a regra que concluiu o valor, a fonte e a força da evidência, e os fatos usados (com seu fator de certeza).</p>
            <ComoArvore no={no} />
          </>
        ) : <ComoSimples no={no} />}
      </Gaveta>
    </>
  )
}

/** "De onde vem?" para o produtor: os dados que entraram na conta, sem regras nem fatores de certeza. */
function ComoSimples({ no }: { no: NoComo }) {
  const folhas = new Map<string, NoComo>()
  const passos: string[] = []
  const visita = (n: NoComo) => {
    if (n.regras?.length) {
      n.regras.forEach((r) => { if (!passos.includes(r.descricao)) passos.push(r.descricao); r.premissas.forEach(visita) })
    } else if (n.conhecido !== false && n.valor !== undefined && !folhas.has(n.fato)) folhas.set(n.fato, n)
  }
  visita(no)
  const padrao = [...folhas.values()].filter((f) => f.origem === 'padrao')
  return (
    <div className="space-y-4 text-sm">
      <p className="rounded-lg bg-campo-50 p-3 text-campo-900"><b>{rotulo(no.fato)}: {fmt(no.valor, no.fato)} {UNIDADES[no.fato] ?? ''}</b> ({certeza(no.cf ?? 1)})</p>
      <div>
        <h4 className="mb-1 font-semibold text-stone-800">Dados usados na conta</h4>
        <ul className="space-y-1">
          {[...folhas.values()].map((f) => (
            <li key={f.fato} className="flex justify-between gap-3 border-b border-stone-100 pb-1">
              <span className="text-stone-600">{rotulo(f.fato)}</span>
              <span className="num font-medium text-stone-900">{fmt(f.valor, f.fato)} {UNIDADES[f.fato] ?? ''}{f.origem === 'padrao' && <span className="ml-1 text-xs text-amber-700">(valor padrão)</span>}</span>
            </li>
          ))}
        </ul>
        {padrao.length > 0 && <p className="mt-2 text-xs text-amber-700">Valores padrão deixam a conta menos certa: informe {padrao.map((f) => rotulo(f.fato).toLowerCase()).join(', ')} para melhorar.</p>}
      </div>
      {passos.length > 0 && (
        <div>
          <h4 className="mb-1 font-semibold text-stone-800">O que o sistema considerou</h4>
          <ul className="ml-4 list-disc space-y-0.5 text-stone-600">{passos.slice(0, 8).map((p) => <li key={p}>{p}</li>)}</ul>
        </div>
      )}
      <p className="text-xs text-stone-400">Na visão técnica aparecem as regras, as fontes e os fatores de certeza.</p>
    </div>
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
          <h4 className="mb-2 text-sm font-semibold text-stone-800">{tecnico() ? 'Histórico do alerta e ações' : 'O que já aconteceu com este aviso'}</h4>
          <LinhaDoTempo itens={hist} />
        </div>
      )}
      {!tecnico() && alerta.contexto && alerta.contexto.length > 0 && (
        <div>
          <h4 className="mb-1 text-sm font-semibold text-stone-800">O que o sistema viu</h4>
          <ul className="space-y-1 text-sm">
            {alerta.contexto.map((c) => (
              <li key={c.fato} className="flex justify-between gap-3 border-b border-stone-100 pb-1">
                <span className="text-stone-600">{rotulo(c.fato)}</span><span className="num font-medium text-stone-900">{fmt(c.valor, c.fato)}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
      {alerta.sessao_id && <Contrafactual sessaoId={alerta.sessao_id} regra={alerta.regra} />}
      {erro && tecnico() && <Erro msg={erro} />}
      {!dados && !erro && alerta.sessao_id && tecnico() && <Carregando />}
      {dados && tecnico() && (
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
  const t = textoAlerta(alerta)
  const tec = tecnico()
  return (
    <div className={alerta.status === 'suprimido' || encerrado ? 'opacity-80' : ''}>
      <div className="flex flex-wrap items-center gap-2">
        <NivelBadge nivel={alerta.nivel} />
        <EstadoBadge estado={alerta.estado} />
        {alerta.status === 'suprimido' && <span className="rounded-full bg-stone-200 px-2 py-0.5 text-xs font-semibold text-stone-600">{tec ? 'Suprimido' : 'Em segundo plano'}</span>}
        {tec ? <>
          <span className="font-mono text-xs text-stone-500">{alerta.regra}</span>
          <ForcaBadge forca={alerta.forca} />
          <CfBarra cf={alerta.cf} />
          {alerta.tambem?.length ? <span className="text-xs text-stone-400">agrupa {alerta.tambem.join(', ')}</span> : null}
        </> : <span className="text-xs text-stone-400">{certeza(alerta.cf)}</span>}
        {alerta.aberto_em ? (
          <span className="text-xs text-stone-400">
            desde {dataBR(alerta.aberto_em)}{alerta.ultima_ocorrencia && alerta.ultima_ocorrencia !== alerta.aberto_em && ` · última ${dataBR(alerta.ultima_ocorrencia)}`}
            {(alerta.ocorrencias ?? 1) > 1 && ` · ${alerta.ocorrencias} ocorrências`}
          </span>
        ) : alerta.data && <span className="text-xs text-stone-400">{dataBR(alerta.data)}</span>}
      </div>
      <p className="mt-1.5 font-medium text-stone-900">{t.titulo}</p>
      {t.causa && <p className="mt-1 text-sm text-stone-600"><span className="font-medium text-stone-700">{tec ? 'Causa provável: ' : 'Por quê: '}</span>{t.causa}</p>}
      {t.acao && <p className="mt-1 text-sm text-stone-600"><span className="font-medium text-campo-700">{tec ? 'Ação sugerida: ' : 'O que fazer: '}</span>{t.acao}</p>}
      {alerta.nota && <p className="mt-1 rounded bg-stone-100 px-2 py-1 text-xs text-stone-600">{tec ? `Meta-regra ${alerta.nota}` : `Observação: ${alerta.nota.replace(/^[A-Z]+-[\w]+: /, '')}`}</p>}
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
                  {tecnico() && <span className="font-mono">{h.alerta.regra} </span>}{(tecnico() ? h.alerta.titulo : h.alerta.titulo_produtor || h.alerta.titulo).slice(0, 80)}
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
      {onAbrir && <button onClick={onAbrir} className="mt-1.5 text-xs font-medium text-campo-600 hover:underline">{tecnico() ? 'Por que este alerta? · histórico' : 'Entender este aviso · o que precisaria mudar'}</button>}
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

// ------------------------------------------------------------------ "o que precisaria mudar?"
const OP_TEXTO: Record<string, string> = { '>=': 'chegar a pelo menos', '>': 'passar de', '<=': 'ficar em no máximo', '<': 'ficar abaixo de' }

function faixa(f: any, fato: string) { return Array.isArray(f) ? `${fmt(f[0], fato)} a ${fmt(f[1], fato)}` : fmt(f, fato) }

function OpcaoMudanca({ o }: { o: any }) {
  const un = UNIDADES[o.fato] ? ` ${UNIDADES[o.fato]}` : ''
  if (o.tipo === 'limite') return <li><b>{rotulo(o.fato)}</b> {OP_TEXTO[o.op]} <b className="num">{fmt(o.limite, o.fato)}{un}</b> <span className="text-stone-500">(hoje {fmt(o.valor, o.fato)}{un})</span></li>
  if (o.tipo === 'sair_da_faixa') return <li><b>{rotulo(o.fato)}</b> sair da faixa {faixa(o.faixa, o.fato)} <span className="text-stone-500">(hoje {fmt(o.valor, o.fato)})</span></li>
  if (o.tipo === 'voltar_para_faixa') return <li><b>{rotulo(o.fato)}</b> voltar para {faixa(o.faixa, o.fato)} <span className="text-stone-500">(hoje {fmt(o.valor, o.fato)})</span></li>
  if (o.tipo === 'conclusao') return (
    <li>
      <b>{rotulo(o.fato)}</b> deixar de valer{o.grupos.length > 1 ? ' — o sistema chegou a isso por mais de um caminho, e todos precisam deixar de valer:' : ':'}
      <ul className="ml-4 mt-1 space-y-1">
        {o.grupos.map((g: any, i: number) => (
          <li key={g.regra} className="rounded bg-stone-50 px-2 py-1">
            <span className="text-xs text-stone-500">{tecnico() ? <><span className="font-mono">{g.regra} </span>{g.descricao}</> : o.grupos.length > 1 ? `Caminho ${i + 1} — basta uma destas:` : 'Basta uma destas:'}</span>
            {g.opcoes.length > 0
              ? <ul className="ml-4 list-disc">{g.opcoes.map((x: any, i: number) => <OpcaoMudanca key={i} o={x} />)}</ul>
              : <p className="text-xs text-stone-400">depende só da situação do lote</p>}
          </li>
        ))}
      </ul>
    </li>
  )
  return null
}

/** Contrafactual: o que faria o aviso deixar de valer (basta uma das mudanças). */
export function Contrafactual({ sessaoId, regra }: { sessaoId: number; regra: string }) {
  const [d, setD] = useState<any>(null)
  const [erro, setErro] = useState('')
  useEffect(() => { api.get(`/inferencia/sessoes/${sessaoId}/contrafactual/${regra}`).then(setD).catch((e) => setErro(e.message)) }, [sessaoId, regra])
  if (erro) return null
  if (!d) return <Carregando texto="Calculando o que precisaria mudar…" />
  return (
    <div className="rounded-lg border border-campo-100 bg-white p-3">
      <h4 className="mb-1 text-sm font-semibold text-stone-800">O que precisaria mudar para este aviso sumir?</h4>
      {d.opcoes.length === 0 ? (
        <p className="text-sm text-stone-600">Este aviso depende só da situação do lote (fase, sistema, raça): não há um número a corrigir.</p>
      ) : (
        <>
          <p className="mb-1 text-xs text-stone-500">Basta <b>uma</b> destas mudanças:</p>
          <ul className="ml-4 list-disc space-y-1 text-sm text-stone-700">{d.opcoes.map((o: any, i: number) => <OpcaoMudanca key={i} o={o} />)}</ul>
        </>
      )}
      {d.contexto?.length > 0 && tecnico() && (
        <p className="mt-2 text-xs text-stone-400">Condições de contexto (não mudam com manejo): {d.contexto.map((c: any) => `${rotulo(c.fato)} = ${fmt(c.valor, c.fato)}`).join('; ')}</p>
      )}
      {d.modulo === 'verificacao' && d.lote_id && <AjusteMinimo loteId={d.lote_id} />}
    </div>
  )
}

/** Menor mudança na dieta que a faz passar em todas as verificações (PL com objetivo de mexer o mínimo). */
export function AjusteMinimo({ loteId, itens, onUsar }: { loteId: number; itens?: ItemDieta[]; onUsar?: (itens: ItemDieta[], custo: number) => void }) {
  const navegar = useNavigate()
  const [r, setR] = useState<any>(null)
  const [ocupado, setOcupado] = useState(false)
  const [erro, setErro] = useState('')
  const calcular = async () => {
    setOcupado(true); setErro('')
    try { setR(await api.post(`/inferencia/lotes/${loteId}/ajuste`, itens ? { itens } : {})) } catch (e: any) { setErro(e.message) }
    setOcupado(false)
  }
  const ok = r && (r.pl.status === 'otimo' || r.pl.status === 'parcial')
  return (
    <div className="mt-3 border-t border-stone-100 pt-3">
      {!r && <button className="btn-secundario" onClick={calcular} disabled={ocupado}>{ocupado ? 'Calculando…' : 'Calcular a menor mudança na dieta'}</button>}
      {erro && <Erro msg={erro} />}
      {r && !ok && <p className="text-sm text-critico">Não há ajuste possível só com os alimentos cadastrados: {(r.alertas ?? []).map((a: Alerta) => textoAlerta(a).titulo).join('; ') || r.pl.status}.</p>}
      {ok && (
        <div className="space-y-2 text-sm">
          <p className="font-medium text-stone-800">Menor mudança que deixa a dieta {r.pl.status === 'otimo' ? 'adequada' : 'o mais perto possível do necessário'}:</p>
          <ul className="space-y-0.5">
            {r.mudancas.map((m: any) => (
              <li key={m.alimento} className="num">
                {m.nome}: {m.de === 0 ? <span className="font-medium text-campo-700">incluir {numero(m.para, 2)} kg</span>
                  : m.para === 0 ? <span className="font-medium text-critico">tirar ({numero(m.de, 2)} kg)</span>
                  : <>{numero(m.de, 2)} → <b>{numero(m.para, 2)} kg</b></>} por vaca/dia
              </li>
            ))}
          </ul>
          <p className="text-xs text-stone-500">Custo: {reais(r.pl.custo)} por vaca/dia · conferido pelas regras: <b>{fmt(r.verificacao?.fatos?.['parecer.dieta']?.valor)}</b></p>
          <button className="btn-primario" onClick={() => (onUsar ? onUsar(r.pl.itens, r.pl.custo)
            : navegar(`/lotes/${loteId}/dieta`, { state: { itensAjuste: r.pl.itens, rotulo: 'Menor mudança calculada' } }))}>
            Abrir no editor da dieta
          </button>
        </div>
      )}
    </div>
  )
}

