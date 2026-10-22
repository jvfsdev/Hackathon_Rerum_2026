"""Cadastro: fazendas, lotes, dietas, registros, eventos e alertas."""
from datetime import date, datetime, timedelta

from fastapi import APIRouter, HTTPException
from sqlmodel import select

from .. import alertas, services
from ..db.models import AlertaDB, AlimentoFazenda, Dieta, Evento, Fazenda, HistoricoAlerta, Lote, Registro, sessao
from .schemas import (AceitarIn, AlimentoIn, BonificacaoIn, DietaIn, EventoIn, ImportacaoIn, LoteIn, MovimentoEstoqueIn,
                      PrecosIn, RecusarIn, RegistroIn)

router = APIRouter()


def _lote(s, lote_id: int) -> Lote:
    lote = s.get(Lote, lote_id)
    if not lote:
        raise HTTPException(404, "lote não encontrado")
    return lote


@router.get("/fazendas")
def listar_fazendas():
    with sessao() as s:
        return s.exec(select(Fazenda)).all()


@router.get("/fazendas/{fazenda_id}/painel")
def painel(fazenda_id: int):
    """Resumo por lote: produção de hoje × esperado, custo, dieta ativa e alertas recentes."""
    hoje = date.today()
    with sessao() as s:
        fazenda = s.get(Fazenda, fazenda_id)
        if not fazenda:
            raise HTTPException(404, "fazenda não encontrada")
        cards = []
        for lote in s.exec(select(Lote).where(Lote.fazenda_id == fazenda_id)).all():
            serie = services.serie_lote(s, lote, hoje)["producao"]
            ultimo = serie[-1] if serie else None
            dieta = services.dieta_ativa(s, lote.id)
            comp = None
            if dieta:
                from ..calc.diet import composicao
                comp = composicao(services.itens_dieta(dieta.itens, services.precos_fazenda(s, fazenda_id),
                                                       services.catalogo(s, fazenda_id)))
            pendentes = s.exec(select(AlertaDB).where(AlertaDB.lote_id == lote.id, AlertaDB.suprimido == False,  # noqa: E712
                                                      AlertaDB.estado.in_(("aberto", "aceito")))
                               .order_by(AlertaDB.ultima_ocorrencia.desc())).all()
            contagem = {n: sum(a.nivel == n for a in pendentes) for n in ("critico", "atencao", "informativo")}
            cards.append({"lote": lote, "hoje": ultimo, "serie": serie[-30:], "dieta": dieta,
                          "custo_dieta": comp.get("custo_vaca_dia") if comp else None, "alertas": contagem,
                          "principal": pendentes and sorted(pendentes, key=lambda a: -alertas.NIVEL[a.nivel])[0]})
        from .. import estoque
        return {"fazenda": fazenda, "data": hoje, "lotes": cards, "estoque": estoque.situacao(s, fazenda_id)["alertas"]}


@router.get("/fazendas/{fazenda_id}/precos")
def listar_precos(fazenda_id: int):
    """Preço vigente de cada alimento (da fazenda ou de referência) com histórico; leite e concentrado."""
    with sessao() as s:
        fazenda = s.get(Fazenda, fazenda_id)
        if not fazenda:
            raise HTTPException(404, "fazenda não encontrada")
        hist = services.historico_precos(s, fazenda_id)

        def linha(item, referencia, **extra):
            regs = hist.get(item, [])
            return {"id": item, "preco_referencia": referencia, "preco": regs[0].preco if regs else referencia,
                    "origem": "fazenda" if regs else "referencia", "data": regs[0].data if regs else None,
                    "fonte": regs[0].fonte if regs else "", **extra,
                    "historico": [{"data": r.data, "preco": r.preco, "fonte": r.fonte} for r in regs[:12]]}

        alimentos = [linha(a["id"], None if a["da_fazenda"] else a["preco_kg_mn"], nome=a["nome"], tipo=a["tipo"],
                           ms=a["ms"], da_fazenda=a["da_fazenda"])
                     for a in services.catalogo(s, fazenda_id, so_ativos=True).values()]
        return {"leite": linha("leite", None) | {"preco": fazenda.preco_leite},
                "concentrado": linha("concentrado", None) | {"preco": fazenda.preco_concentrado},
                "alimentos": alimentos}


