import { useState } from 'react'
import { Navigate, NavLink, Route, Routes, useLocation } from 'react-router-dom'
import { getModo, setModoGlobal, type Modo } from './api'
import { ModoContexto } from './modo'
import { Icone } from './components/ui'
import CampoPagina from './pages/Campo'
import PainelPagina from './pages/Painel'
import LotePagina from './pages/Lote'
import ConsultaPagina from './pages/Consulta'
import BasePagina from './pages/Base'
import NovoLotePagina from './pages/NovoLote'
import PrecosPagina from './pages/Precos'
import EstoquePagina from './pages/Estoque'
import RelatorioPagina from './pages/Relatorio'

/** No celular, a página inicial abre o modo campo — salvo se a pessoa pediu a versão completa nesta sessão. */
function Inicio() {
  const { search } = useLocation()
  if (new URLSearchParams(search).get('completo') === '1') {
    try { sessionStorage.setItem('versao_completa', '1') } catch { /* sem armazenamento */ }
  }
  let completa = false
  try { completa = sessionStorage.getItem('versao_completa') === '1' } catch { /* sem armazenamento */ }
  if (window.innerWidth < 640 && !completa) return <Navigate to="/campo" replace />
  return <PainelPagina />
}

export default function App() {
  const { pathname } = useLocation()
  const [modo, setModoEstado] = useState<Modo>(getModo())
  const setModo = (m: Modo) => { setModoGlobal(m); setModoEstado(m) }
  return (
    <ModoContexto.Provider value={{ modo, setModo }}>
      {pathname.startsWith('/campo')
        ? <Routes><Route path="/campo/*" element={<CampoPagina />} /></Routes>
        : <Completo modo={modo} setModo={setModo} />}
    </ModoContexto.Provider>
  )
}

const NAV: { to: string; nome: string; icone: string; end?: boolean }[] = [
  { to: '/', nome: 'Painel', icone: 'painel', end: true },
  { to: '/consulta', nome: 'Consulta guiada', icone: 'consulta' },
  { to: '/insumos', nome: 'Insumos e preços', icone: 'insumos' },
  { to: '/estoque', nome: 'Estoque', icone: 'estoque' },
  { to: '/relatorio', nome: 'Relatório', icone: 'relatorio' },
  { to: '/base', nome: 'Base de conhecimento', icone: 'base' },
]

/** Marca: o brinco amarelo com a letra C, ao lado do nome. */
function Marca() {
  return (
    <NavLink to="/" className="flex items-center gap-2.5 text-white">
      <svg viewBox="0 0 40 50" className="h-9 w-7 shrink-0" aria-hidden="true">
        <path d="M20 1.5c-4.6 0-8 3-8.6 7.2L6.2 41.4C5.6 45.3 8.6 48.5 12.6 48.5h14.8c4 0 7-3.2 6.4-7.1L28.6 8.7C28 4.5 24.6 1.5 20 1.5z" fill="var(--color-brinco)" />
        <circle cx="20" cy="10" r="3.2" fill="var(--color-campo-900)" />
        <text x="20" y="40" textAnchor="middle" fontFamily="Barlow Condensed, sans-serif" fontWeight="700" fontSize="19" fill="#162019">C</text>
      </svg>
      <span className="leading-none">
        <span className="titulo block text-[1.45rem] font-bold tracking-wide">CochoCerto</span>
        <span className="mt-0.5 block text-[11px] text-campo-100/70">dieta e cocho por lote</span>
      </span>
    </NavLink>
  )
}

function SeletorModo({ modo, setModo, compacto = false }: { modo: Modo; setModo: (m: Modo) => void; compacto?: boolean }) {
  return (
    <div role="group" aria-label="Visão da interface" className="flex rounded-md bg-black/25 p-0.5 text-xs"
      title="Produtor: linguagem de fazenda. Técnico: regras, fatores de certeza e traço do motor.">
      {(['produtor', 'tecnico'] as const).map((m) => (
        <button key={m} onClick={() => setModo(m)} aria-pressed={modo === m}
          className={`flex-1 rounded px-2.5 py-1.5 font-semibold transition-colors ${modo === m ? 'bg-brinco text-stone-900' : 'text-campo-100/80 hover:text-white'}`}>
          {m === 'produtor' ? (compacto ? 'Produtor' : 'Visão do produtor') : (compacto ? 'Técnico' : 'Visão técnica')}
        </button>
      ))}
    </div>
  )
}

