"""Gerador de cenários para o teste de consistência PL × verificação (usado em test_consistencia.py)."""
import random

GRUPOS = {"holandes": (20, 40, 600), "jersey": (15, 28, 420), "girolando": (10, 25, 520), "gir": (6, 14, 450), "mestica": (5, 14, 470)}
CONJUNTOS = [
    ["silagem_milho", "milho_moido", "farelo_soja", "nucleo_mineral"],
    ["silagem_milho", "milho_moido", "farelo_soja", "ureia", "nucleo_mineral"],
    ["silagem_sorgo", "milho_moido", "farelo_soja", "caroco_algodao", "nucleo_mineral"],
    ["capim_elefante", "milho_moido", "farelo_soja", "polpa_citrica", "nucleo_mineral"],
    ["cana", "silagem_milho", "milho_moido", "farelo_soja", "ureia", "nucleo_mineral"],
    ["braquiaria", "milho_moido", "farelo_soja", "nucleo_mineral"],
    ["silagem_milho", "farelo_trigo", "polpa_citrica", "farelo_soja", "nucleo_mineral"],
    None,  # todos os alimentos
]


def cenarios(n: int, semente: int = 7) -> list[tuple[dict, list[str] | None]]:
    rnd = random.Random(semente)
    out = []
    for _ in range(n):
        grupo = rnd.choice(list(GRUPOS))
        lmin, lmax, pv = GRUPOS[grupo]
        fatos = {"lote.grupo_genetico": grupo, "lote.sistema": rnd.choice(["confinado", "semiconfinado", "pasto"]),
                 "lote.pv": pv + rnd.choice([-60, 0, 60]), "lote.gordura": rnd.choice([3.3, 3.7, 4.2]),
                 "lote.proteina": rnd.choice([3.0, 3.2, 3.4]), "lote.fracao_primiparas": rnd.choice([0, 0.3, 1.0]),
                 "lote.ecc": rnd.choice([2.25, 2.75, 3.25, 3.75]), "lote.dias_gestacao": rnd.choice([0, 0, 120, 220])}
        if rnd.random() < 0.15:
            fatos.update({"lote.estado": "seca", "lote.dias_para_parto": rnd.choice([10, 40]),
                          "lote.dias_gestacao": rnd.choice([230, 260])})
        else:
            fatos.update({"lote.estado": "lactacao", "lote.del": rnd.choice([5, 15, 40, 90, 150, 250]),
                          "lote.leite": round(rnd.uniform(lmin, lmax), 1)})
        if fatos["lote.sistema"] == "pasto":
            fatos.update({"lote.distancia_km": rnd.choice([0.5, 2.0, 3.5]), "lote.relevo": rnd.choice(["plano", "acidentado"])})
        out.append((fatos, rnd.choice(CONJUNTOS)))
    return out
