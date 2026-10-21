"""Composição de uma dieta a partir dos alimentos (kg MN por vaca/dia)."""
from .conversions import mn_para_ms, ndt_para_ell


def cnf_alimento(alimento: dict) -> float:
    """CNF = 100 − (PB + FDN + EE + MM); ureia não tem CNF."""
    if alimento.get("cnf") is not None:
        return alimento["cnf"]
    if alimento.get("tipo") in ("ureia", "mineral"):
        return 0.0
    return max(0.0, 100 - (alimento.get("pb", 0) + alimento.get("fdn", 0) + alimento.get("ee", 0) + alimento.get("mm", 0)))


def ell_alimento(alimento: dict) -> float:
    if alimento.get("ell") is not None:
        return alimento["ell"]
    ndt = alimento.get("ndt")
    return ndt_para_ell(ndt) if ndt else 0.0


def composicao(itens: list[dict]) -> dict:
    """itens: [{"alimento": {...}, "kg_mn": float}]. Teores em % da MS; ELl total em Mcal/dia."""
    ms_total = pb = fdn = fdnf = cnf = ee = ndt = ell = ureia = custo = forragem = 0.0
    volumosos = set()
    for item in itens:
        a, kg_mn = item["alimento"], item["kg_mn"]
        kg_ms = mn_para_ms(kg_mn, a["ms"])
        ms_total += kg_ms
        pb += kg_ms * a.get("pb", 0)
        fdn += kg_ms * a.get("fdn", 0)
        cnf += kg_ms * cnf_alimento(a)
        ee += kg_ms * a.get("ee", 0)
        ndt += kg_ms * a.get("ndt", 0)
        ell += kg_ms * ell_alimento(a)
        custo += kg_mn * a.get("preco_kg_mn", 0)
        if a.get("tipo") == "volumoso":
            fdnf += kg_ms * a.get("fdn", 0)
            forragem += kg_ms
            if kg_mn > 0:
                volumosos.add(a["id"])
        if a.get("tipo") == "ureia":
            ureia += kg_ms
    if ms_total == 0:
        return {"ms_kg": 0.0}
    return {
        "ms_kg": ms_total,
        "pb_pct": pb / ms_total,
        "fdn_pct": fdn / ms_total,
        "fdnf_pct": fdnf / ms_total,
        "cnf_pct": cnf / ms_total,
        "ee_pct": ee / ms_total,
        "ndt_pct": ndt / ms_total,
        "ell_mcal": ell,
        "ell_mcal_kg": ell / ms_total,
        "ureia_pct": 100 * ureia / ms_total,
        "forragem_pct": 100 * forragem / ms_total,
        "custo_vaca_dia": custo,
        "cana_unico_volumoso": volumosos == {"cana"},
        "n_volumosos": len(volumosos),
    }
