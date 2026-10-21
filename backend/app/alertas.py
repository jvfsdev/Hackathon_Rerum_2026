"""Ciclo de vida dos alertas (episódios) e histórico de ações.

Um episódio nasce quando uma regra de alerta dispara para um lote, é atualizado enquanto a condição continua e
termina quando:
  - a condição deixa de valer por alguns dias seguidos  → "resolvido" (com o que mudou e as mudanças do período);
  - o dado que sustentava a regra venceu (laudo antigo) → "expirado" (não é resolução);
O usuário pode aceitar (vai para a tela da ação; o que salvar lá entra no histórico) ou recusar (com motivo).
Recusado não volta a incomodar, a menos que o problema se agrave.
"""
from datetime import date, datetime, time, timedelta

from sqlmodel import Session, select

from .db.models import AlertaDB, Dieta, Evento, HistoricoAlerta, Lote, Registro
from .engine.engine import Resultado
from .engine.explain import como
from .engine.rules_loader import BaseConhecimento

ATIVOS = ("aberto", "aceito", "recusado")
NIVEL = {"informativo": 0, "atencao": 1, "critico": 2}
PREFIXOS_CONTEXTO = ("ver.", "mon.", "laudo.", "clima.", "dieta.", "exig.", "meta.", "lote.")

# Tela onde a ação de cada tipo de alerta é registrada (rota relativa ao lote; ?evento= pré-seleciona o tipo).
DESTINOS = {
    "dieta": "dieta", "dieta_queda": "dieta", "cocho": "dieta", "economia": "dieta", "reproducao": "dieta",
    "condicao_corporal": "dieta", "formulacao": "dieta",
    "calor": "registro?evento=manejo_calor", "qualidade": "registro?evento=manejo_sanitario",
    "producao": "registro?evento=conferencia", "registro": "registro", "dados": "registro",
    "manejo": "registro?evento=secagem", "pasto": "registro?evento=manejo_pasto",
}
ROTULO_DESTINO = {"dieta": "ajustar a dieta", "registro?evento=manejo_calor": "registrar o manejo de calor",
                  "registro?evento=manejo_sanitario": "registrar o manejo sanitário",
                  "registro?evento=conferencia": "registrar a conferência (ordenha/registro)", "registro": "fazer o registro",
                  "registro?evento=secagem": "registrar a secagem", "registro?evento=manejo_pasto": "registrar o manejo do pasto"}


def destino(alerta: AlertaDB) -> str:
    rota = DESTINOS.get(alerta.categoria, "registro")
    sep = "&" if "?" in rota else "?"
    return f"/lotes/{alerta.lote_id}/{rota}{sep}alerta={alerta.id}"


def _quando(d: date) -> datetime:
    """Momento do processamento automático do dia d: agora, se for hoje; 18h, se for um dia passado (reprocessamento)."""
    return datetime.now() if d == date.today() else datetime.combine(d, time(18, 0))


def _historico(s: Session, alerta: AlertaDB, tipo: str, descricao: str, quando: datetime,
               automatico: bool = True, ref: dict | None = None):
    s.add(HistoricoAlerta(alerta_id=alerta.id, lote_id=alerta.lote_id, data_hora=quando, tipo=tipo,
                          descricao=descricao, automatico=automatico, ref=ref))


# ------------------------------------------------------------------ contexto (o que sustentou o alerta)
def _contexto(resultado: Resultado, regra: str, limite: int = 4) -> list[dict]:
    """Fatos que sustentaram a regra, dos mais próximos dela para os mais distantes (busca em largura na árvore
    "como?"): primeiro as premissas numéricas da própria regra (ex.: razão PB/alvo, NUL), depois o que as calculou."""
    entrada = next((t for t in resultado.traco if t["regra"] == regra), None)
    if not entrada:
        return []
    fila = [como(resultado, p["fato"]) for p in entrada["premissas"] if p["op"] != "ausente"]
    vistos, out = set(), []
    while fila and len(out) < limite:
        no = fila.pop(0)
        fato, valor = no.get("fato", ""), no.get("valor")
        if fato in vistos:
            continue
        vistos.add(fato)
        escalar = isinstance(valor, (int, float)) and not isinstance(valor, bool)
        if escalar and fato.startswith(PREFIXOS_CONTEXTO) and not fato.startswith("lote."):
            out.append({"fato": fato, "valor": valor})
        for r in no.get("regras", []):
            fila.extend(r["premissas"])
    return out


