/** Abas e painéis do lote: simulador "e se?", planilha de trato, plano de transição e sensibilidade de preços. */
import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Area, CartesianGrid, ComposedChart, Legend, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api, dataBR, fmt, numero, peso, reais, tecnico, textoAlerta, type Alerta, type Alimento, type Dieta, type ItemDieta, type Lote } from '../api'
import { AlertaCorpo, Carregando, Erro, NivelBadge, Painel } from '../components/ui'

const hojeISO = () => new Date().toISOString().slice(0, 10)

// ------------------------------------------------------------------ simulador "e se?"
export function AbaSimular({ lote, dieta }: { lote: Lote; dieta: Dieta | null }) {
  const navegar = useNavigate()
  const [alimentos, setAlimentos] = useState<Alimento[]>([])
  const [itens, setItens] = useState<ItemDieta[]>(dieta?.itens.map((i) => ({ ...i })) ?? [])
  const [leite, setLeite] = useState('')
  const [precoLeite, setPrecoLeite] = useState('')
  const [precos, setPrecos] = useState<Record<string, string>>({})
  const [troca, setTroca] = useState({ de: '', para: '' })
  const [r, setR] = useState<any>(null)
  const [erro, setErro] = useState('')
  const [rodando, setRodando] = useState(false)
  useEffect(() => { api.get<Alimento[]>(`/fazendas/${lote.fazenda_id}/alimentos`).then(setAlimentos) }, [lote.fazenda_id])
  const al = (id: string) => alimentos.find((a) => a.id === id)
  const n = (x: string) => (x.trim() === '' ? undefined : Number(x.replace(',', '.')))

  useEffect(() => {          // simula sozinho a cada mudança (com uma pequena espera)
    if (!itens.length) return
    const t = setTimeout(async () => {
      setRodando(true); setErro('')
      const pr = Object.fromEntries(Object.entries(precos).map(([k, v]) => [k, n(v)]).filter(([, v]) => v !== undefined))
      try {
        setR(await api.post(`/inferencia/lotes/${lote.id}/simular`, {
          itens: itens.filter((i) => i.kg_mn > 0), leite: n(leite) ?? null, preco_leite: n(precoLeite) ?? null,
          precos: Object.keys(pr).length ? pr : null,
        }))
      } catch (e: any) { setErro(e.message) }
      setRodando(false)
    }, 500)
    return () => clearTimeout(t)
  }, [itens, leite, precoLeite, precos, lote.id])  // eslint-disable-line react-hooks/exhaustive-deps

  const concentrados = itens.filter((i) => al(i.alimento)?.tipo === 'concentrado')
  const totalConc = concentrados.reduce((s, i) => s + i.kg_mn, 0)
  const mudarConcentrado = (delta: number) => {
    if (!totalConc) return
    const f = Math.max(0, totalConc + delta) / totalConc
    setItens(itens.map((i) => (al(i.alimento)?.tipo === 'concentrado' ? { ...i, kg_mn: Math.round(i.kg_mn * f * 100) / 100 } : i)))
  }
  const trocarVolumoso = () => {
    const de = itens.find((i) => i.alimento === troca.de), a = al(troca.de), b = al(troca.para)
    if (!de || !a || !b) return
    const kg = Math.round((de.kg_mn * a.ms) / b.ms * 10) / 10       // mesma matéria seca
    const resto = itens.filter((i) => i.alimento !== troca.de && i.alimento !== troca.para)
    const ja = itens.find((i) => i.alimento === troca.para)
    setItens([...resto, { alimento: troca.para, kg_mn: Math.round(((ja?.kg_mn ?? 0) + kg) * 10) / 10 }])
    setTroca({ de: '', para: '' })
  }
  if (!dieta) return <Erro msg="O lote ainda não tem dieta. Monte uma na aba Dieta para simular." />
  const a = r?.atual, b = r?.simulado, vacas = r?.vacas ?? lote.n_vacas
  const linhas: [string, (x: any) => number | null | undefined, (v: number) => string, 'mais' | 'menos' | ''][] = [
    ['Leite previsto por vaca', (x) => x.leite_previsto, (v) => `${numero(v)} L`, 'mais'],
    ['Leite que a comida sustenta', (x) => x.leite_permitido, (v) => `${numero(v)} L`, 'mais'],
    ['Custo da comida por vaca/dia', (x) => x.custo_vaca_dia, (v) => reais(v), 'menos'],
    ['Comida por litro de leite', (x) => x.custo_por_litro, (v) => reais(v), 'menos'],
    ['Dinheiro do leite por vaca/dia', (x) => x.receita_vaca_dia, (v) => reais(v), 'mais'],
    ['Sobra por vaca/dia depois da comida', (x) => x.margem_vaca_dia, (v) => reais(v), 'mais'],
    ['Sobra do lote por mês', (x) => (x.margem_vaca_dia ?? null) !== null ? x.margem_vaca_dia * vacas * 30 : null, (v) => reais(v, 0), 'mais'],
    ['Energia (do necessário)', (x) => x.cobertura_energia, (v) => fmt(v, 'ver.razao_energia'), ''],
    ['Proteína (do necessário)', (x) => x.cobertura_proteina, (v) => fmt(v, 'ver.razao_pb'), ''],
  ]
  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_1.1fr]">
      <div className="space-y-4">
        <Painel titulo="Mude o que quiser" subtitulo="Nada é gravado: o sistema confere a dieta e refaz as contas a cada mudança.">
          <div className="space-y-2">
            {itens.map((it, i) => (
              <div key={i} className="flex items-center gap-2 text-sm">
                <span className="min-w-0 flex-1 truncate text-stone-700">{al(it.alimento)?.nome ?? it.alimento}</span>
                <input className="input num w-20" inputMode="decimal" value={it.kg_mn}
                  onChange={(e) => setItens(itens.map((x, j) => (j === i ? { ...x, kg_mn: Number(e.target.value.replace(',', '.')) || 0 } : x)))} />
                <span className="text-xs text-stone-500">kg</span>
                <input className="input num w-20" inputMode="decimal" placeholder={al(it.alimento) ? numero(al(it.alimento)!.preco_kg_mn, 2) : ''}
                  title="preço por kg neste cenário" value={precos[it.alimento] ?? ''} onChange={(e) => setPrecos({ ...precos, [it.alimento]: e.target.value })} />
                <span className="text-xs text-stone-500">R$/kg</span>
              </div>
            ))}
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            <button className="btn-secundario" disabled={!totalConc} onClick={() => mudarConcentrado(-0.5)}>− 0,5 kg de concentrado</button>
            <button className="btn-secundario" disabled={!totalConc} onClick={() => mudarConcentrado(0.5)}>+ 0,5 kg de concentrado</button>
            <button className="text-sm text-stone-500 hover:underline" onClick={() => { setItens(dieta.itens.map((i) => ({ ...i }))); setPrecos({}); setLeite(''); setPrecoLeite('') }}>voltar à dieta atual</button>
          </div>
          <div className="mt-3 flex flex-wrap items-end gap-2 border-t border-stone-100 pt-3 text-sm">
            <label><span className="rotulo">Trocar o volumoso</span>
              <select className="input" value={troca.de} onChange={(e) => setTroca({ ...troca, de: e.target.value })}>
                <option value="">escolha…</option>
                {itens.filter((i) => al(i.alimento)?.tipo === 'volumoso').map((i) => <option key={i.alimento} value={i.alimento}>{al(i.alimento)?.nome}</option>)}
              </select></label>
            <label><span className="rotulo">por</span>
              <select className="input" value={troca.para} onChange={(e) => setTroca({ ...troca, para: e.target.value })}>
                <option value="">escolha…</option>
                {alimentos.filter((x) => x.tipo === 'volumoso' && x.id !== troca.de && (lote.sistema !== 'confinado' || !x.pastejo)).map((x) => <option key={x.id} value={x.id}>{x.nome}</option>)}
              </select></label>
            <button className="btn-secundario" disabled={!troca.de || !troca.para} onClick={trocarVolumoso}>Trocar</button>
          </div>
          <div className="mt-3 grid grid-cols-2 gap-3 border-t border-stone-100 pt-3">
            <label><span className="rotulo">Meta de leite (L/vaca)</span><input className="input num" inputMode="decimal" placeholder={a ? numero(a.leite_meta) : ''} value={leite} onChange={(e) => setLeite(e.target.value)} /></label>
            <label><span className="rotulo">Preço do leite (R$/L)</span><input className="input num" inputMode="decimal" placeholder={a ? numero(a.preco_leite, 2) : ''} value={precoLeite} onChange={(e) => setPrecoLeite(e.target.value)} /></label>
          </div>
        </Painel>
      </div>
      <div className="space-y-4">
        {erro && <Erro msg={erro} />}
        {!r && <Carregando texto="Simulando…" />}
        {r && (
          <Painel titulo={<>Hoje × simulado {rodando && <span className="ml-2 text-xs font-normal text-stone-400">atualizando…</span>}</>} subtitulo={`${numero(vacas, 0)} vacas. Leite previsto = o menor entre a meta e o que a comida sustenta.`}>
            <table className="w-full text-sm">
              <thead className="text-xs text-stone-500"><tr><th className="py-1 text-left" /><th className="text-right">Hoje</th><th className="pl-3 text-right">Simulado</th><th className="pl-3 text-right">Diferença</th></tr></thead>
              <tbody>
                {linhas.map(([nome, f, fm, melhor]) => {
                  const va = f(a), vb = f(b)
                  const d = va !== null && va !== undefined && vb !== null && vb !== undefined ? vb - va : null
                  const bom = d === null || Math.abs(d) < 1e-6 || !melhor ? null : (melhor === 'mais') === d > 0
                  return (
                    <tr key={nome} className="border-t border-stone-100">
                      <td className="py-1.5 text-stone-600">{nome}</td>
                      <td className="num text-right">{va === null || va === undefined ? '—' : fm(va)}</td>
                      <td className="num text-right font-semibold text-stone-900">{vb === null || vb === undefined ? '—' : fm(vb)}</td>
                      <td className={`num text-right text-xs ${bom === null ? 'text-stone-400' : bom ? 'text-campo-700' : 'text-critico'}`}>
                        {d === null || Math.abs(d) < 1e-6 ? '—' : `${d > 0 ? '+' : '−'}${fm(Math.abs(d)).replace(/^-/, '')}`}
                      </td>
                    </tr>
                  )
                })}
                <tr className="border-t border-stone-100"><td className="py-1.5 text-stone-600">Dieta conferida</td><td className="text-right">{fmt(a.parecer)}</td><td className="text-right font-semibold">{fmt(b.parecer)}</td><td /></tr>
              </tbody>
            </table>
            {b.leite_permitido !== null && b.leite_meta && b.leite_permitido < b.leite_meta - 0.3 && (
              <p className="mt-3 rounded-md border-l-4 border-l-brinco bg-brinco-claro p-2.5 text-sm text-stone-800">A comida não sustenta {numero(b.leite_meta)} L: o lote tende a cair para uns {numero(b.leite_permitido)} L por vaca.</p>
            )}
            {b.leite_permitido !== null && b.leite_meta && b.leite_permitido > b.leite_meta + 1 && (
              <p className="mt-3 rounded-lg bg-stone-50 p-2 text-sm text-stone-600">Sobra energia para uns {numero(b.leite_permitido - b.leite_meta)} L a mais por vaca. Se as vacas não tiverem potencial para produzir mais, essa energia vira gordura (e custo).</p>
            )}
            {b.alertas.length > 0 && (
              <div className="mt-3 space-y-1">
                <p className="text-xs font-medium text-stone-500">Avisos da dieta simulada</p>
                {b.alertas.map((x: Alerta) => <p key={x.regra} className="flex items-start gap-2 text-sm"><NivelBadge nivel={x.nivel} /><span>{tecnico() && <span className="font-mono text-xs">{x.regra} </span>}{textoAlerta(x).titulo}</span></p>)}
              </div>
            )}
            <button className="btn-primario mt-4" onClick={() => navegar('../dieta', { state: { itensAjuste: itens.filter((i) => i.kg_mn > 0), rotulo: 'Dieta do simulador', origem: 'simulacao' } })}>
              Levar esta dieta para o editor
            </button>
          </Painel>
        )}
      </div>
    </div>
  )
}

