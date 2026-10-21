import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Line, LineChart, ResponsiveContainer, YAxis } from 'recharts'
import { api, FASES, fmt, OPCOES, type Alerta } from '../api'
import { AlertaItem, Carregando, Erro, ExplicacaoAlerta, Gaveta, NivelBadge, Painel } from '../components/ui'

export default function PainelPagina() {
  const [dados, setDados] = useState<any>(null)
  const [alertas, setAlertas] = useState<Alerta[]>([])
  const [erro, setErro] = useState('')
  const [aberto, setAberto] = useState<Alerta | null>(null)

  useEffect(() => {
    api.get('/fazendas/1/painel').then(setDados).catch((e) => setErro(e.message))
    api.get<Alerta[]>('/alertas?dias=14&incluir_suprimidos=false').then(setAlertas).catch(() => {})
  }, [])

  if (erro) return <Erro msg={`Não foi possível falar com a API (${erro}). Ela está rodando em localhost:8000?`} />
  if (!dados) return <Carregando texto="Carregando a fazenda…" />
  const nomeLote = (id?: number) => dados.lotes.find((l: any) => l.lote.id === id)?.lote.nome ?? ''

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-semibold text-stone-900">{dados.fazenda.nome}</h1>
        <p className="text-sm text-stone-500">{dados.fazenda.municipio} · leite R$ {dados.fazenda.preco_leite.toFixed(2)}/L · concentrado R$ {dados.fazenda.preco_concentrado.toFixed(2)}/kg · hoje {new Date(dados.data + 'T12:00').toLocaleDateString('pt-BR')}</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {dados.lotes.map((c: any) => {
          const hoje = c.hoje
          const desvio = hoje ? (hoje.observado / hoje.esperado - 1) * 100 : null
          return (
            <Link key={c.lote.id} to={`/lotes/${c.lote.id}`} className="card block min-w-0 overflow-hidden p-4 transition hover:border-campo-500 hover:shadow-md">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div className="min-w-0">
                  <h2 className="font-semibold text-stone-900">{c.lote.nome}</h2>
                  <p className="text-xs text-stone-500">{c.lote.n_vacas} vacas · {OPCOES[c.lote.grupo_genetico]} · {OPCOES[c.lote.sistema]}{hoje ? ` · DEL ${Math.round(hoje.del)}` : ''}</p>
                </div>
                <div className="flex gap-1">
                  {c.alertas.critico > 0 && <span className="rounded-full bg-red-50 px-2 py-0.5 text-xs font-semibold text-critico ring-1 ring-red-200">{c.alertas.critico} crít.</span>}
                  {c.alertas.atencao > 0 && <span className="rounded-full bg-amber-50 px-2 py-0.5 text-xs font-semibold text-atencao ring-1 ring-amber-200">{c.alertas.atencao} atenção</span>}
                </div>
              </div>
              <div className="mt-3 flex items-end justify-between gap-3">
                <div>
                  <div className="num text-2xl font-semibold text-stone-900">{hoje ? fmt(hoje.observado) : '—'}<span className="ml-1 text-sm font-normal text-stone-500">L/vaca</span></div>
                  <div className="num text-xs text-stone-500">esperado {hoje ? fmt(hoje.esperado) : '—'} L
                    {desvio !== null && <span className={`ml-1 font-semibold ${desvio < -5 ? 'text-critico' : desvio < 0 ? 'text-atencao' : 'text-campo-600'}`}>({desvio > 0 ? '+' : ''}{desvio.toFixed(0)}%)</span>}
                  </div>
                  {c.custo_dieta && <div className="num mt-1 text-xs text-stone-500">dieta R$ {c.custo_dieta.toFixed(2)}/vaca/dia</div>}
                </div>
                <div className="h-14 w-28 shrink-0 sm:w-40">
                  <ResponsiveContainer>
                    <LineChart data={c.serie}>
                      <YAxis hide domain={['dataMin - 1', 'dataMax + 1']} />
                      <Line dataKey="esperado" stroke="#a8a29e" strokeDasharray="3 3" dot={false} strokeWidth={1.5} isAnimationActive={false} />
                      <Line dataKey="observado" stroke="#2f7230" dot={false} strokeWidth={2} isAnimationActive={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>
              {c.principal && (
                <div className="mt-3 flex items-start gap-2 rounded-lg bg-stone-50 p-2 text-sm">
                  <NivelBadge nivel={c.principal.nivel} />
                  <span className="text-stone-700">{c.principal.titulo}</span>
                </div>
              )}
              {!c.principal && <div className="mt-3 rounded-lg bg-campo-50 p-2 text-sm text-campo-700">Sem alertas nos últimos 14 dias.</div>}
            </Link>
          )
        })}
      </div>

      <Painel titulo="Alertas dos últimos 14 dias" subtitulo="Ordenados por data. Alertas suprimidos por meta-regras ficam na página de cada lote.">
        {alertas.length === 0 && <p className="text-sm text-stone-500">Nenhum alerta ativo.</p>}
        {alertas.slice(0, 12).map((a) => (
          <div key={a.id}>
            <p className="pt-2 text-xs font-medium text-stone-400">{nomeLote(a.lote_id)}</p>
            <AlertaItem alerta={a} onAbrir={() => setAberto(a)} />
          </div>
        ))}
      </Painel>

      <Gaveta aberta={!!aberto} onFechar={() => setAberto(null)} titulo="Explicação do alerta">
        {aberto && <ExplicacaoAlerta alerta={aberto} />}
      </Gaveta>
    </div>
  )
}

export { FASES }
