"""Orquestra banco, motor de inferência, otimizador e monitor. Não contém regras de decisão."""
from datetime import date, timedelta

from sqlmodel import Session, select

from . import alertas
from .db.models import AlimentoFazenda, Dieta, Evento, Fazenda, Lote, PrecoAlimento, Registro, SessaoInferencia
from .engine.engine import Motor, Resultado
from .engine.explain import como
from .engine.rules_loader import BaseConhecimento, carregar
from .engine.working_memory import MemoriaTrabalho
from .monitor.fatos import HistoricoLote, del_em, fatos_monitoramento, serie_esperado
from .optimizer import lp

_KB: BaseConhecimento | None = None

MODULOS_AVALIACAO = ["classificacao", "exigencias", "verificacao"]
MODULOS_FORMULACAO = ["classificacao", "exigencias", "formulacao"]
MODULOS_ACOMPANHAMENTO = ["classificacao", "acompanhamento_diario", "acompanhamento_semanal", "acompanhamento_mensal", "meta"]


def kb() -> BaseConhecimento:
    global _KB
    if _KB is None:
        _KB = carregar()
    return _KB


def recarregar_kb() -> BaseConhecimento:
    global _KB
    _KB = carregar()
    return _KB


# ------------------------------------------------------------------ fatos de entrada
def fatos_lote(lote: Lote, d: date | None = None, h: HistoricoLote | None = None) -> dict:
    """Fatos lote.* (DEL e gestação avançam a partir da data de referência)."""
    d = d or date.today()
    dias = (d - lote.data_ref).days
    f = {"lote.estado": lote.estado, "lote.sistema": lote.sistema, "lote.grupo_genetico": lote.grupo_genetico,
         "lote.pv": lote.pv, "lote.n_vacas": lote.n_vacas}
    if lote.estado == "lactacao" and lote.del_ref is not None:
        f["lote.del"] = del_em(lote, d)
    if lote.dias_para_parto_ref is not None:
        f["lote.dias_para_parto"] = max(0, lote.dias_para_parto_ref - dias)
    if lote.dias_gestacao_ref:
        f["lote.dias_gestacao"] = lote.dias_gestacao_ref + dias
    elif lote.dias_gestacao_ref == 0:
        f["lote.dias_gestacao"] = 0
    for campo in ("fracao_primiparas", "ecc", "distancia_km", "relevo", "leite", "gordura", "proteina", "forrageira"):
        v = getattr(lote, campo)
        if v is not None:
            f[f"lote.{campo}"] = v
    if h is not None:
        lv = [h.valor("litros", d - timedelta(days=i)) for i in range(7)]
        vc = [h.valor("vacas", d - timedelta(days=i)) for i in range(7)]
        pares = [(a, b) for a, b in zip(lv, vc) if a and b]
        if pares:
            f["lote.leite"] = sum(a / b for a, b in pares) / len(pares)
        for ind in ("temp", "ur"):
            v = h.valor(ind, d)
            if v is not None:
                f[f"lote.{ind}"] = v
        ecc = h.serie("ecc", d, 42)
        if ecc:
            f["lote.ecc"] = ecc[-1][1]
        for ind in ("gordura", "proteina"):
            pts = h.serie(f"laudo_{ind}", d)
            if pts:
                f[f"lote.{ind}"] = pts[-1][1]
    return f


# ------------------------------------------------------------------ catálogo de alimentos (base + fazenda)
TIPOS_ALIMENTO = ("volumoso", "concentrado", "ureia", "mineral")
CF_ORIGEM_DADO = {"laboratorio": "cf_medido_recente", "tabela": "cf_tabela", "estimado": "cf_padrao"}


def _como_alimento(a: AlimentoFazenda) -> dict:
    params = kb().params
    return {"id": a.codigo, "nome": a.nome, "tipo": a.tipo, "ms": a.ms, "pb": a.pb, "fdn": a.fdn, "ndt": a.ndt,
            "ee": a.ee, "mm": a.mm, "fdnd": a.fdnd, "pastejo": a.pastejo,
            **{m: getattr(a, m) for m in ("ca", "p", "mg", "k", "na", "cl", "s")}, "max_pct_ms": a.max_pct_ms, "min_kg_ms": a.min_kg_ms,
            "max_kg_ms": a.max_kg_ms, "preco_kg_mn": 0.0, "fonte": a.fonte or a.origem_dado,
            "forca": {"laboratorio": "B", "tabela": "C", "estimado": "D"}[a.origem_dado],
            "cf": params[CF_ORIGEM_DADO[a.origem_dado]]["valor"], "da_fazenda": True, "ativo": a.ativo,
            "origem_dado": a.origem_dado}


