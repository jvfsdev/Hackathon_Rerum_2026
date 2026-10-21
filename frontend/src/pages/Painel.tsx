import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Line, LineChart, ResponsiveContainer, YAxis } from 'recharts'
import { api, FASES, fmt, numero, OPCOES, reais, tecnico, textoAlerta, type Alerta } from '../api'
import { AlertaItem, BORDA_NIVEL, Brinco, CabecalhoPagina, Carregando, Erro, ExplicacaoAlerta, Gaveta, Icone, NivelBadge, Painel } from '../components/ui'

export default function PainelPagina() {
  const [dados, setDados] = useState<any>(null)
  const [alertas, setAlertas] = useState<Alerta[]>([])
  const [erro, setErro] = useState('')
  const [aberto, setAberto] = useState<Alerta | null>(null)
  const [prev, setPrev] = useState<any>(null)

  useEffect(() => {
    api.get('/fazendas/1/painel').then(setDados).catch((e) => setErro(e.message))
    carregarAlertas()
    api.get('/fazendas/1/previsao?dias=30').then(setPrev).catch(() => {})
  }, [])
  function carregarAlertas() {
    api.get<Alerta[]>('/alertas?estado=pendentes&incluir_suprimidos=false').then(setAlertas).catch(() => {})
  }

  if (erro) return <Erro msg={`Não foi possível falar com a API (${erro}). Ela está rodando em localhost:8000?`} />
  if (!dados) return <Carregando texto="Carregando a fazenda…" />
  const nomeLote = (id?: number) => dados.lotes.find((l: any) => l.lote.id === id)?.lote.nome ?? ''

  const avisosPrev = prev ? [...prev.alertas, ...prev.lotes.flatMap((l: any) => l.alertas.map((a: any) => ({ ...a, lote: l.lote.nome })))]
    .filter((a: any) => a.nivel !== 'informativo' || a.regra === 'PRV-02') : []
  const estoqueAviso = (dados.estoque ?? []).filter((a: Alerta) => a.nivel !== 'informativo')

  return (
    <div className="space-y-6">
      <CabecalhoPagina titulo={dados.fazenda.nome}
        contexto={<>{dados.fazenda.municipio} <span className="text-stone-300">/</span> leite a <b className="num font-semibold text-stone-700">{reais(dados.fazenda.preco_leite)}</b> o litro
          <span className="text-stone-300"> /</span> concentrado a <b className="num font-semibold text-stone-700">{reais(dados.fazenda.preco_concentrado)}</b> o kg
          <span className="text-stone-300"> /</span> {new Date(dados.data + 'T12:00').toLocaleDateString('pt-BR', { weekday: 'long', day: 'numeric', month: 'long' })}</>}
        acoes={<>
          <Link to="/relatorio" className="btn-secundario">Relatório da semana</Link>
          <Link to="/lotes/novo" className="btn-primario"><Icone nome="mais" />Novo lote</Link>
        </>} />

      {estoqueAviso.length > 0 && (
        <Link to="/estoque" className="block rounded-[10px] border border-brinco/70 border-l-4 border-l-brinco bg-brinco-claro px-4 py-3 transition-colors hover:bg-[#fbecb5]">
          <p className="titulo text-lg font-semibold text-stone-900">Estoque pedindo compra</p>
          {estoqueAviso.map((a: Alerta, i: number) => (
            <p key={i} className="mt-1 flex items-start gap-2 text-sm"><NivelBadge nivel={a.nivel} /><span>{textoAlerta(a).titulo}: <span className="text-stone-600">{textoAlerta(a).acao}</span></span></p>
          ))}
        </Link>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        {dados.lotes.map((c: any) => {
          const hoje = c.hoje
          const desvio = hoje ? (hoje.observado / hoje.esperado - 1) * 100 : null
          const pior = c.alertas.critico > 0 ? 'critico' : c.alertas.atencao > 0 ? 'atencao' : 'ok'
          const [nomeCurto, descricao] = c.lote.nome.split(' — ')
          return (
            <Link key={c.lote.id} to={`/lotes/${c.lote.id}`}
              className={`card group block min-w-0 overflow-hidden border-l-4 p-4 transition-colors hover:border-stone-300 sm:p-5 ${BORDA_NIVEL[pior as 'ok']}`}>
              <div className="flex items-start gap-3.5">
                <Brinco nome={c.lote.nome} id={c.lote.id} />
                <div className="min-w-0 flex-1">
                  <h2 className="titulo text-[1.35rem] font-semibold leading-tight text-stone-900 group-hover:text-campo-700">{descricao ?? nomeCurto}</h2>
                  <p className="mt-0.5 text-[13px] text-stone-500">{c.lote.n_vacas} vacas, {OPCOES[c.lote.grupo_genetico]?.toLowerCase()}, {OPCOES[c.lote.sistema]?.toLowerCase()}{hoje ? (tecnico() ? `, DEL ${Math.round(hoje.del)}` : `, ${Math.round(hoje.del)} dias de lactação`) : ''}</p>
                </div>
                <div className="flex shrink-0 flex-col items-end gap-1">
                  {c.alertas.critico > 0 && <span className="rounded-full bg-critico px-2 py-0.5 text-xs font-semibold text-white">{c.alertas.critico} {c.alertas.critico > 1 ? 'críticos' : 'crítico'}</span>}
                  {c.alertas.atencao > 0 && <span className="rounded-full bg-brinco-claro px-2 py-0.5 text-xs font-semibold text-atencao ring-1 ring-brinco/70">{c.alertas.atencao} atenção</span>}
                </div>
              </div>
              <div className="mt-4 flex items-end justify-between gap-4">
                <div>
                  <div className="titulo num text-[2.6rem] font-semibold leading-none text-stone-900">{hoje ? fmt(hoje.observado) : '—'}<span className="ml-1.5 font-sans text-sm font-normal text-stone-500">L por vaca</span></div>
                  <div className="num mt-1.5 text-[13px] text-stone-500">esperado {hoje ? fmt(hoje.esperado) : '—'} L
                    {desvio !== null && <span className={`ml-1.5 rounded px-1 font-semibold ${desvio < -5 ? 'bg-red-50 text-critico' : desvio < 0 ? 'bg-brinco-claro text-atencao' : 'bg-campo-50 text-campo-700'}`}>{desvio > 0 ? '+' : ''}{desvio.toFixed(0)}%</span>}
                  </div>
                  {c.custo_dieta && <div className="num mt-0.5 text-[13px] text-stone-500">comida a {reais(c.custo_dieta)} por vaca/dia</div>}
                </div>
                <div className="h-16 w-32 shrink-0 sm:w-44" title="Leite por vaca: real (linha cheia) e esperado (tracejada)">
                  <ResponsiveContainer>
                    <LineChart data={c.serie}>
                      <YAxis hide domain={['dataMin - 1', 'dataMax + 1']} />
                      <Line dataKey="esperado" stroke="#8b9687" strokeDasharray="3 3" dot={false} strokeWidth={1.5} isAnimationActive={false} />
                      <Line dataKey="observado" stroke="#2f6b3b" dot={false} strokeWidth={2.25} isAnimationActive={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>
              {c.principal ? (
                <div className="mt-4 flex items-start gap-2 border-t border-stone-200 pt-3 text-sm">
                  <NivelBadge nivel={c.principal.nivel} />
                  <span className="text-stone-700">{textoAlerta(c.principal).titulo}</span>
                </div>
              ) : <div className="mt-4 border-t border-stone-200 pt-3 text-sm text-campo-700">Sem alertas nos últimos 14 dias.</div>}
            </Link>
          )
        })}
      </div>

      {prev && (
        <section className="card overflow-hidden">
          <div className="flex flex-wrap items-baseline justify-between gap-2 px-4 pt-4 sm:px-5">
            <h2 className="titulo text-xl font-semibold text-stone-900">Próximos 30 dias</h2>
            <span className="text-[13px] text-stone-500">previsão pela curva de cada lote, com as dietas e os preços de hoje</span>
          </div>
          <dl className="mt-3 grid grid-cols-2 border-y border-stone-200 bg-stone-50 sm:grid-cols-4">
            {([['Leite', `${numero(prev.totais.leite, 0)} L`, ''], ['Venda do leite', reais(prev.totais.receita, 0), ''], ['Comida', reais(prev.totais.custo, 0), ''], ['Sobra depois da comida', reais(prev.totais.margem, 0), 'text-campo-700']] as const).map(([t, v, cor], i) => (
              <div key={t} className={`px-4 py-3 sm:px-5 ${i % 2 ? 'border-l border-stone-200' : ''} ${i === 2 ? 'border-t border-stone-200 sm:border-t-0 sm:border-l' : ''} ${i === 3 ? 'border-t border-stone-200 sm:border-t-0' : ''}`}>
                <dt className="text-[13px] text-stone-500">{t}</dt>
                <dd className={`titulo num text-2xl font-semibold ${cor || 'text-stone-900'}`}>{v}</dd>
              </div>
            ))}
          </dl>
          {(avisosPrev.length > 0 || prev.estoque_acaba.length > 0) && (
            <div className="space-y-1.5 px-4 py-3 sm:px-5">
              {avisosPrev.map((a: any, i: number) => (
                <p key={i} className="flex items-start gap-2 text-sm"><NivelBadge nivel={a.nivel} /><span>{a.lote && <span className="font-medium text-stone-500">{a.lote.replace(/ — .*/, '')}: </span>}{textoAlerta(a).titulo}</span></p>
              ))}
              {prev.estoque_acaba.length > 0 && <p className="text-[13px] text-stone-500">Estoque que acaba no período: {prev.estoque_acaba.map((e: any) => `${e.nome} (${new Date(e.data + 'T12:00').toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })})`).join(', ')}.</p>}
            </div>
          )}
        </section>
      )}

      <Painel titulo={`${tecnico() ? 'Alertas pendentes' : 'Avisos para resolver'} (${alertas.length})`} subtitulo={tecnico() ? 'Abertos ou aceitos e ainda sem resolução. Aceite para ir à tela da ação ou recuse com o motivo; o histórico de cada lote fica na aba Alertas e ações.' : 'Aceite para ir à tela onde se registra o que foi feito, ou recuse dizendo o motivo.'}>
        {alertas.length === 0 && <p className="text-sm text-stone-500">Nenhum alerta pendente.</p>}
        {[...alertas].sort((a, b) => ['critico', 'atencao', 'informativo'].indexOf(a.nivel) - ['critico', 'atencao', 'informativo'].indexOf(b.nivel)).slice(0, 15).map((a) => (
          <div key={a.id}>
            <p className="flex items-center gap-2 pt-3 text-[13px] font-medium text-stone-500"><Brinco nome={nomeLote(a.lote_id)} id={a.lote_id} tamanho="sm" />{nomeLote(a.lote_id)}</p>
            <AlertaItem alerta={a} onAbrir={() => setAberto(a)} onMudou={carregarAlertas} />
          </div>
        ))}
      </Painel>

      <Gaveta aberta={!!aberto} onFechar={() => setAberto(null)} titulo={tecnico() ? 'Explicação do alerta' : 'Entender o aviso'}>
        {aberto && <ExplicacaoAlerta alerta={aberto} />}
      </Gaveta>
    </div>
  )
}

export { FASES }
