/** Fila offline do modo campo (sem dependência de tela, testada em scripts/testar-fila.mjs).
 *
 * Regras:
 * 1. Envia sempre na ordem em que foi registrado: registro retroativo reprocessa os dias seguintes no servidor.
 * 2. Sem conexão, para no primeiro item e mantém a ordem (os seguintes não passam na frente).
 * 3. Recusa do servidor (4xx, ou 5xx com corpo) nunca some: vai para "recusados", com o motivo, até reenviar ou descartar.
 * 4. Uma sincronização por vez; quem pede durante uma em andamento espera a mesma. O que entra na fila durante a
 *    sincronização é preservado: a fila é relida a cada item e só o item processado sai.
 * 5. Envio novo com fila pendente entra no fim da fila (não fura a ordem).
 * 6. Reenvio sem resposta em `prazoMs` conta como sem conexão: a fila não trava esperando uma requisição pendurada. */
export interface Pendente { id: string; caminho: string; corpo: any; descricao: string; criado: string }
export interface Recusado extends Pendente { erro: string; quando: string }

export const CHAVE_FILA = 'campo_fila'
export const CHAVE_RECUSADOS = 'campo_recusados'

interface Armazenamento { getItem(k: string): string | null; setItem(k: string, v: string): void }
let post: (caminho: string, corpo: any) => Promise<any> = async () => { throw new TypeError('fila não configurada') }
let aoMudar: () => void = () => {}
let armazenamento: Armazenamento | null = typeof localStorage !== 'undefined' ? localStorage : null
let prazoMs = 30_000

export function configurarFila(c: { post?: typeof post; aoMudar?: () => void; armazenamento?: Armazenamento; prazoMs?: number }) {
  if (c.post) post = c.post
  if (c.aoMudar) aoMudar = c.aoMudar
  if (c.armazenamento) armazenamento = c.armazenamento
  if (c.prazoMs) prazoMs = c.prazoMs
}

/** Reenvio com prazo: sem resposta a tempo, desiste (sem conexão) e tenta de novo no próximo ciclo. */
function comPrazo<T>(p: Promise<T>): Promise<T> {
  let t: ReturnType<typeof setTimeout>
  const limite = new Promise<never>((_, rej) => { t = setTimeout(() => rej(Object.assign(new Error('sem resposta'), { semConexao: true })), prazoMs) })
  return Promise.race([p, limite]).finally(() => clearTimeout(t))
}

export function lerJSON<T>(chave: string, padrao: T): T {
  try { return JSON.parse(armazenamento?.getItem(chave) ?? '') as T } catch { return padrao }
}
export function gravarJSON(chave: string, valor: unknown) {
  try { armazenamento?.setItem(chave, JSON.stringify(valor)) } catch { /* armazenamento indisponível */ }
}
export const lerFila = () => lerJSON<Pendente[]>(CHAVE_FILA, [])
export const lerRecusados = () => lerJSON<Recusado[]>(CHAVE_RECUSADOS, [])

/** Falha de rede (fetch não completou) ou API inalcançável (proxy devolve 5xx sem corpo). */
export const semConexao = (e: any) => e instanceof TypeError || e?.semConexao === true

function enfileirar(p: Pendente) { gravarJSON(CHAVE_FILA, [...lerFila(), p]); aoMudar() }
function tirarDaFila(id: string) { gravarJSON(CHAVE_FILA, lerFila().filter((x) => x.id !== id)); aoMudar() }
function recusar(p: Pendente, erro: string) {
  gravarJSON(CHAVE_RECUSADOS, [...lerRecusados(), { ...p, erro, quando: new Date().toISOString() }])
  tirarDaFila(p.id)
}

let emAndamento: Promise<void> | null = null
export function sincronizarFila(): Promise<void> {
  if (emAndamento) return emAndamento
  emAndamento = (async () => {
    try {
      for (let p = lerFila()[0]; p; p = lerFila()[0]) {
        try {
          await comPrazo(post(p.caminho, p.corpo))
          tirarDaFila(p.id)
        } catch (e: any) {
          if (semConexao(e)) break
          recusar(p, e?.message || 'recusado pelo servidor')
        }
      }
    } finally { emAndamento = null; aoMudar() }
  })()
  return emAndamento
}

let seq = 0
const novoId = () => `${Date.now()}-${++seq}-${Math.random().toString(36).slice(2, 7)}`

/** Envia já se não houver nada pendente; senão entra no fim da fila. Sem conexão: guarda. Recusa: lança o erro. */
export async function enviarOuGuardar(caminho: string, corpo: any, descricao: string): Promise<{ enviado: boolean; resposta?: any }> {
  const item: Pendente = { id: novoId(), caminho, corpo, descricao, criado: new Date().toISOString() }
  if (!lerFila().length && !emAndamento) {
    try {
      return { enviado: true, resposta: await post(caminho, corpo) }
    } catch (e: any) {
      if (!semConexao(e)) throw e
      enfileirar(item)
      return { enviado: false }
    }
  }
  enfileirar(item)
  await sincronizarFila()
  const recusado = lerRecusados().find((r) => r.id === item.id)
  if (recusado) throw new Error(recusado.erro)
  return { enviado: !lerFila().some((x) => x.id === item.id) }
}

export function reenviarRecusado(id: string) {
  const r = lerRecusados().find((x) => x.id === id)
  if (!r) return
  gravarJSON(CHAVE_RECUSADOS, lerRecusados().filter((x) => x.id !== id))
  const { erro: _e, quando: _q, ...p } = r
  enfileirar(p)
}
/** Tira da fila um registro guardado que o usuário não quer mais enviar. */
export function descartarPendente(id: string) { tirarDaFila(id) }
export function descartarRecusado(id: string) { gravarJSON(CHAVE_RECUSADOS, lerRecusados().filter((x) => x.id !== id)); aoMudar() }