def catalogo(s: Session | None = None, fazenda_id: int | None = None, so_ativos: bool = False) -> dict[str, dict]:
    """Alimentos disponíveis para a fazenda: os da base de conhecimento + os cadastrados por ela.
    Inativos continuam no catálogo (dietas antigas os usam), mas saem das listas de escolha com so_ativos."""
    cat = {aid: a | {"da_fazenda": False, "ativo": True,
                     "preco_ref": {"fonte": "valor de demonstração (sem fonte)", "data": None}}
           for aid, a in kb().alimentos.items()}
    if s is not None:
        from .referencias.coletor import vigentes
        for item, ref in vigentes(s).items():      # cotação pública mais recente substitui o valor de demonstração
            if item in cat:
                cat[item] = cat[item] | {"preco_kg_mn": ref.preco, "preco_ref": {
                    "fonte": ref.fonte, "data": ref.data_cotacao.isoformat(), "praca": ref.praca, "url": ref.url,
                    "valor_original": ref.valor_original, "unidade_original": ref.unidade_original}}
    if s is not None and fazenda_id is not None:
        for a in s.exec(select(AlimentoFazenda).where(AlimentoFazenda.fazenda_id == fazenda_id)).all():
            if a.ativo or not so_ativos:
                cat[a.codigo] = _como_alimento(a)
    return cat


def _slug(texto: str) -> str:
    import re
    import unicodedata
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "_", t).strip("_")[:40] or "insumo"


def criar_alimento(s: Session, fazenda: Fazenda, dados: dict) -> AlimentoFazenda:
    preco = dados.pop("preco_kg_mn", None)
    if not preco or preco <= 0:
        raise EntradaInvalida("informe o preço por kg de matéria natural")
    validar_alimento(dados)
    base_codigo = f"f{fazenda.id}_{_slug(dados['nome'])}"
    codigo, n = base_codigo, 2
    while s.exec(select(AlimentoFazenda).where(AlimentoFazenda.codigo == codigo)).first() or codigo in kb().alimentos:
        codigo, n = f"{base_codigo}_{n}", n + 1
    a = AlimentoFazenda(fazenda_id=fazenda.id, codigo=codigo, **dados)
    s.add(a)
    s.commit()
    registrar_precos(s, fazenda, {codigo: preco}, date.today(), dados.get("fonte") or "cadastro do insumo")
    s.refresh(a)
    return a


def atualizar_alimento(s: Session, a: AlimentoFazenda, dados: dict) -> AlimentoFazenda:
    """Atualiza a composição. O preço segue pelo histórico de preços (não é sobrescrito aqui)."""
    preco = dados.pop("preco_kg_mn", None)
    validar_alimento(dados)
    for k, v in dados.items():
        setattr(a, k, v)
    s.add(a)
    s.commit()
    if preco:
        registrar_precos(s, s.get(Fazenda, a.fazenda_id), {a.codigo: preco}, date.today(), dados.get("fonte") or "")
    s.refresh(a)
    return a


def e_silagem(alimento: dict) -> bool:
    return alimento.get("tipo") == "volumoso" and "silagem" in alimento.get("nome", "").lower()


def alimento_com_preco(aid: str, precos: dict | None = None, cat: dict | None = None) -> dict:
    """Alimento do catálogo com o preço da fazenda (se informado) no lugar do preço de referência."""
    cat = cat or kb().alimentos
    if aid not in cat:
        raise EntradaInvalida(f"alimento desconhecido: {aid}")
    a = cat[aid]
    if precos and aid in precos:
        return a | {"preco_kg_mn": precos[aid], "preco_origem": "fazenda"}
    return a | {"preco_origem": "referencia"}


def itens_dieta(itens: list[dict], precos: dict | None = None, cat: dict | None = None) -> list[dict]:
    return [{"alimento": alimento_com_preco(i["alimento"], precos, cat), "kg_mn": i["kg_mn"]} for i in itens if i.get("kg_mn")]


