"""Memória de trabalho: fatos da sessão atual (entradas do usuário + conclusões)."""
from typing import Any

from .cf import combinar
from .facts import Fato


class MemoriaTrabalho:
    def __init__(self):
        self.fatos: dict[str, Fato] = {}
        self.ciclo = 0
        self.disparadas: set[str] = set()   # refração vale para a sessão inteira

    def __contains__(self, nome: str) -> bool:
        return nome in self.fatos

    def get(self, nome: str) -> Fato | None:
        return self.fatos.get(nome)

    def valor(self, nome: str, padrao: Any = None) -> Any:
        f = self.fatos.get(nome)
        return f.valor if f else padrao

    def declarar(self, nome: str, valor: Any, cf: float = 1.0, origem: str = "usuario", nota: str | None = None):
        """Entrada externa (usuário, tabela, medição, sistema)."""
        self.fatos[nome] = Fato(nome, valor, cf, origem, None, self.ciclo, nota)

    def concluir(self, nome: str, valor: Any, cf: float, regra: str) -> str:
        """Conclusão de regra. Retorna o que aconteceu: novo | combinado | mantido | substituido."""
        atual = self.fatos.get(nome)
        if atual is None:
            self.fatos[nome] = Fato(nome, valor, cf, "regra", regra, self.ciclo)
            return "novo"
        if atual.origem != "regra":
            return "mantido"  # valor informado/medido prevalece sobre conclusão
        if atual.valor == valor:
            atual.cf = combinar(atual.cf, cf)
            atual.regra = f"{atual.regra}+{regra}"
            atual.ciclo = self.ciclo
            return "combinado"
        if cf > atual.cf:
            self.fatos[nome] = Fato(nome, valor, cf, "regra", regra, self.ciclo)
            return "substituido"
        return "mantido"

    def to_dict(self) -> dict:
        return {n: f.to_dict() for n, f in sorted(self.fatos.items())}
