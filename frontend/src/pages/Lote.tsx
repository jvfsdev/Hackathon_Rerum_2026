import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, NavLink, Route, Routes, useLocation, useParams } from 'react-router-dom'
import { CartesianGrid, ComposedChart, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api, fmt, OPCOES, rotulo, UNIDADES, type Alerta, type Alimento, type Dieta, type ItemDieta, type Lote, type Resultado } from '../api'
import LoteForm from '../components/LoteForm'
import { AlertaItem, BotaoComo, Carregando, CfBarra, Erro, ExplicacaoAlerta, Gaveta, NivelBadge, Painel } from '../components/ui'

const aba = ({ isActive }: { isActive: boolean }) =>
  `whitespace-nowrap border-b-2 px-3 py-2 text-sm font-medium ${isActive ? 'border-campo-600 text-campo-700' : 'border-transparent text-stone-500 hover:text-stone-800'}`

export default function LotePagina() {
  const { id } = useParams()
  const [info, setInfo] = useState<{ lote: Lote; fatos: Record<string, any>; dieta: Dieta | null } | null>(null)
  const [erro, setErro] = useState('')
  const [editando, setEditando] = useState(false)
  const recarregar = useCallback(() => { api.get<any>(`/lotes/${id}`).then(setInfo).catch((e) => setErro(e.message)) }, [id])
  useEffect(recarregar, [recarregar])
  if (erro) return <Erro msg={erro} />
  if (!info) return <Carregando texto="Carregando o lote…" />
  const { lote, fatos } = info
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
       <div>
        <h1 className="text-xl font-semibold text-stone-900">{lote.nome}</h1>
        <p className="text-sm text-stone-500">
          {lote.n_vacas} vacas · {OPCOES[lote.grupo_genetico]} · {OPCOES[lote.sistema]} · {OPCOES[lote.estado]}
          {fatos['lote.del'] !== undefined && ` · DEL ${Math.round(fatos['lote.del'])}`} · PV {lote.pv} kg
          {fatos['lote.leite'] !== undefined && ` · ${fmt(fatos['lote.leite'])} L/vaca (média 7 d)`}
        </p>
       </div>
       <button className="btn-secundario" onClick={() => setEditando(true)}>Editar lote</button>
      </div>
      <Gaveta aberta={editando} onFechar={() => setEditando(false)} titulo={`Editar ${lote.nome}`}>
        <LoteForm lote={lote} fatos={fatos} onSalvo={() => { setEditando(false); recarregar() }} />
      </Gaveta>
      <nav className="-mx-4 flex overflow-x-auto border-b border-stone-200 px-4">
        <NavLink end to="" className={aba}>Perfil e exigências</NavLink>
        <NavLink to="dieta" className={aba}>Dieta</NavLink>
        <NavLink to="acompanhamento" className={aba}>Acompanhamento</NavLink>
        <NavLink to="registro" className={aba}>Registro rápido</NavLink>
        <NavLink to="alertas" className={aba}>Alertas</NavLink>
      </nav>
      <Routes>
        <Route index element={<AbaPerfil key={JSON.stringify(lote)} loteId={lote.id} />} />
        <Route path="dieta" element={<AbaDieta lote={lote} dietaAtiva={info.dieta} onSalvo={recarregar} />} />
        <Route path="acompanhamento" element={<AbaAcompanhamento loteId={lote.id} />} />
        <Route path="registro" element={<AbaRegistro lote={lote} />} />
        <Route path="alertas" element={<AbaAlertas loteId={lote.id} />} />
      </Routes>
    </div>
  )
}

// ------------------------------------------------------------------ Perfil e exigências
function AbaPerfil({ loteId }: { loteId: number }) {
  const [r, setR] = useState<Resultado | null>(null)
  const [erro, setErro] = useState('')
  useEffect(() => { api.post<Resultado>(`/inferencia/lotes/${loteId}/avaliar`).then(setR).catch((e) => setErro(e.message)) }, [loteId])
  if (erro) return <Erro msg={erro} />
  if (!r) return <Carregando />
  return <ResultadoAvaliacao r={r} linkDieta="dieta#sugerir" />
}

function Valor({ r, fato, destaque = false }: { r: Resultado; fato: string; destaque?: boolean }) {
  const f = r.fatos[fato]
  if (!f) return null
  return (
    <div className="flex items-baseline justify-between gap-3 border-b border-stone-100 py-1.5 last:border-0">
      <span className="text-sm text-stone-600">{rotulo(fato)}</span>
      <span className="flex items-baseline gap-2">
        <span className={`num ${destaque ? 'text-lg font-semibold text-stone-900' : 'text-sm font-medium text-stone-800'}`}>{fmt(f.valor, fato)}</span>
        <span className="text-xs text-stone-400">{UNIDADES[fato] ?? ''}</span>
        {f.origem === 'regra' && <BotaoComo no={r.explicacoes?.[fato] ?? { fato, valor: f.valor, cf: f.cf, origem: f.origem }} />}
      </span>
    </div>
  )
}

