"""Roda todos os casos de tests/cases.yaml contra a base atual."""
import pytest

from app.engine.casos import carregar_casos, executar_caso
from app.engine.rules_loader import carregar

KB = carregar()


@pytest.mark.parametrize("caso", carregar_casos(), ids=lambda c: c["id"])
def test_caso(caso):
    resultado = executar_caso(caso, KB)
    assert resultado["passou"], "\n".join(resultado["falhas"])
