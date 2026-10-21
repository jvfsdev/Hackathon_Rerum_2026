"""Revisão da base pelo uso real: quais regras os usuários recusam, quais alertas somem sozinhos e quais regras
nunca disparam. Não muda a base: aponta ao especialista onde olhar (limiares citados pela regra)."""
import statistics
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta

from sqlmodel import Session, select

from .db.models import AlertaDB, HistoricoAlerta, SessaoInferencia
from .engine.rules_loader import BaseConhecimento

MODULOS_REVISADOS = ("acompanhamento_diario", "acompanhamento_semanal", "acompanhamento_mensal", "verificacao")


def _params_citados(regra: dict) -> list[str]:
    out = []

    def varre(c):
        for sub in c.get("qualquer", []) + c.get("todos", []):
            varre(sub)
        v = c.get("valor")
        for x in v if isinstance(v, list) else [v]:
            if isinstance(x, str):
                for parte in x.split("|"):
                    if parte.startswith("@params."):
                        out.append(parte[len("@params."):])
    for c in regra.get("se", []):
        varre(c)
    return list(dict.fromkeys(out))


def revisar(s: Session, kb: BaseConhecimento, dias: int = 120, hoje: date | None = None) -> dict:
    hoje = hoje or date.today()
    p = {k: kb.params[k]["valor"] for k in ("revisao_min_episodios", "revisao_taxa_recusa", "revisao_taxa_sozinho",
                                            "revisao_duracao_curta")}
    eps = s.exec(select(AlertaDB).where(AlertaDB.aberto_em >= hoje - timedelta(days=dias))).all()
    hist: dict[int, list[HistoricoAlerta]] = defaultdict(list)
    for h in s.exec(select(HistoricoAlerta).where(HistoricoAlerta.alerta_id.in_([e.id for e in eps]))).all():
        hist[h.alerta_id].append(h)
    por_regra: dict[str, list[AlertaDB]] = defaultdict(list)
    for e in eps:
        por_regra[e.regra].append(e)
    disparos: Counter = Counter()
    n_sessoes = 0
    for sess in s.exec(select(SessaoInferencia).where(
            SessaoInferencia.criado_em >= datetime.combine(hoje - timedelta(days=dias), datetime.min.time()))).all():
        disparos.update({t["regra"] for t in sess.resultado.get("traco", [])})
        n_sessoes += 1

    regras, sugestoes = [], []
    for rid, lista in por_regra.items():
        regra = kb.regra(rid) or {}
        tipos = lambda e: {h.tipo for h in hist[e.id]}
        recusados = [e for e in lista if "recusado" in tipos(e)]
        sozinhos = [e for e in lista if e.estado == "resolvido" and not tipos(e) & {"aceito", "acao_registrada"}]
        duracoes = [(e.estado_em - e.aberto_em).days for e in lista if e.estado == "resolvido" and e.estado_em]
        linha = {"regra": rid, "descricao": regra.get("descricao", ""), "titulo": lista[-1].titulo_produtor or lista[-1].titulo,
                 "episodios": len(lista), "recusados": len(recusados),
                 "aceitos": sum(1 for e in lista if "aceito" in tipos(e)), "resolvidos_sozinhos": len(sozinhos),
                 "duracao_mediana": statistics.median(duracoes) if duracoes else None,
                 "motivos": [h.descricao.removeprefix("Recomendação recusada: ") for e in recusados for h in hist[e.id]
                             if h.tipo == "recusado"],
                 "parametros": _params_citados(regra), "forca": regra.get("forca")}
        regras.append(linha)
        if len(lista) < p["revisao_min_episodios"]:
            continue
        if len(recusados) / len(lista) >= p["revisao_taxa_recusa"]:
            sugestoes.append({"tipo": "muitas_recusas", "regra": rid, "titulo": linha["titulo"],
                              "texto": f"{len(recusados)} de {len(lista)} episódios recusados. Rever o limiar ou o texto "
                                       "da recomendação com os motivos dos usuários.",
                              "parametros": linha["parametros"], "motivos": linha["motivos"]})
        if (len(sozinhos) / len(lista) >= p["revisao_taxa_sozinho"] and linha["duracao_mediana"] is not None
                and linha["duracao_mediana"] <= p["revisao_duracao_curta"]):
            sugestoes.append({"tipo": "some_sozinho", "regra": rid, "titulo": linha["titulo"],
                              "texto": f"{len(sozinhos)} de {len(lista)} episódios se resolveram sozinhos em ~"
                                       f"{linha['duracao_mediana']:.0f} dia(s), sem ação. A regra pode estar sensível "
                                       "demais: exigir mais persistência ou subir o limiar.",
                              "parametros": linha["parametros"], "motivos": []})
    nunca = [{"regra": r["id"], "descricao": r.get("descricao", ""), "modulo": r["modulo"]}
             for r in kb.regras if r["modulo"] in MODULOS_REVISADOS and not disparos[r["id"]]
             and any("alerta" in a for a in r.get("entao", []))]
    regras.sort(key=lambda l: (-l["recusados"], -l["episodios"]))
    return {"dias": dias, "sessoes_analisadas": n_sessoes,
            "regras": regras, "sugestoes": sugestoes, "nunca_dispararam": nunca, "kb_version": kb.versao}
