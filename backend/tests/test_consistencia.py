"""Contrato formulação × verificação, testado em massa (centenas de perfis de lote × conjuntos de alimentos).

1. Toda dieta "ótima" do PL é aprovada pelas regras de verificação (parecer "adequada").
2. Toda dieta "parcial" só é reprovada pelo que o PL declarou inatingível (energia → VER-01, proteína → VER-02).
3. Com todos os alimentos disponíveis, o PL não fica sem resposta só por energia/proteína.
"""
import pytest

from app import services
from consistencia import cenarios  # tests/ entra no sys.path pelo pytest

TODOS = list(services.kb().alimentos)
DEFICIT_PARA_REGRA = {"energia": "VER-01", "proteina": "VER-02"}
CENARIOS = cenarios(300)


def _reprovacoes(verificacao: dict) -> set[str]:
    """Alertas sobre a composição da dieta (estado do lote, como ECC alto, não depende da dieta formulada)."""
    return {a["regra"] for a in verificacao["alertas"]
            if a["status"] == "ativo" and a["nivel"] != "informativo" and a["categoria"] == "dieta"}


@pytest.mark.parametrize("i", range(len(CENARIOS)))
def test_pl_respeita_a_verificacao(i):
    fatos, alimentos = CENARIOS[i]
    out = services.formular(dict(fatos), alimentos or TODOS)
    status = out["pl"]["status"]
    if status == "otimo":
        v = out["verificacao"]
        assert v["fatos"]["parecer.dieta"]["valor"] == "adequada", (fatos, alimentos, _reprovacoes(v))
    elif status == "parcial":
        permitidas = {DEFICIT_PARA_REGRA[g] for g in out["pl"]["restricoes_violadas"]}
        assert _reprovacoes(out["verificacao"]) <= permitidas, (fatos, alimentos, _reprovacoes(out["verificacao"]))
    else:
        assert status == "inviavel"
        assert not set(out["pl"]["restricoes_violadas"]) <= set(DEFICIT_PARA_REGRA), "deveria ser parcial"