@router.put("/fazendas/{fazenda_id}/precos")
def atualizar_precos(fazenda_id: int, dados: PrecosIn):
    """Registra novos preços (o anterior fica no histórico). Valem para verificação, formulação e acompanhamento."""
    with sessao() as s:
        fazenda = s.get(Fazenda, fazenda_id)
        if not fazenda:
            raise HTTPException(404, "fazenda não encontrada")
        services.registrar_precos(s, fazenda, dados.precos, dados.data or date.today(), dados.fonte)
    return listar_precos(fazenda_id)


def _insumo(s, fazenda_id: int, codigo: str) -> AlimentoFazenda:
    a = s.exec(select(AlimentoFazenda).where(AlimentoFazenda.fazenda_id == fazenda_id,
                                             AlimentoFazenda.codigo == codigo)).first()
    if not a:
        raise HTTPException(404, "insumo da fazenda não encontrado (os da base de conhecimento não são editáveis)")
    return a


@router.get("/fazendas/{fazenda_id}/alimentos")
def listar_insumos(fazenda_id: int, incluir_inativos: bool = False):
    """Catálogo da fazenda: alimentos da base de conhecimento + insumos cadastrados (com preço vigente)."""
    with sessao() as s:
        precos = services.precos_fazenda(s, fazenda_id)
        cat = services.catalogo(s, fazenda_id, so_ativos=not incluir_inativos)
        return [services.alimento_com_preco(aid, precos, cat) for aid in cat]


@router.post("/fazendas/{fazenda_id}/alimentos")
def criar_insumo(fazenda_id: int, dados: AlimentoIn):
    with sessao() as s:
        fazenda = s.get(Fazenda, fazenda_id)
        if not fazenda:
            raise HTTPException(404, "fazenda não encontrada")
        a = services.criar_alimento(s, fazenda, dados.model_dump())
        return services.catalogo(s, fazenda_id)[a.codigo]


@router.put("/fazendas/{fazenda_id}/alimentos/{codigo}")
def editar_insumo(fazenda_id: int, codigo: str, dados: AlimentoIn):
    with sessao() as s:
        a = services.atualizar_alimento(s, _insumo(s, fazenda_id, codigo), dados.model_dump())
        return services.catalogo(s, fazenda_id)[a.codigo]


@router.post("/fazendas/{fazenda_id}/alimentos/{codigo}/{acao}")
def ativar_insumo(fazenda_id: int, codigo: str, acao: str):
    """acao = desativar | reativar. Desativado sai das listas de escolha; dietas antigas continuam válidas."""
    if acao not in ("desativar", "reativar"):
        raise HTTPException(404, "ação inválida")
    with sessao() as s:
        a = _insumo(s, fazenda_id, codigo)
        a.ativo = acao == "reativar"
        s.add(a)
        s.commit()
        return {"codigo": codigo, "ativo": a.ativo}


@router.get("/fazendas/{fazenda_id}/bonificacao")
def obter_bonificacao(fazenda_id: int):
    with sessao() as s:
        faz = s.get(Fazenda, fazenda_id)
        if not faz:
            raise HTTPException(404, "fazenda não encontrada")
        return {"tabela": faz.bonificacao or {}}


@router.put("/fazendas/{fazenda_id}/bonificacao")
def salvar_bonificacao(fazenda_id: int, dados: BonificacaoIn):
    """Tabela de bonificação/penalização por qualidade do laticínio (faixas por parâmetro, em R$/L)."""
    validos = {"ccs", "cbt", "gordura", "proteina", "lactose", "solidos"}
    for p, faixas in dados.tabela.items():
        if p not in validos:
            raise HTTPException(422, f"parâmetro desconhecido: {p}")
        for f in faixas:
            if "rs_l" not in f or not -1 < float(f["rs_l"]) < 1:
                raise HTTPException(422, f"{p}: cada faixa precisa de 'rs_l' entre −1 e 1 R$/L")
            if f.get("min") is not None and f.get("max") is not None and f["min"] > f["max"]:
                raise HTTPException(422, f"{p}: faixa com mínimo maior que o máximo")
    with sessao() as s:
        faz = s.get(Fazenda, fazenda_id)
        if not faz:
            raise HTTPException(404, "fazenda não encontrada")
        faz.bonificacao = {p: f for p, f in dados.tabela.items() if f}
        s.add(faz)
        s.commit()
        return {"tabela": faz.bonificacao}


