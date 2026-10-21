"""Executa as fontes, valida e grava as cotações; agenda a coleta diária."""
import logging
import threading
import time as relogio
from datetime import date, datetime, timedelta

from sqlmodel import Session, select

from ..db.models import ColetaPrecos, PrecoReferencia
from .base import Cotacao, Fonte

log = logging.getLogger("referencias")
FONTES: list[Fonte] = []          # preenchida em fontes.py
# Faixas plausíveis (R$/kg MN ou R$/L) para descartar valor quebrado por mudança de layout da fonte.
FAIXA_PLAUSIVEL = {"leite": (0.8, 6.0)}
FAIXA_PADRAO = (0.01, 50.0)


def _plausivel(c: Cotacao, preco: float) -> bool:
    lo, hi = FAIXA_PLAUSIVEL.get(c.item, FAIXA_PADRAO)
    return lo <= preco <= hi and c.data <= date.today() + timedelta(days=1)


def coletar(s: Session, fontes: list[Fonte] | None = None) -> dict:
    """Roda todas as fontes. Falha de uma fonte (rede, layout) não afeta as outras nem apaga valores anteriores."""
    resultado = {}
    for fonte in fontes if fontes is not None else FONTES:
        try:
            cotacoes = fonte.coletar()
            novos = 0
            descartados = []
            for c in cotacoes:
                preco = c.preco_convertido()
                if not _plausivel(c, preco):
                    descartados.append(f"{c.item}={preco:.3f}")
                    continue
                existe = s.exec(select(PrecoReferencia).where(PrecoReferencia.item == c.item, PrecoReferencia.fonte == fonte.nome,
                                                              PrecoReferencia.data_cotacao == c.data)).first()
                if existe:
                    continue
                s.add(PrecoReferencia(item=c.item, preco=preco, valor_original=c.valor, unidade_original=c.unidade,
                                      praca=c.praca, data_cotacao=c.data, fonte=fonte.nome, url=c.url or fonte.url))
                novos += 1
            s.commit()
            resultado[fonte.nome] = {"ok": True, "cotacoes": len(cotacoes), "novas": novos, "descartadas": descartados}
        except Exception as e:  # noqa: BLE001 — qualquer falha de fonte vira status, nunca derruba a coleta
            s.rollback()
            log.warning("fonte %s falhou: %s", fonte.nome, e)
            resultado[fonte.nome] = {"ok": False, "erro": f"{type(e).__name__}: {e}"[:300]}
    s.add(ColetaPrecos(resultado=resultado))
    s.commit()
    return resultado


def vigentes(s: Session) -> dict[str, PrecoReferencia]:
    """Cotação mais recente de cada item (entre todas as fontes)."""
    out: dict[str, PrecoReferencia] = {}
    for p in s.exec(select(PrecoReferencia).order_by(PrecoReferencia.data_cotacao, PrecoReferencia.coletado_em)).all():
        out[p.item] = p
    return out


def ultima_coleta(s: Session) -> ColetaPrecos | None:
    return s.exec(select(ColetaPrecos).order_by(ColetaPrecos.inicio.desc())).first()


def iniciar_agendador(fabrica_sessao, intervalo_h: float = 24, verificar_a_cada_s: float = 3600) -> threading.Thread:
    """Thread de fundo: coleta ao subir (se a última tiver mais de `intervalo_h`) e depois uma vez por dia."""
    def laco():
        while True:
            try:
                with fabrica_sessao() as s:
                    ult = ultima_coleta(s)
                    if ult is None or datetime.now() - ult.inicio >= timedelta(hours=intervalo_h):
                        coletar(s)
            except Exception as e:  # noqa: BLE001
                log.warning("agendador de preços: %s", e)
            relogio.sleep(verificar_a_cada_s)
    t = threading.Thread(target=laco, name="coleta-precos", daemon=True)
    t.start()
    return t
