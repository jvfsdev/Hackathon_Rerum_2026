"""Formulação de dieta de custo mínimo (programação linear).

As metas e restrições vêm das conclusões do motor (fatos pl.*, meta.*, exig.*): o PL é uma ferramenta
chamada pelo sistema especialista, não o sistema especialista. Se for inviável, identifica qual grupo de
restrições impede a solução relaxando um grupo por vez.
"""
from itertools import combinations

import pulp

from ..calc.diet import cnf_alimento, composicao, ell_alimento

GRUPOS = ["consumo", "energia", "proteina", "fibra", "enchimento", "cnf", "gordura", "ureia", "cana"]


def _modelo(alimentos: list[dict], r: dict, ignorar: tuple[str, ...] = ()):
    prob = pulp.LpProblem("dieta_custo_minimo", pulp.LpMinimize)
    x = {a["id"]: prob.add_variable(f"x_{a['id']}", lowBound=0) for a in alimentos}
    total = pulp.lpSum(x.values())
    prob += pulp.lpSum(a["preco_kg_mn"] / (a["ms"] / 100) * x[a["id"]] for a in alimentos)

    def grupo(nome, restricoes):
        if nome not in ignorar:
            for i, c in enumerate(restricoes):
                prob.addConstraint(c, f"{nome}_{i}")

    grupo("consumo", [total >= r["cms"] - r["folga_ms"], total <= r["cms"] + r["folga_ms"]])
    grupo("energia", [pulp.lpSum(ell_alimento(a) * x[a["id"]] for a in alimentos) >= r["ell_min"]])
    grupo("proteina", [pulp.lpSum((a.get("pb", 0) - r["pb_min"]) * x[a["id"]] for a in alimentos) >= 0,
                       pulp.lpSum((a.get("pb", 0) - r["pb_max"]) * x[a["id"]] for a in alimentos) <= 0])
    grupo("fibra", [pulp.lpSum((a.get("fdn", 0) - r["fdn_min"]) * x[a["id"]] for a in alimentos) >= 0,
                    pulp.lpSum(a.get("fdn", 0) * x[a["id"]] for a in alimentos if a["tipo"] == "volumoso")
                    - r["fdnf_min"] * total >= 0])
    grupo("enchimento", [pulp.lpSum(a.get("fdn", 0) / 100 * x[a["id"]] for a in alimentos) <= r["fdn_max_kg"]])
    grupo("cnf", [pulp.lpSum((cnf_alimento(a) - r["cnf_max"]) * x[a["id"]] for a in alimentos) <= 0])
    grupo("gordura", [pulp.lpSum((a.get("ee", 0) - r["ee_max"]) * x[a["id"]] for a in alimentos) <= 0])
    grupo("ureia", [pulp.lpSum(100 * x[a["id"]] for a in alimentos if a["tipo"] == "ureia") - r["ureia_max"] * total <= 0])
    if r.get("cana_max_pct_volumoso") is not None:   # FOR-05: cana não pode ser o único volumoso
        volumoso = pulp.lpSum(x[a["id"]] for a in alimentos if a["tipo"] == "volumoso")
        grupo("cana", [pulp.lpSum(x[a["id"]] for a in alimentos if a["id"] == "cana")
                       - r["cana_max_pct_volumoso"] / 100 * volumoso <= 0])
    # limites de inclusão de cada alimento: nunca relaxados
    for a in alimentos:
        if r.get("excluir_pastejo") and a.get("pastejo"):   # FOR-06: lote confinado não pasteja
            prob.addConstraint(x[a["id"]] <= 0, f"sem_pastejo_{a['id']}")
        if a.get("max_pct_ms") is not None:
            prob += x[a["id"]] <= a["max_pct_ms"] / 100 * total, f"inclusao_max_{a['id']}"
        if a.get("min_kg_ms") is not None:
            prob += x[a["id"]] >= a["min_kg_ms"], f"inclusao_min_{a['id']}"
        if a.get("max_kg_ms") is not None:
            prob += x[a["id"]] <= a["max_kg_ms"], f"inclusao_maxkg_{a['id']}"
    return prob, x


def _resolver(prob) -> str:
    stats = prob.solve(pulp.HiGHS(msg=False))
    return "Optimal" if stats.status == pulp.LpSolveStatus.Optimal else stats.status.name


def diagnosticar(alimentos: list[dict], restricoes: dict) -> list[str]:
    """Menor conjunto de grupos cuja retirada torna o PL viável (um grupo; senão pares; senão trios)."""
    for tamanho in (1, 2, 3):
        violadas = set()
        for grupos in combinations(GRUPOS, tamanho):
            p, _ = _modelo(alimentos, restricoes, ignorar=grupos)
            if _resolver(p) == "Optimal":
                violadas.update(grupos)
        if violadas:
            return [g for g in GRUPOS if g in violadas]
    return ["combinacao"]


def formular(alimentos: list[dict], restricoes: dict) -> dict:
    """alimentos: dicionários de foods.yaml (com preço); restricoes: cms, folga_ms, ell_min, pb_min, pb_max,
    fdn_min, fdnf_min, cnf_max, ee_max, ureia_max, fdn_max_kg e, opcionais, cana_max_pct_volumoso e excluir_pastejo."""
    prob, x = _modelo(alimentos, restricoes)
    if _resolver(prob) != "Optimal":
        return {"status": "inviavel", "restricoes_violadas": diagnosticar(alimentos, restricoes), "restricoes": restricoes}
    porid = {a["id"]: a for a in alimentos}
    itens = []
    for aid, var in x.items():
        kg_ms = var.value() or 0.0
        if kg_ms > 1e-4:
            a = porid[aid]
            itens.append({"alimento": a, "kg_ms": kg_ms, "kg_mn": kg_ms / (a["ms"] / 100)})
    return {"status": "otimo", "custo": pulp.value(prob.objective), "itens": itens,
            "composicao": composicao([{"alimento": i["alimento"], "kg_mn": i["kg_mn"]} for i in itens]),
            "restricoes_violadas": [], "restricoes": restricoes}
