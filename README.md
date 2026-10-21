# CochoCerto — sistema especialista de dietas por lote

Hackathon UFJF 2026 (XXVIII Semana da Computação · RERUM), **Tema T2 — Dietas**.

Orienta e acompanha **lotes** de vacas leiteiras: classifica o lote, calcula exigências, verifica a dieta, sugere a dieta de **custo mínimo** e acompanha o dia a dia (produção × curva esperada, cocho, silagem, ECC, laudo do laticínio). Os alertas vêm com causa provável, ação sugerida e explicação **"por quê?/como?"**.

Quem decide é a **base de conhecimento (153 regras de produção com fator de certeza)** + **motor de inferência próprio** (encadeamento progressivo e regressivo, resolução de conflito, CF estilo MYCIN). Não há LLM no sistema: as decisões são determinísticas e auditáveis.

## Rodar (localhost)

Requisitos: Python 3.11+ e Node 20+.

```bash
# API
cd backend
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/python -m app.db.seed            # fazenda demo: 4 lotes, 60 dias de histórico
.venv/bin/uvicorn app.main:app --port 8000

# Interface (outro terminal)
cd frontend
npm install
npm run dev                                 # http://localhost:5173
```

No celular (mesma rede Wi-Fi): `npm run dev:rede` e abra `http://<ip-do-computador>:5173` — a página inicial vira o **modo campo** (registro rápido + avisos, funciona sem conexão e envia depois).

Testes: `cd backend && .venv/bin/pytest -q`, com 453 testes, entre eles 33 casos de resultado conhecido em `backend/tests/cases.yaml`.

## Onde está cada coisa

| Componente do edital | Onde |
|---|---|
| Base de conhecimento (regras, CF, versionada) | `backend/kb/` (YAML + `CHANGELOG.md`) |
| Motor de inferência | `backend/app/engine/` |
| Memória de trabalho | `backend/app/engine/working_memory.py` |
| Módulo de explicação | `backend/app/engine/explain.py` + gavetas "Como?" / "Por que este alerta?" na UI |
| Aquisição de conhecimento | Tela **Base de conhecimento** (modo especialista) + edição dos YAML |
| Interface | `frontend/` (React) |
| Fontes externas | Open-Meteo (clima → ITU), registros diários/laudos |

## Documentação

- [docs/arquitetura.md](docs/arquitetura.md): arquitetura e fluxo.
- [docs/regras.md](docs/regras.md): regras de produção, parâmetros e alimentos (gerado da base).
- [docs/processo-ia.md](docs/processo-ia.md): processo de desenvolvimento com IA.
- [docs/plano.md](docs/plano.md): plano completo.
- Referências de domínio: `dossie.md`, `dados.md`, `Inferências de dados leiteiros por lote.md`.

> Os valores numéricos são referências de literatura para uma prova de conceito e precisam de validação por zootecnista.
