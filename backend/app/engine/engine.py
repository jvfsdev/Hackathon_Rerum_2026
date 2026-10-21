"""Motor de inferência: encadeamento progressivo (match → resolução de conflito → disparo),
encadeamento regressivo para perguntar só o que falta, CF estilo MYCIN e traço completo."""
import re
from dataclasses import dataclass, field

from .cf import propagar
from .conditions import FALTA, Resolvedor, avaliar, fatos_citados
from .facts import Alerta
from .registry import FUNCOES
from .rules_loader import ORDEM_MODULOS, BaseConhecimento, fatos_concluidos, fatos_requeridos
from .working_memory import MemoriaTrabalho

NIVEIS = ["informativo", "atencao", "critico"]


@dataclass
class Resultado:
    wm: MemoriaTrabalho
    traco: list[dict] = field(default_factory=list)
    alertas: list[Alerta] = field(default_factory=list)
    supressoes: dict = field(default_factory=dict)
    kb_version: str = ""

    def disparadas(self) -> list[str]:
        return [t["regra"] for t in self.traco]

    def alertas_ativos(self) -> list[Alerta]:
        return [a for a in self.alertas if a.status == "ativo"]

    def to_dict(self) -> dict:
        return {"kb_version": self.kb_version, "fatos": self.wm.to_dict(), "traco": self.traco,
                "alertas": [a.to_dict() for a in self.alertas], "supressoes": self.supressoes}