// ------------------------------------------------------------------ planilha de trato
export function AbaTrato({ lote }: { lote: Lote }) {
  const [tratos, setTratos] = useState(2)
  const [divisao, setDivisao] = useState('')
  const [sobra, setSobra] = useState('0')
  const [data, setData] = useState(hojeISO())
  const [p, setP] = useState<any>(null)
  const [erro, setErro] = useState('')
  useEffect(() => {
    setErro('')
    const q = new URLSearchParams({ tratos: String(tratos), sobra_pct: sobra.replace(',', '.') || '0', data })
    if (divisao.trim()) q.set('divisao', divisao.replace(/\//g, ','))
    api.get(`/lotes/${lote.id}/trato?${q}`).then(setP).catch((e) => { setErro(e.message); setP(null) })
  }, [lote.id, tratos, divisao, sobra, data])
  return (
    <div className="space-y-4">
      <Painel className="print:hidden" titulo="Planilha de trato" subtitulo="Quanto colocar de cada alimento para o lote inteiro, em cada trato, na ordem de carregar o vagão.">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <label><span className="rotulo">Tratos por dia</span>
            <select className="input" value={tratos} onChange={(e) => { setTratos(Number(e.target.value)); setDivisao('') }}>{[1, 2, 3, 4].map((t) => <option key={t} value={t}>{t}</option>)}</select></label>
          <label><span className="rotulo">Divisão (%)</span><input className="input" placeholder={Array(tratos).fill(Math.round(100 / tratos)).join('/')} value={divisao} onChange={(e) => setDivisao(e.target.value)} /></label>
          <label><span className="rotulo">Folga de sobra (%)</span><input className="input num" inputMode="decimal" value={sobra} onChange={(e) => setSobra(e.target.value)} /></label>
          <label><span className="rotulo">Dia</span><input type="date" className="input" value={data} onChange={(e) => setData(e.target.value)} /></label>
        </div>
        <button className="btn-primario mt-3" onClick={() => window.print()} disabled={!p}>Imprimir</button>
      </Painel>
      {erro && <Erro msg={erro} />}
      {p && (
        <section className="card p-4 sm:p-5 print:border-0 print:shadow-none">
          <div className="mb-2 flex flex-wrap items-baseline justify-between gap-2">
            <h2 className="titulo text-2xl font-semibold text-stone-900">Trato: {p.lote.nome}</h2>
            <span className="text-sm text-stone-500">{dataBR(p.data)} · {numero(p.vacas, 0)} vacas · dieta v{p.dieta_versao}{p.sobra_pct ? ` · folga ${numero(p.sobra_pct)}%` : ''}</span>
          </div>
          {p.observacoes.length > 0 && (
            <ul className="mb-3 space-y-0.5 rounded-md border-l-4 border-l-brinco bg-brinco-claro p-2.5 text-sm text-stone-800">{p.observacoes.map((o: string) => <li key={o}>• {o}</li>)}</ul>
          )}
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-xs text-stone-500">
                <tr><th className="py-1 text-left">#</th><th className="text-left">Alimento</th><th className="text-right">Por vaca</th><th className="text-right">Dia todo</th>
                  {p.total_por_trato.map((_: number, k: number) => <th key={k} className="text-right">Trato {k + 1} ({Math.round(p.divisao[k] * 100)}%)</th>)}
                  <th className="hidden print:table-cell">feito</th></tr>
              </thead>
              <tbody>
                {p.linhas.map((l: any, i: number) => (
                  <tr key={l.alimento} className="border-t border-stone-100">
                    <td className="py-1.5 text-stone-400">{i + 1}</td>
                    <td className="font-medium text-stone-800">{l.nome}</td>
                    <td className="num text-right text-stone-600">{numero(l.kg_vaca, 2)} kg</td>
                    <td className="num text-right">{peso(l.kg_total)}</td>
                    {l.por_trato.map((kg: number, k: number) => <td key={k} className="num text-right text-base font-semibold text-stone-900">{peso(kg)}</td>)}
                    <td className="hidden text-center print:table-cell">☐</td>
                  </tr>
                ))}
                <tr className="border-t-2 border-stone-300 font-semibold">
                  <td /><td>Total</td><td /><td className="num text-right">{peso(p.total)}</td>
                  {p.total_por_trato.map((kg: number, k: number) => <td key={k} className="num text-right">{peso(kg)}</td>)}
                  <td className="hidden print:table-cell" />
                </tr>
              </tbody>
            </table>
          </div>
          {p.no_pasto.length > 0 && <p className="mt-2 text-xs text-stone-500">No pasto (fora do vagão): {p.no_pasto.map((x: any) => x.nome).join(', ')}.</p>}
          {tecnico() && <p className="mt-2 text-xs text-stone-400">Ordem de carregamento e recomendações vêm dos parâmetros trato_ordem e trato_notas da base.</p>}
        </section>
      )}
    </div>
  )
}

// ------------------------------------------------------------------ plano de transição
export function PlanoTransicao({ dieta, nome }: { dieta: Dieta; nome: (id: string) => string }) {
  const t = dieta.transicao!
  const hoje = hojeISO()
  const fim = t.plano[t.plano.length - 1].data
  const depois = new Date(new Date(fim + 'T12:00').getTime() + 7 * 864e5).toISOString().slice(0, 10)
  if (hoje > depois) return null
  const ids = Array.from(new Set(t.plano.flatMap((e) => e.itens.map((i) => i.alimento))))
  const etapa = t.plano.find((e) => e.data === hoje)
  return (
    <Painel titulo={`Troca de dieta aos poucos: v${t.de_versao} → v${dieta.versao}`}
      subtitulo={etapa ? `Hoje é o dia ${etapa.dia} de ${t.dias} (${etapa.pct_nova}% da dieta nova).` : hoje > fim ? `Troca concluída em ${dataBR(fim)}. O lote segue em observação de adaptação por mais alguns dias.` : `Começa em ${dataBR(t.plano[0].data)}.`}>
      {t.alerta && <p className="mb-2 text-sm text-stone-600">{textoAlerta(t.alerta).causa}</p>}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="text-xs text-stone-500"><tr><th className="py-1 text-left">Dia</th><th className="text-left">Data</th><th className="text-right">Dieta nova</th>{ids.map((id) => <th key={id} className="text-right">{nome(id)}</th>)}</tr></thead>
          <tbody>
            {t.plano.map((e) => (
              <tr key={e.dia} className={`border-t border-stone-100 ${e.data === hoje ? 'bg-campo-50 font-semibold' : ''}`}>
                <td className="py-1">{e.dia}</td><td>{dataBR(e.data)}</td><td className="num text-right">{e.pct_nova}%</td>
                {ids.map((id) => <td key={id} className="num text-right">{numero(e.itens.find((i) => i.alimento === id)?.kg_mn ?? 0, 2)}</td>)}
              </tr>
            ))}
            <tr className="border-t border-stone-200 text-stone-500"><td className="py-1">{t.dias + 1}</td><td>em diante</td><td className="num text-right">100%</td>
              {ids.map((id) => <td key={id} className="num text-right">{numero(dieta.itens.find((i) => i.alimento === id)?.kg_mn ?? 0, 2)}</td>)}</tr>
          </tbody>
        </table>
      </div>
      <p className="mt-2 text-xs text-stone-500">kg por vaca/dia. Durante a troca, olhe o cocho, as fezes e o leite: o sistema avisa se o lote estranhar a dieta nova.</p>
    </Painel>
  )
}

// ------------------------------------------------------------------ sensibilidade de preços
export function Sensibilidade({ loteId, alimentos }: { loteId: number; alimentos: string[] }) {
  const [r, setR] = useState<any>(null)
  const [ocupado, setOcupado] = useState(false)
  const [erro, setErro] = useState('')
  useEffect(() => setR(null), [alimentos.join()])
  const calcular = async () => {
    setOcupado(true); setErro('')
    try { setR(await api.post(`/inferencia/lotes/${loteId}/sensibilidade`, { alimentos })) } catch (e: any) { setErro(e.message) }
    setOcupado(false)
  }
  const META: Record<string, string> = { energia: 'energia', proteina: 'proteína', fibra: 'fibra' }
  return (
    <div className="mt-3 rounded-lg border border-stone-200 p-3">
      {!r && <button className="text-sm font-medium text-campo-600 hover:underline" onClick={calcular} disabled={ocupado}>{ocupado ? 'Calculando…' : 'E se os preços mudarem? (até quanto vale pagar em cada alimento)'}</button>}
      {erro && <Erro msg={erro} />}
      {r && r.status !== 'otimo' && <p className="text-sm text-stone-500">Só dá para calcular quando existe uma dieta que atende tudo.</p>}
      {r?.status === 'otimo' && (
        <div className="space-y-2 text-sm">
          <p className="font-medium text-stone-800">Até quanto vale pagar ({reais(r.custo)} por vaca/dia hoje)</p>
          <ul className="space-y-1">
            {r.alimentos.filter((a: any) => a.na_dieta).map((a: any) => (
              <li key={a.alimento}><b>{a.nome}</b> <span className="text-stone-500">({reais(a.preco)}/kg)</span>: {a.mantem_ate === null ? 'a dieta continua igual mesmo bem mais caro'
                : <>a dieta continua igual até <b>{reais(a.mantem_ate)}</b>/kg</>}{a.mantem_ate !== null && (a.sai_acima === null ? '; depois diminui, mas não sai' : <>; sai da dieta acima de <b>{reais(a.sai_acima)}</b>/kg</>)}.</li>
            ))}
            {r.alimentos.filter((a: any) => !a.na_dieta).map((a: any) => (
              <li key={a.alimento} className="text-stone-600"><b>{a.nome}</b> ({reais(a.preco)}/kg): {a.entra_abaixo ? <>entraria na dieta se custasse menos de <b>{reais(a.entra_abaixo)}</b>/kg</> : 'não entraria nem bem mais barato (limites da dieta)'}.</li>
            ))}
          </ul>
          {r.metas.some((m: any) => m.economia > 0.005) && (
            <p className="text-xs text-stone-500">Quanto custa cada exigência: {r.metas.filter((m: any) => m.economia > 0.005).map((m: any) => `${Math.round(m.variacao * 100)}% menos ${META[m.meta]} economizaria ${reais(m.economia)} por vaca/dia`).join('; ')}.</p>
          )}
        </div>
      )}
    </div>
  )
}

// ------------------------------------------------------------------ previsão dos próximos dias
const diaCurto = (d: string) => new Date(d.slice(0, 10) + 'T12:00').toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })

