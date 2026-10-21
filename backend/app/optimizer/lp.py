"""Formulação de dieta de custo mínimo (programação linear).

As metas e restrições vêm das conclusões do motor (fatos pl.*, meta.*, exig.*): o PL é uma ferramenta
chamada pelo sistema especialista, não o sistema especialista. Se for inviável, identifica qual grupo de
restrições impede a solução relaxando um grupo por vez.

Contrato com a verificação (VER): cada restrição aqui é a mesma definição numérica que a regra de verificação
correspondente usa, apertada por `margem` para a dieta continuar aprovada depois de arredondada. O teste
tests/test_consistencia.py garante que nenhuma dieta ótima seja reprovada pelas regras.
"""
from itertools import combinations

import pulp

from ..calc.diet import cnf_alimento, composicao, dcad_meq_kg, ell_alimento

GRUPOS = ["consumo", "energia", "excesso_energia", "proteina", "fibra", "enchimento", "cnf", "gordura", "ureia", "cana", "dcad"]


# Penalidade das metas flexíveis (melhor dieta possível): muito acima de qualquer custo de alimento,
# então o solver só aceita déficit quando não há outro jeito.
PENALIDADE_MCAL = 100.0       # R$ por Mcal de ELl faltante
PENALIDADE_PB = 10.0          # R$ por (p.p. de PB × kg MS) faltante


def _modelo(alimentos: list[dict], r: dict, ignorar: tuple[str, ...] = (), metas_flexiveis: bool = False):
    prob = pulp.LpProblem("dieta_custo_minimo", pulp.LpMinimize)
    x = {a["id"]: prob.add_variable(f"x_{a['id']}", lowBound=0) for a in alimentos}
    total = pulp.lpSum(x.values())
    custo = pulp.lpSum(a["preco_kg_mn"] / (a["ms"] / 100) * x[a["id"]] for a in alimentos)
    folga_e = prob.add_variable("deficit_energia", lowBound=0) if metas_flexiveis else 0
    folga_p = prob.add_variable("deficit_proteina", lowBound=0) if metas_flexiveis else 0
    prob += custo + (PENALIDADE_MCAL * folga_e + PENALIDADE_PB * folga_p if metas_flexiveis else 0)

    def grupo(nome, restricoes):
        if nome not in ignorar:
            for i, c in enumerate(restricoes):
                prob.addConstraint(c, f"{nome}_{i}")

    m = r.get("margem", 0.0)
    mais, menos = 1 + m, 1 - m                       # aperta mínimos para cima e máximos para baixo
    energia = pulp.lpSum(ell_alimento(a) * x[a["id"]] for a in alimentos)
    fdn_kg = pulp.lpSum(a.get("fdn", 0) / 100 * x[a["id"]] for a in alimentos)
    # VER-06/06B: oferta entre os fatores do CMS. Em lactação a verificação usa CMS = min(equação, teto de fibra),
    # então o mínimo é uma disjunção: come ≥ 95% do CMS da equação OU enche o rúmen (FDN ≥ 95% do teto).
    if r.get("teto_fibra_aplica"):
        enche = prob.add_variable("limitado_pelo_rumen", cat="Binary")
        grupo("consumo", [total >= r["ms_min"] * mais - r["ms_min"] * mais * enche,
                          fdn_kg >= r["fdn_max_kg"] * r["fator_ms_min"] * mais - r["fdn_max_kg"] * (1 - enche),
                          total <= r["ms_max"] * menos])
    else:
        grupo("consumo", [total >= r["ms_min"] * mais, total <= r["ms_max"] * menos])
    # VER-01: energia consumida = min(MS, CMS) × densidade ≥ mínimo. Equivale, de forma linear, a
    #   Σ ELl·x ≥ E   (quando MS ≤ CMS)   e   CMS·Σ ELl·x ≥ E·Σx   (quando MS > CMS)
    grupo("energia", [energia + folga_e >= r["ell_min"] * mais,
                      r["cms"] * (energia + folga_e) - r["ell_min"] * mais * total >= 0])
    # VER-10: energia consumida ≤ teto (Σ ELl·x ≥ consumida, então limitar Σ ELl·x é suficiente)
    if r.get("ell_max") is not None:
        grupo("excesso_energia", [energia <= r["ell_max"] * menos])
    # VER-02/02B: PB entre o alvo e o máximo sem desperdício
    grupo("proteina", [pulp.lpSum((a.get("pb", 0) - r["pb_min"] * mais) * x[a["id"]] for a in alimentos) + folga_p >= 0,
                       pulp.lpSum((a.get("pb", 0) - r["pb_max"] * menos) * x[a["id"]] for a in alimentos) <= 0])
    # VER-03/03C: FDN e FDN de forragem mínimos (com FDNf ≥ mínimo, a meta de FDN não sobe pela EXG-05)
    grupo("fibra", [pulp.lpSum((a.get("fdn", 0) - r["fdn_min"] * mais) * x[a["id"]] for a in alimentos) >= 0,
                    pulp.lpSum(a.get("fdn", 0) * x[a["id"]] for a in alimentos if a["tipo"] == "volumoso")
                    - r["fdnf_min"] * mais * total >= 0])
    # EXG-01D: consumo de FDN ≤ 1,25% do PV (garante MS ≤ teto de fibra, o CMS que a verificação usa)
    grupo("enchimento", [fdn_kg <= r["fdn_max_kg"] * menos])
    # VER-03B, VER-05, VER-04
    grupo("cnf", [pulp.lpSum((cnf_alimento(a) - r["cnf_max"] * menos) * x[a["id"]] for a in alimentos) <= 0])
    grupo("gordura", [pulp.lpSum((a.get("ee", 0) - r["ee_max"] * menos) * x[a["id"]] for a in alimentos) <= 0])
    grupo("ureia", [pulp.lpSum(100 * x[a["id"]] for a in alimentos if a["tipo"] == "ureia")
                    - r["ureia_max"] * menos * total <= 0])
    # VER-15: DCAD do pré-parto (linear: média ponderada da DCAD de cada alimento). Só quando todos têm Na/K/Cl/S,
    # a mesma condição em que a verificação consegue calculá-la.
    if r.get("dcad_max") is not None and all(all(a.get(m) is not None for m in ("na", "k", "cl", "s")) for a in alimentos):
        folga = 5.0   # mEq/kg de margem para a dieta arredondada continuar abaixo do limite
        grupo("dcad", [pulp.lpSum((dcad_meq_kg(a["na"], a["k"], a["cl"], a["s"]) - (r["dcad_max"] - folga)) * x[a["id"]]
                                  for a in alimentos) <= 0])
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
    return prob, x, (folga_e, folga_p)


