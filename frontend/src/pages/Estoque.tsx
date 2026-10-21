import { Fragment, useEffect, useState } from 'react'
import { api, dataBR, numero, peso, tecnico, type Alerta, type Alimento } from '../api'
import { AlertaCorpo, Carregando, Erro, Painel } from '../components/ui'

interface Item {
  item: string; nome: string; saldo_kg: number; consumo_kg_dia: number; dias_restantes: number | null
  ultima_contagem: string | null; contagem_kg: number | null; entradas_kg: number; consumo_periodo_kg: number; alertas: Alerta[]
}

/** Estoque de insumos: saldo estimado pelas dietas dos lotes, dias até acabar e quando comprar (regras EST). */
export default function EstoquePagina() {
  const [dados, setDados] = useState<{ itens: Item[]; alertas: Alerta[]; sem_controle: any[] } | null>(null)
  const [alimentos, setAlimentos] = useState<Alimento[]>([])
  const [mov, setMov] = useState({ item: '', tipo: 'contagem', kg: '', data: new Date().toISOString().slice(0, 10), obs: '' })
  const [historico, setHistorico] = useState<Record<string, any[]>>({})
  const [erro, setErro] = useState('')
  const [ok, setOk] = useState('')
  useEffect(() => {
    api.get<any>('/fazendas/1/estoque').then(setDados).catch((e) => setErro(e.message))
    api.get<Alimento[]>('/fazendas/1/alimentos').then((a) => { setAlimentos(a); setMov((m) => ({ ...m, item: m.item || a[0]?.id || '' })) })
  }, [])
  const salvar = async () => {
    setErro(''); setOk('')
    const kg = Number(mov.kg.replace(',', '.'))
    if (!mov.item || mov.kg.trim() === '' || Number.isNaN(kg)) { setErro('Escolha o insumo e informe a quantidade.'); return }
    try {
      setDados(await api.post('/fazendas/1/estoque', { ...mov, kg }))
      setOk(`${mov.tipo === 'contagem' ? 'Contagem' : 'Entrada'} de ${peso(kg)} registrada.`)
      setMov({ ...mov, kg: '', obs: '' }); setHistorico({})
    } catch (e: any) { setErro(e.message) }
  }
  const verHistorico = async (item: string) => {
    if (historico[item]) { const h = { ...historico }; delete h[item]; setHistorico(h); return }
    setHistorico({ ...historico, [item]: await api.get<any[]>(`/fazendas/1/estoque/movimentos?item=${item}`) })
  }
  if (erro && !dados) return <Erro msg={erro} />
  if (!dados) return <Carregando texto="Calculando o estoque…" />
  const cor = (d: number | null) => d === null ? 'text-stone-500' : d <= 7 ? 'text-critico' : d <= 15 ? 'text-atencao' : 'text-campo-700'
  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-semibold text-stone-900">Estoque de insumos</h1>
        <p className="text-sm text-stone-500">O saldo é a última contagem mais as compras, menos o que as dietas dos lotes consomem a cada dia (inclusive durante as trocas de dieta). Conte o estoque de vez em quando para corrigir.</p>
      </div>
      {dados.alertas.length > 0 && (
        <Painel titulo="Avisos de estoque">
          {dados.alertas.map((a, i) => <div key={i} className="border-b border-stone-100 py-2 last:border-0"><AlertaCorpo alerta={a} /></div>)}
        </Painel>
      )}
      <Painel titulo="Situação hoje" subtitulo="Dias até acabar seguem o consumo previsto dia a dia.">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-xs text-stone-500">
              <tr><th className="py-1 pr-3">Insumo</th><th className="pr-3 text-right">Tem (estimado)</th><th className="pr-3 text-right">Gasto por dia</th><th className="pr-3 text-right">Dá para</th><th className="pr-3">Última contagem</th><th /></tr>
            </thead>
            <tbody>
              {dados.itens.map((i) => (
                <Fragment key={i.item}>
                  <tr className="border-t border-stone-100">
                    <td className="py-2 pr-3 font-medium text-stone-800">{i.nome}</td>
                    <td className="num pr-3 text-right">{i.saldo_kg < 0 ? <span className="text-amber-700">recontar</span> : peso(i.saldo_kg)}</td>
                    <td className="num pr-3 text-right">{i.consumo_kg_dia ? peso(i.consumo_kg_dia) : 'não usado hoje'}</td>
                    <td className={`num pr-3 text-right font-semibold ${cor(i.dias_restantes)}`}>{i.dias_restantes === null ? (i.consumo_kg_dia ? 'mais de 4 meses' : 'deixa de ser usado') : `${numero(i.dias_restantes, 0)} dias`}</td>
                    <td className="pr-3 text-xs text-stone-500">{i.ultima_contagem ? `${dataBR(i.ultima_contagem)}: ${peso(i.contagem_kg)}` : 'sem contagem'}{i.entradas_kg ? ` · +${peso(i.entradas_kg)} comprados` : ''}{tecnico() && ` · consumo desde então ${peso(i.consumo_periodo_kg)}`}</td>
                    <td><button className="text-xs text-campo-600 hover:underline" onClick={() => verHistorico(i.item)}>{historico[i.item] ? 'fechar' : 'histórico'}</button></td>
                  </tr>
                  {historico[i.item] && (
                    <tr><td colSpan={6} className="bg-stone-50 px-3 py-2 text-xs text-stone-600">
                      {historico[i.item].map((m) => <div key={m.id}>{dataBR(m.data)} · {m.tipo === 'contagem' ? 'contagem' : 'entrada'} {peso(m.kg)}{m.obs ? ` — ${m.obs}` : ''}</div>)}
                    </td></tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
        {dados.sem_controle.length > 0 && (
          <p className="mt-3 text-xs text-stone-500">Sem controle de estoque (usados nas dietas): {dados.sem_controle.map((s) => `${s.nome} (${peso(s.consumo_kg_dia)}/dia)`).join(', ')}. Registre uma contagem para acompanhar.</p>
        )}
      </Painel>
      <Painel titulo="Registrar contagem ou compra" subtitulo="Contagem: quanto há agora (substitui a estimativa). Compra: quanto chegou.">
        <div className="grid gap-3 sm:grid-cols-5">
          <label className="sm:col-span-2"><span className="rotulo">Insumo</span>
            <select className="input" value={mov.item} onChange={(e) => setMov({ ...mov, item: e.target.value })}>
              {alimentos.filter((a) => !a.pastejo).map((a) => <option key={a.id} value={a.id}>{a.nome}</option>)}
            </select></label>
          <label><span className="rotulo">Tipo</span>
            <select className="input" value={mov.tipo} onChange={(e) => setMov({ ...mov, tipo: e.target.value })}>
              <option value="contagem">Contagem</option><option value="entrada">Compra / entrada</option>
            </select></label>
          <label><span className="rotulo">Quantidade (kg)</span><input className="input num" inputMode="decimal" value={mov.kg} onChange={(e) => setMov({ ...mov, kg: e.target.value })} /></label>
          <label><span className="rotulo">Data</span><input type="date" className="input" value={mov.data} onChange={(e) => setMov({ ...mov, data: e.target.value })} /></label>
        </div>
        <input className="input mt-3" placeholder="Observação (nota fiscal, silo…)" value={mov.obs} onChange={(e) => setMov({ ...mov, obs: e.target.value })} />
        {erro && <div className="mt-2"><Erro msg={erro} /></div>}
        {ok && <p className="mt-2 rounded bg-campo-50 p-2 text-sm text-campo-800">{ok}</p>}
        <button className="btn-primario mt-3" onClick={salvar}>Registrar</button>
      </Painel>
      {tecnico() && <p className="text-xs text-stone-400">Avisos decididos pelas regras EST-01 a EST-03 (módulo estoque), com os limites de dias nos parâmetros da base.</p>}
    </div>
  )
}
