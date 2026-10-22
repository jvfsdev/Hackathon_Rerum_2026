"""Fatos da memória de trabalho."""
from dataclasses import dataclass, field
from typing import Any

ORIGENS_ENTRADA = ("usuario", "tabela", "medido", "padrao", "sistema")


@dataclass
class Fato:
    nome: str
    valor: Any
    cf: float = 1.0
    origem: str = "usuario"          # usuario | tabela | medido | padrao | sistema | regra
    regra: str | None = None         # id da regra que concluiu (origem == "regra")
    ciclo: int = 0                   # recência: ciclo em que entrou na memória
    nota: str | None = None

    def to_dict(self) -> dict:
        return {"nome": self.nome, "valor": self.valor, "cf": round(self.cf, 3), "origem": self.origem,
                "regra": self.regra, "ciclo": self.ciclo, "nota": self.nota}


@dataclass
class Alerta:
    regra: str
    nivel: str                       # critico | atencao | informativo
    titulo: str
    causa: str
    acao: str
    categoria: str
    cf: float
    fonte: str = ""
    forca: str = ""
    titulo_produtor: str = ""        # mesmos fatos em linguagem do produtor (visão "Produtor" da interface)
    causa_produtor: str = ""
    acao_produtor: str = ""
    problema: str = ""               # chave do problema: regras que medem o mesmo problema em graus diferentes
    status: str = "ativo"            # ativo | suprimido
    nota: str | None = None
    ajuste: dict = field(default_factory=dict)   # proposta de mudança na dieta decidida pela regra (ex.: oferta +5%)
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"regra": self.regra, "nivel": self.nivel, "titulo": self.titulo, "causa": self.causa,
                "acao": self.acao, "categoria": self.categoria, "cf": round(self.cf, 3), "fonte": self.fonte,
                "forca": self.forca, "problema": self.problema, "titulo_produtor": self.titulo_produtor,
                "causa_produtor": self.causa_produtor, "acao_produtor": self.acao_produtor, "status": self.status, "nota": self.nota,
                **({"ajuste": self.ajuste} if self.ajuste else {}), **self.extra}