class Motor:
    def __init__(self, kb: BaseConhecimento, modulos: list[str] | None = None):
        self.kb = kb
        self.regras = [r for r in kb.regras if modulos is None or r["modulo"] in modulos]

    # ------------------------------------------------------------------ forward
    def executar(self, wm: MemoriaTrabalho, resultado: Resultado | None = None, max_ciclos: int = 1000) -> Resultado:
        """Roda até não haver regra aplicável (refração: cada regra dispara uma vez por execução).

        Passe `resultado` para continuar uma sessão depois de declarar fatos novos: as conclusões anteriores são
        descartadas e recalculadas a partir das entradas (manutenção de verdade por recomputação), e o traço e os
        alertas passam a refletir só o estado atual."""
        res = Resolvedor(wm, self.kb.params)
        self._wm_atual = wm
        if resultado is None:
            resultado = Resultado(wm, kb_version=self.kb.versao)
        else:
            wm.reiniciar_derivados()
            resultado.traco.clear()
            resultado.alertas.clear()
            resultado.supressoes.clear()
        disparadas = wm.disparadas
        for _ in range(max_ciclos):
            conjunto = []
            for regra in self.regras:
                if regra["id"] in disparadas:
                    continue
                casou, premissas = self._casar(regra, res)
                if casou:
                    conjunto.append((self._chave(regra, premissas), regra, premissas))
            if not conjunto:
                break
            conjunto.sort(key=lambda c: c[0])
            _, regra, premissas = conjunto[0]
            wm.ciclo += 1
            disparadas.add(regra["id"])
            entrada = self._disparar(regra, premissas, res, resultado)
            entrada["concorrentes"] = [c[1]["id"] for c in conjunto[1:]]
            resultado.traco.append(entrada)
        self._aplicar_supressoes(resultado)
        self._agrupar_problemas(resultado)
        return resultado


    def _casar(self, regra: dict, res: Resolvedor) -> tuple[bool, list[dict]]:
        """Casa as condições. Premissa com CF abaixo do limiar (@params.cf_limiar) não sustenta conclusão."""
        premissas = []
        limiar = self.kb.params["cf_limiar"]["valor"]
        for cond in regra["se"]:
            ok, usadas, _ = avaliar(cond, res)
            if not ok or any(p["op"] != "ausente" and p["cf"] < limiar for p in usadas):
                return False, []
            premissas += usadas
        return True, premissas

    def _chave(self, regra: dict, premissas: list[dict]) -> tuple:
        """Resolução de conflito: módulo → prioridade → especificidade → recência."""
        recencia = max((self._ciclo_fato(p["fato"]) for p in premissas), default=0)
        return (ORDEM_MODULOS[regra["modulo"]], -regra["prioridade"], -len(regra["se"]), -recencia, regra["id"])

    def _ciclo_fato(self, nome: str) -> int:
        f = self._wm_atual.get(nome)
        return f.ciclo if f else 0

    def _disparar(self, regra: dict, premissas: list[dict], res: Resolvedor, resultado: Resultado) -> dict:
        cfs = [p["cf"] for p in premissas if p["op"] != "ausente"]
        cf = propagar(regra["cf"], cfs)
        acoes = []
        for acao in regra.get("entao", []):
            if "concluir" in acao:
                spec = acao["concluir"]
                valor = res.valor(spec["valor"])
                efeito = res.wm.concluir(spec["fato"], valor, cf, regra["id"])
                acoes.append({"tipo": "concluir", "fato": spec["fato"], "valor": valor,
                              "cf": round(res.wm.get(spec["fato"]).cf, 3), "efeito": efeito})
            elif "calcular" in acao:
                acoes.append(self._calcular(acao["calcular"], regra, cf, cfs, res))
            elif "alerta" in acao:
                alerta = self._alerta(acao["alerta"], regra, cf, res)
                resultado.alertas.append(alerta)
                acoes.append({"tipo": "alerta", "nivel": alerta.nivel, "titulo": alerta.titulo})
            elif "suprimir" in acao or "rebaixar" in acao:
                tipo = "suprimir" if "suprimir" in acao else "rebaixar"
                spec = acao[tipo]
                for cat in spec["categorias"]:
                    if resultado.supressoes.get(cat, {}).get("tipo") == "suprimir":
                        continue  # suprimir prevalece sobre rebaixar
                    resultado.supressoes[cat] = {"tipo": tipo, "regra": regra["id"], "para": spec.get("para", "informativo"),
                                                 "motivo": formatar(spec["motivo"], res)}
                acoes.append({"tipo": tipo, "categorias": spec["categorias"]})
        return {"ciclo": res.wm.ciclo, "regra": regra["id"], "descricao": regra.get("descricao", ""),
                "modulo": regra["modulo"], "cf_regra": regra["cf"], "cf": round(cf, 3), "premissas": premissas,
                "acoes": acoes, "fonte": regra.get("fonte", ""), "forca": regra.get("forca", "")}

    def _calcular(self, spec: dict, regra: dict, cf: float, cfs: list[float], res: Resolvedor) -> dict:
        usados: list = []
        args = {}
        for nome, expr in spec.get("args", {}).items():
            v = res.valor(expr, usados)
            if v is FALTA or (isinstance(v, list) and FALTA in v):
                return {"tipo": "calcular", "fato": spec["fato"], "efeito": "ignorado", "motivo": f"falta {nome}"}
            args[nome] = v
        try:
            saida = FUNCOES[spec["funcao"]](**args)
        except (TypeError, ValueError, ZeroDivisionError) as e:   # dado de tipo/valor inválido não derruba a sessão
            return {"tipo": "calcular", "fato": spec["fato"], "efeito": "ignorado", "motivo": f"erro no cálculo: {e}"}
        cf_calc = propagar(regra["cf"], cfs + [u.cf for u in usados])
        efeitos = {}
        if isinstance(saida, dict):
            for k, v in saida.items():
                efeitos[f"{spec['fato']}.{k}"] = res.wm.concluir(f"{spec['fato']}.{k}", v, cf_calc, regra["id"])
        elif saida is not None:
            efeitos[spec["fato"]] = res.wm.concluir(spec["fato"], saida, cf_calc, regra["id"])
        return {"tipo": "calcular", "fato": spec["fato"], "funcao": spec["funcao"],
                "args": {k: _resumo(v) for k, v in args.items()}, "valor": _resumo(saida), "cf": round(cf_calc, 3),
                "usados": sorted({u.nome for u in usados}), "efeito": efeitos}

    def _alerta(self, spec: dict, regra: dict, cf: float, res: Resolvedor) -> Alerta:
        if "cf_de" in spec:  # alerta que reporta o CF combinado de uma hipótese
            f = res.wm.get(spec["cf_de"])
            cf = f.cf if f else cf
        return Alerta(regra=regra["id"], nivel=spec.get("nivel", "atencao"),
                      titulo=formatar(spec["titulo"], res), causa=formatar(spec.get("causa", ""), res),
                      acao=formatar(spec.get("acao", ""), res), categoria=spec.get("categoria", "geral"),
                      cf=cf, fonte=regra.get("fonte", ""), forca=regra.get("forca", ""),
                      problema=spec.get("problema", regra["id"]),
                      **{f"{c}_produtor": formatar(spec.get(f"{c}_produtor", ""), res, br=True) for c in ("titulo", "causa", "acao")})

    def _agrupar_problemas(self, resultado: Resultado) -> None:
        """Regras com o mesmo `problema` (graus do mesmo problema) viram um alerta só: fica o de nível mais alto
        (empate: maior CF); os demais ficam registrados em `tambem` e continuam no traço."""
        grupos: dict[str, list[Alerta]] = {}
        for a in resultado.alertas:
            grupos.setdefault(a.problema or a.regra, []).append(a)
        manter = []
        for alertas in grupos.values():
            if len(alertas) == 1:
                manter.append(alertas[0])
                continue
            ativos = [a for a in alertas if a.status == "ativo"] or alertas
            principal = max(ativos, key=lambda a: (NIVEIS.index(a.nivel), a.cf))
            principal.extra["tambem"] = [a.regra for a in alertas if a is not principal]
            manter.append(principal)
        ids = {id(a) for a in manter}
        resultado.alertas = [a for a in resultado.alertas if id(a) in ids]

    def _aplicar_supressoes(self, resultado: Resultado) -> None:
        for alerta in resultado.alertas:
            sup = resultado.supressoes.get(alerta.categoria)
            if not sup or alerta.regra == sup["regra"]:
                continue
            if sup["tipo"] == "suprimir":
                alerta.status = "suprimido"
            elif NIVEIS.index(sup["para"]) < NIVEIS.index(alerta.nivel):
                alerta.nivel = sup["para"]
            else:
                continue
            alerta.nota = f"{sup['regra']}: {sup['motivo']}"

    # ----------------------------------------------------------------- backward
    def faltantes(self, objetivo: str, wm: MemoriaTrabalho) -> list[dict]:
        """Perguntas necessárias para alcançar o objetivo, com a cadeia de regras (o "por quê")."""
        res = Resolvedor(wm, self.kb.params)
        saida: dict[str, dict] = {}
        self._buscar(objetivo, wm, res, [], saida, set())
        return [p | {"objetivo": objetivo} for p in saida.values()]

    def _buscar(self, objetivo, wm, res, cadeia, saida, visitados):
        if objetivo in visitados:
            return
        visitados.add(objetivo)
        for regra in self.regras:
            if not any(objetivo == f or objetivo.startswith(f + ".") for f in fatos_concluidos(regra)):
                continue
            if self._condicao_falsa(regra, res) or not self._condicoes_alcancaveis(regra, wm, res, set()):
                continue
            for fato in fatos_requeridos(regra):
                if fato in wm or fato in saida:
                    continue
                nova = cadeia + [regra["id"]]
                if fato in self.kb.perguntas:
                    saida[fato] = {"fato": fato, **self.kb.perguntas[fato], "cadeia": nova}
                else:
                    self._buscar(fato, wm, res, nova, saida, visitados)

    def _condicoes_alcancaveis(self, regra: dict, wm, res, pilha: set) -> bool:
        """Poda: toda condição precisa citar fatos conhecidos, perguntáveis ou deriváveis por regra não podada."""
        for cond in regra["se"]:
            if cond.get("op") == "ausente" or "qualquer" in cond:
                continue
            for fato in fatos_citados(cond):
                if not self._alcancavel(fato, wm, res, pilha):
                    return False
        return True

    def _alcancavel(self, fato: str, wm, res, pilha: set) -> bool:
        if fato in wm or fato in self.kb.perguntas:
            return True
        if fato in pilha:
            return False
        for regra in self.regras:
            if any(fato == f or fato.startswith(f + ".") for f in fatos_concluidos(regra)):
                if not self._condicao_falsa(regra, res) and self._condicoes_alcancaveis(regra, wm, res, pilha | {fato}):
                    return True
        return False

    def _condicao_falsa(self, regra: dict, res: Resolvedor) -> bool:
        """Poda: alguma condição cujos fatos já são conhecidos é falsa."""
        for cond in regra["se"]:
            ok, _, faltas = avaliar(cond, res)
            if not ok and not faltas:
                return True
        return False


