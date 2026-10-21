"""API do sistema especialista de dietas por lote (Hackathon UFJF 2026, T2)."""
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api import base, fazendas, inferencia
from .db.models import criar_tabelas
from .services import EntradaInvalida

app = FastAPI(title="CochoCerto — Sistema Especialista", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                   allow_methods=["*"], allow_headers=["*"])
app.include_router(fazendas.router)
app.include_router(inferencia.router)
app.include_router(base.router)


@app.exception_handler(EntradaInvalida)
def entrada_invalida(_: Request, erro: EntradaInvalida):
    return JSONResponse(status_code=422, content={"detail": str(erro)})


@app.on_event("startup")
def iniciar():
    criar_tabelas()
    if os.environ.get("LEITE_SEM_COLETA") != "1":     # coleta diária de preços de referência (fontes públicas)
        from .db.models import sessao
        from .referencias import fontes  # noqa: F401 — registra as fontes
        from .referencias.coletor import iniciar_agendador
        iniciar_agendador(sessao)


@app.get("/")
def raiz():
    return {"sistema": "CochoCerto", "docs": "/docs"}
