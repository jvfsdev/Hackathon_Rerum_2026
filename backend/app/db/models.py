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
    # bonificação/penalização do laticínio por qualidade: {parametro: [{"min": x|None, "max": y|None, "rs_l": z}]}
    bonificacao: dict = Field(default_factory=dict, sa_column=Column(JSON))


class AlimentoFazenda(SQLModel, table=True):
    """Insumo cadastrado pela fazenda (complementa os alimentos da base de conhecimento). Composição em % da MS."""
    id: int | None = Field(default=None, primary_key=True)
    fazenda_id: int = Field(foreign_key="fazenda.id", index=True)
    codigo: str = Field(index=True, unique=True)   # "f{fazenda}_{slug}" — nunca colide com os ids da base
    nome: str
    tipo: str                                       # volumoso | concentrado | ureia | mineral
    ms: float
    pb: float = 0
    fdn: float = 0
    ndt: float = 0
    ee: float = 0
    mm: float = 0
    fdnd: float | None = None                       # digestibilidade da FDN (% da FDN), quando analisada
    ca: float | None = None                         # minerais em % da MS (opcionais; Na/K/Cl/S permitem a DCAD)
    p: float | None = None
    mg: float | None = None
    k: float | None = None
    na: float | None = None
    cl: float | None = None
    s: float | None = None
    pastejo: bool = False
    max_pct_ms: float | None = None
    min_kg_ms: float | None = None
    max_kg_ms: float | None = None
    origem_dado: str = "tabela"                     # laboratorio | tabela | estimado (define o CF)
    fonte: str = ""
    ativo: bool = True
    criado_em: NaiveDatetime = Field(default_factory=datetime.now)


class PrecoAlimento(SQLModel, table=True):
    """Histórico de preços da fazenda. O preço vigente é o registro mais recente de cada item.
    Itens: id de alimento de foods.yaml, ou "leite" (R$/L) e "concentrado" (R$/kg da mistura usada no cocho)."""
    id: int | None = Field(default=None, primary_key=True)
    fazenda_id: int = Field(foreign_key="fazenda.id", index=True)
    item: str = Field(index=True)
    preco: float                          # R$/kg de matéria natural (leite: R$/L)
    data: date = Field(default_factory=date.today)
    fonte: str = ""                       # ex.: "nota fiscal", "cotação cooperativa", "Cepea"
    criado_em: NaiveDatetime = Field(default_factory=datetime.now)


class PrecoReferencia(SQLModel, table=True):
    """Cotação de referência coletada automaticamente de fonte pública (Cepea, Conab…). Uma linha por item,
    fonte e data da cotação; o preço vigente é o da cotação mais recente. Vale enquanto a fazenda não informa o seu."""
    id: int | None = Field(default=None, primary_key=True)
    item: str = Field(index=True)          # id do alimento da base ou "leite"
    preco: float                           # convertido para R$/kg de matéria natural (leite: R$/L)
    valor_original: float
    unidade_original: str                  # ex.: "R$/saca 60 kg"
    praca: str = ""                        # praça/UF da cotação
    data_cotacao: date = Field(index=True)
    fonte: str
    url: str = ""
    coletado_em: NaiveDatetime = Field(default_factory=datetime.now)


class ColetaPrecos(SQLModel, table=True):
    """Registro de cada execução da coleta (para mostrar status e decidir a próxima)."""
    id: int | None = Field(default=None, primary_key=True)
    inicio: NaiveDatetime = Field(default_factory=datetime.now)
    resultado: dict = Field(default_factory=dict, sa_column=Column(JSON))   # {fonte: {"ok": bool, "itens": n, "erro": str}}


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
    forrageira: str | None = None        # mombaca | tanzania | decumbens | marandu | outra (lotes a pasto)
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
    """Episódio de alerta: um problema (regra × lote) do momento em que aparece até ser resolvido.
    Enquanto a condição continua, o episódio só é atualizado (ocorrências, agravamento)."""
    __tablename__ = "alerta"
    id: int | None = Field(default=None, primary_key=True)
    lote_id: int = Field(foreign_key="lote.id", index=True)
    regra: str = Field(index=True)          # regra que sustenta o episódio agora (pode mudar com o grau do problema)
    problema: str = Field(default="", index=True)   # chave do episódio; padrão = id da regra
    modulo: str = ""
    origem: str = "acompanhamento"        # acompanhamento | verificacao (dieta ativa)
    nivel: str
    titulo: str
    causa: str = ""
    acao: str = ""
    categoria: str = ""
    cf: float = 1.0
    fonte: str = ""
    forca: str = ""
    suprimido: bool = False               # condição presente, mas uma meta-regra suprimiu o aviso
    nota: str | None = None
    estado: str = "aberto"                # aberto | aceito | recusado | resolvido | expirado
    aberto_em: date = Field(index=True)
    ultima_ocorrencia: date
    ocorrencias: int = 1
    estado_em: date | None = None
    resolucao: str | None = None
    sessao_id: int | None = None
    contexto: list = Field(default_factory=list, sa_column=Column(JSON))   # fatos de entrada que sustentaram o alerta


class HistoricoAlerta(SQLModel, table=True):
    """Linha do tempo de cada episódio: aberto, agravado, aceito, ação registrada, recusado, resolvido, expirado."""
    id: int | None = Field(default=None, primary_key=True)
    alerta_id: int = Field(foreign_key="alerta.id", index=True)
    lote_id: int = Field(foreign_key="lote.id", index=True)
    data_hora: NaiveDatetime
    tipo: str
    descricao: str = ""
    automatico: bool = True               # False = ação do usuário
    ref: dict | None = Field(default=None, sa_column=Column(JSON))   # ex.: {"dieta_id": 7} ou {"evento_id": 3}


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