def _resolver(prob) -> str:
    stats = prob.solve(pulp.HiGHS(msg=False))
    return "Optimal" if stats.status == pulp.LpSolveStatus.Optimal else stats.status.name


def diagnosticar(alimentos: list[dict], restricoes: dict) -> list[str]:
    """Menor conjunto de grupos cuja retirada torna o PL viável (um grupo; senão pares; senão trios)."""
    for tamanho in (1, 2, 3):
        violadas = set()
        for grupos in combinations(GRUPOS, tamanho):
            p, _, _ = _modelo(alimentos, restricoes, ignorar=grupos)
            if _resolver(p) == "Optimal":
                violadas.update(grupos)
        if violadas:
            return [g for g in GRUPOS if g in violadas]
    return ["combinacao"]


METAS_NUTRICIONAIS = {"energia", "proteina"}


def formular(alimentos: list[dict], restricoes: dict) -> dict:
    """alimentos: dicionários de foods.yaml (com preço); restricoes: cms, ms_min, ms_max, fator_ms_min, ell_min,
    pb_min, pb_max, fdn_min, fdnf_min, cnf_max, ee_max, ureia_max, fdn_max_kg, margem, teto_fibra_aplica e, opcionais,
    cana_max_pct_volumoso e excluir_pastejo.

    status: "otimo" (atende tudo), "parcial" (só energia e/ou proteína são inatingíveis com estes alimentos:
    devolve a melhor dieta possível, com o déficit) ou "inviavel" (nenhuma dieta respeita as demais restrições)."""
    prob, x, _ = _modelo(alimentos, restricoes)
    if _resolver(prob) == "Optimal":
        return _saida("otimo", prob, x, alimentos, restricoes, [])
    violadas = diagnosticar(alimentos, restricoes)
    if set(violadas) <= METAS_NUTRICIONAIS:
        prob, x, (folga_e, folga_p) = _modelo(alimentos, restricoes, metas_flexiveis=True)
        if _resolver(prob) == "Optimal":
            out = _saida("parcial", prob, x, alimentos, restricoes, violadas)
            out["deficit"] = {"energia_mcal": folga_e.value() or 0.0,
                              "proteina_pp": (folga_p.value() or 0.0) / max(out["composicao"]["ms_kg"], 1e-9)}
            return out
    return {"status": "inviavel", "restricoes_violadas": violadas, "restricoes": restricoes}


def _saida(status, prob, x, alimentos, restricoes, violadas) -> dict:
    porid = {a["id"]: a for a in alimentos}
    itens = []
    for aid, var in x.items():
        kg_ms = var.value() or 0.0
        if kg_ms > 1e-4:
            a = porid[aid]
            itens.append({"alimento": a, "kg_ms": kg_ms, "kg_mn": kg_ms / (a["ms"] / 100)})
    comp = composicao([{"alimento": i["alimento"], "kg_mn": i["kg_mn"]} for i in itens])
    return {"status": status, "custo": comp["custo_vaca_dia"], "itens": itens, "composicao": comp,
            "restricoes_violadas": violadas, "restricoes": restricoes}


