"""Funções de cálculo que as regras podem chamar pela ação `calcular`."""
import math

from ..calc import climate, conversions, diet, economics, energy, intake, protein


def _minimo(a, b=None):
    vals = [v for v in (a, b) if v is not None]
    return min(vals)


def _metas_fibra(fdnf_dieta: float, fdn_min: float, fdnf_min: float, cnf_max: float, passo: float,
                 fdnf_min_absoluto: float) -> dict:
    """NRC 2001: para cada ponto de FDNf abaixo do mínimo, FDN mínimo +2 e CNF máximo −2. A tabela só vai até
    FDNf = fdnf_min_absoluto (15%): abaixo disso não extrapola (a VER-03D bloqueia a dieta)."""
    deficit = min(max(0.0, fdnf_min - fdnf_dieta), fdnf_min - fdnf_min_absoluto)
    return {"fdn_min": fdn_min + passo * deficit, "cnf_max": cnf_max - passo * deficit}


def _metas_altura(forrageira: str, tabela: dict, tolerancia: float) -> dict | None:
    """Limites de altura do pasto: rotacionado (entrada máx., saída mín.) ou contínuo (faixa da altura média)."""
    m = tabela.get(forrageira)
    if not m:
        return None
    out = {}
    if "entrada" in m:
        out["entrada_max"] = m["entrada"] * (1 + tolerancia)
    if "saida_min" in m:
        out["saida_min"] = m["saida_min"]
    if "media" in m:
        out["media_min"], out["media_max"] = m["media"] * (1 - tolerancia), m["media"] * (1 + tolerancia)
    return out


FUNCOES = {
    "semana_lactacao": lambda del_: del_ / 7,
    "cms_nrc2001": lambda pv, leite, gordura, semana: intake.cms_nrc2001(pv, leite, gordura, semana),
    "cms_brleite": lambda pv, leite, gordura, del_: intake.cms_brleite(pv, leite, gordura, del_),
    "cms_brleite_cana": lambda pv, leite, gordura, del_: intake.cms_brleite_cana(pv, leite, gordura, del_),
    "cms_preparto": lambda pv, pct: intake.cms_preparto(pv, pct),
    "teto_fibra": lambda pv, fdn, limite: intake.teto_fibra(pv, fdn, limite),
    "cms_pct_pv": lambda cms, pv: intake.cms_pct_pv(cms, pv),
    "minimo": _minimo,
    "ajuste_fdnd": lambda fdnd, ref, kg_por_ponto: (fdnd - ref) * kg_por_ponto,
    "metas_altura": _metas_altura,
    "cms_nasem2021": lambda pv, leite, gordura, proteina, ecc, del_, fracao_primiparas, lactose=None:
        intake.cms_nasem2021(pv, leite, gordura, proteina, ecc, del_, 1 - fracao_primiparas, lactose),
    "cms_final": lambda equacao, ajuste=0.0, teto=None, observado=None: intake.cms_final(equacao, ajuste, teto, observado),
    "aumentar_pct": lambda valor, pct: valor * (1 + pct / 100),
    "ecm": lambda leite, gordura, proteina: conversions.ecm(leite, gordura, proteina),
    "pct": lambda parte, total: 100 * parte / total if total else None,
    "mantenca": lambda pv, k: energy.mantenca(pv, k),
    "ell_leite": lambda leite, gordura, proteina, lactose=None: leite * energy.ell_leite_por_kg(gordura, proteina, lactose),
    "ell_gestacao": lambda dias, peso_bezerro, inicio: energy.gestacao(dias, peso_bezerro, inicio),
    "ell_crescimento": lambda mantenca, fracao, acrescimo: energy.crescimento_primiparas(mantenca, fracao, acrescimo),
    "ell_atividade": lambda pv, distancia, relevo, ondulado: energy.atividade_pastejo(pv, distancia, relevo, ondulado),
    "ell_ajuste_ecc": lambda ecc, meta, dias, mcal_por_ponto, pv, pv_ref: energy.ajuste_ecc(ecc, meta, dias, mcal_por_ponto, pv, pv_ref),
    "fator_mobilizacao": energy.fator_mobilizacao,
    "soma": lambda partes: energy.soma(*partes),
    "leite_permitido": energy.leite_permitido,
    "maximo": lambda valores: max(v for v in valores if v is not None),
    "dias_transicao_conc": lambda delta_kg, passo_kg: math.ceil(abs(delta_kg) / passo_kg),
    "pm_leite": lambda leite, proteina, eficiencia: protein.pm_leite(leite, proteina, eficiencia),
    "pm_gestacao": lambda dias, peso_bezerro, inicio: protein.pm_gestacao(dias, peso_bezerro, inicio),
    "pb_alvo": lambda leite, tabela: protein.pb_alvo(leite, tabela),
    "itu": lambda temp, ur: climate.itu(temp, ur),
    "metas_fibra": _metas_fibra,
    "composicao_dieta": lambda itens, tolerancia_inclusao: diet.composicao(itens, tolerancia_inclusao),
    "ureia_para_nul": lambda ureia: conversions.ureia_para_nul(ureia),
    "energia_consumida": lambda ms, cms, ell_kg: min(ms, cms) * ell_kg,
    "ms_para_mn": lambda kg_ms, ms_pct: conversions.ms_para_mn(kg_ms, ms_pct),
    "faixa": lambda chave, tabela: {"min": tabela[chave][0], "max": tabela[chave][1]},
    "valor_tabela": lambda chave, tabela: tabela.get(chave),
    "perda_ccs": lambda ccs, litros_dia, preco: {
        "pct": economics.perda_producao_ccs_pct(ccs),
        "rs_mes": economics.perda_producao_ccs_pct(ccs) / 100 * litros_dia * preco * 30},
    "razao": lambda a, b: a / b if b else None,
    "produto": lambda a, b: a * b,
    "pct_de": lambda valor, pct: valor * pct / 100,
    "diferenca": lambda a, b: a - b,
}
