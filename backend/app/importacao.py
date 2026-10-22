"""Importação de planilhas (CSV) de registros diários, controle leiteiro e laudo do laticínio.

Fluxo: prévia (validação por linha, sem gravar) → confirmação (grava, substitui o mesmo indicador na mesma data e
reprocessa o acompanhamento a partir da primeira data importada)."""
import csv
import io
import re
import unicodedata
from datetime import date, datetime

# nome da coluna (normalizado) → indicador
ALIASES = {
    "vacas": "vacas", "n_vacas": "vacas", "vacas_ordenhadas": "vacas", "numero_vacas": "vacas",
    "litros": "litros", "leite": "litros", "leite_total": "litros", "litros_lote": "litros", "producao": "litros",
    "concentrado": "concentrado_kg_vaca", "concentrado_kg_vaca": "concentrado_kg_vaca", "conc": "concentrado_kg_vaca",
    "temp": "temp", "temperatura": "temp", "ur": "ur", "umidade": "ur",
    "sobras": "sobras_pct", "sobras_pct": "sobras_pct", "escore_cocho": "escore_cocho", "cocho": "escore_cocho",
    "leitura_cocho": "escore_cocho", "escore_de_cocho": "escore_cocho", "ms_silagem": "ms_silagem", "ms": "ms_silagem",
    "ecc": "ecc", "escore_corporal": "ecc", "fezes": "escore_fezes", "escore_fezes": "escore_fezes",
    "ruminacao": "ruminacao", "distancia": "distancia_km", "distancia_km": "distancia_km",
    "altura_entrada": "altura_entrada", "altura_saida": "altura_saida", "altura_media": "altura_media",
    "gordura": "laudo_gordura", "proteina": "laudo_proteina", "lactose": "laudo_lactose", "nul": "laudo_nul",
    "mun": "laudo_nul", "ureia": "laudo_ureia", "ccs": "laudo_ccs", "cbt": "laudo_cbt", "cpp": "laudo_cbt",
    "crioscopia": "laudo_crioscopia",
}
ALIASES |= {f"laudo_{k}": f"laudo_{k}" for k in ("gordura", "proteina", "lactose", "nul", "ureia", "ccs", "cbt", "crioscopia")}
COLUNAS_DATA = {"data", "dia", "data_coleta", "data_analise"}
# faixa plausível de cada indicador (fora dela a célula é recusada)
FAIXAS = {
    "vacas": (1, 5000), "litros": (0, 200000), "concentrado_kg_vaca": (0, 30), "temp": (-5, 50), "ur": (0, 100),
    "sobras_pct": (0, 50), "escore_cocho": (1, 5), "ms_silagem": (10, 60), "ecc": (1, 5), "escore_fezes": (1, 5), "ruminacao": (0, 800),
    "distancia_km": (0, 20), "altura_entrada": (0, 300), "altura_saida": (0, 300), "altura_media": (0, 300),
    "laudo_gordura": (1, 8), "laudo_proteina": (1, 6), "laudo_lactose": (3, 6), "laudo_nul": (0, 40),
    "laudo_ureia": (0, 90), "laudo_ccs": (1, 10000), "laudo_cbt": (1, 100000), "laudo_crioscopia": (-0.7, -0.4),
    "trato_kg": (0, 500000),
}
LITROS_VACA_MAX = 80        # acima disso por vaca/dia é erro de digitação (recorde mundial ≈ 75 L/dia em vaca individual)


def problema_valor(indicador: str, valor: float) -> str | None:
    """Mesma checagem para registro digitado, fila do celular e planilha: indicador conhecido e valor plausível."""
    if indicador not in FAIXAS:
        return f"indicador desconhecido: {indicador}"
    lo, hi = FAIXAS[indicador]
    if indicador == "vacas" and valor != int(valor):
        return "nº de vacas precisa ser inteiro"
    if not lo <= valor <= hi:
        return f"{indicador} = {valor:g} fora da faixa plausível ({lo:g} a {hi:g})"
    return None
MODELOS = {
    "diario": "data;vacas;litros;concentrado_kg_vaca;temp;ur;escore_cocho;sobras_pct;ms_silagem;ecc\n"
              "20/10/2026;40;864;4;22,5;65;3;;30,8;\n21/10/2026;40;858;4;23,1;63;;2,9;;2,75\n",
    "laudo": "data;gordura;proteina;lactose;nul;ccs;cbt;crioscopia\n"
             "12/10/2026;3,72;3,21;4,58;14,2;240;60;-0,541\n",
}


def _norm(txt: str) -> str:
    t = unicodedata.normalize("NFKD", txt).encode("ascii", "ignore").decode().lower().strip()
    t = re.sub(r"\(.*?\)", "", t)                 # "litros (L)" → "litros"
    return re.sub(r"[^a-z0-9]+", "_", t).strip("_")


def _data(txt: str) -> date:
    txt = txt.strip()
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(txt, fmt).date()
        except ValueError:
            pass
    raise ValueError(f"data '{txt}' não reconhecida (use dd/mm/aaaa)")


def _numero(txt: str) -> float:
    t = txt.strip().replace(" ", "")
    if "," in t:
        t = t.replace(".", "").replace(",", ".")     # 1.234,5 → 1234.5
    return float(t)


def ler(conteudo: str) -> dict:
    """Analisa o CSV sem gravar: registros válidos, erros por linha e mapeamento das colunas."""
    texto = conteudo.lstrip("﻿").strip()
    if not texto:
        raise ValueError("arquivo vazio")
    try:
        dialeto = csv.Sniffer().sniff(texto.splitlines()[0], delimiters=";,\t")
    except csv.Error:
        dialeto = csv.excel
        dialeto.delimiter = ";"
    linhas = list(csv.reader(io.StringIO(texto), dialeto))
    cabecalho = [_norm(c) for c in linhas[0]]
    col_data = next((i for i, c in enumerate(cabecalho) if c in COLUNAS_DATA), None)
    if col_data is None:
        raise ValueError("falta a coluna 'data'")
    colunas = {linhas[0][i].strip(): ALIASES.get(c) for i, c in enumerate(cabecalho) if i != col_data}
    if not any(colunas.values()):
        raise ValueError("nenhuma coluna reconhecida (veja o modelo de planilha)")
    registros, erros, hoje = [], [], date.today()
    for n, linha in enumerate(linhas[1:], start=2):
        if not any(c.strip() for c in linha):
            continue
        try:
            d = _data(linha[col_data])
            if d > hoje:
                raise ValueError(f"data {d:%d/%m/%Y} no futuro")
        except (ValueError, IndexError) as e:
            erros.append({"linha": n, "coluna": "data", "valor": linha[col_data] if col_data < len(linha) else "", "motivo": str(e)})
            continue
        for i, original in enumerate(linhas[0]):
            ind = ALIASES.get(cabecalho[i])
            if i == col_data or not ind or i >= len(linha) or not linha[i].strip():
                continue
            try:
                v = _numero(linha[i])
            except ValueError:
                erros.append({"linha": n, "coluna": original, "valor": linha[i], "motivo": "não é número"})
                continue
            lo, hi = FAIXAS[ind]
            if not lo <= v <= hi:
                erros.append({"linha": n, "coluna": original, "valor": linha[i], "motivo": f"fora da faixa plausível ({lo:g} a {hi:g})"})
                continue
            registros.append({"data": d, "indicador": ind, "valor": v})
    datas = [r["data"] for r in registros]
    return {"registros": registros, "erros": erros, "colunas": colunas,
            "periodo": [min(datas), max(datas)] if datas else None, "linhas": len(linhas) - 1}