const COMPONENTES_ELL = ['exig.ell_mantenca', 'exig.ell_leite', 'exig.ell_gestacao', 'exig.ell_crescimento', 'exig.ell_atividade', 'exig.ell_ecc']

export function ResultadoAvaliacao({ r, linkDieta }: { r: Resultado; linkDieta?: string }) {
  const [aberto, setAberto] = useState<Alerta | null>(null)
  const temDieta = !!r.fatos['dieta.ms_kg']
  const total = r.fatos['exig.ell_total']?.valor ?? 0
  const parecer = r.fatos['parecer.dieta']
  const motivos = r.alertas.filter((a) => a.status === 'ativo' && a.nivel !== 'informativo' && a.categoria === 'dieta')
  return (
    <div className="space-y-4">
      {parecer && (
        <div className={`card flex flex-wrap items-center justify-between gap-3 p-4 ${parecer.valor === 'adequada' ? 'border-campo-500 bg-campo-50' : parecer.valor === 'bloqueada' ? 'border-red-300 bg-red-50' : 'border-amber-300 bg-amber-50'}`}>
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-stone-500">Parecer da dieta</p>
            <p className="text-lg font-semibold text-stone-900">{fmt(parecer.valor)}</p>
            {motivos.length > 0 && (
              <ul className="mt-1 space-y-0.5 text-sm text-stone-700">
                {motivos.map((a) => <li key={a.regra}><span className="font-mono text-xs text-stone-500">{a.regra}</span> {a.titulo}</li>)}
              </ul>
            )}
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <CfBarra cf={parecer.cf} /><BotaoComo no={r.explicacoes?.['parecer.dieta']} />
            {linkDieta && parecer.valor !== 'adequada' && <Link to={linkDieta} className="btn-primario">Sugerir dieta de custo mínimo →</Link>}
          </div>
        </div>
      )}
      <div className="grid gap-4 md:grid-cols-3">
        <Painel titulo="Perfil do lote" subtitulo="Classificação (módulo CLS)">
          <Valor r={r} fato="perfil.fase" destaque />
          <Valor r={r} fato="perfil.equacao_cms" />
          <Valor r={r} fato="clima.itu" />
          <Valor r={r} fato="perfil.estresse_termico" />
          <Valor r={r} fato="perfil.gestacao_avancada" />
          <Valor r={r} fato="perfil.crescimento" />
          <Valor r={r} fato="perfil.atividade_pastejo" />
        </Painel>
        <Painel titulo="Exigências por vaca/dia" subtitulo="Módulo EXG">
          <Valor r={r} fato="exig.cms" destaque />
          <Valor r={r} fato="exig.ell_total" destaque />
          <div className="my-2 space-y-1">
            {COMPONENTES_ELL.filter((c) => r.fatos[c]).map((c) => (
              <div key={c} className="flex items-center gap-2 text-xs">
                <span className="w-32 text-stone-500">{rotulo(c)}</span>
                <span className="h-2 flex-1 overflow-hidden rounded bg-stone-100"><span className="block h-full bg-campo-500" style={{ width: `${Math.max(0, (r.fatos[c].valor / total) * 100)}%` }} /></span>
                <span className="num w-12 text-right text-stone-700">{fmt(r.fatos[c].valor)}</span>
              </div>
            ))}
          </div>
          <Valor r={r} fato="exig.pb_pct_alvo" />
          <Valor r={r} fato="exig.pm_leite" />
        </Painel>
        <Painel titulo="Metas da dieta" subtitulo="Restrições que valem para este lote">
          <Valor r={r} fato="meta.fdn_min" />
          <Valor r={r} fato="meta.fdnf_min" />
          <Valor r={r} fato="meta.cnf_max" />
          <Valor r={r} fato="meta.ee_max" />
          <Valor r={r} fato="meta.ureia_max" />
          <Valor r={r} fato="meta.fator_energia_min" />
        </Painel>
      </div>
      {temDieta && <Comparacao r={r} />}
      {r.alertas.length > 0 && (
        <Painel titulo="Conclusões e alertas">
          {r.alertas.map((a, i) => <AlertaItem key={i} alerta={a} />)}
        </Painel>
      )}
      <Traco r={r} />
      <Gaveta aberta={!!aberto} onFechar={() => setAberto(null)} titulo="Explicação">{aberto && <ExplicacaoAlerta alerta={aberto} />}</Gaveta>
    </div>
  )
}