def validar_alimento(dados: dict) -> dict:
    """Confere a composição de um insumo informado pela fazenda (valores em % da MS)."""
    if not str(dados.get("nome", "")).strip():
        raise EntradaInvalida("informe o nome do insumo")
    if dados.get("tipo") not in TIPOS_ALIMENTO:
        raise EntradaInvalida(f"tipo deve ser um de: {', '.join(TIPOS_ALIMENTO)}")
    if dados.get("origem_dado") not in CF_ORIGEM_DADO:
        raise EntradaInvalida("origem do dado deve ser laboratorio, tabela ou estimado")
    if not 1 <= dados["ms"] <= 100:
        raise EntradaInvalida("MS deve estar entre 1 e 100% da matéria natural")
    limite_pb = 300 if dados["tipo"] == "ureia" else 100
    for campo, maximo in (("pb", limite_pb), ("fdn", 100), ("ndt", 100), ("ee", 100), ("mm", 100)):
        if not 0 <= dados.get(campo, 0) <= maximo:
            raise EntradaInvalida(f"{campo.upper()} deve estar entre 0 e {maximo}% da MS")
    if dados["tipo"] in ("volumoso", "concentrado"):
        soma = dados.get("pb", 0) + dados.get("fdn", 0) + dados.get("ee", 0) + dados.get("mm", 0)
        if soma > 105:
            raise EntradaInvalida(f"PB + FDN + EE + MM = {soma:.0f}% da MS: passa de 100%, confira os valores")
        if dados.get("ndt", 0) <= 0:
            raise EntradaInvalida("informe o NDT (energia) do alimento")
    if dados.get("max_pct_ms") is not None and not 0 < dados["max_pct_ms"] <= 100:
        raise EntradaInvalida("limite de inclusão deve estar entre 0 e 100% da MS")
    for m in ("ca", "p", "mg", "k", "na", "cl", "s"):
        if dados.get(m) is not None and not 0 <= dados[m] <= 70:
            raise EntradaInvalida(f"{m.upper()} deve estar entre 0 e 70% da MS")
    if dados.get("fdnd") is not None and not 10 <= dados["fdnd"] <= 90:
        raise EntradaInvalida("FDND deve estar entre 10 e 90% da FDN")
    if dados.get("pastejo") and dados["tipo"] != "volumoso":
        raise EntradaInvalida("só volumoso pode ser forragem de pastejo")
    return dados


# ------------------------------------------------------------------ preços da fazenda
def historico_precos(s: Session, fazenda_id: int) -> dict[str, list[PrecoAlimento]]:
    """Registros de preço por item, do mais recente para o mais antigo."""
    out: dict[str, list[PrecoAlimento]] = {}
    for p in s.exec(select(PrecoAlimento).where(PrecoAlimento.fazenda_id == fazenda_id)
                    .order_by(PrecoAlimento.data.desc(), PrecoAlimento.criado_em.desc())).all():
        out.setdefault(p.item, []).append(p)
    return out


def precos_fazenda(s: Session, fazenda_id: int) -> dict[str, float]:
    """Preço vigente (R$/kg MN) de cada alimento que a fazenda informou."""
    cat = catalogo(s, fazenda_id)
    return {item: regs[0].preco for item, regs in historico_precos(s, fazenda_id).items() if item in cat}


def registrar_precos(s: Session, fazenda: Fazenda, precos: dict[str, float], d: date, fonte: str) -> None:
    cat = catalogo(s, fazenda.id)
    for item, preco in precos.items():
        if item not in cat and item not in ("leite", "concentrado"):
            raise EntradaInvalida(f"item de preço desconhecido: {item}")
        if not 0 < preco < 1000:
            raise EntradaInvalida(f"{item}: preço R$ {preco} fora da faixa plausível")
        s.add(PrecoAlimento(fazenda_id=fazenda.id, item=item, preco=preco, data=d, fonte=fonte))
    s.flush()
    # leite e concentrado vigentes ficam também na fazenda (usados no acompanhamento econômico)
    hist = historico_precos(s, fazenda.id)
    if "leite" in hist:
        fazenda.preco_leite = hist["leite"][0].preco
    if "concentrado" in hist:
        fazenda.preco_concentrado = hist["concentrado"][0].preco
    s.add(fazenda)
    s.commit()


