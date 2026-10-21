import { Navigate, NavLink, Route, Routes, useLocation } from 'react-router-dom'
import CampoPagina from './pages/Campo'
import PainelPagina from './pages/Painel'
import LotePagina from './pages/Lote'
import ConsultaPagina from './pages/Consulta'
import BasePagina from './pages/Base'
import NovoLotePagina from './pages/NovoLote'
import PrecosPagina from './pages/Precos'

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
  if (pathname.startsWith('/campo')) {
    return <Routes><Route path="/campo/*" element={<CampoPagina />} /></Routes>
  }
  return (
    <div className="min-h-screen">
      <header className="bg-campo-700">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-2 px-4 py-3">
          <NavLink to="/" className="flex items-center gap-2 text-white">
            <span className="text-xl">🐄</span>
            <span className="font-semibold">Leite por Lote</span>
            <span className="hidden text-xs text-campo-100 sm:inline">· sistema especialista de dietas</span>
          </NavLink>
          <nav className="flex flex-wrap gap-1">
            <NavLink to="/" end className={link}>Painel</NavLink>
            <NavLink to="/consulta" className={link}>Consulta guiada</NavLink>
            <NavLink to="/insumos" className={link}>Insumos e preços</NavLink>
            <NavLink to="/base" className={link}>Base de conhecimento</NavLink>
            <NavLink to="/campo" className={link}>📱 Modo campo</NavLink>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-6xl overflow-x-hidden px-4 py-5">
        <Routes>
          <Route path="/" element={<Inicio />} />
          <Route path="/lotes/novo" element={<NovoLotePagina />} />
          <Route path="/lotes/:id/*" element={<LotePagina />} />
          <Route path="/consulta" element={<ConsultaPagina />} />
          <Route path="/base" element={<BasePagina />} />
          <Route path="/insumos" element={<PrecosPagina />} />
          <Route path="/precos" element={<PrecosPagina />} />
        </Routes>
      </main>
      <footer className="mx-auto max-w-6xl px-4 pb-6 text-xs text-stone-400">
        As decisões vêm da base de conhecimento e do motor de inferência (determinístico e auditável). Valores de referência para prova de conceito; validar com zootecnista.
      </footer>
    </div>
  )
}
