import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, NavLink, Route, Routes, useLocation, useParams, useSearchParams } from 'react-router-dom'
import { CartesianGrid, ComposedChart, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api, certeza, comEpisodios, dataBR, fmt, numero, OPCOES, reais, rotulo, tecnico, textoAlerta, UNIDADES, type Alerta, type Alimento, type Dieta, type ItemDieta, type ItemHistorico, type Lote, type Resultado, hora, NOME_INDICADOR, porDia, valorIndicador, type Registro, mudou, paraCampo, hojeLocal, diasAtras } from '../api'
import LoteForm from '../components/LoteForm'
import { EscalaEscore } from '../components/Escala'
import { CampoLitros, type ModoLitros } from '../components/Litros'
import { AjusteMinimo, AlertaItem, BotaoComo, Brinco, CabecalhoPagina, Carregando, CfBarra, Erro, ExplicacaoAlerta, Gaveta, Icone, LinhaDoTempo, NivelBadge, Painel } from '../components/ui'
import { AbaPrevisao, AbaSimular, AbaTrato, PlanoTransicao, Sensibilidade } from './LoteExtras'

const aba = ({ isActive }: { isActive: boolean }) =>
  `-mb-px whitespace-nowrap border-b-[3px] px-3 py-2.5 text-[15px] font-semibold transition-colors ${isActive ? 'border-campo-600 text-stone-900' : 'border-transparent text-stone-500 hover:border-stone-300 hover:text-stone-800'}`

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
    <div className="space-y-5">
      <CabecalhoPagina antes={<Brinco nome={lote.nome} id={lote.id} tamanho="lg" />}
        titulo={lote.nome.split(' — ')[1] ?? lote.nome}
        contexto={<>
          {lote.nome.split(' — ')[1] ? `${lote.nome.split(' — ')[0]}, ` : ''}{lote.n_vacas} vacas, {OPCOES[lote.grupo_genetico]?.toLowerCase()}, {OPCOES[lote.sistema]?.toLowerCase()}, {OPCOES[lote.estado]?.toLowerCase()}
          {fatos['lote.del'] !== undefined && (tecnico() ? `, DEL ${Math.round(fatos['lote.del'])}` : `, ${Math.round(fatos['lote.del'])} dias de lactação`)}
          {tecnico() ? `, PV ${lote.pv} kg` : `, peso médio ${lote.pv} kg`}
          {fatos['lote.leite'] !== undefined && <>, <b className="num font-semibold text-stone-700">{fmt(fatos['lote.leite'])} L/vaca</b> (média de 7 dias)</>}
        </>}
        acoes={<button className="btn-secundario" onClick={() => setEditando(true)}><Icone nome="lapis" />Editar lote</button>} />
      <Gaveta aberta={editando} onFechar={() => setEditando(false)} titulo={`Editar ${lote.nome}`}>
        <LoteForm lote={lote} fatos={fatos} onSalvo={() => { setEditando(false); recarregar() }} />
      </Gaveta>
      <nav className="-mx-4 -mt-1 flex overflow-x-auto border-b border-stone-300/70 px-4 sm:mx-0 sm:px-0" aria-label="Seções do lote">
        <NavLink end to="" className={aba}>{tecnico() ? 'Perfil e exigências' : 'Resumo'}</NavLink>
        <NavLink to="dieta" className={aba}>Dieta</NavLink>
        <NavLink to="simular" className={aba}>Simular (e se?)</NavLink>
        <NavLink to="trato" className={aba}>Trato</NavLink>
        <NavLink to="previsao" className={aba}>Previsão</NavLink>
        <NavLink to="acompanhamento" className={aba}>Acompanhamento</NavLink>
        <NavLink to="registro" className={aba}>Registro rápido</NavLink>
        <NavLink to="alertas" className={aba}>{tecnico() ? 'Alertas e ações' : 'Avisos'}</NavLink>
      </nav>
      <Routes>
        <Route index element={<AbaPerfil key={JSON.stringify(lote)} loteId={lote.id} />} />
        <Route path="dieta" element={<AbaDieta lote={lote} dietaAtiva={info.dieta} onSalvo={recarregar} />} />
        <Route path="simular" element={<AbaSimular lote={lote} dieta={info.dieta} />} />
        <Route path="trato" element={<AbaTrato lote={lote} />} />
        <Route path="previsao" element={<AbaPrevisao lote={lote} />} />
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
  return <ResultadoAvaliacao r={r} linkDieta="dieta#sugerir" loteId={loteId} />
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

const PARECER_PRODUTOR: Record<string, [string, string]> = {
  adequada: ['A dieta está boa para este lote ✓', 'Ela dá o que as vacas precisam, sem passar dos limites seguros.'],
  ajustar: ['A dieta precisa de ajustes', 'Ela funciona, mas falta ou sobra alguma coisa. Veja abaixo.'],
  bloqueada: ['A dieta tem um problema sério', 'Não use esta dieta como está: há risco para as vacas.'],
}

/** Resumo para o produtor: parecer, quanto o lote come, leite que a comida sustenta e o que está faltando/sobrando. */
function ResumoProdutor({ r, linkDieta, loteId }: { r: Resultado; linkDieta?: string; loteId?: number }) {
  const [aberto, setAberto] = useState<Alerta | null>(null)
  const v = (f: string) => r.fatos[f]?.valor
  const parecer = r.fatos['parecer.dieta']
  const motivos = r.alertas.filter((a) => a.status === 'ativo' && a.nivel !== 'informativo' && ['dieta', 'formulacao'].includes(a.categoria))
  const leiteMeta = v('lote.leite'), permitido = v('ver.leite_permitido')
  return (
    <div className="space-y-4">
      {parecer && (
        <div className={`card border-l-[6px] p-4 sm:p-5 ${parecer.valor === 'adequada' ? 'border-campo-500 border-l-campo-600 bg-campo-50' : parecer.valor === 'bloqueada' ? 'border-red-300 border-l-critico bg-red-50' : 'border-brinco/70 border-l-brinco bg-brinco-claro'}`}>
          <p className="titulo text-2xl font-semibold leading-tight text-stone-900">{PARECER_PRODUTOR[parecer.valor]?.[0] ?? fmt(parecer.valor)}</p>
          <p className="text-sm text-stone-600">{PARECER_PRODUTOR[parecer.valor]?.[1]} <span className="text-stone-400">({certeza(parecer.cf)})</span></p>
          {motivos.length > 0 && <ul className="mt-2 ml-4 list-disc space-y-0.5 text-sm text-stone-800">{motivos.map((a) => <li key={a.regra}>{textoAlerta(a).titulo}</li>)}</ul>}
          {r.meta_dieta && (
            <p className="mt-2 rounded-lg bg-white/70 p-2 text-sm text-stone-700">
              <b>Antes de mexer na dieta:</b> {r.meta_dieta.motivo}. Os avisos de dieta ficam em segundo plano até isso se resolver
              {tecnico() ? ` (${r.meta_dieta.regra})` : ''}.
            </p>
          )}
          {parecer.valor !== 'adequada' && !r.meta_dieta && (
            <div className="mt-3 flex flex-wrap gap-2">
              {linkDieta && <Link to={linkDieta} className="btn-primario">Pedir a dieta mais barata que resolve</Link>}
              {loteId && <span className="w-full"><AjusteMinimo loteId={loteId} /></span>}
            </div>
          )}
        </div>
      )}
      <div className="grid gap-4 md:grid-cols-3">
        <Painel titulo="O lote">
          <LinhaSimples rotulo="Fase" valor={fmt(v('perfil.fase'))} />
          {v('lote.del') !== undefined && <LinhaSimples rotulo="Dias de lactação" valor={numero(v('lote.del'), 0)} />}
          {v('perfil.estresse_termico') && <LinhaSimples rotulo="Calor" valor={`${fmt(v('perfil.estresse_termico'))} (índice ${numero(v('clima.itu'))})`} />}
          {v('perfil.gestacao_avancada') && <LinhaSimples rotulo="Prenhez" valor="mais de 190 dias: precisa de mais comida" />}
          {v('perfil.crescimento') && <LinhaSimples rotulo="Novilhas" valor="ainda crescendo: precisam de mais comida" />}
        </Painel>
        <Painel titulo="O que cada vaca precisa por dia">
          <LinhaSimples rotulo="Comer" valor={`${numero(v('exig.cms'))} kg de matéria seca`} como={r.explicacoes?.['exig.cms']} />
          {v('exig.pb_pct_alvo') !== undefined && <LinhaSimples rotulo="Proteína na dieta" valor={`${numero(v('exig.pb_pct_alvo'))}% da matéria seca`} como={r.explicacoes?.['exig.pb_pct_alvo']} />}
          {v('meta.fdn_min') !== undefined && <LinhaSimples rotulo="Fibra na dieta" valor={`pelo menos ${numero(v('meta.fdn_min'), 0)}%`} />}
        </Painel>
        <Painel titulo="O que a dieta dá">
          {v('dieta.ms_kg') !== undefined ? <>
            <LinhaSimples rotulo="Comida oferecida" valor={`${numero(v('dieta.ms_kg'))} kg de matéria seca`} />
            {v('ver.razao_energia') !== undefined && <LinhaSimples rotulo="Energia" valor={`${fmt(v('ver.razao_energia'), 'ver.razao_energia')} do necessário`} />}
            {permitido !== undefined && leiteMeta !== undefined && <LinhaSimples rotulo="Leite que a comida sustenta" valor={textoLeitePermitido(permitido, leiteMeta, v('ver.razao_energia'))} />}
            <LinhaSimples rotulo="Custo da comida" valor={`${reais(v('dieta.custo_vaca_dia'))} por vaca/dia`} />
          </> : <p className="text-sm text-stone-500">Sem dieta cadastrada.</p>}
        </Painel>
      </div>
      {v('dieta.ms_kg') !== undefined && <Comparacao r={r} />}
      {r.alertas.length > 0 && (
        <Painel titulo="Avisos" subtitulo={r.episodios ? 'Aceite para ajustar a dieta ou recuse dizendo o motivo.' : undefined}>
          {comEpisodios(r).map((a, i) => <AlertaItem key={i} alerta={{ ...a, sessao_id: a.sessao_id ?? r.sessao_id }} onAbrir={() => setAberto({ ...a, sessao_id: a.sessao_id ?? r.sessao_id })} />)}
        </Painel>
      )}
      <Gaveta aberta={!!aberto} onFechar={() => setAberto(null)} titulo="Entender o aviso">{aberto && <ExplicacaoAlerta alerta={aberto} />}</Gaveta>
    </div>
  )
}

