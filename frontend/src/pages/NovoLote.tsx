import { useNavigate } from 'react-router-dom'
import LoteForm from '../components/LoteForm'
import { Painel } from '../components/ui'

export default function NovoLotePagina() {
  const navegar = useNavigate()
  return (
    <Painel titulo="Novo lote" subtitulo="Depois de criar, monte a dieta (ou peça a sugestão de custo mínimo) e comece os registros diários.">
      <LoteForm onSalvo={(l) => navegar(`/lotes/${l.id}/dieta`)} />
    </Painel>
  )
}