def cf_itens(itens: list[dict]) -> float:
    return min((i["alimento"].get("cf", kb().params["cf_tabela"]["valor"]) for i in itens), default=1.0)


class EntradaInvalida(ValueError):
    pass


def normalizar(fatos: dict) -> dict:
    """Converte e valida os tipos das entradas pelo que perguntas.yaml declara (número / opção)."""
    perguntas = kb().perguntas
    out = {}
    for nome, valor in fatos.items():
        p = perguntas.get(nome)
        if p and valor is not None:
            if p["tipo"] == "numero":
                try:
                    valor = float(str(valor).replace(",", "."))
                except ValueError:
                    raise EntradaInvalida(f"{nome}: '{valor}' não é número")
            elif p["tipo"] == "opcao" and valor not in p["opcoes"]:
                raise EntradaInvalida(f"{nome}: '{valor}' não é uma opção válida ({', '.join(p['opcoes'])})")
        out[nome] = valor
    return out


def memoria(fatos: dict, origem: str = "usuario", padroes: set | None = None) -> MemoriaTrabalho:
    wm = MemoriaTrabalho()
    params = kb().params
    cf_entrada = params["cf_medido_recente"]["valor"] if origem == "medido" else 1.0
    for nome, valor in normalizar(fatos).items():
        if padroes and nome in padroes:
            wm.declarar(nome, valor, cf=params["cf_padrao"]["valor"], origem="padrao",
                        nota="valor padrão (usuário não informou)")
        else:
            wm.declarar(nome, valor, cf=cf_entrada, origem=origem)
    return wm


def historico(s: Session, lote_id: int) -> HistoricoLote:
    regs = s.exec(select(Registro).where(Registro.lote_id == lote_id)).all()
    evs = s.exec(select(Evento).where(Evento.lote_id == lote_id)).all()
    return HistoricoLote(regs, evs)


def dieta_ativa(s: Session, lote_id: int) -> Dieta | None:
    return s.exec(select(Dieta).where(Dieta.lote_id == lote_id, Dieta.ativa == True)  # noqa: E712
                  .order_by(Dieta.versao.desc())).first()


def dieta_vigente(s: Session, lote_id: int, d: date) -> Dieta | None:
    """Versão da dieta em vigor na data d (a de início mais recente até d)."""
    return s.exec(select(Dieta).where(Dieta.lote_id == lote_id, Dieta.inicio <= d)
                  .order_by(Dieta.inicio.desc(), Dieta.versao.desc())).first()


def _pacote(resultado: Resultado, explicar: list[str]) -> dict:
    out = resultado.to_dict()
    out["explicacoes"] = {f: como(resultado, f) for f in explicar if f in resultado.wm}
    return out


def _salvar_sessao(s: Session, lote_id, tipo, resultado: dict, d: date | None = None) -> int:
    sessao = SessaoInferencia(lote_id=lote_id, tipo=tipo, kb_version=kb().versao, resultado=resultado, data_ref=d)
    s.add(sessao)
    s.commit()
    s.refresh(sessao)
    return sessao.id


# ------------------------------------------------------------------ avaliação (perfil + exigências + dieta)
EXPLICAR_AVALIACAO = ["perfil.fase", "exig.cms", "exig.ell_total", "exig.pb_pct_alvo", "meta.fdn_min", "meta.cnf_max",
                      "ver.razao_energia", "ver.razao_pb", "ver.risco_acidose", "parecer.dieta", "clima.itu"]


def avaliar(fatos: dict, itens: list[dict] | None, padroes: set | None = None, precos: dict | None = None,
            cat: dict | None = None) -> dict:
    wm = memoria(fatos, padroes=padroes)
    if itens:
        enriquecidos = itens_dieta(itens, precos, cat)
        wm.declarar("dieta.itens", enriquecidos, cf=cf_itens(enriquecidos), origem="tabela",
                    nota="composição dos alimentos de tabela")
    resultado = Motor(kb(), MODULOS_AVALIACAO).executar(wm)
    return _pacote(resultado, EXPLICAR_AVALIACAO)


