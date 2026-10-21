import { numero, type Registro } from '../api'

export type ModoLitros = 'somar' | 'corrigir'

/** Litros do dia: se já houve ordenha anotada, a nova entrada soma (2ª ordenha) ou corrige o total. */
export function CampoLitros({ valor, onChange, gravado, modo, setModo, dica, campo = false }: {
  valor: string; onChange: (v: string) => void; gravado?: Registro; modo: ModoLitros; setModo: (m: ModoLitros) => void
  dica?: string; campo?: boolean
}) {
  const novo = valor.trim() === '' ? null : Number(valor.replace(',', '.'))
  const somando = !!gravado && modo === 'somar'
  const total = gravado && novo !== null && !Number.isNaN(novo) ? (somando ? gravado.valor + novo : novo) : null
  return (
    <div className={campo ? 'col-span-2' : 'sm:col-span-3'}>
      <label className="block">
        <span className={campo ? 'mb-1 block text-sm font-medium text-stone-700' : 'rotulo'}>
          {gravado ? (somando ? 'Litros desta ordenha' : 'Total de litros do dia (corrigir)') : 'Litros do lote'} <span className="font-normal text-stone-400">(L)</span>
        </span>
        <input className={campo ? 'input num py-3 text-lg' : 'input num'} inputMode="decimal" value={valor} onChange={(e) => onChange(e.target.value)}
          placeholder={gravado ? (somando ? 'ex.: litros da 2ª ordenha' : numero(gravado.valor, 0)) : dica} />
      </label>
      {gravado && (
        <div className="mt-1.5 rounded-lg bg-stone-50 p-2 text-sm">
          <p className="text-stone-700">Já ordenhado neste dia: <b className="num">{numero(gravado.valor, 0)} L</b>
            {gravado.texto && <span className="text-stone-500"> ({gravado.texto.replace(/\./g, ',')})</span>}</p>
          <div className="mt-1.5 flex gap-1.5">
            {(['somar', 'corrigir'] as const).map((m) => (
              <button key={m} type="button" onClick={() => setModo(m)}
                className={`flex-1 rounded-md border px-2 py-1.5 text-xs font-medium ${modo === m ? 'border-campo-600 bg-campo-600 text-white' : 'border-stone-300 bg-white text-stone-700'}`}>
                {m === 'somar' ? 'Somar (outra ordenha)' : 'Corrigir o total'}
              </button>
            ))}
          </div>
          {total !== null && <p className="num mt-1.5 text-xs text-campo-700">Total do dia vai ficar em <b>{numero(total, 0)} L</b>{somando ? ` (${numero(gravado.valor, 0)} + ${numero(novo, 0)})` : ''}.</p>}
        </div>
      )}
    </div>
  )
}
