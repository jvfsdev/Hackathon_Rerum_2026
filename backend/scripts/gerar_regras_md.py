"""Gera docs/regras.md a partir da base de conhecimento (as regras documentadas são as executadas).
Uso: python -m scripts.gerar_regras_md  (dentro de backend/)
"""
from pathlib import Path

from app.engine.rules_loader import ORDEM_MODULOS, carregar

SAIDA = Path(__file__).resolve().parents[2] / "docs" / "regras.md"
NOMES = {"classificacao": "A — Classificação do lote (CLS)", "exigencias": "B — Exigências e metas (EXG)",
         "verificacao": "C — Verificação da dieta (VER)", "formulacao": "F — Formulação por programação linear (FOR)",
         "acompanhamento_diario": "D1 — Acompanhamento diário (ACP)", "acompanhamento_semanal": "D2 — Acompanhamento semanal (ACP)",
         "acompanhamento_mensal": "D3 — Acompanhamento mensal / laudo (ACP)", "meta": "M — Meta-regras (resolução de conflito)"}


def cond(c: dict) -> str:
    if "qualquer" in c:
        return "(" + " OU ".join(cond(x) for x in c["qualquer"]) + ")"
    if "todos" in c:
        return "(" + " E ".join(cond(x) for x in c["todos"]) + ")"
    v = c.get("valor", "")
    return f"`{c['fato']}` {c.get('op', 'existe')} {v if v != '' else ''}".strip()


def acao(a: dict) -> str:
    if "concluir" in a:
        return f"concluir `{a['concluir']['fato']}` = {a['concluir']['valor']}"
    if "calcular" in a:
        return f"calcular `{a['calcular']['fato']}` = {a['calcular']['funcao']}(…)"
    if "alerta" in a:
        return f"alerta **{a['alerta']['nivel']}** ({a['alerta'].get('categoria', '')}): {a['alerta']['titulo']}"
    for t in ("suprimir", "rebaixar"):
        if t in a:
            return f"{t} alertas de {', '.join(a[t]['categorias'])}"
    return str(a)


def main():
    kb = carregar()
    linhas = [f"# Regras de produção — base v{kb.versao}", "",
              f"{len(kb.regras)} regras · {len(kb.params)} parâmetros · {len(kb.alimentos)} alimentos. "
              "Gerado automaticamente de `backend/kb/` (não editar à mão).", "",
              "Formato: **SE** condições **ENTÃO** ações [CF da regra]. Limiares `@params.*` estão na tabela de parâmetros no fim.",
              "Força da evidência: A = norma/meta-análise; B = estudo revisado ou extensão com dados; C = extensão sem dados ou "
              "população diferente; D = escolha de engenharia.", ""]
    for modulo in sorted({r["modulo"] for r in kb.regras}, key=lambda m: (ORDEM_MODULOS[m], m)):
        linhas += [f"## {NOMES.get(modulo, modulo)}", "", "| ID | Descrição | SE | ENTÃO | CF | Força | Fonte |", "|---|---|---|---|---|---|---|"]
        for r in [r for r in kb.regras if r["modulo"] == modulo]:
            se = " E ".join(cond(c) for c in r["se"]).replace("|", "\\|")
            entao = "; ".join(acao(a) for a in r.get("entao", [])).replace("|", "\\|")
            linhas.append(f"| {r['id']} | {r.get('descricao', '')} | {se} | {entao} | {r['cf']} | {r.get('forca', '')} | {r.get('fonte', '')} |")
        linhas.append("")
    linhas += ["## Parâmetros", "", "| Parâmetro | Valor | Unidade | Força | Fonte | Descrição |", "|---|---|---|---|---|---|"]
    for nome, p in kb.params.items():
        linhas.append(f"| `{nome}` | {p['valor']} | {p.get('unidade', '')} | {p.get('forca', '')} | {p.get('fonte', '')} | {p.get('descricao', '')} |")
    linhas += ["", "## Alimentos", "", "| ID | Nome | MS | PB | FDN | NDT | EE | R$/kg MN | Fonte |", "|---|---|---|---|---|---|---|---|---|"]
    for a in kb.alimentos.values():
        linhas.append(f"| {a['id']} | {a['nome']} | {a['ms']} | {a['pb']} | {a['fdn']} | {a['ndt']} | {a['ee']} | {a['preco_kg_mn']} | {a['fonte']} |")
    SAIDA.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    print(f"{SAIDA} gerado ({len(kb.regras)} regras).")


if __name__ == "__main__":
    main()