_PADRAO = re.compile(r"\{([@a-z_][\w\.]*)(?::([^}]+))?\}")


def formatar(texto: str, res: Resolvedor, br: bool = False) -> str:
    """Substitui {fato} / {fato:.1f} / {@params.x} por valores da memória de trabalho.
    br=True escreve números no padrão brasileiro (vírgula decimal, ponto de milhar): textos para o produtor."""
    def troca(m):
        txt = _troca(m)
        if br and re.fullmatch(r"[+-]?[\d.,]+%?", txt):
            txt = txt.replace(",", "_").replace(".", ",").replace("_", ".")
        return txt

    def _troca(m):
        nome, spec = m.group(1), m.group(2)
        v = res.valor(nome if nome.startswith("@") else "$" + nome)
        if v is FALTA:
            return "?"
        if isinstance(v, (list, tuple)):
            return ", ".join(str(x) for x in v) or "—"
        try:
            return format(v, spec) if spec else (f"{v:.2f}".rstrip("0").rstrip(".") if isinstance(v, float) else str(v))
        except (ValueError, TypeError):
            return str(v)
    return _PADRAO.sub(troca, texto or "")


def _resumo(v):
    if isinstance(v, float):
        return round(v, 3)
    if isinstance(v, dict):
        return {k: _resumo(x) for k, x in v.items()}
    if isinstance(v, list) and v and isinstance(v[0], dict) and "alimento" in v[0]:
        return [{"alimento": i["alimento"]["id"], "kg_mn": i["kg_mn"]} for i in v]
    return v