function Comparacao({ r }: { r: Resultado }) {
  const v = (f: string) => r.fatos[f]?.valor
  const linhas = [
    { nome: 'Energia (ELl)', oferta: v('ver.ell_consumida'), alvo: v('exig.ell_total'), un: 'Mcal', tipo: 'min', tol: v('meta.fator_energia_min') ?? 0.95 },
    { nome: 'Proteína bruta', oferta: v('dieta.pb_pct'), alvo: v('exig.pb_pct_alvo'), un: '% MS', tipo: 'min', tol: 0.95 },
    { nome: 'Matéria seca', oferta: v('dieta.ms_kg'), alvo: v('exig.cms'), un: 'kg', tipo: 'faixa' },
    { nome: 'FDN', oferta: v('dieta.fdn_pct'), alvo: v('meta.fdn_min'), un: '% MS', tipo: 'min', tol: 1 },
    { nome: 'FDN de forragem', oferta: v('dieta.fdnf_pct'), alvo: v('meta.fdnf_min'), un: '% MS', tipo: 'min', tol: 1 },
    { nome: 'CNF', oferta: v('dieta.cnf_pct'), alvo: v('meta.cnf_max'), un: '% MS', tipo: 'max' },
    { nome: 'Gordura (EE)', oferta: v('dieta.ee_pct'), alvo: v('meta.ee_max'), un: '% MS', tipo: 'max' },
    { nome: 'Ureia', oferta: v('dieta.ureia_pct'), alvo: v('meta.ureia_max'), un: '% MS', tipo: 'max' },
  ].filter((l) => l.oferta !== undefined && l.alvo !== undefined)
  return (
    <Painel titulo="Oferta × exigência" subtitulo={`Dieta: ${fmt(v('dieta.ms_kg'))} kg MS · R$ ${fmt(v('dieta.custo_vaca_dia'))}/vaca/dia · ${fmt(v('dieta.forragem_pct'))}% de volumoso na MS`}>
      <div className="space-y-2">
        {linhas.map((l) => {
          const razao = l.oferta / l.alvo
          const ok = l.tipo === 'min' ? razao >= (l.tol ?? 1) : l.tipo === 'max' ? l.oferta <= l.alvo : razao >= 0.9 && razao <= 1.05
          const largura = Math.min(100, (razao / 1.5) * 100)
          return (
            <div key={l.nome} className="grid grid-cols-[110px_1fr_auto] items-center gap-3 text-sm sm:grid-cols-[150px_1fr_200px]">
              <span className="text-stone-600">{l.nome}</span>
              <span className="relative h-3 rounded bg-stone-100">
                <span className={`absolute inset-y-0 left-0 rounded ${ok ? 'bg-campo-500' : 'bg-amber-500'}`} style={{ width: `${largura}%` }} />
                <span className="absolute inset-y-[-3px] w-0.5 bg-stone-800" style={{ left: `${(1 / 1.5) * 100}%` }} title="alvo" />
              </span>
              <span className="num text-right text-xs text-stone-700">
                {fmt(l.oferta)} {l.tipo === 'max' ? '≤' : l.tipo === 'min' ? '≥' : '≈'} {fmt(l.alvo)} {l.un} {ok ? '✓' : '⚠'}
              </span>
            </div>
          )
        })}
      </div>
    </Painel>
  )
}

