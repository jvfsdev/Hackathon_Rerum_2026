"""Contrato dos adaptadores de fonte de preço e conversões de unidade."""
from dataclasses import dataclass
from datetime import date

# Fatores para converter a unidade publicada em R$/kg (ou R$/L para leite).
UNIDADES = {
    "R$/kg": 1.0,
    "R$/L": 1.0,
    "R$/saca 60 kg": 1 / 60,
    "R$/saca 50 kg": 1 / 50,
    "R$/saca 40 kg": 1 / 40,
    "R$/tonelada": 1 / 1000,
    "R$/arroba": 1 / 15,
}


@dataclass
class Cotacao:
    item: str                 # id do alimento da base (ou "leite")
    valor: float              # na unidade publicada pela fonte
    unidade: str              # chave de UNIDADES
    data: date                # data da cotação (não da coleta)
    praca: str = ""
    url: str = ""

    def preco_convertido(self) -> float:
        if self.unidade not in UNIDADES:
            raise ValueError(f"unidade desconhecida: {self.unidade}")
        return self.valor * UNIDADES[self.unidade]


class Fonte:
    """Adaptador de uma fonte pública. `coletar` devolve as cotações mais recentes disponíveis."""
    nome: str = ""
    url: str = ""
    itens: tuple[str, ...] = ()
    frequencia: str = "diária"
    idade_maxima_dias: int = 7      # cotação mais velha que isso (pela data de referência) = desatualizada
    timeout: float = 15.0

    def coletar(self) -> list[Cotacao]:  # pragma: no cover - implementado por cada fonte
        raise NotImplementedError
