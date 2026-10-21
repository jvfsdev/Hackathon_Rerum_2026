"""Funções de cálculo que as regras podem chamar pela ação `calcular`."""
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


FUNCOES = {
    "semana_lactacao": lambda del_: del_ / 7,
    "cms_nrc2001": lambda pv, leite, gordura, semana: intake.cms_nrc2001(pv, leite, gordura, semana),
    "cms_brleite": lambda pv, leite, gordura, del_: intake.cms_brleite(pv, leite, gordura, del_),
    "cms_brleite_cana": lambda pv, leite, gordura, del_: intake.cms_brleite_cana(pv, leite, gordura, del_),
    "cms_preparto": lambda pv, pct: intake.cms_preparto(pv, pct),
    "teto_fibra": lambda pv, fdn, limite: intake.teto_fibra(pv, fdn, limite),
    "cms_pct_pv": lambda cms, pv: intake.cms_pct_pv(cms, pv),
    "minimo": _minimo,
    "mantenca": lambda pv, k: energy.mantenca(pv, k),
    "ell_leite": lambda leite, gordura, proteina, lactose=None: leite * energy.ell_leite_por_kg(gordura, proteina, lactose),
    "ell_gestacao": lambda dias, peso_bezerro, inicio: energy.gestacao(dias, peso_bezerro, inicio),
    "ell_crescimento": lambda mantenca, fracao, acrescimo: energy.crescimento_primiparas(mantenca, fracao, acrescimo),
    "ell_atividade": lambda pv, distancia, relevo: energy.atividade_pastejo(pv, distancia, relevo),
    "ell_ajuste_ecc": lambda ecc, meta, dias, mcal_por_ponto, pv, pv_ref: energy.ajuste_ecc(ecc, meta, dias, mcal_por_ponto, pv, pv_ref),
    "fator_mobilizacao": energy.fator_mobilizacao,
    "soma": lambda partes: energy.soma(*partes),
    "pm_leite": lambda leite, proteina, eficiencia: protein.pm_leite(leite, proteina, eficiencia),
    "pm_gestacao": lambda dias, peso_bezerro, inicio: protein.pm_gestacao(dias, peso_bezerro, inicio),
    "pb_alvo": lambda leite, tabela: protein.pb_alvo(leite, tabela),
    "itu": lambda temp, ur: climate.itu(temp, ur),
    "metas_fibra": _metas_fibra,
    "composicao_dieta": lambda itens: diet.composicao(itens),
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
