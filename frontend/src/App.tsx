import { useState } from 'react'
import { Navigate, NavLink, Route, Routes, useLocation } from 'react-router-dom'
import { getModo, setModoGlobal, type Modo } from './api'
import { ModoContexto } from './modo'
import CampoPagina from './pages/Campo'
import PainelPagina from './pages/Painel'
import LotePagina from './pages/Lote'
import ConsultaPagina from './pages/Consulta'
import BasePagina from './pages/Base'
import NovoLotePagina from './pages/NovoLote'
import PrecosPagina from './pages/Precos'
import EstoquePagina from './pages/Estoque'
import RelatorioPagina from './pages/Relatorio'

const link = ({ isActive }: { isActive: boolean }) =>
  `rounded-lg px-3 py-1.5 text-sm font-medium transition ${isActive ? 'bg-white/15 text-white' : 'text-campo-100 hover:bg-white/10 hover:text-white'}`

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

function Completo({ modo, setModo }: { modo: Modo; setModo: (m: Modo) => void }) {
  return (
    <div className="min-h-screen" key={modo}>
      <header className="bg-campo-700 print:hidden">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-2 px-4 py-3">
          <NavLink to="/" className="flex items-center gap-2 text-white">
            <span className="text-xl">🐄</span>
            <span className="font-semibold">CochoCerto</span>
            <span className="hidden text-xs text-campo-100 sm:inline">· sistema especialista de dietas</span>
          </NavLink>
          <nav className="flex flex-wrap gap-1">
            <NavLink to="/" end className={link}>Painel</NavLink>
            <NavLink to="/consulta" className={link}>Consulta guiada</NavLink>
            <NavLink to="/insumos" className={link}>Insumos e preços</NavLink>
            <NavLink to="/estoque" className={link}>Estoque</NavLink>
            <NavLink to="/relatorio" className={link}>Relatório</NavLink>
            <NavLink to="/base" className={link}>Base de conhecimento</NavLink>
            <NavLink to="/campo" className={link}>📱 Modo campo</NavLink>
          </nav>
          <div className="flex rounded-lg bg-white/10 p-0.5 text-xs" title="Produtor: linguagem de fazenda. Técnico: regras, fatores de certeza e traço do motor.">
            {(['produtor', 'tecnico'] as const).map((m) => (
              <button key={m} onClick={() => setModo(m)}
                className={`rounded-md px-2.5 py-1 font-medium ${modo === m ? 'bg-white text-campo-700' : 'text-campo-100 hover:text-white'}`}>
                {m === 'produtor' ? 'Visão do produtor' : 'Visão técnica'}
              </button>
            ))}
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl overflow-x-hidden px-4 py-5 print:max-w-none print:p-0">
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
      <footer className="mx-auto max-w-6xl px-4 pb-6 text-xs text-stone-400 print:hidden">
        As decisões vêm da base de conhecimento e do motor de inferência (determinístico e auditável). Valores de referência para prova de conceito; validar com zootecnista.
      </footer>
    </div>
  )
}