def avaliar_lote(s: Session, lote: Lote, itens: list[dict] | None = None) -> dict:
    """Avalia o lote. Sem `itens`, avalia a DIETA ATIVA e sincroniza os alertas dela (episódios de verificação);
    com `itens`, é uma simulação e não mexe nos alertas."""
    h = historico(s, lote.id)
    dieta = dieta_ativa(s, lote.id)
    simulacao = itens is not None
    itens = itens if simulacao else (dieta.itens if dieta else None)
    fatos = fatos_lote(lote, date.today(), h)
    out = avaliar(fatos, itens, precos=precos_fazenda(s, lote.fazenda_id), cat=catalogo(s, lote.fazenda_id))
    out["sessao_id"] = _salvar_sessao(s, lote.id, "avaliacao", out)
    if not simulacao and dieta:
        resultado = alertas_resultado(out)
        alertas.sincronizar(s, kb(), lote.id, date.today(), resultado, out["sessao_id"], "verificacao",
                            modulos={"verificacao"}, causa_extra=f"dieta ativa v{dieta.versao} ({dieta.motivo})")
        out["episodios"] = episodios_por_regra(s, lote.id, "verificacao")
    return out


def alertas_resultado(pacote: dict) -> Resultado:
    from .engine.explain import resultado_de_dict
    from .engine.facts import Alerta
    r = resultado_de_dict(pacote)
    r.alertas = [Alerta(**{k: a[k] for k in ("regra", "nivel", "titulo", "causa", "acao", "categoria", "cf", "fonte",
                                             "forca", "status", "nota")}) for a in pacote["alertas"]]
    return r


def episodios_por_regra(s: Session, lote_id: int, origem: str) -> dict:
    from .db.models import AlertaDB
    return {a.regra: {"id": a.id, "estado": a.estado} for a in s.exec(select(AlertaDB).where(
        AlertaDB.lote_id == lote_id, AlertaDB.origem == origem, AlertaDB.estado.in_(alertas.ATIVOS))).all()}


# ------------------------------------------------------------------ formulação (PL)
def formular(fatos: dict, alimentos_ids: list[str], precos: dict | None = None, cat: dict | None = None) -> dict:
    base = kb()
    wm = memoria(fatos)
    wm.declarar("formulacao.solicitada", True, origem="sistema")
    motor = Motor(base, MODULOS_FORMULACAO)
    resultado = motor.executar(wm)
    v = wm.valor
    if v("exig.cms") is None or v("exig.ell_total") is None or v("exig.pb_pct_alvo") is None:
        out = _pacote(resultado, ["exig.cms", "exig.ell_total"])
        out["pl"] = {"status": "dados_insuficientes"}
        return out
    restricoes = {"cms": v("exig.cms"), "ms_min": v("pl.ms_min"), "ms_max": v("pl.ms_max"), "ell_min": v("pl.ell_min"),
                  "pb_min": v("pl.pb_min"), "pb_max": v("pl.pb_max"), "fdn_min": v("meta.fdn_min"),
                  "fdnf_min": v("meta.fdnf_min"), "cnf_max": v("meta.cnf_max"), "ee_max": v("meta.ee_max"),
                  "ureia_max": v("meta.ureia_max"), "fdn_max_kg": v("pl.fdn_max_kg"),
                  "cana_max_pct_volumoso": v("pl.cana_max_pct_volumoso"), "excluir_pastejo": v("pl.excluir_pastejo"),
                  "margem": base.params["pl_margem"]["valor"], "fator_ms_min": base.params["pl_fator_ms_min"]["valor"],
                  "teto_fibra_aplica": v("exig.cms_equacao") is not None, "ell_max": v("pl.ell_max"),
                  "dcad_max": v("pl.dcad_max")}
    alimentos = [alimento_com_preco(a, precos, cat) for a in alimentos_ids]
    excluidos = [a["nome"] for a in alimentos if restricoes["excluir_pastejo"] and a.get("pastejo")]
    wm.declarar("pl.alimentos_excluidos", excluidos, origem="sistema")
    pl, verificacao, iteracoes = _formular_ate_ponto_fixo(fatos, alimentos, restricoes, base.params, precos, cat)
    wm.declarar("pl.status", pl["status"], origem="sistema")
    wm.declarar("pl.restricoes_violadas", pl["restricoes_violadas"], origem="sistema")
    if pl["status"] in ("otimo", "parcial"):
        wm.declarar("pl.custo", pl["custo"], origem="sistema")
    motor.executar(wm, resultado)   # segunda fase: regras de diagnóstico do resultado do PL
    out = _pacote(resultado, ["exig.cms", "exig.ell_total", "exig.pb_pct_alvo", "pl.ell_min"])
    out["pl"] = {"status": pl["status"], "restricoes": restricoes, "restricoes_violadas": pl["restricoes_violadas"],
                 "iteracoes": iteracoes}
    if pl["status"] in ("otimo", "parcial"):
        out["pl"].update({"custo": pl["custo"], "itens": pl["itens_arredondados"], "composicao": pl["composicao"],
                          "deficit": pl.get("deficit")})
        out["verificacao"] = verificacao
    return out


