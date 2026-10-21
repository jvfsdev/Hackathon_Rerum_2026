import { useState } from 'react'
import { api, fmt, OPCOES, rotulo } from '../api'
import { Carregando, Erro, Painel } from '../components/ui'
import { ResultadoAvaliacao } from './Lote'

/** Consulta guiada: o motor faz encadeamento regressivo e pergunta só o que falta para concluir. */
export default function ConsultaPagina() {
  const [estado, setEstado] = useState<any>(null)
  const [valor, setValor] = useState<string>('')
  const [carregando, setCarregando] = useState(false)
  const [erro, setErro] = useState('')
  const [verPorQue, setVerPorQue] = useState(false)

  const iniciar = async () => {
    setCarregando(true); setErro('')
    try { setEstado(await api.post('/inferencia/consulta', { fatos: {} })) } catch (e: any) { setErro(e.message) }
    setCarregando(false)
  }
  const responder = async (naoSei = false) => {
    const p = estado.pergunta
    const v = p.tipo === 'numero' ? Number(valor.replace(',', '.')) : valor
    if (!naoSei && (valor === '' || (p.tipo === 'numero' && Number.isNaN(v)))) { setErro('Informe um valor.'); return }
    setCarregando(true); setErro('')
    try {
      setEstado(await api.post(`/inferencia/consulta/${estado.consulta}/responder`, { fato: p.fato, valor: v, nao_sei: naoSei }))
      setValor(''); setVerPorQue(false)
    } catch (e: any) { setErro(e.message) }
    setCarregando(false)
  }

  if (!estado) {
    return (
      <Painel titulo="Consulta guiada" subtitulo="Descreva um lote respondendo às perguntas. O motor de inferência faz encadeamento regressivo: a partir do objetivo (exigências do lote) ele procura as regras que concluem cada fato e pergunta só o que ainda falta. Respostas anteriores podam o que não é mais necessário.">
        {erro && <Erro msg={erro} />}
        <button className="btn-primario mt-2" onClick={iniciar} disabled={carregando}>Começar</button>
      </Painel>
    )
  }

  const p = estado.pergunta
  const respondidas = Object.entries(estado.fatos)
  return (
    <div className="grid gap-5 lg:grid-cols-[1fr_280px]">
      <div className="space-y-5">
        {p && (
          <Painel titulo={p.texto} subtitulo={p.ajuda}>
            {p.tipo === 'opcao' ? (
              <div className="flex flex-wrap gap-2">
                {p.opcoes.map((o: string) => (
                  <button key={o} onClick={() => setValor(o)} className={`btn ${valor === o ? 'bg-campo-600 text-white' : 'border border-stone-300 bg-white hover:bg-stone-100'}`}>{OPCOES[o] ?? o}</button>
                ))}
              </div>
            ) : (
              <div className="flex max-w-xs items-center gap-2">
                <input autoFocus className="input num" inputMode="decimal" value={valor} onChange={(e) => setValor(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && responder()} placeholder={p.padrao !== undefined ? `ex.: ${p.padrao}` : ''} />
                {p.unidade && <span className="text-sm text-stone-500">{p.unidade}</span>}
              </div>
            )}
            {erro && <div className="mt-2"><Erro msg={erro} /></div>}
            <div className="mt-4 flex flex-wrap gap-2">
              <button className="btn-primario" onClick={() => responder()} disabled={carregando}>Responder</button>
              {p.padrao !== undefined && (
                <button className="btn-secundario" onClick={() => responder(true)} disabled={carregando} title="Usa o valor padrão com fator de certeza menor">
                  Não sei (usar {fmt(p.padrao)})
                </button>
              )}
              {p.padrao === undefined && p.opcional && (
                <button className="btn-secundario" onClick={() => responder(true)} disabled={carregando} title="As regras que dependem desta informação não serão aplicadas">
                  Não sei (pular)
                </button>
              )}
              <button className="text-sm font-medium text-campo-600 hover:underline" onClick={() => setVerPorQue(!verPorQue)}>Por que estou perguntando?</button>
            </div>
            {verPorQue && (
              <div className="mt-3 rounded-lg bg-stone-50 p-3 text-sm">
                <p className="mb-1 text-stone-600">O objetivo <b>{rotulo(p.objetivo)}</b> depende desta cadeia de regras:</p>
                <ol className="space-y-1">
                  {p.por_que.map((r: any, i: number) => (
                    <li key={r.regra} className="flex gap-2" style={{ paddingLeft: i * 12 }}>
                      <span className="font-mono text-xs font-semibold text-campo-700">{r.regra}</span>
                      <span className="text-stone-700">{r.descricao}</span>
                    </li>
                  ))}
                </ol>
                <p className="mt-1 text-xs text-stone-500">…e a última regra precisa de <b>{rotulo(p.fato)}</b>.</p>
              </div>
            )}
            <p className="mt-3 text-xs text-stone-400">{estado.pendentes} pergunta(s) possivelmente restante(s) — o número cai conforme as respostas podam regras.</p>
          </Painel>
        )}
        {carregando && <Carregando />}
        {estado.resultado && (
          <>
            <div className="rounded-xl bg-campo-50 p-4 text-sm text-campo-900">Pronto: o motor tem todos os fatos para concluir. {estado.padroes.length > 0 && `Valores padrão usados (CF menor): ${estado.padroes.map(rotulo).join(', ')}.`}</div>
            <ResultadoAvaliacao r={estado.resultado} />
            <button className="btn-secundario" onClick={() => { setEstado(null); setValor('') }}>Nova consulta</button>
          </>
        )}
      </div>
      <aside className="card h-fit p-4">
        <h3 className="mb-2 text-sm font-semibold text-stone-800">Memória de trabalho</h3>
        {respondidas.length === 0 && <p className="text-xs text-stone-400">Vazia.</p>}
        <dl className="space-y-1 text-sm">
          {respondidas.map(([f, v]) => (
            <div key={f} className="flex justify-between gap-2">
              <dt className="text-stone-500">{rotulo(f)}</dt>
              <dd className={`num font-medium ${estado.padroes.includes(f) ? 'text-amber-700' : 'text-stone-800'}`}>{fmt(v)}</dd>
            </div>
          ))}
        </dl>
      </aside>
    </div>
  )
}
