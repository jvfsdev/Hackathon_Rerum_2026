import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, fmt, OPCOES, rotulo, tecnico } from '../api'
import { CabecalhoPagina, Carregando, Erro, Painel } from '../components/ui'
import { EscalaEscore } from '../components/Escala'
import { ResultadoAvaliacao } from './Lote'

/** Consulta guiada: o motor faz encadeamento regressivo e pergunta só o que falta para concluir. */
export default function ConsultaPagina() {
  const [estado, setEstado] = useState<any>(null)
  const [valor, setValor] = useState<string>('')
  const [carregando, setCarregando] = useState(false)
  const [erro, setErro] = useState('')
  const [verPorQue, setVerPorQue] = useState(false)
  const navegar = useNavigate()
  const tec = tecnico()

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
      <div className="space-y-6">
        <CabecalhoPagina titulo="Consulta guiada" contexto="Descreva um lote respondendo a perguntas, uma de cada vez. O sistema pergunta só o que falta para calcular o que o lote precisa." />
        <Painel titulo="Como funciona" subtitulo={tec
          ? 'O motor de inferência faz encadeamento regressivo: a partir do objetivo (exigências do lote) ele procura as regras que concluem cada fato e pergunta só o que ainda falta. Respostas anteriores podam o que não é mais necessário. Se não souber uma resposta, use o valor padrão: a conclusão sai com certeza menor.'
          : 'O sistema faz uma pergunta de cada vez e pula o que não importa para o seu lote (por exemplo, não pergunta de pasto se as vacas são confinadas). Se não souber alguma resposta, toque em "Não sei": o sistema usa um valor comum e avisa que a conta ficou menos certa. No fim, ele mostra o que o lote precisa e você pode criar o lote com essas respostas.'}>
          {erro && <Erro msg={erro} />}
          <button className="btn-primario mt-1" onClick={iniciar} disabled={carregando}>{carregando ? 'Começando…' : 'Começar a consulta'}</button>
        </Painel>
      </div>
    )
  }

  const p = estado.pergunta
  const respondidas = Object.entries(estado.fatos)
  return (
    <div className="space-y-6">
    <CabecalhoPagina titulo="Consulta guiada" contexto={p ? 'Responda a pergunta abaixo. Se não souber, use o valor padrão.' : 'Consulta concluída.'}
      acoes={<button className="btn-secundario" onClick={() => { setEstado(null); setValor('') }}>Recomeçar</button>} />
    <div className="grid gap-5 lg:grid-cols-[1fr_280px]">
      <div className="space-y-5">
        {p && (
          <Painel titulo={(!tec && p.texto_produtor) || p.texto} subtitulo={(!tec && p.ajuda_produtor) || p.ajuda}>
            {p.escala ? (
              <EscalaEscore tipo={p.escala} valor={valor} onChange={setValor} />
            ) : p.tipo === 'opcao' ? (
              <div className="flex flex-wrap gap-2">
                {p.opcoes.map((o: string) => (
                  <button key={o} onClick={() => setValor(o)} aria-pressed={valor === o} className={`btn border ${valor === o ? 'border-campo-600 bg-campo-600 text-white' : 'border-stone-300 bg-white text-stone-700 hover:bg-stone-50'}`}>{OPCOES[o] ?? o}</button>
                ))}
              </div>
            ) : (
              <div className="flex max-w-xs items-center gap-2">
                <input autoFocus className="input num" inputMode="decimal" value={valor} onChange={(e) => setValor(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && responder()} placeholder={p.padrao !== undefined ? `ex.: ${p.padrao}` : ''} />
                {p.unidade && <span className="text-sm text-stone-500">{(!tec && p.unidade_produtor) || p.unidade}</span>}
              </div>
            )}
            {erro && <div className="mt-2"><Erro msg={erro} /></div>}
            <div className="mt-4 flex flex-wrap gap-2">
              <button className="btn-primario" onClick={() => responder()} disabled={carregando}>Responder</button>
              {p.padrao !== undefined && (
                <button className="btn-secundario" onClick={() => responder(true)} disabled={carregando} title={tec ? 'Usa o valor padrão com fator de certeza menor' : 'Usa um valor comum; a conta fica menos certa'}>
                  Não sei (usar {fmt(p.padrao)})
                </button>
              )}
              {p.padrao === undefined && p.opcional && (
                <button className="btn-secundario" onClick={() => responder(true)} disabled={carregando} title={tec ? 'As regras que dependem desta informação não serão aplicadas' : 'O sistema segue sem esta informação'}>
                  Não sei (pular)
                </button>
              )}
              <button className="text-sm font-medium text-campo-600 hover:underline" onClick={() => setVerPorQue(!verPorQue)}>Por que estou perguntando?</button>
            </div>
            {verPorQue && !tec && (
              <div className="mt-3 rounded-lg bg-stone-50 p-3 text-sm text-stone-700">
                <p>{p.ajuda_produtor || p.ajuda}</p>
                <p className="mt-1 text-stone-600">Com esta resposta o sistema calcula: <b>{rotulo(p.objetivo).toLowerCase()}</b>.</p>
                <p className="mt-1 text-xs text-stone-400">Na visão técnica aparecem as regras que usam esta informação.</p>
              </div>
            )}
            {verPorQue && tec && (
              <div className="mt-3 rounded-lg bg-stone-50 p-3 text-sm">
                <p className="mb-1 text-stone-600">O objetivo <b>{rotulo(p.objetivo)}</b> depende desta cadeia de regras:</p>
                <ol className="space-y-1">
                  {p.por_que.map((r: any, i: number) => (
                    <li key={r.regra} className="flex gap-2" style={{ paddingLeft: i * 12 }}>
                      {tecnico() && <span className="font-mono text-xs font-semibold text-campo-700">{r.regra}</span>}
                      <span className="text-stone-700">{r.descricao}</span>
                    </li>
                  ))}
                </ol>
                <p className="mt-1 text-xs text-stone-500">…e a última regra precisa de <b>{rotulo(p.fato)}</b>.</p>
              </div>
            )}
            <p className="mt-3 text-xs text-stone-400">{tec
              ? `${estado.pendentes} pergunta(s) possivelmente restante(s) — o número cai conforme as respostas podam regras.`
              : `Faltam no máximo ${estado.pendentes} pergunta(s); pode ser menos, dependendo das respostas.`}</p>
          </Painel>
        )}
        {carregando && <Carregando />}
        {estado.resultado && (
          <>
            <div className="rounded-[10px] border border-campo-500 border-l-[6px] border-l-campo-600 bg-campo-50 p-4 text-sm text-campo-900">{tec ? 'Pronto: o motor tem todos os fatos para concluir.' : 'Pronto: já dá para calcular o que o lote precisa.'}{' '}
              {estado.padroes.length > 0 && (tec ? `Valores padrão usados (CF menor): ${estado.padroes.map(rotulo).join(', ')}.`
                : `Você respondeu "não sei" em: ${estado.padroes.map((f: string) => rotulo(f).toLowerCase()).join(', ')}. Usamos valores comuns, então a conta ficou menos certa.`)}</div>
            <ResultadoAvaliacao r={estado.resultado} />
            <div className="flex flex-wrap gap-2">
              <button className="btn-primario" onClick={() => navegar('/lotes/novo', { state: { fatos: estado.fatos, padroes: estado.padroes } })}>
                Criar lote com estas respostas
              </button>
              <button className="btn-secundario" onClick={() => { setEstado(null); setValor('') }}>Nova consulta</button>
            </div>
          </>
        )}
      </div>
      <aside className="card h-fit border-t-4 border-t-campo-700 p-4 lg:sticky lg:top-6">
        <h3 className="titulo mb-0.5 text-lg font-semibold text-stone-900">{tec ? 'Memória de trabalho' : 'Suas respostas'}</h3>
        <p className="mb-3 text-xs text-stone-500">{tec ? 'O que o motor já sabe. Em amarelo, valores padrão.' : 'Em amarelo, o que ficou no valor comum ("não sei").'}</p>
        {respondidas.length === 0 && <p className="text-xs text-stone-400">{tec ? 'Vazia.' : 'Nenhuma ainda.'}</p>}
        <dl className="space-y-1 text-sm">
          {respondidas.map(([f, v]) => (
            <div key={f} className="flex justify-between gap-2">
              <dt className="text-stone-500">{rotulo(f)}</dt>
              <dd className={`num font-semibold ${estado.padroes.includes(f) ? 'rounded bg-brinco-claro px-1 text-atencao' : 'text-stone-800'}`}>{fmt(v)}</dd>
            </div>
          ))}
        </dl>
      </aside>
    </div>
    </div>
  )
}