@router.get("/modelos/faixas")
def faixas_registro():
    """Faixas plausíveis por indicador (o celular guarda para validar mesmo sem conexão)."""
    from ..importacao import FAIXAS, LITROS_VACA_MAX
    return {"faixas": FAIXAS, "litros_vaca_max": LITROS_VACA_MAX}


@router.get("/modelos/importacao/{tipo}")
def modelo_importacao(tipo: str):
    from fastapi.responses import PlainTextResponse
    from ..importacao import MODELOS
    if tipo not in MODELOS:
        raise HTTPException(404, "modelos: diario, laudo")
    return PlainTextResponse(MODELOS[tipo], media_type="text/csv",
                             headers={"Content-Disposition": f"attachment; filename=modelo_{tipo}.csv"})


@router.post("/lotes/{lote_id}/importar")
def importar(lote_id: int, dados: ImportacaoIn):
    """Prévia (confirmar=false) ou gravação (confirmar=true) de uma planilha CSV de registros/laudos."""
    from ..importacao import ler
    try:
        lido = ler(dados.conteudo)
    except ValueError as e:
        raise HTTPException(422, str(e))
    resumo = {k: lido[k] for k in ("erros", "colunas", "periodo", "linhas")} | {
        "registros": len(lido["registros"]), "amostra": lido["registros"][:8]}
    if not dados.confirmar or not lido["registros"]:
        return resumo | {"gravado": False}
    with sessao() as s:
        lote = _lote(s, lote_id)
        for r in lido["registros"]:
            existente = s.exec(select(Registro).where(Registro.lote_id == lote_id, Registro.data == r["data"],
                                                      Registro.indicador == r["indicador"])).first()
            if existente:
                existente.valor, existente.atualizado_em, existente.metodo = r["valor"], datetime.now(), "importação CSV"
                s.add(existente)
            else:
                s.add(Registro(lote_id=lote_id, metodo="importação CSV", **r))
        s.commit()
        services.reprocessar(s, lote, lido["periodo"][0], date.today())
        pendentes = s.exec(select(AlertaDB).where(AlertaDB.lote_id == lote_id, AlertaDB.estado.in_(("aberto", "aceito")))).all()
    return resumo | {"gravado": True, "alertas_pendentes": len(pendentes)}


@router.get("/lotes")
def listar_lotes(fazenda_id: int | None = None):
    with sessao() as s:
        q = select(Lote)
        if fazenda_id:
            q = q.where(Lote.fazenda_id == fazenda_id)
        return s.exec(q).all()


@router.get("/lotes/{lote_id}")
def obter_lote(lote_id: int):
    with sessao() as s:
        lote = _lote(s, lote_id)
        return {"lote": lote, "fatos": services.fatos_lote(lote, date.today(), services.historico(s, lote.id)),
                "dieta": services.dieta_ativa(s, lote.id)}


@router.post("/lotes")
def criar_lote(dados: LoteIn):
    with sessao() as s:
        lote = Lote(**dados.model_dump(), data_ref=date.today())
        s.add(lote)
        s.commit()
        s.refresh(lote)
        return lote


@router.put("/lotes/{lote_id}")
def atualizar_lote(lote_id: int, dados: LoteIn):
    with sessao() as s:
        lote = _lote(s, lote_id)
        for k, v in dados.model_dump().items():
            setattr(lote, k, v)
        lote.data_ref = date.today()
        s.add(lote)
        s.commit()
        s.refresh(lote)
        return lote


@router.get("/lotes/{lote_id}/dietas")
def listar_dietas(lote_id: int):
    with sessao() as s:
        return s.exec(select(Dieta).where(Dieta.lote_id == lote_id).order_by(Dieta.versao.desc())).all()