def _diferente(a, b) -> bool:
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(a - b) > max(1e-6, 0.005 * max(abs(a), abs(b)))
    return a != b


def _fmt(v) -> str:
    if isinstance(v, float):
        return f"{v:.2f}".rstrip("0").rstrip(".")
    return str(v)


# ------------------------------------------------------------------ sincronização com uma execução do motor
def sincronizar(s: Session, kb: BaseConhecimento, lote_id: int, d: date, resultado: Resultado, sessao_id: int | None,
                origem: str, modulos: set[str] | None = None, causa_extra: str = "") -> None:
    """Atualiza os episódios do lote a partir dos alertas de uma execução do motor no dia d."""
    modulo_de = {r["id"]: r["modulo"] for r in kb.regras}
    disparados = {(a.problema or a.regra): a for a in resultado.alertas
                  if modulos is None or modulo_de.get(a.regra) in modulos}
    abertos = {(a.problema or a.regra): a for a in s.exec(select(AlertaDB).where(
        AlertaDB.lote_id == lote_id, AlertaDB.origem == origem, AlertaDB.estado.in_(ATIVOS))).all()}
    quando = _quando(d) if origem == "acompanhamento" else datetime.now()

    for problema, a in disparados.items():
        regra = a.regra
        ep = abertos.get(problema)
        contexto = _contexto(resultado, regra)
        if ep is None:
            ep = AlertaDB(lote_id=lote_id, regra=regra, problema=problema, modulo=modulo_de.get(regra, ""), origem=origem, nivel=a.nivel,
                          titulo=a.titulo, causa=a.causa, acao=a.acao, categoria=a.categoria, cf=a.cf, fonte=a.fonte,
                          forca=a.forca, suprimido=a.status == "suprimido", nota=a.nota, aberto_em=d,
                          ultima_ocorrencia=d, sessao_id=sessao_id, contexto=contexto)
            s.add(ep)
            s.flush()
            base = "; ".join(f"{c['fato']} = {_fmt(c['valor'])}" for c in contexto)
            _historico(s, ep, "aberto", f"{a.titulo}" + (f" ({base})" if base else ""), quando)
            continue
        agravou = NIVEL[a.nivel] > NIVEL[ep.nivel]
        if agravou:
            _historico(s, ep, "agravado", f"Nível {ep.nivel} → {a.nivel}: {a.titulo}", quando)
            ep.nivel = a.nivel
            if ep.estado == "recusado":
                ep.estado, ep.estado_em = "aberto", d
                _historico(s, ep, "reaberto", "Recusado anteriormente, mas o problema se agravou", quando)
        elif NIVEL[a.nivel] < NIVEL[ep.nivel] and ep.regra != regra:
            _historico(s, ep, "atenuado", f"Nível {ep.nivel} → {a.nivel}: {a.titulo}", quando)
            ep.nivel = a.nivel
        ep.regra, ep.modulo = regra, modulo_de.get(regra, ep.modulo)
        ep.titulo, ep.causa, ep.acao, ep.cf = a.titulo, a.causa, a.acao, a.cf
        ep.suprimido, ep.nota = a.status == "suprimido", a.nota
        ep.ultima_ocorrencia, ep.ocorrencias, ep.sessao_id = d, ep.ocorrencias + 1, sessao_id
        ep.contexto = contexto or ep.contexto
        s.add(ep)

    dias_resolver = kb.params["resolucao_dias"]["valor"]
    atuais = {f.nome: f.valor for f in resultado.wm.fatos.values()}
    for problema, ep in abertos.items():
        if problema in disparados:
            continue
        if (d - ep.ultima_ocorrencia).days < dias_resolver.get(ep.modulo, 1):
            continue
        _encerrar(s, ep, d, atuais, quando, causa_extra)
    s.commit()


