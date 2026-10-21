"""API do sistema especialista de dietas por lote (Hackathon UFJF 2026, T2)."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import base, fazendas, inferencia
from .db.models import criar_tabelas

app = FastAPI(title="Leite por Lote — Sistema Especialista", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                   allow_methods=["*"], allow_headers=["*"])
app.include_router(fazendas.router)
app.include_router(inferencia.router)
app.include_router(base.router)


@app.on_event("startup")
def iniciar():
    criar_tabelas()


@app.get("/")
def raiz():
    return {"sistema": "Leite por Lote", "docs": "/docs"}
