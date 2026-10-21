import { useEffect, useState } from 'react'
import { api, dataBR, numero, reais } from '../api'
import { Brinco, Carregando, Erro } from '../components/ui'

const ROTULO_EVENTO: Record<string, string> = {
  troca_volumoso: 'troca de volumoso', silo_novo: 'silo novo', movimentacao: 'mudança de vacas', correcao_ms: 'correção da silagem',
  mudanca_concentrado: 'mudança de concentrado', manejo_calor: 'manejo de calor', manejo_sanitario: 'manejo sanitário',
  conferencia: 'conferência', secagem: 'secagem', manejo_pasto: 'manejo do pasto', outro: 'outro',
}
const COR: Record<string, string> = { critico: 'border-l-critico', atencao: 'border-l-atencao', informativo: 'border-l-stone-300' }

/** Relatório semanal da fazenda para imprimir ou salvar em PDF (impressão do navegador). */
export default function RelatorioPagina() {
  const [dias, setDias] = useState(7)
  const [r, setR] = useState<any>(null)
  const [erro, setErro] = useState('')
  useEffect(() => { setR(null); api.get(`/fazendas/1/relatorio?dias=${dias}`).then(setR).catch((e) => setErro(e.message)) }, [dias])
  if (erro) return <Erro msg={erro} />
  if (!r) return <Carregando texto="Montando o relatório…" />
  const variacao = (v: number | null) => v === null ? '' : `${v > 0 ? '+' : ''}${numero(v, 1)}%`
  return (
    <div className="space-y-5 print:space-y-3 print:text-[12px]">
      <div className="flex flex-wrap items-center justify-between gap-3 print:hidden">
        <div className="flex rounded-lg border border-stone-300 p-0.5 text-sm">
          {[7, 14, 30].map((d) => (
            <button key={d} onClick={() => setDias(d)} className={`rounded-md px-3 py-1 ${dias === d ? 'bg-campo-600 text-white' : 'text-stone-600'}`}>{d} dias</button>
          ))}
        </div>
        <button className="btn-primario" onClick={() => window.print()}>Imprimir / salvar em PDF</button>
      </div>

      <header className="border-b-[3px] border-campo-700 pb-3">
        <p className="text-sm font-semibold text-campo-700">Relatório {dias === 7 ? 'semanal' : `de ${dias} dias`} do CochoCerto</p>
        <h1 className="titulo text-[2.2rem] font-semibold leading-tight text-stone-900">{r.fazenda.nome}</h1>
        <p className="text-sm text-stone-500">{r.fazenda.municipio}, de {dataBR(r.inicio)} a {dataBR(r.fim)}, leite a {reais(r.preco_leite)}/L</p>
      </header>

      <section className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {[['Vacas', numero(r.totais.vacas, 0)], ['Leite por dia (média)', `${numero(r.totais.leite_dia, 0)} L`],
          ['Sobra por dia depois da comida', reais(r.totais.margem_dia, 0)], ['Avisos pendentes / resolvidos', `${r.totais.pendentes} / ${r.totais.resolvidos}`]].map(([t, v]) => (
          <div key={t} className="card px-4 py-3 print:shadow-none"><p className="text-[13px] text-stone-500">{t}</p><p className="titulo num text-[1.7rem] font-semibold leading-tight text-stone-900">{v}</p></div>
        ))}
      </section>

      {r.previsao && (
        <section className="card p-4 print:shadow-none">
          <h2 className="titulo mb-1 text-xl font-semibold text-stone-900">Próximo mês (previsão)</h2>
          <p className="num text-sm text-stone-700">~{numero(r.previsao.totais.leite, 0)} L · {reais(r.previsao.totais.receita, 0)} do leite · {reais(r.previsao.totais.custo, 0)} de comida · sobra de {reais(r.previsao.totais.margem, 0)}</p>
          {r.previsao.marcos.length > 0 && <p className="mt-1 text-sm text-stone-700">Datas: {r.previsao.marcos.map((m: any) => `${m.texto.toLowerCase()} — ${m.lote} (${dataBR(m.data)})`).join('; ')}.</p>}
          {r.previsao.avisos.length > 0 && <ul className="mt-1 ml-4 list-disc text-sm text-stone-700">{r.previsao.avisos.map((a: any, i: number) => <li key={i}>{a.titulo}</li>)}</ul>}
        </section>
      )}

      {r.estoque.length > 0 && (
        <section className="card p-4 print:shadow-none">
          <h2 className="titulo mb-1 text-xl font-semibold text-stone-900">Estoque</h2>
          <ul className="space-y-0.5 text-sm">{r.estoque.map((e: any, i: number) => <li key={i}><b>{e.titulo}</b> — {e.acao}</li>)}</ul>
        </section>
      )}

      {r.lotes.map((l: any) => (
        <section key={l.lote.id} className="card break-inside-avoid p-4 print:shadow-none">
          <div className="flex flex-wrap items-baseline justify-between gap-2 border-b border-stone-100 pb-2">
            <h2 className="titulo flex items-center gap-2.5 text-xl font-semibold text-stone-900"><Brinco nome={l.lote.nome} id={l.lote.id} tamanho="sm" />{l.lote.nome}</h2>
            <span className="text-sm text-stone-500">{numero(l.vacas, 0)} vacas</span>
          </div>
          <div className="mt-2 grid grid-cols-2 gap-2 text-sm sm:grid-cols-4">
            <div><p className="text-xs text-stone-500">Leite por vaca</p><p className="num font-semibold">{numero(l.leite_vaca)} L <span className={`text-xs ${l.variacao_pct < 0 ? 'text-critico' : 'text-campo-700'}`}>{variacao(l.variacao_pct)}</span></p>
              <p className="text-xs text-stone-400">semana anterior {numero(l.leite_vaca_anterior)} · esperado {numero(l.esperado_vaca)}</p></div>
            <div><p className="text-xs text-stone-500">Comida por vaca/dia</p><p className="num font-semibold">{reais(l.custo_vaca_dia)}</p></div>
            <div><p className="text-xs text-stone-500">Comida por litro</p><p className="num font-semibold">{reais(l.custo_por_litro)}</p></div>
            <div><p className="text-xs text-stone-500">Sobra por vaca/dia</p><p className="num font-semibold">{reais(l.margem_vaca_dia)}</p></div>
          </div>
          {l.proximos_passos.length > 0 && (
            <div className="mt-3 rounded-lg bg-campo-50 p-2 text-sm text-campo-900">
              <p className="font-semibold">Próximos passos</p>
              <ol className="ml-5 list-decimal">{l.proximos_passos.map((p: string, i: number) => <li key={i}>{p}</li>)}</ol>
            </div>
          )}
          <div className="mt-3 grid gap-3 text-sm sm:grid-cols-2">
            <div>
              <h3 className="mb-1 font-medium text-stone-800">Avisos em aberto ({l.pendentes.length})</h3>
              {l.pendentes.length === 0 && <p className="text-stone-500">Nenhum.</p>}
              <ul className="space-y-1">{l.pendentes.map((p: any) => <li key={p.id} className={`border-l-4 pl-2 ${COR[p.nivel]}`}>{p.titulo}{p.estado === 'aceito' && <span className="text-xs text-campo-700"> (em andamento)</span>}</li>)}</ul>
            </div>
            <div>
              <h3 className="mb-1 font-medium text-stone-800">Resolvidos no período ({l.resolvidos.length})</h3>
              {l.resolvidos.length === 0 && <p className="text-stone-500">Nenhum.</p>}
              <ul className="space-y-1">{l.resolvidos.map((p: any) => <li key={p.id} className="text-stone-700">✓ {p.titulo}</li>)}</ul>
            </div>
            {(l.acoes.length > 0 || l.eventos.length > 0 || l.dietas_novas.length > 0) && (
              <div className="sm:col-span-2">
                <h3 className="mb-1 font-medium text-stone-800">O que foi feito</h3>
                <ul className="space-y-0.5 text-stone-700">
                  {l.dietas_novas.map((d: any) => <li key={`d${d.versao}`}>{dataBR(d.inicio)} · dieta nova (versão {d.versao}){d.motivo ? `: ${d.motivo}` : ''}</li>)}
                  {l.eventos.map((e: any, i: number) => <li key={`e${i}`}>{dataBR(e.data)} · {ROTULO_EVENTO[e.tipo] ?? e.tipo}{e.descricao ? `: ${e.descricao}` : ''}</li>)}
                  {l.acoes.filter((a: any) => !(a.tipo === 'acao_registrada' && /^(Evento|Nova dieta)/.test(a.descricao))).map((a: any, i: number) => (
                    <li key={`a${i}`}>{dataBR(a.data)} · {a.tipo === 'aceito' ? <>aceitou o aviso “{a.aviso}”</> : a.tipo === 'recusado' ? <>recusou o aviso “{a.aviso}” (motivo: {a.descricao.replace(/^Recomendação recusada: /, '')})</> : a.descricao}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </section>
      ))}
      <p className="text-xs text-stone-400">Gerado pelo CochoCerto em {new Date().toLocaleString('pt-BR')}. Valores de referência para prova de conceito; validar com o técnico da fazenda.</p>
    </div>
  )
}
