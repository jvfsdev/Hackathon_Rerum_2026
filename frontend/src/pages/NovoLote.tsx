import { useLocation, useNavigate } from 'react-router-dom'
import LoteForm, { valoresDaConsulta } from '../components/LoteForm'
import { Painel } from '../components/ui'
import { rotulo } from '../api'

/** Novo lote; vindo da consulta guiada, chega com as respostas em `state.fatos` e os valores padrão usados em `state.padroes`. */
export default function NovoLotePagina() {
  const navegar = useNavigate()
  const estado = useLocation().state as { fatos?: Record<string, any>; padroes?: string[] } | null
  const daConsulta = !!estado?.fatos
  const padroes = (estado?.padroes ?? []).filter((f) => f.startsWith('lote.'))
  return (
    <Painel titulo="Novo lote" subtitulo="Depois de criar, monte a dieta (ou peça a sugestão de custo mínimo) e comece os registros diários.">
      {daConsulta && (
        <div className="mb-4 rounded-lg bg-campo-50 p-3 text-sm text-campo-900">
          Preenchido com as respostas da consulta guiada. Dê um nome ao lote, informe o nº de vacas e confira os campos.
          {padroes.length > 0 && <span className="text-amber-800"> Valores padrão (você respondeu "não sei"): {padroes.map(rotulo).join(', ')}.</span>}
        </div>
      )}
      <LoteForm inicial={daConsulta ? valoresDaConsulta(estado!.fatos!) : undefined} onSalvo={(l) => navegar(`/lotes/${l.id}/dieta`)} />
    </Painel>
  )
}