export function AbaPrevisao({ lote }: { lote: Lote }) {
  const [dias, setDias] = useState(30)
  const [p, setP] = useState<any>(null)
  const [erro, setErro] = useState('')
  useEffect(() => { setP(null); api.get(`/lotes/${lote.id}/previsao?dias=${dias}`).then(setP).catch((e) => setErro(e.message)) }, [lote.id, dias])
  const dados = useMemo(() => p ? [
    ...p.historico.map((h: any) => ({ dia: diaCurto(h.data), real: h.observado, esperado: h.esperado })),
    ...p.serie.map((x: any) => ({ dia: diaCurto(x.data), previsto: x.leite_vaca, faixa: x.baixo !== null ? [x.baixo, x.alto] : null })),
  ] : [], [p])
  if (erro) return <Erro msg={erro} />
  if (!p) return <Carregando texto="Projetando os próximos dias…" />
  const t = p.totais
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex rounded-lg border border-stone-300 p-0.5 text-sm">
          {[15, 30, 60].map((d) => <button key={d} onClick={() => setDias(d)} className={`rounded-md px-3 py-1 ${dias === d ? 'bg-campo-600 text-white' : 'text-stone-600'}`}>{d} dias</button>)}
        </div>
        <p className="text-xs text-stone-500">{p.clima_dias ? `Calor previsto pela meteorologia nos próximos ${p.clima_dias} dias.` : 'Sem previsão do tempo (offline): calor não descontado.'}</p>
      </div>
      <section className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {[['Leite no período', `${numero(t.leite, 0)} L`], ['Dinheiro do leite', reais(t.receita, 0)], ['Comida', reais(t.custo, 0)], ['Sobra depois da comida', reais(t.margem, 0)]].map(([n, v]) => (
          <div key={n} className="card px-4 py-3"><p className="text-[13px] text-stone-500">{n}</p><p className="titulo num text-2xl font-semibold text-stone-900">{v}</p></div>
        ))}
      </section>
      {p.alertas.length > 0 && <Painel titulo="O que a previsão aponta">{p.alertas.map((a: Alerta, i: number) => <div key={i} className="border-b border-stone-100 py-2 last:border-0"><AlertaCorpo alerta={a} /></div>)}</Painel>}
      <Painel titulo="Leite por vaca: últimos 30 dias e próximos dias"
        subtitulo={p.calibrando ? 'A curva do lote ainda está sendo ajustada: a previsão repete a média dos últimos dias.'
          : `A faixa mostra onde o leite deve ficar 9 em cada 10 dias (variação típica deste lote: ±${numero(p.sigma * 100, 0)}%).${Math.abs(p.desvio_atual) >= 0.02 ? ` O lote está ${p.desvio_atual > 0 ? '+' : ''}${numero(p.desvio_atual * 100, 0)}% em relação ao esperado e a previsão mantém essa diferença.` : ''}`}>
        <div className="h-80">
          <ResponsiveContainer>
            <ComposedChart data={dados} margin={{ left: -10, right: 10 }}>
              <CartesianGrid stroke="#e8ece5" vertical={false} />
              <XAxis dataKey="dia" tick={{ fontSize: 11 }} minTickGap={24} />
              <YAxis tick={{ fontSize: 11 }} domain={['auto', 'auto']} unit=" L" />
              <Tooltip formatter={(v: any) => (Array.isArray(v) ? `${numero(v[0])} a ${numero(v[1])} L` : `${numero(v)} L`)} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Area dataKey="faixa" name="Faixa provável" stroke="none" fill="#cfe5cf" fillOpacity={0.5} isAnimationActive={false} />
              <Line dataKey="esperado" name="Esperado" stroke="#8b9687" strokeDasharray="5 4" dot={false} isAnimationActive={false} />
              <Line dataKey="real" name="Real" stroke="#2f6b3b" strokeWidth={2.5} dot={false} isAnimationActive={false} />
              <Line dataKey="previsto" name="Previsto" stroke="#24552f" strokeWidth={2} strokeDasharray="2 3" dot={false} isAnimationActive={false} />
              <ReferenceLine x={diaCurto(p.hoje)} stroke="#374035" label={{ value: 'hoje', fontSize: 10, position: 'insideTopLeft' }} />
              {p.marcos.map((m: any) => <ReferenceLine key={m.data + m.tipo} x={diaCurto(m.data)} stroke="#9a5800" strokeDasharray="4 3" label={{ value: m.texto, fontSize: 10, fill: '#9a5800', position: 'insideTopRight' }} />)}
            </ComposedChart>
          </ResponsiveContainer>
        </div>
        <p className="mt-2 text-xs text-stone-500">Leite {reais(p.preco_leite)}/L{p.bonificacao ? ` (com bonificação de ${reais(p.bonificacao, 3)})` : ''} · {numero(p.vacas, 0)} vacas · preços e dieta de hoje (a troca de dieta em andamento entra dia a dia). Não prevê doenças nem compra e venda de vacas.</p>
      </Painel>
    </div>
  )
}

