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


MINERAIS = ("ca", "p", "mg", "k", "na", "cl", "s")


def dcad_meq_kg(na: float, k: float, cl: float, s: float) -> float:
    """Diferença cátion-ânion da dieta (mEq/kg MS) a partir dos teores em % da MS:
    [(Na/0,023 + K/0,039) − (Cl/0,0355 + S/0,016)] × 10."""
    return ((na / 0.023 + k / 0.039) - (cl / 0.0355 + s / 0.016)) * 10


def composicao(itens: list[dict]) -> dict:
    """itens: [{"alimento": {...}, "kg_mn": float}]. Teores em % da MS; ELl total em Mcal/dia."""
    ms_total = pb = fdn = fdnf = cnf = ee = ndt = ell = ureia = custo = forragem = mineral = 0.0
    volumosos = set()
    kg_ms_por_alimento: dict[str, float] = {}
    tem_pastejo = False
    fdn_forr_com_fdnd = fdnd_pond = 0.0
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
            if a.get("fdnd") is not None:      # digestibilidade da FDN (% da FDN), quando analisada
                fdn_forr_com_fdnd += kg_ms * a.get("fdn", 0)
                fdnd_pond += kg_ms * a.get("fdn", 0) * a["fdnd"]
            forragem += kg_ms
            if kg_mn > 0:
                volumosos.add(a["id"])
        if a.get("tipo") == "ureia":
            ureia += kg_ms
        if a.get("tipo") == "mineral":
            mineral += kg_ms
        if a.get("pastejo") and kg_mn > 0:
            tem_pastejo = True
        kg_ms_por_alimento[a["id"]] = kg_ms_por_alimento.get(a["id"], 0.0) + kg_ms
    if ms_total == 0:
        return {"ms_kg": 0.0}
    # minerais (% MS) só quando TODOS os alimentos da dieta trazem o dado (senão o valor seria subestimado)
    minerais = {}
    for m in MINERAIS:
        com_dado = [i for i in itens if i["kg_mn"] > 0]
        if com_dado and all(i["alimento"].get(m) is not None for i in com_dado):
            minerais[f"{m}_pct"] = sum(mn_para_ms(i["kg_mn"], i["alimento"]["ms"]) * i["alimento"][m] for i in com_dado) / ms_total
    if all(f"{m}_pct" in minerais for m in ("na", "k", "cl", "s")):
        minerais["dcad_meq_kg"] = dcad_meq_kg(minerais["na_pct"], minerais["k_pct"], minerais["cl_pct"], minerais["s_pct"])
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
        "tem_pastejo": tem_pastejo,
        **minerais,
        **({"fdnd_forragem": fdnd_pond / fdn_forr_com_fdnd} if fdn_forr_com_fdnd > 0 else {}),
        "mineral_kg_ms": mineral,
        "inclusao_excedida": sorted(
            aid for aid, kg in kg_ms_por_alimento.items()
            if _limite(itens, aid) is not None and 100 * kg / ms_total > _limite(itens, aid) + 0.5),
    }


def _limite(itens: list[dict], aid: str):
    return next((i["alimento"].get("max_pct_ms") for i in itens if i["alimento"]["id"] == aid), None)