/** Abaixo de metade do que o lote produz, o número da fórmula (que pode chegar a 0) não ajuda: as vacas estão comendo
 * mais pasto do que a equação estima ou tirando do corpo. Mostra a situação em palavras. */
export function textoLeitePermitido(permitido: number, hoje: number, razaoEnergia?: number) {
  if (permitido < 0.5 * hoje) return `bem menos do que produz hoje (${numero(hoje)} L)${razaoEnergia ? `: a energia cobre ${Math.round(razaoEnergia * 100)}%` : ''}`
  return `${numero(permitido)} L (hoje ${numero(hoje)} L)`
}

function LinhaSimples({ rotulo: r, valor, como }: { rotulo: string; valor: string; como?: any }) {
  return (
    <div className="flex items-baseline justify-between gap-3 border-b border-stone-100 py-1.5 text-sm last:border-0">
      <span className="text-stone-600">{r}</span>
      <span className="flex items-baseline gap-2 text-right font-medium text-stone-900">{valor}{como && <BotaoComo no={como} />}</span>
    </div>
  )
}

export function ResultadoAvaliacao({ r, linkDieta, loteId }: { r: Resultado; linkDieta?: string; loteId?: number }) {
  if (!tecnico()) return <ResumoProdutor r={r} linkDieta={linkDieta} loteId={loteId} />
  return <ResultadoTecnico r={r} linkDieta={linkDieta} />
}