def ajuste_minimo(alimentos: list[dict], restricoes: dict, atual: dict[str, float], peso_novo: float = 3.0) -> dict:
    """Menor mudança na dieta atual (kg MS por alimento) que respeita todas as restrições: minimiza Σ|x − atual|,
    com alimento novo pesando `peso_novo` e o custo só como desempate. Mesmas restrições (e contrato com a
    verificação) da formulação de custo mínimo; se só energia/proteína forem inatingíveis, devolve "parcial"."""
    for flexivel in (False, True):
        prob, x, (folga_e, folga_p) = _modelo(alimentos, restricoes, metas_flexiveis=flexivel)
        desvio = []
        for a in alimentos:
            aid = a["id"]
            mais = prob.add_variable(f"mais_{aid}", lowBound=0)
            menos = prob.add_variable(f"menos_{aid}", lowBound=0)
            prob.addConstraint(x[aid] - mais + menos == atual.get(aid, 0.0), f"desvio_{aid}")
            desvio.append((1.0 if atual.get(aid) else peso_novo) * (mais + menos))
        custo = pulp.lpSum(a["preco_kg_mn"] / (a["ms"] / 100) * x[a["id"]] for a in alimentos)
        objetivo = pulp.lpSum(desvio) + 0.001 * custo
        if flexivel:
            objetivo += PENALIDADE_MCAL * folga_e + PENALIDADE_PB * folga_p
        prob.setObjective(objetivo)
        if _resolver(prob) == "Optimal":
            if not flexivel:
                return _saida("otimo", prob, x, alimentos, restricoes, [])
            violadas = diagnosticar(alimentos, restricoes)
            if set(violadas) <= METAS_NUTRICIONAIS:
                out = _saida("parcial", prob, x, alimentos, restricoes, violadas)
                out["deficit"] = {"energia_mcal": folga_e.value() or 0.0,
                                  "proteina_pp": (folga_p.value() or 0.0) / max(out["composicao"]["ms_kg"], 1e-9)}
                return out
    return {"status": "inviavel", "restricoes_violadas": diagnosticar(alimentos, restricoes), "restricoes": restricoes}


# ------------------------------------------------------------------ sensibilidade de preços (análise pós-ótimo)
def _kg_ms(alimentos: list[dict], restricoes: dict) -> dict[str, float] | None:
    pl = formular(alimentos, dict(restricoes))
    if pl["status"] != "otimo":
        return None
    return {i["alimento"]["id"]: i["kg_ms"] for i in pl["itens"]} | {"_custo": pl["custo"]}


def _com_preco(alimentos: list[dict], aid: str, preco: float) -> list[dict]:
    return [a | {"preco_kg_mn": preco} if a["id"] == aid else a for a in alimentos]


def _bissecao(cond, baixo: float, alto: float, passos: int = 14) -> float:
    """Maior valor em [baixo, alto] em que cond(valor) é verdadeira (cond(baixo) verdadeira, cond(alto) falsa)."""
    for _ in range(passos):
        meio = (baixo + alto) / 2
        baixo, alto = (meio, alto) if cond(meio) else (baixo, meio)
    return baixo


def sensibilidade(alimentos: list[dict], restricoes: dict, variacao_meta: float = 0.05, fator_max: float = 6.0) -> dict:
    """Para a dieta de custo mínimo: até que preço cada alimento fica na dieta (sem mudar a dieta e antes de sair),
    abaixo de que preço um alimento de fora entraria, e quanto cada meta nutricional custa. Tudo medido resolvendo o
    mesmo PL com o preço (ou a meta) alterado: sem aproximação linear."""
    base = _kg_ms(alimentos, restricoes)
    if base is None:
        return {"status": "sem_otimo"}
    saida = []
    for a in alimentos:
        aid, p0 = a["id"], a["preco_kg_mn"]
        kg0 = base.get(aid, 0.0)
        linha = {"alimento": aid, "nome": a.get("nome", aid), "preco": p0, "kg_mn": kg0 / (a["ms"] / 100),
                 "na_dieta": kg0 > 0.01}

        def kg(preco):
            r = _kg_ms(_com_preco(alimentos, aid, preco), restricoes)
            return r.get(aid, 0.0) if r else 0.0

        if linha["na_dieta"]:
            alto = p0 * fator_max if p0 > 0 else 1.0
            igual = lambda p: abs(kg(p) - kg0) <= 0.05 * kg0
            fica = lambda p: kg(p) > 0.02 * kg0
            linha["mantem_ate"] = None if igual(alto) else _bissecao(igual, p0, alto)
            linha["sai_acima"] = None if fica(alto) else _bissecao(fica, p0, alto)
        else:
            entra = lambda p: kg(p) > 0.05
            linha["entra_abaixo"] = None if not entra(p0 * 0.001) else _bissecao(entra, p0 * 0.001, p0)
        saida.append(linha)
    metas = []
    for meta, campos in (("energia", ("ell_min",)), ("proteina", ("pb_min",)), ("fibra", ("fdn_min", "fdnf_min"))):
        r = dict(restricoes)
        for c in campos:
            if r.get(c) is not None:
                r[c] = r[c] * (1 - variacao_meta)
        alt = _kg_ms(alimentos, r)
        if alt is not None:
            metas.append({"meta": meta, "variacao": variacao_meta, "economia": base["_custo"] - alt["_custo"]})
    return {"status": "otimo", "custo": base["_custo"], "alimentos": saida, "metas": metas}