@router.post("/lotes/{lote_id}/dietas")
def nova_dieta(lote_id: int, dados: DietaIn):
    """Cria nova versão da dieta (com motivo) e anexa o parecer da inferência."""
    with sessao() as s:
        lote = _lote(s, lote_id)
        anteriores = s.exec(select(Dieta).where(Dieta.lote_id == lote_id)).all()
        ativa = services.dieta_ativa(s, lote_id)
        for d in anteriores:
            d.ativa = False
            s.add(d)
        itens = [i.model_dump() for i in dados.itens]
        parecer = services.avaliar_lote(s, lote, itens)
        cat = services.catalogo(s, lote.fazenda_id)
        silagem = next((i for i in itens if services.e_silagem(cat.get(i["alimento"], {}))), None)
        ms_ref = None
        if silagem:
            ms = services.historico(s, lote_id).serie("ms_silagem", date.today(), 14)
            ms_ref = ms[-1][1] if ms else cat[silagem["alimento"]]["ms"]
        versao = max((d.versao for d in anteriores), default=0) + 1
        hoje = date.today()
        transicao = None
        if ativa:
            fator = services.fator_proporcional(ativa.itens, itens)
            if fator and services.em_transicao(ativa, hoje):
                # ajuste de oferta no meio de uma troca gradual: a troca continua, com os dias que faltam × fator
                transicao = services.escalar_transicao(ativa.transicao, fator, hoje)
            elif dados.gradual:
                # a troca parte do que está no cocho hoje (a mistura do dia, se já havia uma troca em andamento)
                transicao = services.planejar_transicao(lote, services.itens_do_dia(ativa, hoje), itens, cat, hoje,
                                                        ativa.versao)
        dieta = Dieta(lote_id=lote_id, versao=versao, itens=itens, transicao=transicao,
                      origem=dados.origem, motivo=dados.motivo, inicio=date.today(), ativa=True, ms_silagem_ref=ms_ref,
                      parecer={"parecer": parecer["fatos"].get("parecer.dieta", {}).get("valor"),
                               "sessao_id": parecer["sessao_id"], "kb_version": parecer["kb_version"]})
        s.add(dieta)
        s.commit()
        s.refresh(dieta)
        _acao(s, dados.alerta_id, lote_id, f"Nova dieta v{dieta.versao}: {dieta.motivo or 'ajuste'}"
              + f" (parecer: {dieta.parecer.get('parecer') or '—'})", {"dieta_id": dieta.id})
        services.avaliar_lote(s, lote)          # alertas da dieta ativa: os que a nova versão corrige são resolvidos
        s.refresh(dieta)
        return dieta.model_dump()


@router.post("/lotes/{lote_id}/registros")
def registrar(lote_id: int, dados: RegistroIn):
    """Grava os valores do dia (substitui o mesmo indicador na mesma data) e roda o acompanhamento. Só os indicadores
    enviados são tocados: leite à noite e cocho de manhã podem ser registrados em envios separados."""
    with sessao() as s:
        lote = _lote(s, lote_id)
        if not dados.valores:
            raise HTTPException(422, "nenhum valor para registrar")
        if set(dados.somar) - SOMAVEIS:
            raise HTTPException(422, f"só dá para somar: {', '.join(sorted(SOMAVEIS))}")
        from ..importacao import LITROS_VACA_MAX, problema_valor
        dia = {r.indicador: r for r in s.exec(select(Registro).where(Registro.lote_id == lote_id, Registro.data == dados.data)).all()}
        finais = {}
        for ind, valor in dados.valores.items():                  # valida tudo antes de gravar qualquer coisa
            final = valor + dia[ind].valor if ind in dados.somar and ind in dia else valor
            erro = problema_valor(ind, final) or (problema_valor(ind, valor) if ind not in dados.somar else None)
            if ind in dados.somar and valor <= 0:
                erro = f"{ind}: a parcela a somar precisa ser maior que zero"
            if erro:
                raise HTTPException(422, erro)
            finais[ind] = final
        litros = finais.get("litros", dia["litros"].valor if "litros" in dia else None)
        vacas = finais.get("vacas", dia["vacas"].valor if "vacas" in dia else None)
        if litros and vacas and litros / vacas > LITROS_VACA_MAX:
            raise HTTPException(422, f"{litros:g} L para {vacas:g} vacas dá {litros / vacas:.0f} L por vaca: confira os números")
        for ind, valor in dados.valores.items():
            existente = s.exec(select(Registro).where(Registro.lote_id == lote_id, Registro.data == dados.data,
                                                      Registro.indicador == ind)).first()
            somar = ind in dados.somar
            if existente:
                # 2ª ordenha (ou 2º trato): soma ao total do dia e guarda as parcelas; senão substitui (correção)
                if somar:
                    partes = existente.texto or f"{existente.valor:g}"
                    existente.valor, existente.texto = existente.valor + valor, f"{partes} + {valor:g}"
                else:
                    existente.valor, existente.texto = valor, None
                existente.atualizado_em = datetime.now()
                existente.metodo = dados.metodo or existente.metodo
                s.add(existente)
            else:
                s.add(Registro(lote_id=lote_id, data=dados.data, indicador=ind, valor=valor, metodo=dados.metodo))
        s.commit()
        _acao(s, dados.alerta_id, lote_id, f"Registro de {dados.data:%d/%m}: " + ", ".join(
            f"{k} {'+' if k in dados.somar else ''}{v:g}" for k, v in dados.valores.items()), {"registro_data": dados.data.isoformat()})
        out = services.monitorar(s, lote, dados.data)
        hoje = date.today()
        if dados.data < hoje:   # registro retroativo: os dias seguintes dependem dele (série, corrida, médias)
            services.reprocessar(s, lote, dados.data + timedelta(days=1), hoje)
        return out