function ResultadoTecnico({ r, linkDieta }: { r: Resultado; linkDieta?: string }) {
  const [aberto, setAberto] = useState<Alerta | null>(null)
  const temDieta = !!r.fatos['dieta.ms_kg']
  const total = r.fatos['exig.ell_total']?.valor ?? 0
  const parecer = r.fatos['parecer.dieta']
  const motivos = r.alertas.filter((a) => a.status === 'ativo' && a.nivel !== 'informativo' && a.categoria === 'dieta')
  return (
    <div className="space-y-4">
      {parecer && (
        <div className={`card flex flex-wrap items-center justify-between gap-3 border-l-[6px] p-4 sm:p-5 ${parecer.valor === 'adequada' ? 'border-campo-500 border-l-campo-600 bg-campo-50' : parecer.valor === 'bloqueada' ? 'border-red-300 border-l-critico bg-red-50' : 'border-brinco/70 border-l-brinco bg-brinco-claro'}`}>
          <div>
            <p className="text-[13px] font-medium text-stone-500">Parecer da dieta</p>
            <p className="titulo text-2xl font-semibold leading-tight text-stone-900">{fmt(parecer.valor)}</p>
            {motivos.length > 0 && (
              <ul className="mt-1 space-y-0.5 text-sm text-stone-700">
                {motivos.map((a) => <li key={a.regra}><span className="font-mono text-xs text-stone-500">{a.regra}</span> {a.titulo}</li>)}
              </ul>
            )}
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <CfBarra cf={parecer.cf} /><BotaoComo no={r.explicacoes?.['parecer.dieta']} />
            {linkDieta && parecer.valor !== 'adequada' && <Link to={linkDieta} className="btn-primario">Sugerir dieta de custo mínimo</Link>}
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
          <Valor r={r} fato="exig.cms_ajuste_fdnd" />
          <Valor r={r} fato="exig.ell_total" destaque />
          <div className="my-2 space-y-1">
            {COMPONENTES_ELL.filter((c) => r.fatos[c]).map((c) => (
              <div key={c} className="flex items-center gap-2 text-xs">
                <span className="w-32 text-stone-500">{rotulo(c)}</span>
                <span className="h-2 flex-1 overflow-hidden rounded-sm bg-stone-100"><span className="block h-full bg-campo-500" style={{ width: `${Math.max(0, (r.fatos[c].valor / total) * 100)}%` }} /></span>
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
        <Painel titulo="Conclusões e alertas" subtitulo={r.episodios ? 'Alertas da dieta ativa: aceite para ajustar a dieta ou recuse com o motivo.' : undefined}>
          {comEpisodios(r).map((a, i) => <AlertaItem key={i} alerta={a} onAbrir={() => setAberto({ ...a, sessao_id: a.sessao_id ?? r.sessao_id })} />)}
        </Painel>
      )}
      <Traco r={r} />
      <Gaveta aberta={!!aberto} onFechar={() => setAberto(null)} titulo="Explicação">{aberto && <ExplicacaoAlerta alerta={aberto} />}</Gaveta>
    </div>
  )
}

function Comparacao({ r }: { r: Resultado }) {
  const v = (f: string) => r.fatos[f]?.valor
  const t = tecnico()
  const linhas = [
    { nome: t ? 'Energia (ELl)' : 'Energia', oferta: v('ver.ell_consumida'), alvo: v('exig.ell_total'), un: t ? 'Mcal' : 'Mcal', tipo: 'min', tol: v('meta.fator_energia_min') ?? 0.95 },
    { nome: t ? 'Proteína bruta' : 'Proteína', oferta: v('dieta.pb_pct'), alvo: v('exig.pb_pct_alvo'), un: '%', tipo: 'min', tol: 0.95 },
    { nome: t ? 'Matéria seca' : 'Quantidade de comida', oferta: v('dieta.ms_kg'), alvo: v('exig.cms'), un: 'kg', tipo: 'faixa' },
    { nome: t ? 'FDN' : 'Fibra', oferta: v('dieta.fdn_pct'), alvo: v('meta.fdn_min'), un: '%', tipo: 'min', tol: 1 },
    { nome: t ? 'FDN de forragem' : 'Fibra do volumoso', oferta: v('dieta.fdnf_pct'), alvo: v('meta.fdnf_min'), un: '%', tipo: 'min', tol: 1 },
    { nome: t ? 'CNF' : 'Amido e açúcares', oferta: v('dieta.cnf_pct'), alvo: v('meta.cnf_max'), un: '%', tipo: 'max' },
    { nome: t ? 'Gordura (EE)' : 'Gordura', oferta: v('dieta.ee_pct'), alvo: v('meta.ee_max'), un: '%', tipo: 'max' },
    { nome: 'Ureia', oferta: v('dieta.ureia_pct'), alvo: v('meta.ureia_max'), un: '%', tipo: 'max' },
    ...(r.fatos['perfil.fase']?.valor === 'pre_parto' && v('dieta.dcad_meq_kg') !== undefined
      ? [{ nome: 'DCAD (pré-parto)', oferta: v('dieta.dcad_meq_kg'), alvo: 0, un: 'mEq/kg', tipo: 'dcad' }] : []),
  ].filter((l) => l.oferta !== undefined && l.alvo !== undefined)
  return (
    <Painel titulo={t ? 'Oferta × exigência' : 'A dieta item por item'} subtitulo={t ? `Dieta: ${fmt(v('dieta.ms_kg'))} kg MS · R$ ${fmt(v('dieta.custo_vaca_dia'))}/vaca/dia · ${fmt(v('dieta.forragem_pct'))}% de volumoso na MS`
      : `Barra verde: dentro do certo. Amarela: falta ou passou. O traço escuro é o necessário. ${fmt(v('dieta.forragem_pct'))}% da comida é volumoso.`}>
      <div className="space-y-2">
        {linhas.map((l) => {
          const razao = l.tipo === 'dcad' ? (l.oferta + 300) / 300 : l.oferta / l.alvo
          const ok = l.tipo === 'dcad' ? l.oferta <= 0 : l.tipo === 'min' ? razao >= (l.tol ?? 1) : l.tipo === 'max' ? l.oferta <= l.alvo : razao >= 0.9 && razao <= 1.05
          const largura = Math.max(0, Math.min(100, (razao / 1.5) * 100))
          return (
            <div key={l.nome} className="grid grid-cols-[110px_1fr_auto] items-center gap-3 text-sm sm:grid-cols-[150px_1fr_200px]">
              <span className="text-stone-600">{l.nome}</span>
              <span className="relative h-3.5 rounded-sm bg-stone-100 ring-1 ring-inset ring-stone-200">
                <span className={`absolute inset-y-0 left-0 rounded-sm ${ok ? 'bg-campo-500' : 'bg-brinco'}`} style={{ width: `${largura}%` }} />
                <span className="absolute inset-y-[-4px] w-[3px] rounded-full bg-stone-900" style={{ left: `calc(${(1 / 1.5) * 100}% - 1px)` }} title="alvo" />
              </span>
              <span className="num text-right text-xs text-stone-700">
                {t ? <>{fmt(l.oferta)} {l.tipo === 'max' || l.tipo === 'dcad' ? '≤' : l.tipo === 'min' ? '≥' : '≈'} {fmt(l.alvo)} {l.un} {ok ? '✓' : '⚠'}</>
                  : ok ? <span className="text-campo-700">ok</span>
                  : <span className="font-medium text-atencao">{l.tipo === 'max' || l.tipo === 'dcad' ? 'passou do limite' : razao < 1 ? 'falta' : 'sobra'}</span>}
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
  if (!tecnico()) return null
  return (
    <Painel titulo="Traço de inferência" subtitulo={`${r.traco.length} regras disparadas · base v${r.kb_version}`}
      acoes={<button className="btn-secundario py-1.5" aria-expanded={aberto} onClick={() => setAberto(!aberto)}>{aberto ? 'Ocultar' : 'Mostrar'}</button>}>
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

// ------------------------------------------------------------------ Ação vinda de um alerta aceito
/** Lê ?alerta=ID da URL: a tela foi aberta para registrar a ação de um alerta aceito. */
function useAlertaDaAcao() {
  const [params, setParams] = useSearchParams()
  const id = params.get('alerta')
  const [alerta, setAlerta] = useState<Alerta | null>(null)
  useEffect(() => { if (id) api.get<Alerta>(`/alertas/${id}`).then(setAlerta).catch(() => setAlerta(null)); else setAlerta(null) }, [id])
  const concluir = () => { params.delete('alerta'); params.delete('evento'); setParams(params, { replace: true }) }
  return { alertaId: id ? Number(id) : null, alerta, concluir }
}

function BannerAcao({ alerta, onCancelar }: { alerta: Alerta | null; onCancelar: () => void }) {
  if (!alerta) return null
  return (
    <div className="rounded-[10px] border border-campo-500 border-l-[6px] border-l-campo-600 bg-campo-50 p-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="text-[13px] font-semibold text-campo-700">Registrando a ação do alerta aceito</p>
          <p className="mt-0.5 font-medium text-stone-900">{tecnico() && <span className="font-mono text-xs text-stone-500">{alerta.regra} </span>}{textoAlerta(alerta).titulo}</p>
          <p className="mt-1 text-sm text-stone-700"><b>{tecnico() ? 'Recomendação' : 'O que fazer'}:</b> {textoAlerta(alerta).acao}</p>
          <p className="mt-1 text-xs text-stone-500">O que você salvar nesta tela entra no histórico do alerta. A resolução é confirmada pelo sistema quando a condição deixar de valer.</p>
        </div>
        <button className="text-sm text-stone-500 hover:underline" onClick={onCancelar}>não registrar agora</button>
      </div>
    </div>
  )
}

// ------------------------------------------------------------------ Dieta
function AbaDieta({ lote, dietaAtiva, onSalvo }: { lote: Lote; dietaAtiva: Dieta | null; onSalvo: () => void }) {
  const { alertaId, alerta, concluir } = useAlertaDaAcao()
  const [registrado, setRegistrado] = useState('')
  const [alimentos, setAlimentos] = useState<Alimento[]>([])
  const [itens, setItens] = useState<ItemDieta[]>(dietaAtiva?.itens ?? [])
  const [versoes, setVersoes] = useState<Dieta[]>([])
  const [res, setRes] = useState<Resultado | null>(null)
  const [pl, setPl] = useState<any>(null)
  const [escolhidos, setEscolhidos] = useState<string[]>([])
  const [motivo, setMotivo] = useState('')
  const [ocupado, setOcupado] = useState('')
  const [erro, setErro] = useState('')
  const [gradual, setGradual] = useState(true)
  const [ajustando, setAjustando] = useState(false)
  // de onde veio o que está no editor: dieta ativa, sugestão do PL ou versão anterior
  const [base, setBase] = useState<{ rotulo: string; origem: string; motivo: string; itens: ItemDieta[] }>(
    { rotulo: dietaAtiva ? `Dieta ativa v${dietaAtiva.versao}` : 'Nova dieta', origem: 'usuario', motivo: '', itens: dietaAtiva?.itens ?? [] })
  const alterado = JSON.stringify(itens) !== JSON.stringify(base.itens)
  const kgBase = (alimento: string) => base.itens.find((b) => b.alimento === alimento)?.kg_mn

  const carregarNoEditor = (lista: ItemDieta[], rotulo: string, origem: string, motivoSugerido: string) => {
    const copia = lista.map((i) => ({ ...i }))
    setItens(copia); setBase({ rotulo, origem, motivo: motivoSugerido, itens: copia.map((i) => ({ ...i })) })
    setMotivo(motivoSugerido); setRes(null); setErro('')
    document.getElementById('editor')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
  /** Origem gravada na versão: sugestão do PL intacta, PL ajustada à mão, retorno a uma versão ou manual. */
  const origemAoSalvar = () => base.origem === 'pl' ? (alterado ? 'pl_ajustada' : 'pl')
    : ['restauracao', 'ajuste', 'simulacao'].includes(base.origem) ? (alterado ? 'usuario' : base.origem) : 'usuario'

  useEffect(() => {
    // catálogo da fazenda (base + insumos cadastrados), com o preço vigente de cada um
    api.get<Alimento[]>(`/fazendas/${lote.fazenda_id}/alimentos`).then(setAlimentos)
    api.get<Dieta[]>(`/lotes/${lote.id}/dietas`).then(setVersoes)
  }, [lote.id, lote.fazenda_id])
  useEffect(() => { setEscolhidos(Array.from(new Set([...(dietaAtiva?.itens.map((i) => i.alimento) ?? []), 'ureia']))) }, [dietaAtiva])
  const loc = useLocation()
  const hash = loc.hash
  useEffect(() => {
    if (hash === '#sugerir' && alimentos.length) document.getElementById('sugerir')?.scrollIntoView({ behavior: 'smooth' })
  }, [hash, alimentos.length])
  // veio do "o que precisaria mudar" ou do simulador com uma dieta pronta para revisar
  useEffect(() => {
    const st = loc.state as { itensAjuste?: ItemDieta[]; rotulo?: string; origem?: string } | null
    if (st?.itensAjuste) carregarNoEditor(st.itensAjuste, st.rotulo ?? 'Menor mudança calculada', st.origem ?? 'ajuste',
      st.origem === 'simulacao' ? 'Dieta testada no simulador' : 'Menor mudança para corrigir a dieta')
  }, [loc.state])  // eslint-disable-line react-hooks/exhaustive-deps

  const nome = (id: string) => alimentos.find((a) => a.id === id)?.nome ?? id
  const verificar = async () => {
    setOcupado('verificar'); setErro('')
    try { setRes(await api.post<Resultado>(`/inferencia/lotes/${lote.id}/avaliar`, { itens })) } catch (e: any) { setErro(e.message) }
    setOcupado('')
  }
  const salvar = async (lista: ItemDieta[], origem: string, mot: string) => {
    setOcupado('salvar'); setErro('')
    try {
      const d = await api.post<Dieta>(`/lotes/${lote.id}/dietas`, { itens: lista, motivo: mot || 'Ajuste manual', origem, alerta_id: alertaId, gradual })
      setVersoes(await api.get<Dieta[]>(`/lotes/${lote.id}/dietas`)); setMotivo(''); onSalvo()
      const salvos = lista.map((i) => ({ ...i }))
      setItens(salvos); setBase({ rotulo: `Dieta ativa v${d.versao}`, origem: 'usuario', motivo: '', itens: salvos.map((i) => ({ ...i })) })
      const troca = d.transicao ? ` A troca será feita aos poucos, em ${d.transicao.dias} dias: a planilha de trato já mostra a mistura de cada dia.` : ''
      setRegistrado((alertaId ? `Dieta v${d.versao} salva e registrada como ação do aviso.` : `Dieta v${d.versao} salva.`) + troca)
      if (alertaId) concluir()
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
      <BannerAcao alerta={alerta} onCancelar={concluir} />
      {registrado && (
        <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-campo-50 p-3 text-sm text-campo-800">
          {registrado}<Link to="../alertas" className="font-medium underline">ver alertas e ações</Link>
        </div>
      )}
      <div className="grid gap-4 lg:grid-cols-2">
        <div id="editor" className="scroll-mt-4">
        <Painel titulo="Montar e verificar a dieta" subtitulo={tecnico() ? 'Quantidades por vaca/dia em matéria natural (como fornecido).' : 'Quantos kg de cada alimento cada vaca recebe por dia (do jeito que vai no cocho).'}
          className={base.origem !== 'usuario' ? 'ring-2 ring-campo-500' : ''}>
          <div className="mb-3 flex flex-wrap items-center gap-2 rounded-lg bg-stone-50 px-3 py-2 text-xs text-stone-600">
            <span>Editando a partir de: <b className="text-stone-800">{base.rotulo}</b></span>
            {alterado ? <span className="rounded-full bg-amber-50 px-2 py-0.5 font-semibold text-atencao ring-1 ring-amber-200">alterada</span>
              : <span className="rounded-full bg-stone-200 px-2 py-0.5 font-semibold text-stone-600">sem alterações</span>}
            {alterado && <button className="text-campo-600 hover:underline" onClick={() => { setItens(base.itens.map((i) => ({ ...i }))); setMotivo(base.motivo) }}>desfazer alterações</button>}
            {base.origem !== 'usuario' && dietaAtiva && (
              <button className="text-campo-600 hover:underline" onClick={() => carregarNoEditor(dietaAtiva.itens, `Dieta ativa v${dietaAtiva.versao}`, 'usuario', '')}>voltar para a dieta ativa</button>
            )}
          </div>
          <div className="space-y-2">
            {itens.map((it, i) => (
              <div key={i} className="flex items-center gap-2">
                <select className="input min-w-0 flex-1" value={it.alimento} onChange={(e) => setItens(itens.map((x, j) => (j === i ? { ...x, alimento: e.target.value } : x)))}>
                  {alimentos.map((a) => <option key={a.id} value={a.id}>{a.nome}</option>)}
                </select>
                <input className="input num w-20 shrink-0" inputMode="decimal" value={it.kg_mn}
                  onChange={(e) => setItens(itens.map((x, j) => (j === i ? { ...x, kg_mn: Number(e.target.value.replace(',', '.')) || 0 } : x)))} />
                <span className="text-xs text-stone-500">kg</span>
                <button className="text-stone-400 hover:text-critico" onClick={() => setItens(itens.filter((_, j) => j !== i))} aria-label="Remover">✕</button>
                <span className="num w-16 shrink-0 text-xs">
                  {kgBase(it.alimento) === undefined && base.itens.length > 0 && <span className="font-medium text-campo-700">novo</span>}
                  {kgBase(it.alimento) !== undefined && kgBase(it.alimento) !== it.kg_mn && <span className="text-atencao">era {kgBase(it.alimento)}</span>}
                </span>
              </div>
            ))}
            {base.itens.filter((b) => !itens.some((i) => i.alimento === b.alimento)).map((b) => (
              <p key={b.alimento} className="text-xs text-stone-400 line-through">{nome(b.alimento)} {b.kg_mn} kg (removido)</p>
            ))}
            <button className="text-sm font-medium text-campo-600 hover:underline" onClick={() => setItens([...itens, { alimento: alimentos[0]?.id ?? 'silagem_milho', kg_mn: 1 }])}>+ alimento</button>
          </div>
          {erro && <div className="mt-2"><Erro msg={erro} /></div>}
          <div className="mt-4 flex flex-wrap items-center gap-2">
            <button className="btn-primario" onClick={verificar} disabled={!!ocupado || !itens.length}>Verificar dieta</button>
            <input className="input max-w-56" placeholder="Motivo da mudança" value={motivo} onChange={(e) => setMotivo(e.target.value)} />
            <button className="btn-secundario" onClick={() => salvar(itens, origemAoSalvar(), motivo)} disabled={!!ocupado || !itens.length}>Salvar nova versão</button>
          </div>
          <label className="mt-2 flex items-center gap-2 text-xs text-stone-600" title="As regras de transição decidem se a troca precisa ser gradual e em quantos dias.">
            <input type="checkbox" className="accent-campo-600" checked={gradual} onChange={(e) => setGradual(e.target.checked)} />
            Fazer a troca aos poucos quando a mudança for grande (recomendado)
          </label>
          <div className="mt-2">
            {!ajustando
              ? <button className="text-sm font-medium text-campo-600 hover:underline" onClick={() => setAjustando(true)} disabled={!itens.length}>Corrigir esta dieta com a menor mudança possível</button>
              : <AjusteMinimo key={JSON.stringify(itens)} loteId={lote.id} itens={itens}
                  onUsar={(lista, custo) => { setAjustando(false); carregarNoEditor(lista, `Menor mudança (${reais(custo)}/vaca/dia)`, 'ajuste', 'Menor mudança para corrigir a dieta') }} />}
          </div>
        </Painel>
        </div>
        <div id="sugerir" className="scroll-mt-4">
        <Painel className={hash === '#sugerir' ? 'ring-2 ring-campo-500' : ''} titulo={tecnico() ? 'Sugerir dieta de custo mínimo' : 'Sugerir a dieta mais barata'} subtitulo={tecnico() ? 'As regras definem metas e restrições; a programação linear acha as quantidades; as regras verificam o resultado.' : 'Marque o que tem na fazenda. O sistema monta a dieta mais barata que atende o lote e confere o resultado.'}>
          <div className="grid gap-x-5 gap-y-0.5 sm:grid-cols-2">
            {alimentos.map((a) => (
              <label key={a.id} className="flex items-center gap-2 border-b border-stone-100 py-1.5 text-sm text-stone-700">
                <input type="checkbox" className="accent-campo-600" checked={escolhidos.includes(a.id)}
                  onChange={(e) => setEscolhidos(e.target.checked ? [...escolhidos, a.id] : escolhidos.filter((x) => x !== a.id))} />
                <span>{a.nome.replace(/ \(.*\)/, '')}{a.da_fazenda && <span className="ml-1 rounded bg-campo-100 px-1 text-[10px] font-semibold text-campo-700">fazenda</span>}</span>
                <span className={`num ml-auto shrink-0 text-xs ${a.preco_origem === 'fazenda' ? 'font-semibold text-campo-700' : 'text-stone-400'}`} title={a.preco_origem === 'fazenda' ? 'preço da fazenda' : 'preço de referência (demonstração)'}>R${a.preco_kg_mn.toFixed(2)}</span>
              </label>
            ))}
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <button className="btn-primario" onClick={sugerir} disabled={!!ocupado || !escolhidos.length}>{ocupado === 'pl' ? 'Otimizando…' : 'Sugerir dieta'}</button>
            <Link to="/insumos" className="text-xs font-medium text-campo-600 hover:underline">Insumos e preços</Link>
          </div>
          {pl?.pl?.status === 'otimo' && <Sensibilidade loteId={lote.id} alimentos={escolhidos} />}
          {pl && <ResultadoPL pl={pl} nome={nome}
            onAceitar={(lista) => salvar(lista, 'pl', `Dieta de custo mínimo (PL), R$ ${pl.pl.custo.toFixed(2)}/vaca/dia`)}
            onEditar={(lista) => carregarNoEditor(lista, `Sugestão de custo mínimo (R$ ${pl.pl.custo.toFixed(2)}/vaca/dia)`, 'pl',
              `Dieta de custo mínimo (PL) ajustada manualmente`)} />}
        </Painel>
        </div>
      </div>
      {ocupado === 'verificar' && <Carregando />}
      {res && <ResultadoAvaliacao r={res} />}
      <CalculadoraPearson alimentos={alimentos} />
      {dietaAtiva?.transicao && <PlanoTransicao dieta={dietaAtiva} nome={nome} />}
      <Painel titulo="Versões da dieta" subtitulo="Cada ajuste vira uma nova versão com motivo e parecer. Uma versão antiga pode ser carregada no editor para modificar, ou reativada (vira uma nova versão; nada é apagado).">
        <ol className="space-y-2">
          {versoes.map((d) => (
            <li key={d.id} className="flex flex-wrap items-baseline gap-2 border-b border-stone-100 pb-2 text-sm last:border-0">
              <span className="font-semibold text-stone-900">v{d.versao}</span>
              {d.ativa && <span className="rounded-full bg-campo-100 px-2 text-xs font-semibold text-campo-700">ativa</span>}
              <span className="text-stone-400">{new Date(d.inicio + 'T12:00').toLocaleDateString('pt-BR')}</span>
              <span className="rounded bg-stone-100 px-1.5 text-xs text-stone-600">{ORIGEM_DIETA[d.origem] ?? d.origem}</span>
              <span className="text-stone-700">{d.motivo}</span>
              <span className="w-full text-xs text-stone-500">{d.itens.map((i) => `${nome(i.alimento)} ${i.kg_mn} kg`).join(' · ')}</span>
              {d.parecer?.parecer && <span className="text-xs text-stone-500">Parecer: <b>{fmt(d.parecer.parecer)}</b>{tecnico() && ` (base v${d.parecer.kb_version})`}</span>}
              {d.transicao && <span className="text-xs text-campo-700">troca gradual em {d.transicao.dias} dias a partir da v{d.transicao.de_versao}</span>}
              <span className="flex w-full flex-wrap gap-3 text-xs">
                <button className="font-medium text-campo-600 hover:underline" disabled={!!ocupado}
                  onClick={() => carregarNoEditor(d.itens, `Versão v${d.versao} (${new Date(d.inicio + 'T12:00').toLocaleDateString('pt-BR')})`,
                    d.ativa ? 'usuario' : 'restauracao', d.ativa ? '' : `Retorno à v${d.versao}`)}>Carregar no editor</button>
                {!d.ativa && (
                  <button className="font-medium text-campo-600 hover:underline" disabled={!!ocupado}
                    onClick={() => window.confirm(`Reativar a v${d.versao} como nova versão da dieta? A dieta atual continua no histórico.`)
                      && salvar(d.itens, 'restauracao', `Retorno à v${d.versao}${d.motivo ? ` (${d.motivo})` : ''}`)}>Voltar para esta versão</button>
                )}
              </span>
            </li>
          ))}
        </ol>
      </Painel>
    </div>
  )
}

/** Quadrado de Pearson: proporção de 2 ingredientes para atingir um teor de PB (ferramenta didática do dossiê). */
function CalculadoraPearson({ alimentos }: { alimentos: Alimento[] }) {
  const [aberto, setAberto] = useState(false)
  const [a, setA] = useState('milho_moido')
  const [b, setB] = useState('farelo_soja')
  const [alvo, setAlvo] = useState('18')
  const [res, setRes] = useState<any>(null)
  const [erro, setErro] = useState('')
  const pa = alimentos.find((x) => x.id === a), pb = alimentos.find((x) => x.id === b)
  const calcular = async () => {
    setErro(''); setRes(null)
    if (!pa || !pb) return
    try { setRes(await api.get(`/ferramentas/pearson?teor_a=${pa.pb}&teor_b=${pb.pb}&alvo=${alvo.replace(',', '.')}`)) }
    catch (e: any) { setErro(e.message) }
  }
  return (
    <Painel titulo="Quadrado de Pearson" subtitulo="Proporção de dois ingredientes para chegar a um teor de proteína bruta na mistura (ex.: concentrado com 18% PB)."
      acoes={<button className="btn-secundario py-1.5" aria-expanded={aberto} onClick={() => setAberto(!aberto)}>{aberto ? 'Fechar' : 'Abrir calculadora'}</button>}>
      {aberto && (
        <div className="space-y-3">
          <div className="flex flex-wrap items-end gap-2">
            {([['Ingrediente A', a, setA], ['Ingrediente B', b, setB]] as const).map(([rot, v, set]) => (
              <label key={rot}><span className="rotulo">{rot}</span>
                <select className="input" value={v} onChange={(e) => { set(e.target.value); setRes(null) }}>
                  {alimentos.map((x) => <option key={x.id} value={x.id}>{x.nome} ({x.pb}% PB)</option>)}
                </select></label>
            ))}
            <label><span className="rotulo">PB desejada (% MS)</span><input className="input num w-24" value={alvo} onChange={(e) => { setAlvo(e.target.value); setRes(null) }} /></label>
            <button className="btn-secundario" onClick={calcular}>Calcular</button>
          </div>
          {erro && <Erro msg={erro} />}
          {res && pa && pb && (
            <p className="rounded-lg bg-campo-50 p-3 text-sm text-stone-700">
              <b>{res.pct_a.toFixed(1)}%</b> de {pa.nome} + <b>{res.pct_b.toFixed(1)}%</b> de {pb.nome} (na matéria seca) →
              {' '}{alvo}% PB. Partes: {res.partes_a.toFixed(1)} : {res.partes_b.toFixed(1)} (diferenças em diagonal no quadrado).
            </p>
          )}
        </div>
      )}
    </Painel>
  )
}

const ORIGEM_DIETA: Record<string, string> = {
  usuario: 'manual', pl: 'PL custo mínimo', pl_ajustada: 'PL ajustada à mão', restauracao: 'retorno a versão anterior',
  ajuste: 'menor mudança', simulacao: 'testada no simulador',
}

const GRUPO_SIMPLES: Record<string, string> = {
  consumo: 'quantidade de comida', energia: 'energia', excesso_energia: 'energia demais', proteina: 'proteína', fibra: 'fibra',
  enchimento: 'fibra demais (enche a barriga)', cnf: 'amido e açúcares', gordura: 'gordura', ureia: 'ureia', cana: 'cana demais',
  dcad: 'dieta aniônica', combinacao: 'a combinação dos limites',
}

function ResultadoPL({ pl, nome, onAceitar, onEditar }: { pl: any; nome: (id: string) => string; onAceitar: (itens: ItemDieta[]) => void; onEditar: (itens: ItemDieta[]) => void }) {
  const st = pl.pl.status
  const alertas: Alerta[] = (pl.alertas ?? []).filter((a: Alerta) => a.categoria === 'formulacao')
  if (st === 'dados_insuficientes') return <Erro msg="Faltam dados do lote para calcular as exigências." />
  return (
    <div className="mt-4 space-y-3">
      {alertas.filter((a) => a.nivel === 'critico').map((a, i) => (
        <div key={i} className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm">
          <div className="flex items-center gap-2"><NivelBadge nivel={a.nivel} />{tecnico() && <span className="font-mono text-xs">{a.regra}</span>}</div>
          <p className="mt-1 font-medium text-stone-900">{textoAlerta(a).titulo}</p>
          <p className="text-stone-600">{textoAlerta(a).causa}</p>
          <p className="text-campo-700">{textoAlerta(a).acao}</p>
        </div>
      ))}
      {st === 'inviavel' && <p className="text-sm text-stone-600">{tecnico() ? 'Restrições que impedem a solução' : 'O que não dá para atender com esses alimentos'}: <b>{pl.pl.restricoes_violadas.map((g: string) => tecnico() ? g : GRUPO_SIMPLES[g] ?? g).join(', ')}</b>.</p>}
      {pl.pl.iteracoes?.length > 1 && tecnico() && (
        <p className="text-xs text-stone-500">A dieta mudou o próprio consumo previsto (teto de fibra / equação de consumo); a formulação foi refeita {pl.pl.iteracoes.length - 1} vez(es) até ficar consistente.</p>
      )}
      {(st === 'otimo' || st === 'parcial') && (
        <>
          {st === 'parcial' && (
            <p className="rounded-lg bg-amber-50 p-2 text-sm text-atencao">
              Melhor dieta possível com estes alimentos: não atinge {pl.pl.restricoes_violadas.map((g: string) => tecnico() ? g : GRUPO_SIMPLES[g] ?? g).join(' e ')}
              {pl.pl.deficit?.energia_mcal > 0.01 && ` (faltam ${pl.pl.deficit.energia_mcal.toFixed(1)} Mcal/dia)`}. Todas as demais restrições são respeitadas.
            </p>
          )}
          <div className={`rounded-lg p-3 ${st === 'otimo' ? 'bg-campo-50' : 'bg-stone-50'}`}>
            {tecnico()
              ? <p className="num text-sm font-semibold text-campo-900">R$ {pl.pl.custo.toFixed(2)} por vaca/dia · {fmt(pl.pl.composicao.ms_kg)} kg MS · PB {fmt(pl.pl.composicao.pb_pct)}% · FDN {fmt(pl.pl.composicao.fdn_pct)}%</p>
              : <p className="num text-sm font-semibold text-campo-900">Custa {reais(pl.pl.custo)} por vaca por dia</p>}
            <ul className="mt-1 text-sm text-stone-700">
              {pl.pl.itens.map((i: ItemDieta) => <li key={i.alimento} className="num">{nome(i.alimento)}: <b>{numero(i.kg_mn, 2)}</b> {tecnico() ? 'kg MN' : 'kg por vaca/dia'}</li>)}
            </ul>
            <p className="mt-2 text-xs text-stone-600">{tecnico() ? 'Verificação pelas regras' : 'Conferida pelo sistema'}: <b>{fmt(pl.verificacao?.fatos?.['parecer.dieta']?.valor)}</b></p>
            {(pl.verificacao?.alertas ?? []).filter((a: Alerta) => a.nivel !== 'informativo').map((a: Alerta) => (
              <p key={a.regra} className="mt-1 text-xs text-atencao">{tecnico() && <span className="font-mono">{a.regra} </span>}{textoAlerta(a).titulo}</p>
            ))}
          </div>
          <div className="flex flex-wrap gap-2">
            <button className="btn-primario" onClick={() => onAceitar(pl.pl.itens)}>{st === 'parcial' ? 'Aceitar mesmo assim' : 'Aceitar como nova versão'}</button>
            <button className="btn-secundario" onClick={() => onEditar(pl.pl.itens)}>Editar antes de salvar</button>
          </div>
        </>
      )}
    </div>
  )
}

// ------------------------------------------------------------------ Acompanhamento
const ROTULO_EVENTO: Record<string, string> = {
  troca_volumoso: 'troca de volumoso', silo_novo: 'silo novo', movimentacao: 'movimentação', correcao_ms: 'correção de MS',
  mudanca_concentrado: 'mudança de concentrado', manejo_calor: 'manejo de calor', manejo_sanitario: 'manejo sanitário',
  conferencia: 'conferência de ordenha/registro', secagem: 'secagem', manejo_pasto: 'manejo do pasto', outro: 'outro',
}

interface GrupoEvento { n: number; dia: string; eventos: { tipo: string; descricao: string; data: string }[] }

/** Marcador numerado no topo de cada linha de evento (o número corresponde à legenda abaixo do gráfico). */
function MarcadorEvento({ viewBox, n, ativo }: { viewBox?: { x: number; y: number }; n: number; ativo: boolean }) {
  if (!viewBox) return null
  return (
    <g transform={`translate(${viewBox.x},${viewBox.y + 10})`}>
      <circle r={9} fill={ativo ? '#24552f' : '#4b5548'} />
      <text textAnchor="middle" dy={4} fontSize={11} fontWeight={700} fill="#fff">{n}</text>
    </g>
  )
}

/** Balão do gráfico: valores do dia + eventos registrados nele. */
function BalaoProducao({ active, payload, label, grupos }: any) {
  if (!active || !payload?.length) return null
  const p = payload[0].payload
  const g: GrupoEvento | undefined = grupos.find((x: GrupoEvento) => x.dia === label)
  return (
    <div className="max-w-xs rounded-lg border border-stone-200 bg-white p-2.5 text-xs shadow-md">
      <p className="mb-1 font-semibold text-stone-800">{label} · DEL {Math.round(p.del)}</p>
      <p className="num text-campo-700">Observado: <b>{p.observado?.toFixed(1)} L/vaca</b></p>
      <p className="num text-stone-500">Esperado: {p.esperado?.toFixed(1)} L/vaca ({p.residuo > 0 ? '+' : ''}{(p.residuo * 100).toFixed(0)}%)</p>
      {p.itu != null && <p className="num text-atencao">ITU: {p.itu.toFixed(1)}</p>}
      {p.transicao && <p className="text-stone-500">Dia de transição (fora dos detectores de queda)</p>}
      {g && (
        <div className="mt-1.5 border-t border-stone-100 pt-1.5">
          {g.eventos.map((e, i) => (
            <p key={i} className="text-stone-700"><span className="mr-1 inline-flex h-4 w-4 items-center justify-center rounded-full bg-stone-600 text-[10px] font-bold text-white">{g.n}</span>
              <b>{ROTULO_EVENTO[e.tipo] ?? e.tipo}</b>{e.descricao ? ` — ${e.descricao}` : ''}</p>
          ))}
        </div>
      )}
    </div>
  )
}
const dataCurta = (d: string) => new Date(d.slice(0, 10) + 'T12:00').toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })

function AbaAcompanhamento({ loteId }: { loteId: number }) {
  const [s, setS] = useState<any>(null)
  const [destaque, setDestaque] = useState<number | null>(null)
  useEffect(() => { api.get(`/lotes/${loteId}/serie`).then(setS) }, [loteId])
  const dados = useMemo(() => s?.producao.map((p: any) => ({ ...p, dia: dataCurta(p.data) })) ?? [], [s])
  // eventos do mesmo dia viram uma linha só, numerada na ordem do tempo
  const grupos: GrupoEvento[] = useMemo(() => {
    const porDia = new Map<string, GrupoEvento['eventos']>()
    for (const e of s?.eventos ?? []) {
      const dia = dataCurta(e.data)
      porDia.set(dia, [...(porDia.get(dia) ?? []), e])
    }
    return [...porDia.entries()].map(([dia, eventos], i) => ({ n: i + 1, dia, eventos }))
  }, [s])
  if (!s) return <Carregando texto="Carregando séries…" />
  const mini = (ind: string, titulo: string, un: string, refs: { y: number; rotulo: string }[] = []) => {
    const d = s.indicadores[ind]?.map((p: any) => ({ dia: dataCurta(p.data), valor: p.valor })) ?? []
    if (!d.length) return null
    return (
      <Painel key={ind} titulo={titulo} subtitulo={un}>
        <div className="h-36">
          <ResponsiveContainer>
            <LineChart data={d} margin={{ left: -20, right: 8 }}>
              <CartesianGrid stroke="#e8ece5" vertical={false} />
              <XAxis dataKey="dia" tick={{ fontSize: 10 }} minTickGap={20} />
              <YAxis tick={{ fontSize: 10 }} domain={['auto', 'auto']} />
              <Tooltip />
              {refs.map((r) => <ReferenceLine key={r.rotulo} y={r.y} stroke="#9a5800" strokeDasharray="4 3" label={{ value: r.rotulo, fontSize: 10, fill: '#9a5800', position: 'insideTopRight' }} />)}
              <Line dataKey="valor" stroke="#2f6b3b" strokeWidth={2} dot={{ r: 2 }} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Painel>
    )
  }
  return (
    <div className="space-y-4">
      <Painel titulo={tecnico() ? 'Produção observada × esperada' : 'Leite por vaca: real × esperado'} subtitulo={tecnico() ? 'Esperado = curva de lactação (Cobuci) × escala da fazenda, corrigido pelo ITU. Linhas numeradas = eventos registrados (passe o mouse no gráfico ou na legenda abaixo).'
        : 'O esperado é quanto este lote costuma produzir nesta fase da lactação, descontando o calor. Os números no gráfico são o que foi anotado (troca de silo, mudança de vacas…).'}>
        <div className="h-72">
          <ResponsiveContainer>
            <ComposedChart data={dados} margin={{ left: -10, right: 10 }}>
              <CartesianGrid stroke="#e8ece5" vertical={false} />
              <XAxis dataKey="dia" tick={{ fontSize: 11 }} minTickGap={24} />
              <YAxis yAxisId="l" tick={{ fontSize: 11 }} domain={['auto', 'auto']} unit=" L" />
              <YAxis yAxisId="itu" orientation="right" tick={{ fontSize: 11 }} domain={[60, 90]} />
              <Tooltip content={<BalaoProducao grupos={grupos} />} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <ReferenceLine yAxisId="itu" y={72} stroke="#fca5a5" strokeDasharray="2 4" />
              {grupos.map((g) => (
                <ReferenceLine key={g.dia} yAxisId="l" x={g.dia} stroke={destaque === g.n ? '#24552f' : '#646f60'}
                  strokeWidth={destaque === g.n ? 2.5 : 1} strokeDasharray={destaque === g.n ? undefined : '3 3'}
                  label={<MarcadorEvento n={g.n} ativo={destaque === g.n} />} />
              ))}
              <Line yAxisId="itu" dataKey="itu" name="ITU" stroke="#c98a12" strokeWidth={1} dot={false} isAnimationActive={false} />
              <Line yAxisId="l" dataKey="esperado" name="Esperado (L/vaca)" stroke="#8b9687" strokeDasharray="5 4" strokeWidth={2} dot={false} isAnimationActive={false} />
              <Line yAxisId="l" dataKey="observado" name="Observado (L/vaca)" stroke="#2f6b3b" strokeWidth={2.5} dot={false} isAnimationActive={false} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
        {grupos.length > 0 && (
          <ol className="mt-3 space-y-1.5 text-sm">
            {grupos.map((g) => (
              <li key={g.dia} onMouseEnter={() => setDestaque(g.n)} onMouseLeave={() => setDestaque(null)}
                onClick={() => setDestaque(destaque === g.n ? null : g.n)}
                className={`flex cursor-pointer items-start gap-2 rounded-lg px-2 py-1 transition ${destaque === g.n ? 'bg-campo-50' : 'hover:bg-stone-50'}`}>
                <span className={`mt-0.5 inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[11px] font-bold text-white ${destaque === g.n ? 'bg-campo-700' : 'bg-stone-600'}`}>{g.n}</span>
                <span className="num w-12 shrink-0 font-semibold text-stone-800">{g.dia}</span>
                <span className="text-stone-700">
                  {g.eventos.map((e, i) => (
                    <span key={i} className="block">
                      <b>{ROTULO_EVENTO[e.tipo] ?? e.tipo}</b>{e.descricao ? ` — ${e.descricao}` : ''}
                      <span className="ml-1 text-xs text-stone-400">{new Date(e.data).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}</span>
                    </span>
                  ))}
                </span>
              </li>
            ))}
          </ol>
        )}
      </Painel>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {mini('escore_cocho', 'Leitura de cocho', 'escore 1–5 (meta 3)', [{ y: 3, rotulo: 'meta' }])}
        {mini('sobras_pct', 'Sobras pesadas', '% da oferta', [{ y: 2, rotulo: 'mín.' }])}
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
  diario: [['vacas', 'Vacas ordenhadas', 'nº'], ['litros', 'Litros do lote', 'L'], ['concentrado_kg_vaca', 'Concentrado', 'kg/vaca'], ['temp', 'Temperatura média', '°C'], ['ur', 'Umidade média', '%'],
    ['sobras_pct', 'Sobras pesadas (se pesar)', '% da oferta']],
  semanal: [['ms_silagem', 'MS da silagem', '%'], ['ruminacao', 'Ruminação média', 'min/d'],
    ['distancia_km', 'Caminhada', 'km/dia'], ['altura_entrada', 'Altura na entrada do piquete', 'cm'], ['altura_saida', 'Altura na saída do piquete', 'cm'], ['altura_media', 'Altura média (contínuo)', 'cm']],
  mensal: [['laudo_gordura', 'Gordura', '%'], ['laudo_proteina', 'Proteína', '%'], ['laudo_lactose', 'Lactose', '%'], ['laudo_ureia', 'Ureia', 'mg/dL'], ['laudo_nul', 'NUL', 'mg/dL'], ['laudo_ccs', 'CCS', 'mil/mL'], ['laudo_cbt', 'CBT', 'mil UFC/mL'], ['laudo_crioscopia', 'Crioscopia', '°H']],
} as const

function AbaRegistro({ lote }: { lote: Lote }) {
  const { alertaId, alerta, concluir } = useAlertaDaAcao()
  const [params] = useSearchParams()
  const eventoSugerido = params.get('evento')
  const hoje = hojeLocal()
  const [data, setData] = useState(hoje)
  const [valores, setValores] = useState<Record<string, string>>({})
  const [regs, setRegs] = useState<Registro[]>([])
  const [recarga, setRecarga] = useState(0)
  const [modoLitros, setModoLitros] = useState<ModoLitros>('somar')
  const [abertos, setAbertos] = useState<Record<string, boolean>>({ diario: true })
  const doDia = useMemo(() => Object.fromEntries(regs.filter((r) => r.data === data).map((r) => [r.indicador, r])) as Record<string, Registro>, [regs, data])
  const somarLitros = !!doDia.litros && modoLitros === 'somar'
  // o formulário abre com o que já está anotado no dia; nº de vacas vem do último registro (ou do cadastro)
  useEffect(() => {
    api.get<Registro[]>(`/lotes/${lote.id}/registros?desde=${diasAtras(45)}`).then((lista) => {
      setRegs(lista)
      const dia = Object.fromEntries(lista.filter((r) => r.data === data).map((r) => [r.indicador, paraCampo(r.valor)]))
      delete dia.litros            // o total do dia aparece abaixo do campo; o campo fica para a próxima ordenha
      const ultVacas = [...lista].filter((r) => r.indicador === 'vacas' && r.data < data).pop()?.valor
      setValores({ ...dia, vacas: dia.vacas ?? String(ultVacas ?? lote.n_vacas) })
    }).catch(() => setRegs([]))
  }, [lote.id, lote.n_vacas, data, recarga])
  const [evento, setEvento] = useState({ tipo: eventoSugerido ?? 'troca_volumoso', descricao: '' })
  useEffect(() => { if (eventoSugerido) setEvento((e) => ({ ...e, tipo: eventoSugerido })) }, [eventoSugerido])
  const [res, setRes] = useState<Resultado | null>(null)
  const [erro, setErro] = useState('')
  const [ok, setOk] = useState('')

  const clima = async () => {
    setErro(''); setOk('')
    try {
      const c: any = await api.get(`/clima/${lote.fazenda_id}?data=${data}`)
      if (c.disponivel) {
        setValores((v) => ({ ...v, temp: String(c.temp), ur: String(c.ur) }))
        setOk(`Média do dia ${dataBR(data)} pela meteorologia (Open-Meteo, ${c.local}): ${c.temp} °C, ${c.ur}% — ITU ${c.itu}.`)
      } else setErro(`${c.motivo ?? 'Meteorologia indisponível'}: digite temperatura e umidade.`)
    } catch { setErro('Sem conexão com a meteorologia: digite temperatura e umidade.') }
  }
  const enviar = async () => {
    setErro(''); setOk('')
    // só vai o que é novo ou foi mudado: leite e cocho podem ser anotados em momentos diferentes
    const nums = Object.fromEntries(Object.entries(valores).filter(([, v]) => v !== '').map(([k, v]) => [k, Number(v.replace(',', '.'))])
      .filter(([k, v]) => (k === 'litros' && somarLitros) || mudou(doDia[k as string]?.valor, v as number)))
    if (!Object.keys(nums).length) { setErro(Object.keys(doDia).length ? 'Nada novo: esses valores já estão anotados neste dia.' : 'Preencha ao menos um valor.'); return }
    try {
      setRes(await api.post<Resultado>(`/lotes/${lote.id}/registros`, { data, valores: nums, alerta_id: alertaId,
        somar: somarLitros && nums.litros !== undefined ? ['litros'] : [] }))
      setOk((alertaId ? 'Registro salvo, acompanhamento executado e ação registrada no histórico do alerta.' : 'Registro salvo e acompanhamento executado.')
        + ` (${Object.keys(nums).length} valor(es) novo(s)).`)
      setRecarga((n) => n + 1)
      if (alertaId) concluir()
    } catch (e: any) { setErro(e.message) }
  }
  const apagar = async (ind: string) => {
    if (!window.confirm(`Apagar ${NOME_INDICADOR[ind] ?? ind} de ${dataBR(data)}? O acompanhamento é refeito a partir desse dia.`)) return
    setErro(''); setOk('')
    try { await api.del(`/lotes/${lote.id}/registros?data=${data}&indicador=${ind}`); setOk('Valor apagado e acompanhamento refeito.'); setRecarga((n) => n + 1) }
    catch (e: any) { setErro(e.message) }
  }
  const enviarEvento = async () => {
    setErro(''); setOk('')
    if (!evento.descricao.trim() && alertaId) { setErro('Descreva o que foi feito.'); return }
    try {
      const agora = new Date().toTimeString().slice(0, 5)
      await api.post(`/lotes/${lote.id}/eventos`, { data_hora: `${data}T${data === hoje ? agora : '08:00'}:00`, ...evento, alerta_id: alertaId })
      setOk(alertaId ? 'Ação registrada no histórico do alerta. A resolução é confirmada quando a condição deixar de valer.' : 'Evento registrado: abre janelas de supressão e de atribuição de causa.')
      setEvento({ ...evento, descricao: '' })
      if (alertaId) concluir()
    } catch (e: any) { setErro(e.message) }
  }
  const secao = (k: keyof typeof CAMPOS, titulo: string) => (
    <div className="border-t border-stone-100 pt-3">
      <button className="flex w-full items-center justify-between text-left text-sm font-semibold text-stone-800" onClick={() => setAbertos({ ...abertos, [k]: !abertos[k] })}>
        {titulo}<span className="text-stone-400">{abertos[k] ? '−' : '+'}</span>
      </button>
      {abertos[k] && k === 'diario' && (
        <div className="mt-2"><EscalaEscore tipo="cocho" valor={valores.escore_cocho ?? ''} onChange={(v) => setValores({ ...valores, escore_cocho: v })} /></div>
      )}
      {abertos[k] && k === 'semanal' && (
        <div className="mt-2 space-y-4">
          <EscalaEscore tipo="ecc" valor={valores.ecc ?? ''} onChange={(v) => setValores({ ...valores, ecc: v })} />
          <EscalaEscore tipo="fezes" valor={valores.escore_fezes ?? ''} onChange={(v) => setValores({ ...valores, escore_fezes: v })} />
        </div>
      )}
      {abertos[k] && (
        <div className="mt-2 grid grid-cols-2 gap-3 sm:grid-cols-3">
          {CAMPOS[k].map(([ind, nome, un]) => ind === 'litros' && doDia.litros ? (
            <CampoLitros key={ind} valor={valores.litros ?? ''} onChange={(x) => setValores({ ...valores, litros: x })} gravado={doDia.litros} modo={modoLitros} setModo={setModoLitros} />
          ) : (
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
    <div className="space-y-4">
    <BannerAcao alerta={alerta} onCancelar={concluir} />
    <div className="grid items-start gap-4 lg:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)]">
      <div className="space-y-4">
        <Painel titulo="Registro do dia" subtitulo="O mínimo é nº de vacas, litros e concentrado. O resto é opcional e entra quando houver.">
          <div className="mb-3 flex flex-wrap items-end gap-2">
            <label><span className="rotulo">Data</span><input type="date" className="input" value={data} onChange={(e) => setData(e.target.value)} /></label>
            <button className="btn-secundario" onClick={clima}>Buscar clima do dia (meteorologia)</button>
          </div>
          {Object.keys(doDia).length > 0 && (
            <div className="mb-3 rounded-lg bg-campo-50 p-3 text-sm text-campo-900">
              <p className="font-medium">Já anotado em {dataBR(data)} (o formulário mostra esses valores; só o que você mudar será enviado):</p>
              <div className="mt-1 flex flex-wrap gap-1.5">
                {Object.values(doDia).map((r) => (
                  <span key={r.indicador} className="inline-flex items-center gap-1 rounded-full bg-white px-2 py-0.5 text-xs ring-1 ring-campo-100" title={`gravado às ${hora(r.atualizado_em)}${r.metodo ? ` · ${r.metodo}` : ''}`}>
                    {NOME_INDICADOR[r.indicador] ?? r.indicador} <b className="num">{valorIndicador(r.indicador, r.valor, r.texto)}</b>
                    <button className="text-stone-400 hover:text-critico" onClick={() => apagar(r.indicador)} aria-label="apagar">✕</button>
                  </span>
                ))}
              </div>
            </div>
          )}
          <div className="space-y-3">
            {secao('diario', 'Diário (produção, concentrado, clima e cocho)')}
            {secao('semanal', 'Semanal (silagem, ECC, fezes, pasto)')}
            {secao('mensal', 'Mensal (laudo do laticínio / controle leiteiro)')}
          </div>
          {erro && <div className="mt-3"><Erro msg={erro} /></div>}
          {ok && <div className="mt-3 rounded-lg bg-campo-50 p-2 text-sm text-campo-700">{ok}</div>}
          <button className="btn-primario mt-4" onClick={enviar}>Salvar e analisar</button>
        </Painel>
        {res && (
          <Painel titulo={tecnico() ? 'Resultado do acompanhamento' : 'Como o lote está'} subtitulo={tecnico() ? `${res.traco.length} regras disparadas` : undefined}>
            {res.alertas.length === 0 && <p className="text-sm text-campo-700">Nenhum alerta: o lote está dentro do esperado.</p>}
            {comEpisodios(res).map((a, i) => <AlertaItem key={i} alerta={a} />)}
            {['mon.litros_vaca', 'mon.esperado_vaca', 'mon.residuo', 'mon.itu_2d', 'mon.litros_por_kg_conc'].filter((f) => res.fatos[f]).map((f) => (
              <div key={f} className="flex justify-between border-t border-stone-100 py-1 text-sm"><span className="text-stone-500">{rotulo(f)}</span><span className="num">{fmt(res.fatos[f].valor, f)}</span></div>
            ))}
          </Painel>
        )}
      </div>
      <div className="space-y-4">
        <Painel titulo={alerta ? 'Registrar o que foi feito' : 'Registrar evento'} subtitulo="Eventos explicam variações, evitam alarmes falsos e ficam no histórico dos alertas."
          className={eventoSugerido && alerta ? 'ring-2 ring-campo-500' : ''}>
          <div className="space-y-2">
            <label className="block"><span className="rotulo">Tipo</span>
              <select className="input" value={evento.tipo} onChange={(e) => setEvento({ ...evento, tipo: e.target.value })}>
                {Object.entries(ROTULO_EVENTO).map(([k, v]) => <option key={k} value={k}>{v[0].toUpperCase() + v.slice(1)}</option>)}
              </select></label>
            <label className="block"><span className="rotulo">{alerta ? 'O que foi feito' : 'Descrição'}</span>
              <textarea className="input h-20" placeholder={alerta ? 'Ex.: aspersão ligada das 11h às 16h' : 'Ex.: abri o silo 3; 5 vacas entraram do lote 2'} value={evento.descricao} onChange={(e) => setEvento({ ...evento, descricao: e.target.value })} /></label>
            <button className="btn-secundario" onClick={enviarEvento}>Registrar evento</button>
          </div>
        </Painel>
        <ImportarPlanilha lote={lote} />
      </div>
    </div>
    <HistoricoRegistros regs={regs} lote={lote} dataAtual={data} onAbrir={(d) => { setData(d); window.scrollTo({ top: 0, behavior: 'smooth' }) }} />
    </div>
  )
}

const COLUNAS_HIST: [string, string][] = [['vacas', 'Vacas'], ['litros', 'Litros'], ['concentrado_kg_vaca', 'Conc./vaca'], ['escore_cocho', 'Cocho'],
  ['sobras_pct', 'Sobras %'], ['temp', '°C'], ['ur', 'UR %']]

/** Histórico dos registros do lote (45 dias): uma linha por dia; clicar abre o dia no formulário para completar/corrigir. */
function HistoricoRegistros({ regs, lote, dataAtual, onAbrir }: { regs: Registro[]; lote: Lote; dataAtual: string; onAbrir: (d: string) => void }) {
  const [todos, setTodos] = useState(false)
  const dias = porDia(regs)
  const visiveis = todos ? dias : dias.slice(0, 10)
  const fixos = new Set(COLUNAS_HIST.map(([k]) => k))
  return (
    <Painel titulo="Histórico de registros" subtitulo="O que foi anotado em cada dia. Clique num dia para completar ou corrigir (o acompanhamento é refeito a partir dele).">
      {dias.length === 0 && <p className="text-sm text-stone-500">Nada anotado nos últimos 45 dias.</p>}
      {dias.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-xs text-stone-500">
              <tr><th className="py-1 pr-3">Dia</th><th className="pr-3 text-right">L/vaca</th>{COLUNAS_HIST.map(([k, n]) => <th key={k} className="pr-3 text-right">{n}</th>)}<th className="pr-3">Outros</th><th>Última anotação</th></tr>
            </thead>
            <tbody>
              {visiveis.map(([d, ind]) => {
                const lv = ind.litros && ind.vacas ? ind.litros.valor / ind.vacas.valor : null
                const outros = Object.values(ind).filter((r) => !fixos.has(r.indicador))
                const falta = !ind.litros || !ind.vacas || (lote.sistema !== 'pasto' && !ind.escore_cocho && !ind.sobras_pct)
                return (
                  <tr key={d} onClick={() => onAbrir(d)} className={`cursor-pointer border-t border-stone-100 hover:bg-stone-50 ${d === dataAtual ? 'bg-campo-50' : ''}`}>
                    <td className="py-1.5 pr-3 font-medium text-stone-800">{dataBR(d)}{falta && <span className="ml-1 text-xs text-amber-700" title="faltou leite, vacas ou cocho">●</span>}</td>
                    <td className="num pr-3 text-right font-semibold text-campo-700">{lv !== null ? numero(lv) : '—'}</td>
                    {COLUNAS_HIST.map(([k]) => <td key={k} className="num pr-3 text-right text-stone-700">{ind[k] ? numero(ind[k].valor, k === 'concentrado_kg_vaca' ? 2 : 1) : <span className="text-stone-300">—</span>}</td>)}
                    <td className="pr-3 text-xs text-stone-500">{outros.map((r) => `${NOME_INDICADOR[r.indicador] ?? r.indicador} ${valorIndicador(r.indicador, r.valor, r.texto)}`).join(' · ')}</td>
                    <td className="text-xs text-stone-400">{hora(Object.values(ind).map((r) => r.atualizado_em ?? '').sort().pop())}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
      {dias.length > 10 && <button className="mt-2 text-sm text-campo-600 hover:underline" onClick={() => setTodos(!todos)}>{todos ? 'mostrar menos' : `mostrar os ${dias.length} dias`}</button>}
      <p className="mt-2 text-xs text-stone-400">● faltou leite, vacas ou leitura de cocho nesse dia.</p>
    </Painel>
  )
}

/** Importação de planilha CSV (registros diários, controle leiteiro, laudo): prévia antes de gravar. */
function ImportarPlanilha({ lote }: { lote: Lote }) {
  const [aberto, setAberto] = useState(false)
  const [conteudo, setConteudo] = useState('')
  const [previa, setPrevia] = useState<any>(null)
  const [erro, setErro] = useState('')
  const [ok, setOk] = useState('')
  const [ocupado, setOcupado] = useState(false)
  const enviar = async (confirmar: boolean) => {
    setErro(''); setOk(''); setOcupado(true)
    try {
      const r = await api.post<any>(`/lotes/${lote.id}/importar`, { conteudo, confirmar })
      setPrevia(r)
      if (r.gravado) { setOk(`${r.registros} valores gravados (${dataBR(r.periodo[0])} a ${dataBR(r.periodo[1])}); acompanhamento reprocessado. Alertas pendentes do lote: ${r.alertas_pendentes}.`); setConteudo('') }
    } catch (e: any) { setErro(e.message); setPrevia(null) }
    setOcupado(false)
  }
  const arquivo = (e: any) => {
    const f = e.target.files?.[0]
    if (!f) return
    const leitor = new FileReader()
    leitor.onload = () => { setConteudo(String(leitor.result)); setPrevia(null) }
    leitor.readAsText(f, 'utf-8')
  }
  return (
    <Painel titulo="Importar planilha (CSV)" subtitulo="Registros diários, controle leiteiro ou laudo do laticínio. Uma linha por data; colunas com os nomes do modelo."
      acoes={<button className="btn-secundario py-1.5" aria-expanded={aberto} onClick={() => setAberto(!aberto)}>{aberto ? 'Fechar' : 'Importar'}</button>}>
      {aberto && (
        <div className="space-y-3">
          <p className="text-xs text-stone-500">Modelos: <a className="text-campo-600 hover:underline" href="/api/modelos/importacao/diario">registros diários</a> · <a className="text-campo-600 hover:underline" href="/api/modelos/importacao/laudo">laudo / controle leiteiro</a>. Separador ; ou , e vírgula decimal são aceitos.</p>
          <input type="file" accept=".csv,.txt" onChange={arquivo} className="text-sm" />
          <textarea className="input h-28 font-mono text-xs" placeholder="…ou cole aqui o conteúdo do CSV" value={conteudo}
            onChange={(e) => { setConteudo(e.target.value); setPrevia(null) }} />
          <div className="flex flex-wrap gap-2">
            <button className="btn-secundario" disabled={!conteudo.trim() || ocupado} onClick={() => enviar(false)}>Ver prévia</button>
            {previa && !previa.gravado && previa.registros > 0 && (
              <button className="btn-primario" disabled={ocupado} onClick={() => enviar(true)}>Gravar {previa.registros} valores</button>
            )}
          </div>
          {erro && <Erro msg={erro} />}
          {ok && <div className="rounded-lg bg-campo-50 p-2 text-sm text-campo-700">{ok}</div>}
          {previa && !previa.gravado && (
            <div className="space-y-2 text-sm">
              <p><b>{previa.registros}</b> valores válidos em {previa.linhas} linha(s){previa.periodo && <> · {dataBR(previa.periodo[0])} a {dataBR(previa.periodo[1])}</>}{previa.erros.length > 0 && <span className="text-atencao"> · {previa.erros.length} célula(s) com problema</span>}</p>
              <div className="flex flex-wrap gap-1 text-xs">
                {Object.entries(previa.colunas).map(([col, ind]: any) => (
                  <span key={col} className={`rounded px-1.5 py-0.5 ${ind ? 'bg-campo-50 text-campo-700' : 'bg-stone-100 text-stone-400 line-through'}`} title={ind ? `→ ${ind}` : 'coluna ignorada'}>{col}{ind ? ` → ${rotuloIndicador(ind)}` : ''}</span>
                ))}
              </div>
              {previa.erros.length > 0 && (
                <ul className="max-h-32 overflow-y-auto rounded bg-amber-50 p-2 text-xs text-stone-700">
                  {previa.erros.map((e: any, i: number) => <li key={i}>Linha {e.linha}, {e.coluna} = “{e.valor}”: {e.motivo}</li>)}
                </ul>
              )}
            </div>
          )}
        </div>
      )}
    </Painel>
  )
}

const rotuloIndicador = (ind: string) => {
  if (ind === 'escore_cocho') return 'Leitura de cocho (1–5)'
  if (ind === 'ecc') return 'ECC médio (1–5)'
  if (ind === 'escore_fezes') return 'Escore de fezes (1–5)'
  const todos = [...CAMPOS.diario, ...CAMPOS.semanal, ...CAMPOS.mensal] as unknown as [string, string, string][]
  return todos.find(([k]) => k === ind)?.[1] ?? ind
}

// ------------------------------------------------------------------ Alertas
function AbaAlertas({ loteId }: { loteId: number }) {
  const [alertas, setAlertas] = useState<Alerta[] | null>(null)
  const [hist, setHist] = useState<ItemHistorico[] | null>(null)
  const [aberto, setAberto] = useState<Alerta | null>(null)
  const [filtro, setFiltro] = useState('pendentes')
  const [vista, setVista] = useState<'alertas' | 'historico'>('alertas')
  const carregar = useCallback(() => {
    api.get<Alerta[]>(`/alertas?lote_id=${loteId}&estado=${filtro}&dias=120`).then(setAlertas)
    api.get<ItemHistorico[]>(`/historico?lote_id=${loteId}&dias=120`).then(setHist)
  }, [loteId, filtro])
  useEffect(carregar, [carregar])
  const abrirPorId = async (id: number) => setAberto(await api.get<Alerta>(`/alertas/${id}`))
  return (
    <Painel titulo={tecnico() ? 'Alertas e ações' : 'Avisos do lote'}
      subtitulo={tecnico() ? 'Cada problema é um episódio: aberto → aceito (ação registrada) ou recusado → resolvido quando a condição deixa de valer, mesmo sem passar pelo aceite.'
        : 'Aceite para ir à tela onde se registra o que foi feito, ou recuse dizendo o motivo. O aviso some sozinho quando o problema for resolvido, e fica no histórico.'}
      acoes={
        <div className="flex flex-wrap gap-2">
          <div className="flex rounded-lg border border-stone-300 p-0.5 text-sm">
            {(['alertas', 'historico'] as const).map((v) => (
              <button key={v} onClick={() => setVista(v)} className={`rounded-md px-3 py-1 ${vista === v ? 'bg-campo-600 text-white' : 'text-stone-600'}`}>{v === 'alertas' ? 'Alertas' : 'Histórico'}</button>
            ))}
          </div>
          {vista === 'alertas' && (
            <select className="input w-44" value={filtro} onChange={(e) => setFiltro(e.target.value)}>
              <option value="pendentes">Pendentes</option><option value="abertos">Abertos</option><option value="aceitos">Aceitos (em andamento)</option>
              <option value="recusados">Recusados</option><option value="resolvidos">Resolvidos</option><option value="expirados">Expirados</option>
              <option value="todos">Todos</option>
            </select>
          )}
        </div>
      }>
      {vista === 'alertas' && !alertas && <Carregando />}
      {vista === 'alertas' && alertas?.length === 0 && <p className="text-sm text-stone-500">Nenhum alerta neste filtro.</p>}
      {vista === 'alertas' && alertas?.map((a) => <AlertaItem key={a.id} alerta={a} onAbrir={() => setAberto(a)} onMudou={carregar} />)}
      {vista === 'historico' && (hist ? <LinhaDoTempo itens={hist} mostrarAlerta onAbrirAlerta={abrirPorId} /> : <Carregando />)}
      <Gaveta aberta={!!aberto} onFechar={() => { setAberto(null); carregar() }} titulo={tecnico() ? 'Alerta: explicação e histórico' : 'Entender o aviso'}>
        {aberto && <ExplicacaoAlerta key={aberto.id} alerta={aberto} />}
      </Gaveta>
    </Painel>
  )
}