def _formular_ate_ponto_fixo(fatos: dict, alimentos: list[dict], restricoes: dict, params: dict,
                             precos: dict | None = None, cat: dict | None = None, max_iter: int = 4):
    """Resolve o PL e verifica a dieta com as regras. Exigências que dependem da própria dieta (teto de consumo
    pela fibra, equação de CMS com cana…) só são conhecidas depois: se a verificação recalcular o CMS da dieta
    proposta, o PL é refeito com o menor CMS visto (monótono, então converge). Retorna (pl, verificação, iterações)."""
    iteracoes = []
    for _ in range(max_iter):
        pl = lp.formular(alimentos, restricoes)
        if pl["status"] not in ("otimo", "parcial"):
            return pl, None, iteracoes
        pl["itens_arredondados"] = [{"alimento": i["alimento"]["id"], "kg_mn": arredondar_kg(i["kg_mn"])} for i in pl["itens"]]
        verificacao = avaliar(fatos, pl["itens_arredondados"], precos=precos, cat=cat)   # a dieta do PL passa pela verificação
        cms_verif = verificacao["fatos"].get("exig.cms", {}).get("valor")
        iteracoes.append({"cms_usado": restricoes["cms"], "cms_da_dieta": cms_verif,
                          "parecer": verificacao["fatos"].get("parecer.dieta", {}).get("valor")})
        if cms_verif is None or cms_verif >= restricoes["cms"] * 0.999:
            return pl, verificacao, iteracoes
        cms = cms_verif
        restricoes.update({"cms": cms, "ms_min": cms * params["pl_fator_ms_min"]["valor"],
                           "ms_max": cms * params["fator_oferta_max"]["valor"]})
    return pl, verificacao, iteracoes


def arredondar_kg(kg: float) -> float:
    """Arredonda para pesar na fazenda com erro relativo ≤ 0,5% (abaixo da margem do PL): 2 casas a partir de
    1 kg, gramas abaixo disso (ureia e mineral são pesados em gramas)."""
    return round(kg, 2) if kg >= 1 else round(kg, 3)


def formular_lote(s: Session, lote: Lote, alimentos_ids: list[str], precos: dict | None = None) -> dict:
    """Formula com os preços vigentes da fazenda; `precos` (opcional) simula outros valores sem gravar."""
    vigentes = precos_fazenda(s, lote.fazenda_id) | (precos or {})
    out = formular(fatos_lote(lote, date.today(), historico(s, lote.id)), alimentos_ids, vigentes,
                   catalogo(s, lote.fazenda_id))
    out["sessao_id"] = _salvar_sessao(s, lote.id, "formulacao", out)
    return out


# ------------------------------------------------------------------ acompanhamento
EXPLICAR_ACOMPANHAMENTO = ["hipotese.queda_sustentada", "hipotese.causa_calor", "hipotese.causa_volumoso",
                           "hipotese.acidose", "hipotese.mastite", "laudo.nul", "mon.silagem_kg_mn_novo"]