def _encerrar(s: Session, ep: AlertaDB, d: date, atuais: dict, quando: datetime, causa_extra: str = ""):
    """Resolve ou expira o episódio explicando o que mudou e o que aconteceu no período."""
    sem_dado = [c["fato"] for c in ep.contexto if c["fato"].startswith("laudo.") and c["fato"] not in atuais]
    sumiu = [c["fato"] for c in ep.contexto if c["fato"] not in atuais and not c["fato"].startswith("laudo.")]
    mudou = []
    for c in ep.contexto:
        if c["fato"] in atuais and _diferente(atuais[c["fato"]], c["valor"]):
            mudou.append(f"{c['fato']}: {_fmt(c['valor'])} → {_fmt(atuais[c['fato']])}")
    causas = _mudancas_no_periodo(s, ep, d)
    if causa_extra:
        causas.insert(0, causa_extra)
    if sem_dado:
        ep.estado = "expirado"
        texto = f"Sem dado atual para confirmar ({', '.join(sem_dado)}): o laudo que sustentava o alerta venceu."
    else:
        ep.estado = "resolvido"
        detalhes = mudou + [f"{f}: não se aplica mais" for f in sumiu]
        texto = "A condição deixou de valer" + (f" ({'; '.join(detalhes)})" if detalhes else "") + "."
    if causas:
        texto += " Mudanças no período: " + "; ".join(causas) + "."
    elif ep.estado == "resolvido":
        texto += " Nenhuma ação ou mudança registrada no período."
    ep.estado_em, ep.resolucao = d, texto
    s.add(ep)
    _historico(s, ep, ep.estado, texto, quando)


def _mudancas_no_periodo(s: Session, ep: AlertaDB, d: date) -> list[str]:
    out = []
    inicio = datetime.combine(ep.aberto_em, time.min)
    for h in s.exec(select(HistoricoAlerta).where(HistoricoAlerta.alerta_id == ep.id,
                                                  HistoricoAlerta.tipo == "acao_registrada")).all():
        out.append(f"ação registrada em {h.data_hora:%d/%m}: {h.descricao}")
    for dieta in s.exec(select(Dieta).where(Dieta.lote_id == ep.lote_id, Dieta.inicio > ep.aberto_em,
                                            Dieta.inicio <= d)).all():
        out.append(f"nova dieta v{dieta.versao} em {dieta.inicio:%d/%m} ({dieta.motivo})")
    for ev in s.exec(select(Evento).where(Evento.lote_id == ep.lote_id, Evento.data_hora >= inicio,
                                          Evento.data_hora <= datetime.combine(d, time.max))).all():
        out.append(f"{ev.tipo.replace('_', ' ')} em {ev.data_hora:%d/%m}" + (f" ({ev.descricao})" if ev.descricao else ""))
    if ep.modulo == "acompanhamento_mensal":
        laudos = s.exec(select(Registro).where(Registro.lote_id == ep.lote_id, Registro.indicador.like("laudo_%"),
                                               Registro.data > ep.aberto_em, Registro.data <= d)).all()
        if laudos:
            out.append(f"novo laudo em {max(r.data for r in laudos):%d/%m}")
    return out