SOMAVEIS = {"litros", "trato_kg"}


@router.delete("/lotes/{lote_id}/registros")
def apagar_registro(lote_id: int, data: date, indicador: str):
    """Remove um valor digitado errado e refaz o acompanhamento a partir daquela data."""
    with sessao() as s:
        lote = _lote(s, lote_id)
        r = s.exec(select(Registro).where(Registro.lote_id == lote_id, Registro.data == data,
                                          Registro.indicador == indicador)).first()
        if not r:
            raise HTTPException(404, "registro não encontrado")
        s.delete(r)
        s.commit()
        services.reprocessar(s, lote, data, date.today())
        return {"apagado": True, "data": data, "indicador": indicador}


@router.get("/lotes/{lote_id}/registros")
def listar_registros(lote_id: int, desde: date | None = None):
    with sessao() as s:
        q = select(Registro).where(Registro.lote_id == lote_id)
        if desde:
            q = q.where(Registro.data >= desde)
        return s.exec(q.order_by(Registro.data)).all()


@router.post("/lotes/{lote_id}/eventos")
def registrar_evento(lote_id: int, dados: EventoIn):
    """Registra um evento. Movimentação com nº de vacas atualiza o cadastro do lote (e do outro lote, se informado)."""
    with sessao() as s:
        lote = _lote(s, lote_id)
        ev = Evento(lote_id=lote_id, **dados.model_dump(exclude={"alerta_id", "vacas", "outro_lote_id"}))
        if dados.tipo == "movimentacao" and dados.vacas:
            outro = _lote(s, dados.outro_lote_id) if dados.outro_lote_id else None
            if outro is not None and outro.id == lote_id:
                raise HTTPException(422, "o outro lote precisa ser diferente")
            antes = lote.n_vacas
            if antes + dados.vacas < 1 or (outro is not None and outro.n_vacas - dados.vacas < 0):
                raise HTTPException(422, "o lote ficaria sem vacas: confira o número")
            lote.n_vacas = antes + dados.vacas
            s.add(lote)
            sentido = "Entrada" if dados.vacas > 0 else "Saída"
            ev.descricao = (f"{sentido} de {abs(dados.vacas)} vaca(s)" + (f" {'do' if dados.vacas > 0 else 'para o'} {outro.nome}" if outro else "")
                            + f" ({antes} → {lote.n_vacas})" + (f". {dados.descricao}" if dados.descricao else ""))
            if outro is not None:
                antes_o = outro.n_vacas
                outro.n_vacas = antes_o - dados.vacas
                s.add(outro)
                s.add(Evento(lote_id=outro.id, data_hora=dados.data_hora, tipo="movimentacao",
                             descricao=f"{'Saída' if dados.vacas > 0 else 'Entrada'} de {abs(dados.vacas)} vaca(s) "
                                       f"{'para o' if dados.vacas > 0 else 'do'} {lote.nome} ({antes_o} → {outro.n_vacas})"))
        s.add(ev)
        s.commit()
        s.refresh(ev)
        _acao(s, dados.alerta_id, lote_id, f"Evento {ev.tipo.replace('_', ' ')} em {ev.data_hora:%d/%m %H:%M}"
              + (f": {ev.descricao}" if ev.descricao else ""), {"evento_id": ev.id})
        s.refresh(ev)
        return ev.model_dump()


