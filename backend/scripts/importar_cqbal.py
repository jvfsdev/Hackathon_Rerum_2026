"""Atualiza a composição dos alimentos da base (kb/foods.yaml) a partir de relatórios do CQBAL 4.0.

Fonte: VALADARES FILHO, S.C., LOPES, S.A. et al. CQBAL 4.0. Tabelas Brasileiras de Composição de Alimentos para
Ruminantes. 2018. Disponível em: www.cqbal.com.br. Sem licença publicada: uso acadêmico com citação; pedir
autorização à equipe do CQBAL (UFV) antes de redistribuir. Este script NÃO consulta o site: lê relatórios já
obtidos (JSON da consulta pública de composição, um arquivo rel<id>.json por derivado).

Uso: python -m scripts.importar_cqbal <pasta_com_rel_json>
"""
import json
import sys
from datetime import date
from pathlib import Path

import yaml

KB = Path(__file__).resolve().parents[1] / "kb"
CITACAO = "CQBAL 4.0 (Valadares Filho et al., 2018)"
# alimento da base → id do derivado no CQBAL 4.0
MAPA = {
    "silagem_milho": 52, "silagem_sorgo": 887, "capim_elefante": 170, "braquiaria": 245, "braquiaria_marandu": 1370,
    "cana": 90, "milho_moido": 1, "farelo_soja": 4, "caroco_algodao": 157, "farelo_trigo": 30, "polpa_citrica": 808,
    "ureia": 42,
}
NOVOS = {"braquiaria_marandu": {"nome": "Braquiária brizantha Marandu (pastejo)", "tipo": "volumoso", "pastejo": True,
                                "preco_kg_mn": 0.05}}
CAMPOS = {"MS": "ms", "PB": "pb", "EE": "ee", "MM": "mm", "FDN": "fdn", "CNF": "cnf",
          "Ca": "ca", "P": "p", "Mg": "mg", "K": "k", "Na": "na", "Cl": "cl", "S": "s"}
N_MIN_NDT_OBS = 10


def nutrientes(relatorio: dict) -> tuple[dict, dict]:
    """{código: (média, n)} dos dados originais e {código: média} dos calculados."""
    d = relatorio["data"]
    orig = {}
    for linha in d["lista"]:
        for cod, med, n in (("NUTRIENTE", "media", "n"), ("NUTRIENTE2", "media2", "n2")):
            if linha.get(cod) and linha.get(med) is not None:
                orig[linha[cod]] = (float(linha[med]), int(linha.get(n) or 0))
    calc = {c["NUTRIENTE"]: float(c["media"]) for c in d.get("dadosCalculados", []) if c.get("media") is not None}
    return orig, calc


def composicao(relatorio: dict, cqbal_id: int) -> dict:
    orig, calc = nutrientes(relatorio)
    out, n = {}, {}
    for cod, campo in CAMPOS.items():
        if cod in orig:
            out[campo], n[cod] = round(orig[cod][0], 3), orig[cod][1]
    if "mm" not in out and "CZ" in orig:          # cinzas como matéria mineral (só se não houver MM)
        out["mm"], n["CZ"] = round(orig["CZ"][0], 3), orig["CZ"][1]
    if "NDT OBS" in orig and orig["NDT OBS"][1] >= N_MIN_NDT_OBS:
        out["ndt"], n["NDT OBS"], ndt_origem = round(orig["NDT OBS"][0], 2), orig["NDT OBS"][1], "observado"
    elif "NDT_BRCORTE2016" in calc:
        out["ndt"], ndt_origem = round(calc["NDT_BRCORTE2016"], 2), "calculado BR-CORTE 2016"
    else:
        ndt_origem = None
    if "cnf" not in out and "CNF_CALC_BRCORTE2016" in calc:
        out["cnf"] = round(calc["CNF_CALC_BRCORTE2016"], 2)
    out["fonte"] = f"{CITACAO}, derivado {cqbal_id}" + (f"; NDT {ndt_origem}" if ndt_origem else "")
    out["forca"], out["cf"], out["n_amostras"] = "B", 0.8, n
    return out


def main(pasta: Path):
    arq = KB / "foods.yaml"
    texto = arq.read_text(encoding="utf-8")
    cabecalho = "".join(l for l in texto.splitlines(keepends=True) if l.startswith("#") and not l.startswith("# Composição: CQBAL"))
    alimentos = yaml.safe_load(texto)
    por_id = {a["id"]: a for a in alimentos}
    for aid, cid in MAPA.items():
        rel = json.loads((pasta / f"rel{cid}.json").read_text(encoding="utf-8"))
        novo = composicao(rel, cid)
        if aid == "ureia":                             # NNP puro: não tem fibra, gordura, energia nem minerais (permite a DCAD)
            novo |= {m: 0.0 for m in ("ca", "p", "mg", "k", "na", "cl", "s")} | {"fdn": 0, "ndt": 0, "ee": 0}
            novo["fonte"] += "; FDN/EE/NDT e minerais = 0 por definição (NNP puro)"
        if aid not in por_id:
            por_id[aid] = {"id": aid, **NOVOS[aid]}
            alimentos.append(por_id[aid])
        por_id[aid].update(novo)
    linhas = [cabecalho.rstrip() + "\n# Composição: CQBAL 4.0 (importada por scripts/importar_cqbal.py em "
              f"{date.today():%d/%m/%Y}); n_amostras = número de análises da média.\n"]
    for a in alimentos:
        linhas.append("- " + yaml.safe_dump(a, default_flow_style=True, allow_unicode=True, sort_keys=False, width=4000).strip() + "\n")
    arq.write_text("".join(linhas), encoding="utf-8")
    print(f"{len(MAPA)} alimentos atualizados em {arq}")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