def monitorar(s: Session, lote: Lote, d: date, h: HistoricoLote | None = None, persistir: bool = True) -> dict:
    """Acompanhamento do lote no dia d. Persistindo, reanalisar o dia desfaz o que o processamento automático
    tinha concluído a partir dele (dado corrigido → episódios revistos) e sincroniza os episódios."""
    base = kb()
    h = h or historico(s, lote.id)
    fazenda = s.get(Fazenda, lote.fazenda_id)
    dieta = dieta_vigente(s, lote.id, d)
    fatos = fatos_lote(lote, d, h)
    cat = catalogo(s, lote.fazenda_id)
    fatos.update(fatos_monitoramento(lote, fazenda, dieta, h, base.params, cat, d))
    fatos.update(_fatos_economicos(s, fazenda, dieta, cat, fatos))
    resultado = Motor(base, MODULOS_ACOMPANHAMENTO).executar(memoria(fatos, origem="medido"))
    out = _pacote(resultado, EXPLICAR_ACOMPANHAMENTO)
    if persistir:
        out["sessao_id"] = _salvar_sessao(s, lote.id, "acompanhamento", out, d)
        alertas.reverter_desde(s, lote.id, d)
        alertas.sincronizar(s, base, lote.id, d, resultado, out["sessao_id"], "acompanhamento")
        out["episodios"] = episodios_por_regra(s, lote.id, "acompanhamento")
    return out


def _fatos_economicos(s: Session, fazenda: Fazenda, dieta: Dieta | None, cat: dict, fatos: dict) -> dict:
    """Custo da dieta vigente (preços da fazenda), consumo medido pelas sobras, bonificação do laticínio e IOFC."""
    from .calc import economics
    from .calc.diet import composicao
    f: dict = {}
    preco_leite = fazenda.preco_leite
    laudo = {k.split(".", 1)[1]: v for k, v in fatos.items() if k.startswith("laudo.")}
    if fazenda.bonificacao and laudo:
        b = economics.bonificacao(laudo, fazenda.bonificacao)
        f["mon.bonificacao_rs_l"] = b["total"]
        preco_leite += b["total"]
        if b["perda_vs_maximo"] and fatos.get("mon.litros_lote"):
            f["mon.bonificacao_perda_rs_mes"] = b["perda_vs_maximo"] * fatos["mon.litros_lote"] * 30
            f["mon.bonificacao_detalhe"] = ", ".join(f"{p.upper()} {laudo[p]:g} → R$ {v:+.3f}/L"
                                                    for p, v in b["por_parametro"].items())
    f["mon.preco_leite_efetivo"] = preco_leite
    if dieta:
        comp = composicao(itens_dieta(dieta.itens, precos_fazenda(s, fazenda.id), cat))
        if comp.get("ms_kg"):
            f["mon.custo_dieta_vaca"] = comp["custo_vaca_dia"]
            if fatos.get("mon.sobras_mm3") is not None:   # consumo MEDIDO: oferta − sobras (% da oferta)
                f["mon.cms_medido"] = comp["ms_kg"] * (1 - fatos["mon.sobras_mm3"] / 100)
            lv = fatos.get("mon.litros_vaca")
            if lv:
                receita = lv * preco_leite
                f["mon.iofc"] = economics.iofc(lv, preco_leite, comp["custo_vaca_dia"])
                f["mon.alimento_pct_receita"] = 100 * comp["custo_vaca_dia"] / receita
    return f


def reprocessar(s: Session, lote: Lote, inicio: date, fim: date):
    """Roda o acompanhamento dia a dia (usado no seed para gerar o histórico de alertas)."""
    h = historico(s, lote.id)
    d = inicio
    while d <= fim:
        if lote.estado != "lactacao" or (del_em(lote, d) or 0) >= 1:   # lote ainda sem vacas paridas
            monitorar(s, lote, d, h)
        d += timedelta(days=1)


def serie_lote(s: Session, lote: Lote, ate: date | None = None) -> dict:
    """Séries para os gráficos de acompanhamento."""
    ate = ate or date.today()
    h = historico(s, lote.id)
    pontos = serie_esperado(lote, h, kb().params, ate)
    indicadores = {}
    for ind in ("escore_cocho", "sobras_pct", "ms_silagem", "ecc", "escore_fezes", "concentrado_kg_vaca", "laudo_nul", "laudo_gordura",
                "laudo_proteina", "laudo_lactose", "laudo_ccs", "laudo_cbt", "temp", "ur", "vacas"):
        indicadores[ind] = [{"data": d.isoformat(), "valor": v} for d, v in h.serie(ind, ate, 60)]
    eventos = [{"data": e.data_hora.isoformat(), "tipo": e.tipo, "descricao": e.descricao} for e in h.eventos]
    return {"producao": [p | {"data": p["data"].isoformat()} for p in pontos], "indicadores": indicadores, "eventos": eventos}
