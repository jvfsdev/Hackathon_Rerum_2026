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
    pv: float = 500
    del_ref: float | None = None
    dias_para_parto_ref: float | None = None
    dias_gestacao_ref: float | None = 0
    fracao_primiparas: float | None = None
    ecc: float | None = None
    distancia_km: float | None = None
    relevo: str | None = None
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


class RegistroIn(BaseModel):
    data: date
    valores: dict[str, float]
    metodo: str | None = None


class EventoIn(BaseModel):
    data_hora: datetime
    tipo: str
    descricao: str = ""


class ConsultaIn(BaseModel):
    fatos: dict[str, Any] = {}
    itens: list[ItemDieta] | None = None


class RespostaIn(BaseModel):
    fato: str
    valor: Any = None
    nao_sei: bool = False


class AlertaUpdate(BaseModel):
    status_usuario: str


class ParametroUpdate(BaseModel):
    valor: float
    motivo: str = ""