const itemLateral = ({ isActive }: { isActive: boolean }) =>
  `group flex items-center gap-3 rounded-md px-3 py-2 text-[15px] font-medium transition-colors ${isActive ? 'bg-white/10 text-white shadow-[inset_3px_0_0_var(--color-brinco)]' : 'text-campo-100/75 hover:bg-white/5 hover:text-white'}`
const itemTopo = ({ isActive }: { isActive: boolean }) =>
  `flex shrink-0 items-center gap-1.5 whitespace-nowrap border-b-2 px-2.5 py-2 text-sm font-medium ${isActive ? 'border-brinco text-white' : 'border-transparent text-campo-100/75'}`

function Completo({ modo, setModo }: { modo: Modo; setModo: (m: Modo) => void }) {
  return (
    <div className="min-h-screen lg:flex" key={modo}>
      {/* trilho lateral (telas largas) */}
      <aside className="sticky top-0 hidden h-screen w-64 shrink-0 flex-col bg-campo-900 px-4 py-5 lg:flex print:hidden">
        <Marca />
        <nav className="mt-8 flex flex-col gap-0.5" aria-label="Principal">
          {NAV.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.end} className={itemLateral}>
              <Icone nome={n.icone} className="h-[18px] w-[18px] opacity-80 group-hover:opacity-100" />{n.nome}
            </NavLink>
          ))}
        </nav>
        <NavLink to="/campo" className="mt-4 flex items-center gap-3 rounded-md border border-white/15 px-3 py-2 text-sm font-medium text-campo-100/85 hover:border-white/30 hover:text-white">
          <Icone nome="celular" className="h-[18px] w-[18px]" />Modo campo (celular)
        </NavLink>
        <div className="mt-auto space-y-3">
          <div>
            <p className="mb-1.5 text-[11px] font-medium text-campo-100/60">Linguagem da interface</p>
            <SeletorModo modo={modo} setModo={setModo} compacto />
          </div>
          <p className="text-[11px] leading-snug text-campo-100/50">
            Quem decide é a base de conhecimento e o motor de inferência: determinístico e auditável.
          </p>
        </div>
      </aside>

      {/* barra superior (celular e tablet) */}
      <header className="sticky top-0 z-30 bg-campo-900 pt-[env(safe-area-inset-top,0px)] lg:hidden print:hidden">
        <div className="flex items-center justify-between gap-3 px-4 pt-3 pb-1">
          <Marca />
          <SeletorModo modo={modo} setModo={setModo} compacto />
        </div>
        <nav className="flex overflow-x-auto px-2" aria-label="Principal">
          {NAV.map((n) => <NavLink key={n.to} to={n.to} end={n.end} className={itemTopo}>{n.nome}</NavLink>)}
          <NavLink to="/campo" className={itemTopo}><Icone nome="celular" />Modo campo</NavLink>
        </nav>
      </header>

      <div className="min-w-0 flex-1">
        <main className="mx-auto max-w-6xl overflow-x-hidden px-4 py-6 sm:px-6 lg:px-8 lg:py-8 print:max-w-none print:p-0">
          <Routes>
            <Route path="/" element={<Inicio />} />
            <Route path="/lotes/novo" element={<NovoLotePagina />} />
            <Route path="/lotes/:id/*" element={<LotePagina />} />
            <Route path="/consulta" element={<ConsultaPagina />} />
            <Route path="/base" element={<BasePagina />} />
            <Route path="/insumos" element={<PrecosPagina />} />
            <Route path="/precos" element={<PrecosPagina />} />
            <Route path="/estoque" element={<EstoquePagina />} />
            <Route path="/relatorio" element={<RelatorioPagina />} />
          </Routes>
        </main>
        <footer className="mx-auto max-w-6xl px-4 pb-8 text-xs text-stone-400 sm:px-6 lg:px-8 print:hidden">
          Valores de referência para prova de conceito; validar com zootecnista.
        </footer>
      </div>
    </div>
  )
}
