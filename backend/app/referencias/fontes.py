"""Fontes públicas de preço (adaptadores). Escolhidas por serem oficiais/reconhecidas e acessíveis sem login
(pesquisa de 21/10/2026). Cepea: licença CC BY-NC 4.0 — citar "Fonte: Cepea/Esalq-USP".

Sem fonte pública diária (ficam com valor de demonstração até a fazenda informar): silagens, capins, cana,
braquiária, núcleo mineral, polpa cítrica, farelo de trigo, caroço de algodão, ureia pecuária."""
import html
import re
from datetime import date, datetime

import httpx

from .base import Cotacao, Fonte
from .coletor import FONTES

FONTES_POR_ITEM: dict[str, list[str]] = {}
NAVEGADOR = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/126 Safari/537.36"}
MESES = {"jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6, "jul": 7, "ago": 8, "set": 9, "out": 10,
         "nov": 11, "dez": 12}


def registrar(fonte: Fonte) -> Fonte:
    FONTES.append(fonte)
    for item in fonte.itens:
        FONTES_POR_ITEM.setdefault(item, []).append(fonte.nome)
    return fonte


def tabelas(pagina: str) -> list[list[list[str]]]:
    """Todas as <table> da página como listas de linhas de células (texto limpo)."""
    out = []
    for t in re.findall(r"<table.*?</table>", pagina, re.S | re.I):
        linhas = []
        for tr in re.findall(r"<tr.*?</tr>", t, re.S | re.I):
            celulas = [re.sub(r"\s+", " ", html.unescape(re.sub(r"<.*?>", " ", c))).strip()
                       for c in re.findall(r"<t[dh].*?</t[dh]>", tr, re.S | re.I)]
            if celulas:
                linhas.append(celulas)
        out.append(linhas)
    return out


def numero_br(txt: str) -> float:
    return float(txt.replace(".", "").replace(",", "."))


def _get(url: str, timeout: float) -> str:
    r = httpx.get(url, headers=NAVEGADOR, timeout=timeout, follow_redirects=True)
    r.raise_for_status()
    return r.text


# ------------------------------------------------------------------ Cepea — milho
def ler_cepea_milho(pagina: str) -> Cotacao:
    """Indicador do Milho ESALQ/B3 (Campinas-SP): 1ª linha de dados = mais recente, R$/saca de 60 kg."""
    texto = html.unescape(re.sub(r"<.*?>", " ", pagina))
    if "saca de 60 kg" not in texto:
        raise ValueError("unidade 'saca de 60 kg' não encontrada: layout da página mudou")
    for linha in tabelas(pagina)[0]:
        if re.fullmatch(r"\d{2}/\d{2}/\d{4}", linha[0]):
            return Cotacao("milho_moido", numero_br(linha[1]), "R$/saca 60 kg",
                           datetime.strptime(linha[0], "%d/%m/%Y").date(), "Campinas-SP (indicador ESALQ/B3)")
    raise ValueError("nenhuma linha de cotação na tabela do milho")


class CepeaMilho(Fonte):
    nome = "Cepea/Esalq-USP — Indicador do Milho"
    url = "https://www.cepea.org.br/br/indicador/milho.aspx"
    itens = ("milho_moido",)
    frequencia = "diária (dias úteis)"

    def coletar(self) -> list[Cotacao]:
        c = ler_cepea_milho(_get(self.url, self.timeout))
        c.url = self.url
        return [c]


# ------------------------------------------------------------------ Cepea — leite ao produtor (MG)
def ler_cepea_leite(pagina: str, uf: str = "MG") -> Cotacao:
    """Preço médio do leite ao produtor por estado (mensal): linhas [mês/aa, UF, preço]."""
    for linha in tabelas(pagina)[0]:
        if len(linha) >= 3 and linha[1] == uf and re.fullmatch(r"[a-z]{3}/\d{2}", linha[0]):
            mes, ano = linha[0].split("/")
            return Cotacao("leite", numero_br(linha[2]), "R$/L", date(2000 + int(ano), MESES[mes], 1),
                           f"{uf} (média mensal ao produtor)")
    raise ValueError(f"linha de {uf} não encontrada na tabela do leite ao produtor")


class CepeaLeite(Fonte):
    nome = "Cepea/Esalq-USP — Leite ao Produtor"
    url = "https://www.cepea.org.br/br/indicador/leite.aspx"
    itens = ("leite",)
    frequencia = "mensal (defasagem de ~2 meses)"
    idade_maxima_dias = 95

    def coletar(self) -> list[Cotacao]:
        c = ler_cepea_leite(_get(self.url, self.timeout))
        c.url = self.url
        return [c]


# ------------------------------------------------------------------ IPEADATA — farelo de soja (Deral-PR)
def ler_ipeadata(dados: dict, item: str, unidade: str, praca: str) -> Cotacao:
    valores = [v for v in dados.get("value", []) if v.get("VALVALOR") is not None]
    if not valores:
        raise ValueError("série sem valores")
    ult = max(valores, key=lambda v: v["VALDATA"])
    return Cotacao(item, float(ult["VALVALOR"]), unidade, date.fromisoformat(ult["VALDATA"][:10]), praca)


class IpeadataFareloSoja(Fonte):
    nome = "IPEADATA — Seab/Deral-PR (farelo de soja, atacado)"
    serie = "DERAL12_ATFSO12"
    url = f"https://www.ipeadata.gov.br/api/odata4/ValoresSerie(SERCODIGO='{serie}')"
    itens = ("farelo_soja",)
    frequencia = "mensal (defasagem de ~1 mês)"
    idade_maxima_dias = 60
    timeout = 60.0

    def coletar(self) -> list[Cotacao]:
        r = httpx.get(self.url, timeout=self.timeout)
        r.raise_for_status()
        c = ler_ipeadata(r.json(), "farelo_soja", "R$/tonelada", "Paraná (atacado)")
        c.url = "http://www.ipeadata.gov.br/ExibeSerie.aspx?serid=" + self.serie
        return [c]


for _f in (CepeaMilho(), CepeaLeite(), IpeadataFareloSoja()):
    registrar(_f)
