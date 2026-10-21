"""Modelos persistidos (SQLite via SQLModel)."""
from datetime import date, datetime
from pathlib import Path

from pydantic import NaiveDatetime
from sqlmodel import JSON, Column, Field, Session, SQLModel, create_engine

DB_PATH = Path(__file__).resolve().parents[2] / "leite.db"
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})


class Fazenda(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    nome: str
    municipio: str = ""
    porte: str = "medio"                 # pequeno | medio | grande
    preco_leite: float = 2.45            # R$/L
    preco_concentrado: float = 1.90      # R$/kg
    latitude: float | None = None
    longitude: float | None = None


class Lote(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    fazenda_id: int = Field(foreign_key="fazenda.id")
    nome: str
    finalidade: str = ""
    estado: str = "lactacao"             # lactacao | seca
    sistema: str = "confinado"           # confinado | semiconfinado | pasto
    grupo_genetico: str = "girolando"
    n_vacas: int = 20
    pv: float = 500
    data_ref: date = Field(default_factory=date.today)  # DEL e dias de gestação valem nesta data e avançam com o tempo
    del_ref: float | None = 120
    dias_para_parto_ref: float | None = None
    dias_gestacao_ref: float | None = 0
    fracao_primiparas: float | None = 0.3
    ecc: float | None = None
    distancia_km: float | None = None
    relevo: str | None = None
    leite: float | None = None           # kg/vaca/dia de referência (o diário vem dos registros)
    gordura: float | None = 3.5
    proteina: float | None = 3.2
    k_curva: float | None = None         # escala da curva de lactação ajustada à fazenda


class Dieta(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    lote_id: int = Field(foreign_key="lote.id")
    versao: int = 1
    itens: list = Field(default_factory=list, sa_column=Column(JSON))   # [{alimento: id, kg_mn}]
    origem: str = "usuario"              # usuario | pl
    motivo: str = ""
    inicio: date = Field(default_factory=date.today)
    ativa: bool = True
    ms_silagem_ref: float | None = None  # MS da silagem usada na formulação
    parecer: dict | None = Field(default=None, sa_column=Column(JSON))


class Registro(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    lote_id: int = Field(foreign_key="lote.id", index=True)
    data: date = Field(index=True)
    indicador: str                        # vacas, litros, concentrado_kg_vaca, sobras_pct, ms_silagem, ecc, ...
    valor: float | None = None
    texto: str | None = None
    metodo: str | None = None
    confianca: str = "medido"


class Evento(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    lote_id: int = Field(foreign_key="lote.id", index=True)
    data_hora: NaiveDatetime
    tipo: str                             # troca_volumoso | silo_novo | movimentacao | correcao_ms | mudanca_concentrado
    descricao: str = ""


class AlertaDB(SQLModel, table=True):
    __tablename__ = "alerta"
    id: int | None = Field(default=None, primary_key=True)
    lote_id: int = Field(foreign_key="lote.id", index=True)
    data: date = Field(index=True)
    regra: str
    modulo: str = ""
    nivel: str
    titulo: str
    causa: str = ""
    acao: str = ""
    categoria: str = ""
    cf: float = 1.0
    fonte: str = ""
    forca: str = ""
    status: str = "ativo"                 # ativo | suprimido
    nota: str | None = None
    status_usuario: str = "novo"          # novo | visto | aceito | rejeitado
    sessao_id: int | None = None


class SessaoInferencia(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    lote_id: int | None = Field(default=None, foreign_key="lote.id")
    tipo: str                             # avaliacao | formulacao | acompanhamento | consulta
    kb_version: str
    criado_em: NaiveDatetime = Field(default_factory=datetime.now)
    data_ref: date | None = None
    resultado: dict = Field(default_factory=dict, sa_column=Column(JSON))


def criar_tabelas():
    SQLModel.metadata.create_all(engine)


def sessao() -> Session:
    return Session(engine)
