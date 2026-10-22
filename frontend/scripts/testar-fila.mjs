// Testa as regras da fila offline (src/lib/fila.ts) com um servidor simulado. Uso: node scripts/testar-fila.mjs
import { build } from 'esbuild'
import assert from 'node:assert/strict'

const { outputFiles } = await build({ entryPoints: ['src/lib/fila.ts'], bundle: true, write: false, format: 'esm', platform: 'node' })
const F = await import('data:text/javascript;base64,' + Buffer.from(outputFiles[0].text).toString('base64'))

const memoria = () => { const m = new Map(); return { getItem: (k) => m.get(k) ?? null, setItem: (k, v) => m.set(k, v) } }
const semRede = () => new TypeError('Failed to fetch')
const recusa = (msg) => Object.assign(new Error(msg), { status: 422 })
let passou = 0
async function caso(nome, fn) { await fn(); passou++; console.log('✓', nome) }

await caso('sem conexão: para no primeiro item e mantém a ordem', async () => {
  const recebidos = []; let online = false
  F.configurarFila({ armazenamento: memoria(), post: async (c, b) => { if (!online) throw semRede(); recebidos.push(b.n) } })
  for (const n of [1, 2, 3]) assert.deepEqual(await F.enviarOuGuardar('/x', { n }, `r${n}`), { enviado: false })
  assert.deepEqual(F.lerFila().map((p) => p.corpo.n), [1, 2, 3])
  online = true
  await F.sincronizarFila()
  assert.deepEqual(recebidos, [1, 2, 3])
  assert.equal(F.lerFila().length, 0)
})

await caso('a rede cai no meio: o restante fica na fila, na ordem, sem pular itens', async () => {
  const recebidos = []
  F.configurarFila({ armazenamento: memoria(), post: async () => { throw semRede() } })
  for (const n of [1, 2, 3, 4]) await F.enviarOuGuardar('/x', { n }, '')
  let i = 0
  F.configurarFila({ post: async (c, b) => { i++; if (i === 2) throw semRede(); recebidos.push(b.n) } })
  await F.sincronizarFila()                                   // envia 1, cai no 2: para
  assert.deepEqual(recebidos, [1])
  assert.deepEqual(F.lerFila().map((p) => p.corpo.n), [2, 3, 4])
  await F.sincronizarFila()
  assert.deepEqual(recebidos, [1, 2, 3, 4])
})

await caso('recusa do servidor (4xx) não some: vai para recusados com o motivo, e os seguintes continuam', async () => {
  const recebidos = []
  F.configurarFila({ armazenamento: memoria(), post: async () => { throw semRede() } })
  for (const n of [1, 2, 3]) await F.enviarOuGuardar('/x', { n }, `r${n}`)
  F.configurarFila({ post: async (c, b) => { if (b.n === 2) throw recusa('vacas = 0 fora da faixa'); recebidos.push(b.n) } })
  await F.sincronizarFila()
  assert.deepEqual(recebidos, [1, 3])
  assert.equal(F.lerFila().length, 0)
  const [r] = F.lerRecusados()
  assert.equal(r.corpo.n, 2); assert.equal(r.erro, 'vacas = 0 fora da faixa')
  F.reenviarRecusado(r.id)                                   // corrigido no servidor: tentar de novo
  F.configurarFila({ post: async (c, b) => { recebidos.push(b.n) } })
  await F.sincronizarFila()
  assert.deepEqual(recebidos, [1, 3, 2]); assert.equal(F.lerRecusados().length, 0)
})

await caso('registro que entra na fila durante a sincronização não é sobrescrito', async () => {
  const recebidos = []; let liberar
  F.configurarFila({ armazenamento: memoria(), post: async () => { throw semRede() } })
  await F.enviarOuGuardar('/x', { n: 1 }, '')
  F.configurarFila({ post: async (c, b) => { if (b.n === 1) await new Promise((r) => (liberar = r)); recebidos.push(b.n) } })
  const sync = F.sincronizarFila()
  await new Promise((r) => setTimeout(r, 5))
  const novo = F.enviarOuGuardar('/x', { n: 2 }, '')          // chega durante a sincronização: entra no fim
  await new Promise((r) => setTimeout(r, 5))
  assert.deepEqual(F.lerFila().map((p) => p.corpo.n), [1, 2])
  liberar(); await sync
  assert.deepEqual(await novo, { enviado: true })
  assert.deepEqual(recebidos, [1, 2]); assert.equal(F.lerFila().length, 0)
})

await caso('intervalo, evento online e botão ao mesmo tempo: uma sincronização só, sem envio duplicado', async () => {
  const recebidos = []
  F.configurarFila({ armazenamento: memoria(), post: async () => { throw semRede() } })
  for (const n of [1, 2, 3]) await F.enviarOuGuardar('/x', { n }, '')
  F.configurarFila({ post: async (c, b) => { await new Promise((r) => setTimeout(r, 3)); recebidos.push(b.n) } })
  const a = F.sincronizarFila(), b = F.sincronizarFila(), c = F.sincronizarFila()
  assert.equal(a, b); assert.equal(b, c)
  await Promise.all([a, b, c])
  assert.deepEqual(recebidos, [1, 2, 3])
})

await caso('envio novo com fila pendente não passa na frente dos antigos', async () => {
  const recebidos = []
  F.configurarFila({ armazenamento: memoria(), post: async () => { throw semRede() } })
  await F.enviarOuGuardar('/x', { n: 1 }, '')
  F.configurarFila({ post: async (c, b) => { recebidos.push(b.n) } })
  assert.deepEqual(await F.enviarOuGuardar('/x', { n: 2 }, ''), { enviado: true })
  assert.deepEqual(recebidos, [1, 2])
})

await caso('envio direto recusado aparece como erro na hora (não entra na fila)', async () => {
  F.configurarFila({ armazenamento: memoria(), post: async () => { throw recusa('litros fora da faixa') } })
  await assert.rejects(F.enviarOuGuardar('/x', { n: 1 }, ''), /litros fora da faixa/)
  assert.equal(F.lerFila().length, 0)
})

await caso('reenvio pendurado (sem resposta) não trava a fila: desiste no prazo e envia no ciclo seguinte', async () => {
  const recebidos = []
  F.configurarFila({ armazenamento: memoria(), prazoMs: 30, post: async () => { throw semRede() } })
  await F.enviarOuGuardar('/x', { n: 1 }, '')
  F.configurarFila({ post: () => new Promise(() => {}) })     // a requisição nunca responde
  await F.sincronizarFila()
  assert.deepEqual(F.lerFila().map((p) => p.corpo.n), [1])   // continua guardado, e a sincronização terminou
  F.configurarFila({ post: async (c, b) => { recebidos.push(b.n) } })
  await F.sincronizarFila()
  assert.deepEqual(recebidos, [1])
  assert.equal(F.lerFila().length, 0)
})

await caso('descartar um registro guardado tira só ele da fila', async () => {
  F.configurarFila({ armazenamento: memoria(), post: async () => { throw semRede() } })
  for (const n of [1, 2]) await F.enviarOuGuardar('/x', { n }, '')
  F.descartarPendente(F.lerFila()[0].id)
  assert.deepEqual(F.lerFila().map((p) => p.corpo.n), [2])
})

console.log(`\n${passou} casos da fila offline passaram`)
