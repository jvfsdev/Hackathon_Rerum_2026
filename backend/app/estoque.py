"""Estoque de insumos: saldo = última contagem + entradas − consumo estimado pelas dietas dos lotes (dia a dia).
Quem decide se o estoque é crítico são as regras EST (módulo estoque)."""
from collections import defaultdict
from datetime import date, timedelta

from sqlmodel import Session, select

from . import services
from .db.models import Lote, MovimentoEstoque
from .engine.engine import Motor


def _texto_kg(kg: float) -> str:
    return f"{kg / 1000:.1f} t".replace(".", ",") if abs(kg) >= 2000 else f"{kg:.0f} kg"


class Consumo:
    """Consumo diário (kg MN) de cada insumo pela fazenda, a partir da dieta em vigor e das vacas de cada lote."""

    def __init__(self, s: Session, fazenda_id: int, cat: dict):
        self.s, self.cat = s, cat
        self.lotes = [(lote, services.historico(s, lote.id))
                      for lote in s.exec(select(Lote).where(Lote.fazenda_id == fazenda_id)).all()]
        self._cache: dict[date, dict[str, float]] = {}

    def do_dia(self, d: date) -> dict[str, float]:
        if d not in self._cache:
            out: dict[str, float] = defaultdict(float)
            for lote, h in self.lotes:
                dieta = services.dieta_vigente(self.s, lote.id, d)
                vacas = services.vacas_em(h, lote, d)
                for i in services.itens_do_dia(dieta, d):
                    a = self.cat.get(i["alimento"])
                    if a is not None and not a.get("pastejo"):
                        out[a["id"]] += i["kg_mn"] * vacas
            self._cache[d] = dict(out)
        return self._cache[d]


def dias_ate_acabar(consumo: Consumo, item: str, saldo: float, d: date, horizonte: int = 120) -> float | None:
    """Dias até o saldo acabar, seguindo o consumo previsto dia a dia (transições de dieta incluídas).
    None = não acaba no horizonte (o item deixa de ser usado ou sobra)."""
    if saldo <= 0:
        return 0.0
    for k in range(1, horizonte + 1):
        uso = consumo.do_dia(d + timedelta(days=k)).get(item, 0.0)
        if uso >= saldo:
            return k - 1 + saldo / uso
        saldo -= uso
    return None


def situacao(s: Session, fazenda_id: int, d: date | None = None) -> dict:
    d = d or date.today()
    kb = services.kb()
    cat = services.catalogo(s, fazenda_id)
    consumo = Consumo(s, fazenda_id, cat)
    movs = s.exec(select(MovimentoEstoque).where(MovimentoEstoque.fazenda_id == fazenda_id, MovimentoEstoque.data <= d)
                  .order_by(MovimentoEstoque.data, MovimentoEstoque.id)).all()
    por_item: dict[str, list[MovimentoEstoque]] = defaultdict(list)
    for m in movs:
        por_item[m.item].append(m)
    hoje = consumo.do_dia(d)
    itens, alertas = [], []
    for item, lista in por_item.items():
        contagens = [m for m in lista if m.tipo == "contagem"]
        if contagens:
            base = contagens[-1]
            saldo, desde = base.kg, base.data          # contagem vale para o fim do dia em que foi feita
            entradas = sum(m.kg for m in lista if m.tipo == "entrada" and m.data > desde)
            dias = [desde + timedelta(days=k) for k in range(1, (d - desde).days + 1)]
        else:
            base, desde = None, lista[0].data
            saldo = 0.0
            entradas = sum(m.kg for m in lista if m.tipo == "entrada")
            dias = [desde + timedelta(days=k) for k in range((d - desde).days + 1)]
        usado = sum(consumo.do_dia(x).get(item, 0.0) for x in dias)
        saldo += entradas - usado
        diario = hoje.get(item, 0.0)
        restantes = dias_ate_acabar(consumo, item, saldo, d) if diario > 0 else None
        nome = cat.get(item, {}).get("nome", item)
        fatos = {"estoque.item_nome": nome, "estoque.saldo_kg": saldo, "estoque.consumo_kg_dia": diario,
                 "estoque.saldo_texto": _texto_kg(max(saldo, 0)), "estoque.consumo_texto": _texto_kg(diario)}
        if restantes is not None:
            fatos["estoque.dias_restantes"] = restantes
            pedido = d + timedelta(days=max(0, int(restantes) - kb.params["estoque_prazo_compra"]["valor"]))
            fatos["estoque.data_pedido"] = pedido.strftime("%d/%m")
        res = Motor(kb, ["estoque"]).executar(services.memoria(fatos, origem="sistema"))
        meus = [a.to_dict() | {"item": item} for a in res.alertas]
        alertas += meus
        itens.append({"item": item, "nome": nome, "saldo_kg": saldo, "consumo_kg_dia": diario,
                      "dias_restantes": restantes, "ultima_contagem": base.data.isoformat() if base else None,
                      "contagem_kg": base.kg if base else None, "entradas_kg": entradas, "consumo_periodo_kg": usado,
                      "alertas": meus})
    ordem = {"critico": 0, "atencao": 1, "informativo": 2}
    alertas.sort(key=lambda a: ordem[a["nivel"]])
    itens.sort(key=lambda i: (i["dias_restantes"] is None, i["dias_restantes"] or 0))
    sem_controle = [{"item": aid, "nome": cat[aid]["nome"], "consumo_kg_dia": kg}
                    for aid, kg in hoje.items() if aid not in por_item and kg > 0]
    return {"data": d.isoformat(), "itens": itens, "alertas": alertas, "sem_controle": sem_controle}


def registrar(s: Session, fazenda_id: int, item: str, tipo: str, kg: float, d: date, obs: str = "") -> MovimentoEstoque:
    if tipo not in ("contagem", "entrada"):
        raise services.EntradaInvalida("tipo deve ser contagem ou entrada")
    if item not in services.catalogo(s, fazenda_id):
        raise services.EntradaInvalida(f"insumo desconhecido: {item}")
    if not 0 <= kg < 5_000_000:
        raise services.EntradaInvalida("quantidade fora da faixa plausível")
    m = MovimentoEstoque(fazenda_id=fazenda_id, item=item, data=d, tipo=tipo, kg=kg, obs=obs)
    s.add(m)
    s.commit()
    s.refresh(m)
    return m