def reverter_desde(s: Session, lote_id: int, d0: date) -> None:
    """Desfaz o processamento automático do acompanhamento a partir de d0 (dado corrigido ou registro retroativo).
    Ações do usuário (aceite, recusa, ação registrada) nunca são apagadas."""
    corte = datetime.combine(d0, time.min)
    eps = s.exec(select(AlertaDB).where(AlertaDB.lote_id == lote_id, AlertaDB.origem == "acompanhamento")).all()
    for ep in eps:
        hist = s.exec(select(HistoricoAlerta).where(HistoricoAlerta.alerta_id == ep.id)).all()
        tem_usuario = any(not h.automatico for h in hist)
        for h in hist:
            # a abertura de um episódio em que o usuário já agiu faz parte da história dele: fica
            if h.automatico and h.data_hora >= corte and not (tem_usuario and h.tipo == "aberto"):
                s.delete(h)
    s.flush()
    for ep in eps:
        restantes = s.exec(select(HistoricoAlerta).where(HistoricoAlerta.alerta_id == ep.id)
                           .order_by(HistoricoAlerta.data_hora)).all()
        if ep.aberto_em >= d0 and not restantes:
            s.delete(ep)
            continue
        if ep.estado in ("resolvido", "expirado") and ep.estado_em and ep.estado_em >= d0:
            usuario = [h for h in restantes if not h.automatico and h.tipo in ("aceito", "recusado")]
            ep.estado = usuario[-1].tipo if usuario else "aberto"
            ep.estado_em, ep.resolucao = (usuario[-1].data_hora.date() if usuario else None), None
        if ep.ultima_ocorrencia >= d0:
            ep.ultima_ocorrencia = max(ep.aberto_em, d0 - timedelta(days=1))
        s.add(ep)
    s.commit()


# ------------------------------------------------------------------ ações do usuário
def aceitar(s: Session, ep: AlertaDB, observacao: str = "", quando: datetime | None = None) -> str:
    if ep.estado not in ("aberto", "recusado"):
        raise ValueError(f"alerta está {ep.estado}")
    quando = quando or datetime.now()
    rota = DESTINOS.get(ep.categoria, "registro")
    ep.estado, ep.estado_em = "aceito", quando.date()
    s.add(ep)
    _historico(s, ep, "aceito", f"Recomendação aceita: {ep.acao.rstrip('.')}" + (f" — {observacao}" if observacao else "")
               + f". Próximo passo: {ROTULO_DESTINO.get(rota, 'registrar a ação')}.", quando, automatico=False)
    s.commit()
    return destino(ep)


def recusar(s: Session, ep: AlertaDB, motivo: str, quando: datetime | None = None) -> None:
    if ep.estado not in ("aberto", "aceito"):
        raise ValueError(f"alerta está {ep.estado}")
    if not motivo.strip():
        raise ValueError("informe o motivo da recusa")
    quando = quando or datetime.now()
    ep.estado, ep.estado_em = "recusado", quando.date()
    s.add(ep)
    _historico(s, ep, "recusado", f"Recomendação recusada: {motivo.strip()}", quando, automatico=False)
    s.commit()


def registrar_acao(s: Session, alerta_id: int | None, lote_id: int, descricao: str, ref: dict,
                   quando: datetime | None = None) -> None:
    """Liga o que o usuário salvou (dieta, evento, registro) ao alerta aceito que o levou até a tela."""
    if not alerta_id:
        return
    ep = s.get(AlertaDB, alerta_id)
    if ep is None or ep.lote_id != lote_id:
        raise ValueError("alerta não pertence a este lote")
    quando = quando or datetime.now()
    if ep.estado == "aberto":       # registrou direto, sem passar pelo aceite: conta como aceite
        ep.estado, ep.estado_em = "aceito", quando.date()
        _historico(s, ep, "aceito", "Recomendação aceita ao registrar a ação", quando, automatico=False)
    _historico(s, ep, "acao_registrada", descricao, quando, automatico=False, ref=ref)
    s.add(ep)
    s.commit()


def historico_do(s: Session, alerta_id: int) -> list[HistoricoAlerta]:
    return s.exec(select(HistoricoAlerta).where(HistoricoAlerta.alerta_id == alerta_id)
                  .order_by(HistoricoAlerta.data_hora, HistoricoAlerta.id)).all()


def lote_de(s: Session, ep: AlertaDB) -> Lote | None:
    return s.get(Lote, ep.lote_id)
