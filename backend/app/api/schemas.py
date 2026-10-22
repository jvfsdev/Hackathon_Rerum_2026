"""Contrato da API (fonte da verdade para o frontend)."""
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel


class ItemDieta(BaseModel):
    alimento: str
    kg_mn: float


class LoteIn(BaseModel):
    fazenda_id: int = 1
    nome: str
    finalidade: str = ""
    estado: str = "lactacao"
    sistema: str = "confinado"
    grupo_genetico: str = "girolando"
    n_vacas: int = 20
    pv: float                  # sem padrão: peso vivo entra em quase toda equação e não há valor seguro
    del_ref: float | None = None
    dias_para_parto_ref: float | None = None
    dias_gestacao_ref: float | None = 0
    fracao_primiparas: float | None = None
    ecc: float | None = None
    distancia_km: float | None = None
    relevo: str | None = None
    forrageira: str | None = None
    leite: float | None = None
    gordura: float | None = None
    proteina: float | None = None


class AvaliarIn(BaseModel):
    fatos: dict[str, Any] = {}
    itens: list[ItemDieta] | None = None
    padroes: list[str] = []


class AvaliarLoteIn(BaseModel):
    itens: list[ItemDieta] | None = None


class FormularIn(BaseModel):
    alimentos: list[str]
    precos: dict[str, float] | None = None


class DietaIn(BaseModel):
    itens: list[ItemDieta]
    motivo: str = ""
    origem: str = "usuario"
    alerta_id: int | None = None      # alerta aceito que levou a esta ação
    gradual: bool = True              # deixar as regras TRN decidirem a troca gradual a partir da versão anterior


class RegistroIn(BaseModel):
    data: date
    valores: dict[str, float]
    metodo: str | None = None
    alerta_id: int | None = None
    somar: list[str] = []             # indicadores somados ao valor já gravado no dia (ex.: litros da 2ª ordenha)


class EventoIn(BaseModel):
    data_hora: datetime
    tipo: str
    descricao: str = ""
    alerta_id: int | None = None


class ConsultaIn(BaseModel):
    fatos: dict[str, Any] = {}
    itens: list[ItemDieta] | None = None


class RespostaIn(BaseModel):
    fato: str
    valor: Any = None
    nao_sei: bool = False


class AceitarIn(BaseModel):
    observacao: str = ""


class RecusarIn(BaseModel):
    motivo: str


class ParametroUpdate(BaseModel):
    valor: float | str
    motivo: str = ""


class PrecosIn(BaseModel):
    precos: dict[str, float]          # id do alimento (R$/kg MN), "leite" (R$/L) ou "concentrado" (R$/kg)
    fonte: str = ""
    data: date | None = None


class AlimentoIn(BaseModel):
    nome: str
    tipo: str                         # volumoso | concentrado | ureia | mineral
    ms: float                         # % da matéria natural
    pb: float = 0                     # % da MS
    fdn: float = 0
    ndt: float = 0
    ee: float = 0
    mm: float = 0
    fdnd: float | None = None         # digestibilidade da FDN (% da FDN), opcional
    ca: float | None = None           # minerais em % da MS, opcionais
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
    origem_dado: str = "tabela"       # laboratorio | tabela | estimado
    fonte: str = ""
    preco_kg_mn: float | None = None  # obrigatório no cadastro


class BonificacaoIn(BaseModel):
    tabela: dict[str, list[dict]]      # {"ccs": [{"min": null, "max": 200, "rs_l": 0.03}, ...], "cbt": [...], ...}


class ImportacaoIn(BaseModel):
    conteudo: str                      # texto do CSV (separador ; , ou tab; decimal com vírgula ou ponto)
    confirmar: bool = False            # False = só prévia


class SimularIn(BaseModel):
    itens: list[ItemDieta]             # dieta do cenário (kg MN/vaca/dia)
    leite: float | None = None         # meta de leite do cenário (kg/vaca/dia); padrão = o atual do lote
    preco_leite: float | None = None   # R$/L do cenário
    precos: dict[str, float] | None = None   # preços de alimentos do cenário (R$/kg MN)


class AjusteIn(BaseModel):
    itens: list[ItemDieta] | None = None     # dieta a ajustar; padrão = dieta ativa


class SensibilidadeIn(BaseModel):
    alimentos: list[str]


class MovimentoEstoqueIn(BaseModel):
    item: str
    tipo: str                          # contagem | entrada
    kg: float                          # kg de matéria natural
    data: date | None = None
    obs: str = ""

