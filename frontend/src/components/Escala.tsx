/** Escalas visuais de campo (1 a 5) com a descrição de cada nível — padronizam a avaliação entre pessoas. */

export interface Nivel { n: number; nome: string; descricao: string }
export interface DefEscala { titulo: string; niveis: Nivel[]; passo: number; rodape?: string }

export const ESCALAS: Record<'cocho' | 'ecc' | 'fezes', DefEscala> = {
  cocho: {
    titulo: 'Leitura de cocho (antes do 1º trato)', passo: 1,
    niveis: [
      { n: 1, nome: 'Vazio', descricao: 'Cocho limpo há horas: as vacas ficaram sem comida.' },
      { n: 2, nome: 'Quase vazio', descricao: 'Só restos espalhados; menos de 1% de sobra.' },
      { n: 3, nome: 'Na meta', descricao: 'Camada fina e uniforme de sobra (2–4%).' },
      { n: 4, nome: 'Sobra visível', descricao: 'Sobra cobrindo o fundo do cocho (5–10%).' },
      { n: 5, nome: 'Muita sobra', descricao: 'Mais de 10% de sobra ou trato praticamente intocado.' },
    ],
    rodape: 'Se pesar as sobras, use o campo de % (ele prevalece sobre o escore).',
  },
  ecc: {
    titulo: 'Escore de condição corporal (média do lote)', passo: 0.25,
    niveis: [
      { n: 1, nome: 'Muito magra', descricao: 'Coluna, costelas, ponta do quadril e ísquio muito salientes; base da cauda funda, sem gordura.' },
      { n: 2, nome: 'Magra', descricao: 'Costelas visíveis; pontas dos processos da coluna palpáveis com facilidade; quadril anguloso.' },
      { n: 3, nome: 'Moderada', descricao: 'Costelas pouco visíveis; ossos cobertos e palpáveis com leve pressão; quadril arredondado.' },
      { n: 4, nome: 'Gorda', descricao: 'Costelas não visíveis; processos da coluna só com pressão firme; gordura em volta da base da cauda.' },
      { n: 5, nome: 'Muito gorda', descricao: 'Ossos não palpáveis; dobras e depósitos de gordura na cauda, no quadril e no peito.' },
    ],
    rodape: 'Metas: parto 3,25–3,75 · pico 2,5–3,0 · meio da lactação 2,75–3,25 · final 3,0–3,75. Perder mais de 0,5–0,75 ponto numa fase indica balanço energético negativo.',
  },
  fezes: {
    titulo: 'Escore de fezes', passo: 0.5,
    niveis: [
      { n: 1, nome: 'Muito líquida', descricao: 'Escorre como sopa, não forma monte.' },
      { n: 2, nome: 'Mole', descricao: 'Espalha ao cair, monte com menos de 2,5 cm; sem anéis.' },
      { n: 3, nome: 'Ideal', descricao: 'Consistência de pudim: monte de 4–5 cm com anéis e depressão no centro.' },
      { n: 4, nome: 'Firme', descricao: 'Monte alto que não se espalha; marca pouco a bota.' },
      { n: 5, nome: 'Muito firme', descricao: 'Bolas secas e duras, como fezes de cavalo.' },
    ],
    rodape: 'Metas: 3,0 em alta produção · 2,5 nas recém-paridas · 3,5 em secas e final de lactação. Mole: excesso de proteína/amido ou acidose; firme: excesso de fibra ou pouca proteína.',
  },
}

const fmt = (v: number) => v.toLocaleString('pt-BR', { minimumFractionDigits: 0, maximumFractionDigits: 2 })

export function nivelDe(escala: DefEscala, valor: number): Nivel {
  return escala.niveis[Math.min(4, Math.max(0, Math.round(valor) - 1))]
}

/** Botões 1–5 com a descrição do nível; para escalas com passo menor que 1, ajuste fino (−/+). */
export function EscalaEscore({ tipo, valor, onChange }: { tipo: keyof typeof ESCALAS; valor: string; onChange: (v: string) => void }) {
  const escala = ESCALAS[tipo]
  const num = valor === '' ? null : Number(valor.replace(',', '.'))
  const ajustar = (delta: number) => {
    const base = num ?? 3
    onChange(String(Math.min(5, Math.max(1, Math.round((base + delta) / escala.passo) * escala.passo))))
  }
  const atual = num !== null ? nivelDe(escala, num) : null
  return (
    <div>
      <span className="rotulo">{escala.titulo}</span>
      <div className="grid grid-cols-5 gap-1.5">
        {escala.niveis.map((nv) => {
          const ativo = num !== null && Math.round(num) === nv.n
          return (
            <button key={nv.n} type="button" title={nv.descricao}
              onClick={() => onChange(num !== null && num === nv.n ? '' : String(nv.n))}
              className={`rounded-lg border px-1 py-1.5 text-center text-xs leading-tight transition ${ativo ? 'border-campo-600 bg-campo-600 text-white' : 'border-stone-300 bg-white text-stone-700 hover:bg-stone-50'}`}>
              <span className="block text-base font-semibold">{nv.n}</span>{nv.nome}
            </button>
          )
        })}
      </div>
      {escala.passo < 1 && num !== null && (
        <div className="mt-1.5 flex items-center gap-2 text-sm">
          <button type="button" className="btn-secundario px-2 py-0.5" onClick={() => ajustar(-escala.passo)} aria-label="diminuir">−{fmt(escala.passo)}</button>
          <span className="num w-12 text-center text-base font-semibold text-stone-900">{fmt(num)}</span>
          <button type="button" className="btn-secundario px-2 py-0.5" onClick={() => ajustar(escala.passo)} aria-label="aumentar">+{fmt(escala.passo)}</button>
          <span className="text-xs text-stone-500">ajuste fino em passos de {fmt(escala.passo)}</span>
        </div>
      )}
      <p className="mt-1 text-xs text-stone-600">
        {atual ? <><b>{atual.n} · {atual.nome}:</b> {atual.descricao}</> : 'Toque no nível que melhor descreve o lote.'}
      </p>
      {escala.rodape && <p className="mt-0.5 text-xs text-stone-400">{escala.rodape}</p>}
    </div>
  )
}
