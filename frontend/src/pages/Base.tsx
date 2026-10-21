import { useEffect, useMemo, useState } from 'react'
import { api } from '../api'
import { Carregando, Erro, ForcaBadge, Painel, RegraCartao } from '../components/ui'

const NOME_MODULO: Record<string, string> = {
  classificacao: 'A · Classificação', exigencias: 'B · Exigências', verificacao: 'C · Verificação', formulacao: 'F · Formulação (PL)',
  acompanhamento_diario: 'D1 · Acompanhamento diário', acompanhamento_semanal: 'D2 · Acompanhamento semanal',
  acompanhamento_mensal: 'D3 · Acompanhamento mensal', meta: 'M · Meta-regras',
}

export default function BasePagina() {
  const [resumo, setResumo] = useState<any>(null)
  const [regras, setRegras] = useState<any[]>([])
  const [params, setParams] = useState<Record<string, any>>({})
  const [testes, setTestes] = useState<any>(null)
  const [modulo, setModulo] = useState('todos')
  const [busca, setBusca] = useState('')
  const [especialista, setEspecialista] = useState(false)
  const [edicao, setEdicao] = useState<Record<string, string>>({})
  const [msg, setMsg] = useState('')
  const [erro, setErro] = useState('')
  const [rodando, setRodando] = useState(false)

  const carregar = () => {
    api.get('/kb').then(setResumo).catch((e) => setErro(e.message))
    api.get<any[]>('/kb/regras').then(setRegras)
    api.get<Record<string, any>>('/kb/parametros').then(setParams)
  }
  useEffect(carregar, [])

  const ordem = Object.keys(NOME_MODULO)
  const filtradas = useMemo(() => regras.filter((r) => (modulo === 'todos' || r.modulo === modulo) &&
    (!busca || `${r.id} ${r.descricao} ${r.fonte}`.toLowerCase().includes(busca.toLowerCase())))
    .sort((a, b) => ordem.indexOf(a.modulo) - ordem.indexOf(b.modulo)), [regras, modulo, busca])

  const rodarTestes = async () => { setRodando(true); setTestes(await api.post('/kb/testes')); setRodando(false) }
  const salvarParam = async (nome: string) => {
    setErro(''); setMsg('')
    try {
      const r: any = await api.put(`/kb/parametros/${nome}`, { valor: Number(edicao[nome].replace(',', '.')), motivo: 'Editado pelo especialista na interface.' })
      setMsg(`Base agora na versão ${r.versao}: ${nome} ${r.antes} → ${r.depois}. Casos de teste: ${r.testes.passaram}/${r.testes.total}.`)
      setTestes(r.testes); setEdicao({ ...edicao, [nome]: '' }); carregar()
    } catch (e: any) { setErro(e.message) }
  }

  if (erro && !resumo) return <Erro msg={erro} />
  if (!resumo) return <Carregando />
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-stone-900">Base de conhecimento <span className="font-mono text-base text-campo-700">v{resumo.versao}</span></h1>
          <p className="text-sm text-stone-500">{resumo.regras} regras de produção · {resumo.parametros} parâmetros com fonte e força de evidência · {resumo.alimentos} alimentos. Versionada no git (backend/kb/).</p>
        </div>
        <button className="btn-primario" onClick={rodarTestes} disabled={rodando}>{rodando ? 'Rodando…' : 'Rodar casos de teste'}</button>
      </div>

      {testes && (
        <Painel titulo={`Casos de teste — ${testes.passaram}/${testes.total} passaram`} subtitulo={`Validação da versão ${testes.kb_version} contra resultados conhecidos do domínio (tests/cases.yaml).`}>
          <div className="grid gap-1 sm:grid-cols-2">
            {testes.resultados.map((t: any) => (
              <div key={t.id} className={`rounded px-2 py-1 text-sm ${t.passou ? 'bg-campo-50' : 'bg-red-50'}`}>
                <span className={`mr-2 font-mono font-semibold ${t.passou ? 'text-campo-700' : 'text-critico'}`}>{t.passou ? '✓' : '✗'} {t.id}</span>
                <span className="text-stone-700">{t.descricao}</span>
                {!t.passou && <ul className="ml-6 list-disc text-xs text-critico">{t.falhas.map((f: string) => <li key={f}>{f}</li>)}</ul>}
              </div>
            ))}
          </div>
        </Painel>
      )}

      <div className="flex flex-wrap gap-2">
        <button onClick={() => setModulo('todos')} className={`btn ${modulo === 'todos' ? 'bg-campo-600 text-white' : 'border border-stone-300 bg-white'}`}>Todos ({regras.length})</button>
        {Object.keys(NOME_MODULO).filter((m) => resumo.modulos[m]).map((m) => [m, resumo.modulos[m]] as const).map(([m, n]) => (
          <button key={m} onClick={() => setModulo(m)} className={`btn ${modulo === m ? 'bg-campo-600 text-white' : 'border border-stone-300 bg-white'}`}>{NOME_MODULO[m] ?? m} ({n as number})</button>
        ))}
      </div>
      <input className="input max-w-md" placeholder="Buscar regra por ID, descrição ou fonte" value={busca} onChange={(e) => setBusca(e.target.value)} />
      <div className="space-y-2">{filtradas.map((r) => <RegraCartao key={r.id} regra={r} />)}</div>

      <Painel titulo="Parâmetros (limiares)" subtitulo="Valores conflitantes ou não verificados na literatura ficam aqui, nunca escondidos nas regras. No modo especialista, editar um valor cria nova versão da base e roda os casos de teste."
        acoes={<label className="flex items-center gap-2 text-sm"><input type="checkbox" className="accent-campo-600" checked={especialista} onChange={(e) => setEspecialista(e.target.checked)} />Modo especialista</label>}>
        {msg && <div className="mb-2 rounded bg-campo-50 p-2 text-sm text-campo-800">{msg}</div>}
        {erro && <div className="mb-2"><Erro msg={erro} /></div>}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-xs text-stone-500"><tr><th className="py-1 pr-3">Parâmetro</th><th className="pr-3">Valor</th><th className="pr-3">Força</th><th>Fonte</th></tr></thead>
            <tbody>
              {Object.entries(params).map(([nome, p]) => {
                const escalar = typeof p.valor === 'number'
                return (
                  <tr key={nome} className="border-t border-stone-100 align-top">
                    <td className="py-1.5 pr-3"><div className="font-mono text-xs text-stone-800">{nome}</div><div className="text-xs text-stone-500">{p.descricao}</div></td>
                    <td className="num pr-3 whitespace-nowrap">
                      {especialista && escalar ? (
                        <span className="flex items-center gap-1">
                          <input className="input w-20 py-1" placeholder={String(p.valor)} value={edicao[nome] ?? ''} onChange={(e) => setEdicao({ ...edicao, [nome]: e.target.value })} />
                          <button className="btn-secundario px-2 py-1 text-xs" disabled={!edicao[nome]} onClick={() => salvarParam(nome)}>Salvar</button>
                        </span>
                      ) : <span className="text-stone-800">{typeof p.valor === 'object' ? JSON.stringify(p.valor) : String(p.valor)}</span>}
                      <span className="ml-1 text-xs text-stone-400">{p.unidade}</span>
                    </td>
                    <td className="pr-3"><ForcaBadge forca={p.forca} /></td>
                    <td className="text-xs text-stone-500">{p.fonte}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </Painel>

      <Painel titulo="Histórico de versões (CHANGELOG)">
        <pre className="whitespace-pre-wrap font-sans text-sm text-stone-700">{resumo.changelog}</pre>
      </Painel>
    </div>
  )
}