function Traco({ r }: { r: Resultado }) {
  const [aberto, setAberto] = useState(false)
  return (
    <Painel titulo="Traço de inferência" subtitulo={`${r.traco.length} regras disparadas · base v${r.kb_version}`}
      acoes={<button className="btn-secundario" onClick={() => setAberto(!aberto)}>{aberto ? 'Ocultar' : 'Mostrar'}</button>}>
      {aberto && (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="text-stone-500"><tr><th className="py-1 pr-2">Ciclo</th><th className="pr-2">Regra</th><th className="pr-2">Descrição</th><th className="pr-2">CF</th><th>Concorrentes no ciclo</th></tr></thead>
            <tbody>
              {r.traco.map((t) => (
                <tr key={t.ciclo} className="border-t border-stone-100 align-top">
                  <td className="num py-1 pr-2 text-stone-400">{t.ciclo}</td>
                  <td className="pr-2 font-mono font-semibold text-campo-700">{t.regra}</td>
                  <td className="pr-2 text-stone-700">{t.descricao}</td>
                  <td className="num pr-2">{t.cf.toFixed(2)}</td>
                  <td className="text-stone-400">{t.concorrentes.length ? t.concorrentes.join(', ') : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Painel>
  )
}

// ------------------------------------------------------------------ Dieta
function AbaDieta({ lote, dietaAtiva, onSalvo }: { lote: Lote; dietaAtiva: Dieta | null; onSalvo: () => void }) {
  const [alimentos, setAlimentos] = useState<Alimento[]>([])
  const [itens, setItens] = useState<ItemDieta[]>(dietaAtiva?.itens ?? [])
  const [versoes, setVersoes] = useState<Dieta[]>([])
  const [res, setRes] = useState<Resultado | null>(null)
  const [pl, setPl] = useState<any>(null)
  const [escolhidos, setEscolhidos] = useState<string[]>([])
  const [motivo, setMotivo] = useState('')
  const [ocupado, setOcupado] = useState('')
  const [erro, setErro] = useState('')

  useEffect(() => {
    api.get<Alimento[]>('/alimentos').then(setAlimentos)
    api.get<Dieta[]>(`/lotes/${lote.id}/dietas`).then(setVersoes)
  }, [lote.id])
  useEffect(() => { setEscolhidos(Array.from(new Set([...(dietaAtiva?.itens.map((i) => i.alimento) ?? []), 'ureia']))) }, [dietaAtiva])
  const { hash } = useLocation()
  useEffect(() => {
    if (hash === '#sugerir' && alimentos.length) document.getElementById('sugerir')?.scrollIntoView({ behavior: 'smooth' })
  }, [hash, alimentos.length])

  const nome = (id: string) => alimentos.find((a) => a.id === id)?.nome ?? id
  const verificar = async () => {
    setOcupado('verificar'); setErro('')
    try { setRes(await api.post<Resultado>(`/inferencia/lotes/${lote.id}/avaliar`, { itens })) } catch (e: any) { setErro(e.message) }
    setOcupado('')
  }
  const salvar = async (lista: ItemDieta[], origem: string, mot: string) => {
    setOcupado('salvar'); setErro('')
    try {
      await api.post(`/lotes/${lote.id}/dietas`, { itens: lista, motivo: mot || 'Ajuste manual', origem })
      setVersoes(await api.get<Dieta[]>(`/lotes/${lote.id}/dietas`)); setMotivo(''); onSalvo()
    } catch (e: any) { setErro(e.message) }
    setOcupado('')
  }
  const sugerir = async () => {
    setOcupado('pl'); setErro(''); setPl(null)
    try { setPl(await api.post(`/inferencia/lotes/${lote.id}/formular`, { alimentos: escolhidos })) } catch (e: any) { setErro(e.message) }
    setOcupado('')
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-4 lg:grid-cols-2">
        <Painel titulo="Montar e verificar a dieta" subtitulo="Quantidades por vaca/dia em matéria natural (como fornecido).">
          <div className="space-y-2">
            {itens.map((it, i) => (
              <div key={i} className="flex items-center gap-2">
                <select className="input" value={it.alimento} onChange={(e) => setItens(itens.map((x, j) => (j === i ? { ...x, alimento: e.target.value } : x)))}>
                  {alimentos.map((a) => <option key={a.id} value={a.id}>{a.nome}</option>)}
                </select>
                <input className="input num w-24" inputMode="decimal" value={it.kg_mn}
                  onChange={(e) => setItens(itens.map((x, j) => (j === i ? { ...x, kg_mn: Number(e.target.value.replace(',', '.')) || 0 } : x)))} />
                <span className="text-xs text-stone-500">kg</span>
                <button className="text-stone-400 hover:text-critico" onClick={() => setItens(itens.filter((_, j) => j !== i))} aria-label="Remover">✕</button>
              </div>
            ))}
            <button className="text-sm font-medium text-campo-600 hover:underline" onClick={() => setItens([...itens, { alimento: alimentos[0]?.id ?? 'silagem_milho', kg_mn: 1 }])}>+ alimento</button>
          </div>
          {erro && <div className="mt-2"><Erro msg={erro} /></div>}
          <div className="mt-4 flex flex-wrap items-center gap-2">
            <button className="btn-primario" onClick={verificar} disabled={!!ocupado || !itens.length}>Verificar dieta</button>
            <input className="input max-w-56" placeholder="Motivo da mudança" value={motivo} onChange={(e) => setMotivo(e.target.value)} />
            <button className="btn-secundario" onClick={() => salvar(itens, 'usuario', motivo)} disabled={!!ocupado || !itens.length}>Salvar nova versão</button>
          </div>
        </Painel>
        <div id="sugerir" className="scroll-mt-4">
        <Painel className={hash === '#sugerir' ? 'ring-2 ring-campo-500' : ''} titulo="Sugerir dieta de custo mínimo" subtitulo="As regras definem metas e restrições; a programação linear acha as quantidades; as regras verificam o resultado.">
          <div className="grid grid-cols-2 gap-1.5 sm:grid-cols-3">
            {alimentos.map((a) => (
              <label key={a.id} className="flex items-center gap-1.5 text-sm text-stone-700">
                <input type="checkbox" className="accent-campo-600" checked={escolhidos.includes(a.id)}
                  onChange={(e) => setEscolhidos(e.target.checked ? [...escolhidos, a.id] : escolhidos.filter((x) => x !== a.id))} />
                <span>{a.nome.replace(/ \(.*\)/, '')}</span>
                <span className="num text-xs text-stone-400">R${a.preco_kg_mn.toFixed(2)}</span>
              </label>
            ))}
          </div>
          <button className="btn-primario mt-3" onClick={sugerir} disabled={!!ocupado || !escolhidos.length}>{ocupado === 'pl' ? 'Otimizando…' : 'Sugerir dieta'}</button>
          {pl && <ResultadoPL pl={pl} nome={nome} onAceitar={(lista) => salvar(lista, 'pl', `Dieta de custo mínimo (PL), R$ ${pl.pl.custo.toFixed(2)}/vaca/dia`)} />}
        </Painel>
        </div>
      </div>
      {ocupado === 'verificar' && <Carregando />}
      {res && <ResultadoAvaliacao r={res} />}
      <Painel titulo="Versões da dieta" subtitulo="Cada ajuste aceito vira uma nova versão com motivo e parecer.">
        <ol className="space-y-2">
          {versoes.map((d) => (
            <li key={d.id} className="flex flex-wrap items-baseline gap-2 border-b border-stone-100 pb-2 text-sm last:border-0">
              <span className="font-semibold text-stone-900">v{d.versao}</span>
              {d.ativa && <span className="rounded-full bg-campo-100 px-2 text-xs font-semibold text-campo-700">ativa</span>}
              <span className="text-stone-400">{new Date(d.inicio + 'T12:00').toLocaleDateString('pt-BR')}</span>
              <span className="rounded bg-stone-100 px-1.5 text-xs text-stone-600">{d.origem === 'pl' ? 'PL custo mínimo' : 'manual'}</span>
              <span className="text-stone-700">{d.motivo}</span>
              <span className="w-full text-xs text-stone-500">{d.itens.map((i) => `${nome(i.alimento)} ${i.kg_mn} kg`).join(' · ')}</span>
              {d.parecer?.parecer && <span className="text-xs text-stone-500">Parecer: <b>{fmt(d.parecer.parecer)}</b> (base v{d.parecer.kb_version})</span>}
            </li>
          ))}
        </ol>
      </Painel>
    </div>
  )
}

function ResultadoPL({ pl, nome, onAceitar }: { pl: any; nome: (id: string) => string; onAceitar: (itens: ItemDieta[]) => void }) {
  const st = pl.pl.status
  const alertas: Alerta[] = (pl.alertas ?? []).filter((a: Alerta) => a.categoria === 'formulacao')
  if (st === 'dados_insuficientes') return <Erro msg="Faltam dados do lote para calcular as exigências." />
  return (
    <div className="mt-4 space-y-3">
      {alertas.filter((a) => a.nivel !== 'informativo').map((a, i) => (
        <div key={i} className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm">
          <div className="flex items-center gap-2"><NivelBadge nivel={a.nivel} /><span className="font-mono text-xs">{a.regra}</span></div>
          <p className="mt-1 font-medium text-stone-900">{a.titulo}</p>
          <p className="text-stone-600">{a.causa}</p>
          <p className="text-campo-700">{a.acao}</p>
        </div>
      ))}
      {st === 'inviavel' && <p className="text-sm text-stone-600">Restrições que impedem a solução: <b>{pl.pl.restricoes_violadas.join(', ')}</b>.</p>}
      {st === 'otimo' && (
        <>
          <div className="rounded-lg bg-campo-50 p-3">
            <p className="num text-sm font-semibold text-campo-900">R$ {pl.pl.custo.toFixed(2)} por vaca/dia · {fmt(pl.pl.composicao.ms_kg)} kg MS · PB {fmt(pl.pl.composicao.pb_pct)}% · FDN {fmt(pl.pl.composicao.fdn_pct)}%</p>
            <ul className="mt-1 text-sm text-stone-700">
              {pl.pl.itens.map((i: ItemDieta) => <li key={i.alimento} className="num">{nome(i.alimento)}: <b>{i.kg_mn}</b> kg MN</li>)}
            </ul>
            <p className="mt-2 text-xs text-stone-600">Verificação pelas regras: <b>{fmt(pl.verificacao?.fatos?.['parecer.dieta']?.valor)}</b></p>
            {(pl.verificacao?.alertas ?? []).filter((a: Alerta) => a.nivel !== 'informativo').map((a: Alerta) => (
              <p key={a.regra} className="mt-1 text-xs text-atencao"><span className="font-mono">{a.regra}</span> {a.titulo}</p>
            ))}
          </div>
          <button className="btn-primario" onClick={() => onAceitar(pl.pl.itens)}>Aceitar como nova versão</button>
        </>
      )}
    </div>
  )
}

// ------------------------------------------------------------------ Acompanhamento
const ROTULO_EVENTO: Record<string, string> = { troca_volumoso: 'troca de volumoso', silo_novo: 'silo novo', movimentacao: 'movimentação', correcao_ms: 'correção de MS', mudanca_concentrado: 'mudança de concentrado' }
const dataCurta = (d: string) => new Date(d.slice(0, 10) + 'T12:00').toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })

function AbaAcompanhamento({ loteId }: { loteId: number }) {
  const [s, setS] = useState<any>(null)
  useEffect(() => { api.get(`/lotes/${loteId}/serie`).then(setS) }, [loteId])
  const dados = useMemo(() => s?.producao.map((p: any) => ({ ...p, dia: dataCurta(p.data) })) ?? [], [s])
  if (!s) return <Carregando texto="Carregando séries…" />
  const eventos = s.eventos.filter((e: any) => e.tipo !== 'silo_novo')
  const mini = (ind: string, titulo: string, un: string, refs: { y: number; rotulo: string }[] = []) => {
    const d = s.indicadores[ind]?.map((p: any) => ({ dia: dataCurta(p.data), valor: p.valor })) ?? []
    if (!d.length) return null
    return (
      <Painel key={ind} titulo={titulo} subtitulo={un}>
        <div className="h-36">
          <ResponsiveContainer>
            <LineChart data={d} margin={{ left: -20, right: 8 }}>
              <CartesianGrid stroke="#f0eeec" />
              <XAxis dataKey="dia" tick={{ fontSize: 10 }} minTickGap={20} />
              <YAxis tick={{ fontSize: 10 }} domain={['auto', 'auto']} />
              <Tooltip />
              {refs.map((r) => <ReferenceLine key={r.rotulo} y={r.y} stroke="#b54708" strokeDasharray="4 3" label={{ value: r.rotulo, fontSize: 10, fill: '#b54708', position: 'insideTopRight' }} />)}
              <Line dataKey="valor" stroke="#2f7230" strokeWidth={2} dot={{ r: 2 }} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Painel>
    )
  }
  return (
    <div className="space-y-4">
      <Painel titulo="Produção observada × esperada" subtitulo="Esperado = curva de lactação (Cobuci) × escala da fazenda, corrigido pelo ITU. Linhas verticais = eventos registrados.">
        <div className="h-72">
          <ResponsiveContainer>
            <ComposedChart data={dados} margin={{ left: -10, right: 10 }}>
              <CartesianGrid stroke="#f0eeec" />
              <XAxis dataKey="dia" tick={{ fontSize: 11 }} minTickGap={24} />
              <YAxis yAxisId="l" tick={{ fontSize: 11 }} domain={['auto', 'auto']} unit=" L" />
              <YAxis yAxisId="itu" orientation="right" tick={{ fontSize: 11 }} domain={[60, 90]} />
              <Tooltip formatter={(v: any, n: any) => [typeof v === 'number' ? v.toFixed(1) : v, n]} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <ReferenceLine yAxisId="itu" y={72} stroke="#fca5a5" strokeDasharray="2 4" />
              {eventos.map((e: any) => (
                <ReferenceLine key={e.data + e.tipo} yAxisId="l" x={dataCurta(e.data)} stroke="#78716c" strokeDasharray="3 3" />
              ))}
              <Line yAxisId="itu" dataKey="itu" name="ITU" stroke="#f97316" strokeWidth={1} dot={false} isAnimationActive={false} />
              <Line yAxisId="l" dataKey="esperado" name="Esperado (L/vaca)" stroke="#a8a29e" strokeDasharray="5 4" strokeWidth={2} dot={false} isAnimationActive={false} />
              <Line yAxisId="l" dataKey="observado" name="Observado (L/vaca)" stroke="#2f7230" strokeWidth={2.5} dot={false} isAnimationActive={false} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
        {eventos.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-2 text-xs">
            {eventos.map((e: any) => (
              <span key={e.data + e.tipo} className="rounded-full bg-stone-100 px-2 py-0.5 text-stone-600">
                <b>{dataCurta(e.data)}</b> {ROTULO_EVENTO[e.tipo] ?? e.tipo}{e.descricao ? ` — ${e.descricao}` : ''}
              </span>
            ))}
          </div>
        )}
      </Painel>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {mini('sobras_pct', 'Sobras de cocho', '% da oferta', [{ y: 2, rotulo: 'mín.' }])}
        {mini('ms_silagem', 'MS da silagem', '% (micro-ondas)')}
        {mini('ecc', 'Escore de condição corporal', '1 a 5')}
        {mini('concentrado_kg_vaca', 'Concentrado', 'kg/vaca/dia')}
        {mini('laudo_nul', 'NUL (laudo)', 'mg/dL', [{ y: 16, rotulo: 'alto' }, { y: 19.5, rotulo: 'reprodução' }])}
        {mini('laudo_gordura', 'Gordura (laudo)', '%')}
        {mini('laudo_lactose', 'Lactose (laudo)', '%', [{ y: 4.3, rotulo: 'IN 76' }])}
        {mini('laudo_ccs', 'CCS (laudo)', 'mil cél/mL', [{ y: 500, rotulo: 'IN 76' }])}
      </div>
    </div>
  )
}

// ------------------------------------------------------------------ Registro rápido
const CAMPOS = {
  diario: [['vacas', 'Vacas ordenhadas', 'nº'], ['litros', 'Litros do lote', 'L'], ['concentrado_kg_vaca', 'Concentrado', 'kg/vaca'], ['temp', 'Temperatura', '°C'], ['ur', 'Umidade', '%']],
  semanal: [['sobras_pct', 'Sobras de cocho', '%'], ['ms_silagem', 'MS da silagem', '%'], ['ecc', 'ECC médio', '1–5'], ['escore_fezes', 'Escore de fezes', '1–5'], ['ruminacao', 'Ruminação média', 'min/d']],
  mensal: [['laudo_gordura', 'Gordura', '%'], ['laudo_proteina', 'Proteína', '%'], ['laudo_lactose', 'Lactose', '%'], ['laudo_ureia', 'Ureia', 'mg/dL'], ['laudo_nul', 'NUL', 'mg/dL'], ['laudo_ccs', 'CCS', 'mil/mL'], ['laudo_cbt', 'CBT', 'mil UFC/mL']],
} as const

function AbaRegistro({ lote }: { lote: Lote }) {
  const hoje = new Date().toISOString().slice(0, 10)
  const [data, setData] = useState(hoje)
  const [valores, setValores] = useState<Record<string, string>>({ vacas: String(lote.n_vacas) })
  const [abertos, setAbertos] = useState<Record<string, boolean>>({ diario: true })
  const [evento, setEvento] = useState({ tipo: 'troca_volumoso', descricao: '' })
  const [res, setRes] = useState<Resultado | null>(null)
  const [erro, setErro] = useState('')
  const [ok, setOk] = useState('')

  const clima = async () => {
    const c: any = await api.get(`/clima/${lote.fazenda_id}`)
    if (c.disponivel) setValores((v) => ({ ...v, temp: String(c.temp), ur: String(c.ur) }))
    else setErro('Sem internet para buscar o clima: digite temperatura e umidade.')
  }
  const enviar = async () => {
    setErro(''); setOk('')
    const nums = Object.fromEntries(Object.entries(valores).filter(([, v]) => v !== '').map(([k, v]) => [k, Number(v.replace(',', '.'))]))
    try { setRes(await api.post<Resultado>(`/lotes/${lote.id}/registros`, { data, valores: nums })); setOk('Registro salvo e acompanhamento executado.') }
    catch (e: any) { setErro(e.message) }
  }
  const enviarEvento = async () => {
    setErro(''); setOk('')
    try { await api.post(`/lotes/${lote.id}/eventos`, { data_hora: `${data}T08:00:00`, ...evento }); setOk('Evento registrado: abre janelas de supressão e de atribuição de causa.') }
    catch (e: any) { setErro(e.message) }
  }
  const secao = (k: keyof typeof CAMPOS, titulo: string) => (
    <div className="border-t border-stone-100 pt-3">
      <button className="flex w-full items-center justify-between text-left text-sm font-semibold text-stone-800" onClick={() => setAbertos({ ...abertos, [k]: !abertos[k] })}>
        {titulo}<span className="text-stone-400">{abertos[k] ? '−' : '+'}</span>
      </button>
      {abertos[k] && (
        <div className="mt-2 grid grid-cols-2 gap-3 sm:grid-cols-3">
          {CAMPOS[k].map(([ind, nome, un]) => (
            <label key={ind}>
              <span className="rotulo">{nome} ({un})</span>
              <input className="input num" inputMode="decimal" value={valores[ind] ?? ''} onChange={(e) => setValores({ ...valores, [ind]: e.target.value })} />
            </label>
          ))}
        </div>
      )}
    </div>
  )
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <div className="space-y-4">
        <Painel titulo="Registro do dia" subtitulo="O mínimo é nº de vacas, litros e concentrado. O resto é opcional e entra quando houver.">
          <div className="mb-3 flex flex-wrap items-end gap-2">
            <label><span className="rotulo">Data</span><input type="date" className="input" value={data} onChange={(e) => setData(e.target.value)} /></label>
            <button className="btn-secundario" onClick={clima}>Clima atual (Open-Meteo)</button>
          </div>
          <div className="space-y-3">
            {secao('diario', 'Diário')}
            {secao('semanal', 'Semanal (cocho, silagem, ECC)')}
            {secao('mensal', 'Mensal (laudo do laticínio / controle leiteiro)')}
          </div>
          {erro && <div className="mt-3"><Erro msg={erro} /></div>}
          {ok && <div className="mt-3 rounded-lg bg-campo-50 p-2 text-sm text-campo-700">{ok}</div>}
          <button className="btn-primario mt-4" onClick={enviar}>Salvar e analisar</button>
        </Painel>
        <Painel titulo="Registrar evento" subtitulo="Eventos explicam variações e evitam alarmes falsos.">
          <div className="flex flex-wrap gap-2">
            <select className="input max-w-52" value={evento.tipo} onChange={(e) => setEvento({ ...evento, tipo: e.target.value })}>
              {Object.entries(ROTULO_EVENTO).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
            <input className="input flex-1" placeholder="Descrição" value={evento.descricao} onChange={(e) => setEvento({ ...evento, descricao: e.target.value })} />
            <button className="btn-secundario" onClick={enviarEvento}>Registrar</button>
          </div>
        </Painel>
      </div>
      <div>
        {res && (
          <Painel titulo="Resultado do acompanhamento" subtitulo={`${res.traco.length} regras disparadas`}>
            {res.alertas.length === 0 && <p className="text-sm text-campo-700">Nenhum alerta: o lote está dentro do esperado.</p>}
            {res.alertas.map((a, i) => <AlertaItem key={i} alerta={a} />)}
            {['mon.litros_vaca', 'mon.esperado_vaca', 'mon.residuo', 'mon.itu_2d', 'mon.litros_por_kg_conc'].filter((f) => res.fatos[f]).map((f) => (
              <div key={f} className="flex justify-between border-t border-stone-100 py-1 text-sm"><span className="text-stone-500">{rotulo(f)}</span><span className="num">{fmt(res.fatos[f].valor, f)}</span></div>
            ))}
          </Painel>
        )}
      </div>
    </div>
  )
}

// ------------------------------------------------------------------ Alertas
function AbaAlertas({ loteId }: { loteId: number }) {
  const [alertas, setAlertas] = useState<Alerta[] | null>(null)
  const [aberto, setAberto] = useState<Alerta | null>(null)
  const [filtro, setFiltro] = useState('todos')
  useEffect(() => { api.get<Alerta[]>(`/alertas?lote_id=${loteId}&dias=60`).then(setAlertas) }, [loteId])
  if (!alertas) return <Carregando />
  const lista = alertas.filter((a) => filtro === 'todos' || (filtro === 'suprimido' ? a.status === 'suprimido' : a.nivel === filtro && a.status === 'ativo'))
  return (
    <Painel titulo="Histórico de alertas (60 dias)" subtitulo="Alertas repetidos são agrupados por janela; suprimidos mostram a meta-regra responsável."
      acoes={
        <select className="input w-44" value={filtro} onChange={(e) => setFiltro(e.target.value)}>
          <option value="todos">Todos</option><option value="critico">Críticos</option><option value="atencao">Atenção</option>
          <option value="informativo">Informativos</option><option value="suprimido">Suprimidos</option>
        </select>
      }>
      {lista.length === 0 && <p className="text-sm text-stone-500">Nenhum alerta.</p>}
      {lista.map((a) => <AlertaItem key={a.id} alerta={a} onAbrir={() => setAberto(a)} />)}
      <Gaveta aberta={!!aberto} onFechar={() => setAberto(null)} titulo="Explicação do alerta">{aberto && <ExplicacaoAlerta alerta={aberto} />}</Gaveta>
    </Painel>
  )
}