@router.get("/lotes/{lote_id}/trato")
def trato(lote_id: int, tratos: int = 2, sobra_pct: float = 0.0, data: date | None = None, divisao: str | None = None):
    """Planilha do trato do dia: kg por alimento para o lote, por trato, na ordem de carregamento do vagão.
    divisao = porcentagens separadas por vírgula (ex.: 60,40)."""
    fracoes = None
    if divisao:
        try:
            fracoes = [float(x) / 100 for x in divisao.split(",")]
        except ValueError:
            raise HTTPException(422, "divisão inválida")
    with sessao() as s:
        return services.plano_trato(s, _lote(s, lote_id), data, tratos, fracoes, sobra_pct)


@router.get("/fazendas/{fazenda_id}/estoque")
def ver_estoque(fazenda_id: int):
    from .. import estoque
    with sessao() as s:
        if not s.get(Fazenda, fazenda_id):
            raise HTTPException(404, "fazenda não encontrada")
        return estoque.situacao(s, fazenda_id)


@router.post("/fazendas/{fazenda_id}/estoque")
def movimentar_estoque(fazenda_id: int, dados: MovimentoEstoqueIn):
    from .. import estoque
    with sessao() as s:
        if not s.get(Fazenda, fazenda_id):
            raise HTTPException(404, "fazenda não encontrada")
        estoque.registrar(s, fazenda_id, dados.item, dados.tipo, dados.kg, dados.data or date.today(), dados.obs)
        return estoque.situacao(s, fazenda_id)


@router.get("/fazendas/{fazenda_id}/estoque/movimentos")
def movimentos_estoque(fazenda_id: int, item: str | None = None):
    from ..db.models import MovimentoEstoque
    with sessao() as s:
        q = select(MovimentoEstoque).where(MovimentoEstoque.fazenda_id == fazenda_id)
        if item:
            q = q.where(MovimentoEstoque.item == item)
        return s.exec(q.order_by(MovimentoEstoque.data.desc(), MovimentoEstoque.id.desc())).all()


@router.get("/lotes/{lote_id}/previsao")
def previsao_lote(lote_id: int, dias: int = 30):
    """Projeção do lote: leite com faixa, receita, custo, sobra, marcos (secagem, parto, fim de transição) e avisos PRV."""
    from .. import previsao
    if not 7 <= dias <= 90:
        raise HTTPException(422, "horizonte entre 7 e 90 dias")
    with sessao() as s:
        lote = _lote(s, lote_id)
        return previsao.projetar_lote(s, lote, dias, itu_futuro=previsao.clima_previsto(s.get(Fazenda, lote.fazenda_id), dias))


@router.get("/fazendas/{fazenda_id}/previsao")
def previsao_fazenda(fazenda_id: int, dias: int = 30):
    from .. import previsao
    if not 7 <= dias <= 90:
        raise HTTPException(422, "horizonte entre 7 e 90 dias")
    with sessao() as s:
        if not s.get(Fazenda, fazenda_id):
            raise HTTPException(404, "fazenda não encontrada")
        return previsao.projetar_fazenda(s, fazenda_id, dias)


@router.get("/fazendas/{fazenda_id}/relatorio")
def relatorio(fazenda_id: int, dias: int = 7):
    from .. import relatorio as rel
    with sessao() as s:
        if not s.get(Fazenda, fazenda_id):
            raise HTTPException(404, "fazenda não encontrada")
        return rel.gerar(s, fazenda_id, dias)


@router.get("/lotes/{lote_id}/serie")
def serie(lote_id: int):
    with sessao() as s:
        return services.serie_lote(s, _lote(s, lote_id))


def _acao(s, alerta_id, lote_id, descricao, ref):
    try:
        alertas.registrar_acao(s, alerta_id, lote_id, descricao, ref)
    except ValueError as e:
        raise HTTPException(400, str(e))


ESTADOS = {"pendentes": ("aberto", "aceito"), "abertos": ("aberto",), "aceitos": ("aceito",), "recusados": ("recusado",),
           "resolvidos": ("resolvido",), "expirados": ("expirado",), "encerrados": ("resolvido", "expirado", "recusado")}


@router.get("/alertas")
def listar_alertas(lote_id: int | None = None, estado: str = "pendentes", dias: int = 120, incluir_suprimidos: bool = True):
    """Episódios de alerta. estado: pendentes | abertos | aceitos | recusados | resolvidos | expirados | encerrados | todos."""
    with sessao() as s:
        q = select(AlertaDB).where(AlertaDB.ultima_ocorrencia >= date.today() - timedelta(days=dias))
        if lote_id:
            q = q.where(AlertaDB.lote_id == lote_id)
        if estado in ESTADOS:
            q = q.where(AlertaDB.estado.in_(ESTADOS[estado]))
        if not incluir_suprimidos:
            q = q.where(AlertaDB.suprimido == False)  # noqa: E712
        eps = s.exec(q.order_by(AlertaDB.ultima_ocorrencia.desc(), AlertaDB.id.desc())).all()
        return [_ep(a) for a in eps]


def _ep(a: AlertaDB) -> dict:
    return a.model_dump() | {"data": a.ultima_ocorrencia, "status": "suprimido" if a.suprimido else "ativo",
                             "destino": alertas.destino(a)}


@router.get("/alertas/{alerta_id}")
def obter_alerta(alerta_id: int):
    with sessao() as s:
        a = s.get(AlertaDB, alerta_id)
        if not a:
            raise HTTPException(404, "alerta não encontrado")
        return _ep(a) | {"historico": alertas.historico_do(s, alerta_id)}


@router.get("/alertas/{alerta_id}/proposta")
def proposta_alerta(alerta_id: int):
    """Dieta proposta pelo aviso (decidida pela regra): a tela da dieta já abre com ela para conferir e salvar."""
    with sessao() as s:
        a = s.get(AlertaDB, alerta_id)
        if not a:
            raise HTTPException(404, "alerta não encontrado")
        return services.proposta_ajuste(s, a)


@router.post("/alertas/{alerta_id}/aceitar")
def aceitar_alerta(alerta_id: int, dados: AceitarIn | None = None):
    """Aceita a recomendação e devolve a tela onde a ação deve ser registrada."""
    with sessao() as s:
        a = s.get(AlertaDB, alerta_id)
        if not a:
            raise HTTPException(404, "alerta não encontrado")
        try:
            destino = alertas.aceitar(s, a, dados.observacao if dados else "")
        except ValueError as e:
            raise HTTPException(400, str(e))
        return {"destino": destino, "alerta": _ep(a)}


@router.post("/alertas/{alerta_id}/recusar")
def recusar_alerta(alerta_id: int, dados: RecusarIn):
    with sessao() as s:
        a = s.get(AlertaDB, alerta_id)
        if not a:
            raise HTTPException(404, "alerta não encontrado")
        try:
            alertas.recusar(s, a, dados.motivo)
        except ValueError as e:
            raise HTTPException(400, str(e))
        return _ep(a)


@router.get("/historico")
def historico_acoes(lote_id: int | None = None, dias: int = 120):
    """Linha do tempo de alertas e ações (aberto, aceito, ação registrada, recusado, resolvido, expirado)."""
    with sessao() as s:
        q = select(HistoricoAlerta, AlertaDB).join(AlertaDB, AlertaDB.id == HistoricoAlerta.alerta_id).where(
            HistoricoAlerta.data_hora >= datetime.now() - timedelta(days=dias))
        if lote_id:
            q = q.where(HistoricoAlerta.lote_id == lote_id)
        linhas = s.exec(q.order_by(HistoricoAlerta.data_hora.desc(), HistoricoAlerta.id.desc())).all()
        return [h.model_dump() | {"alerta": {"id": a.id, "regra": a.regra, "titulo": a.titulo,
                                             "titulo_produtor": a.titulo_produtor, "nivel": a.nivel,
                                             "estado": a.estado, "categoria": a.categoria}} for h, a in linhas]
