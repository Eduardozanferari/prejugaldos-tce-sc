"""Teste 4: garimpo (Grok) e peneira (OpenAI, modelo mais barato) para o curador de comentários.

Roda num único tema e não toca no portal. Etapas:
- A1 passo 1: os 5 fatos mais discutidos em 48 h;
- A1 passo 2: para cada fato, análises de pessoas, excluindo contas institucionais, veículos e o
  autor original, com teste de recuperação de citações (quote posts);
- A2: marcas de discurso de quem analisa (PT e EN), com teste do operador de piso de curtidas;
- peneira: rubrica de 5 critérios (0 a 3) com o perfil do leitor; corte em total >= 9 e acréscimo >= 2;
- agrupamento dos aprovados que tratam do mesmo fato.

Grava as consultas internas que o Grok fez (custom_tool_call), para auditar operadores e citações.
Limite rígido de gasto: o script para quando o total passa de LIMITE_USD.

Uso: XAI_API_KEY=... OPENAI_API_KEY=... python teste4_garimpo_peneira.py
"""
import datetime as dt
import json
import pathlib
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import requests  # noqa: E402
from openai import OpenAI  # noqa: E402
from openai.lib._pydantic import to_strict_json_schema  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

from briefing import config  # noqa: E402
from briefing.precos import custo_tokens  # noqa: E402

SAIDA = pathlib.Path(__file__).parent / "saida"
SAIDA.mkdir(exist_ok=True)
PROMPTS = config.PASTA_PROMPTS
PERFIL = (config.RAIZ / "perfil.md").read_text(encoding="utf-8")
LIMITE_USD = 12.0
MODELO_X = "grok-4.7"
MODELO_PENEIRA = "gpt-6-luna"
ESFORCO = "high"
TURNOS_FATOS, TURNOS_GARIMPO = 4, 6

TEMA = ("Direito e controle externo: comentários a decisões do STF, do STJ e de tribunais de contas; "
        "processo legislativo e consultoria legislativa; inovação e tecnologia no mundo jurídico e no "
        "controle externo")
# Contas institucionais e veículos de imprensa excluídos da busca (limite da API: 20).
EXCLUIDAS = ["STF_oficial", "STJnoticias", "TCUoficial", "CNJ_oficial", "TSEjusbr", "camaradeputados",
             "SenadoFederal", "OABNacional", "JotaInfo", "migalhas", "conjur", "g1", "folha", "Estadao",
             "UOLNoticias", "CNNBrasil", "Metropoles", "GloboNews", "valoreconomico", "AgenciaSenado"]

gasto = 0.0


class Fato(BaseModel):
    fato: str
    por_que: str
    link_origem: Optional[str]
    conta_origem: Optional[str] = Field(description="handle sem @")
    palavras_chave: list[str]


class Fatos(BaseModel):
    fatos: list[Fato]


class Candidato(BaseModel):
    link: str = Field(description="URL do post no X")
    autor: str = Field(description="handle sem @")
    bio: str = Field(description="bio do autor em uma linha")
    tese: str = Field(description="a tese do autor em uma frase, em português")
    acrescimo: str = Field(description="o que ele acrescenta, em português")
    e_thread: bool
    e_citacao: bool = Field(description="true se o post é uma citação (quote post) de outro post")
    link_citado: Optional[str] = Field(description="link do post citado, se for citação")
    cita_documento: bool
    documento: Optional[str] = Field(description="documento, estudo, dado ou obra citado ou anexado")
    idioma: str
    repercussao_mostrada: Optional[str] = Field(
        description="repercussão somente se a ferramenta a mostrou; null caso contrário")


class Garimpo(BaseModel):
    itens: list[Candidato]


def chamar_grok(prompt: str, schema, max_turns: int, excluidas: list[str]) -> tuple[dict, dict]:
    global gasto
    if gasto >= LIMITE_USD:
        raise RuntimeError(f"limite de US$ {LIMITE_USD} atingido")
    hoje = dt.datetime.now(dt.timezone.utc).date()
    payload = {
        "model": MODELO_X, "stream": True,
        "input": [{"role": "user", "content": prompt}],
        "tools": [{"type": "x_search", "from_date": (hoje - dt.timedelta(days=1)).isoformat(),
                   "to_date": (hoje + dt.timedelta(days=1)).isoformat(),
                   "excluded_x_handles": excluidas[:20]}],
        "reasoning": {"effort": ESFORCO}, "max_turns": max_turns,
        "text": {"format": {"type": "json_schema", "name": "saida", "strict": True,
                            "schema": to_strict_json_schema(schema)}},
    }
    final = None
    with requests.post("https://api.x.ai/v1/responses", json=payload, stream=True, timeout=900,
                       headers={"Authorization": f"Bearer {config.chave('XAI_API_KEY') or 'proxy-injected'}"}) as r:
        if r.status_code != 200:
            raise RuntimeError(f"xAI HTTP {r.status_code}: {r.text[:300]}")
        for bruto in r.iter_lines():
            linha = bruto.decode("utf-8", "replace") if bruto else ""
            if linha.startswith("data:") and linha[5:].strip() != "[DONE]":
                ev = json.loads(linha[5:])
                if ev.get("type") in ("response.completed", "response.incomplete", "response.failed"):
                    final = ev["response"]
    uso = final.get("usage") or {}
    custo = (uso.get("cost_in_usd_ticks") or 0) / 1e10
    gasto += custo
    consultas = [{"ferramenta": o.get("name"), "entrada": o.get("input")}
                 for o in final.get("output", []) if o.get("type") == "custom_tool_call"]
    texto = "".join(c.get("text", "") for o in final.get("output", []) if o.get("type") == "message"
                    for c in o.get("content", []) if c.get("type") == "output_text")
    det = uso.get("server_side_tool_usage_details") or {}
    meta = {"status": final.get("status"), "erro": final.get("error"), "custo_usd": round(custo, 4),
            "posts_buscados": det.get("x_posts_fetched"), "perfis_buscados": det.get("x_users_fetched"),
            "consultas": consultas, "tokens": {k: uso.get(k) for k in ("input_tokens", "output_tokens")}}
    try:
        dados = schema.model_validate_json(texto).model_dump()
    except Exception as e:
        dados, meta["erro_formato"] = None, f"{e}"[:300]
    print(f"   status={meta['status']} posts={meta['posts_buscados']} consultas={len(consultas)} "
          f"US$ {meta['custo_usd']} (acumulado US$ {gasto:.2f})", flush=True)
    return dados, meta


def garimpo_prompt(angulo: str, janela: str, maximo: int) -> str:
    return (PROMPTS / "garimpo.md").read_text(encoding="utf-8").format(
        tema=TEMA, angulo=angulo, janela=janela, maximo=maximo)


# Peneira ------------------------------------------------------------------------------------

class Notas(BaseModel):
    acrescimo: int
    densidade: int
    lastro: int
    autoria: int
    aderencia: int
    justificativa: str = Field(description="até duas frases, em português")
    assunto: str = Field(description="o fato ou assunto tratado, em até 8 palavras")


def peneirar(c: dict, oai: OpenAI) -> dict:
    global gasto
    campos = {k: c[k] for k in ("link", "autor", "bio", "tese", "acrescimo", "e_thread", "e_citacao",
                                "cita_documento", "documento", "idioma")}
    entrada = (PROMPTS / "peneira.md").read_text(encoding="utf-8").format(
        perfil=PERFIL, exemplos_sim="(ainda não há)", exemplos_nao="(ainda não há)", tema=TEMA,
        candidato=json.dumps(campos, ensure_ascii=False, indent=1))
    resp = oai.responses.parse(model=MODELO_PENEIRA, input=[{"role": "user", "content": entrada}],
                               text_format=Notas, reasoning={"effort": "low"})
    u = resp.usage
    custo = custo_tokens(MODELO_PENEIRA, u.input_tokens, u.output_tokens,
                         (u.input_tokens_details.cached_tokens if u.input_tokens_details else 0))
    gasto += custo
    n = resp.output_parsed.model_dump()
    for k in ("acrescimo", "densidade", "lastro", "autoria", "aderencia"):
        n[k] = max(0, min(3, int(n[k])))
    n["total"] = sum(n[k] for k in ("acrescimo", "densidade", "lastro", "autoria", "aderencia"))
    n["aprovado"] = n["total"] >= 9 and n["acrescimo"] >= 2
    n["custo_usd"] = round(custo, 5)
    return n


class Grupo(BaseModel):
    assunto: str
    links: list[str]


class Grupos(BaseModel):
    grupos: list[Grupo]


def agrupar(aprovados: list[dict], oai: OpenAI) -> list[dict]:
    global gasto
    lista = "\n".join(f"- {c['link']} | {c['peneira']['assunto']} | {c['tese']}" for c in aprovados)
    resp = oai.responses.parse(
        model=MODELO_PENEIRA, reasoning={"effort": "low"}, text_format=Grupos,
        input=[{"role": "user", "content": "Agrupe os posts abaixo que tratam do MESMO fato ou da mesma obra "
                "(não do mesmo tema amplo). Cada link aparece em exatamente um grupo; posts sem par ficam "
                "sozinhos no próprio grupo.\n\n" + lista}])
    u = resp.usage
    gasto += custo_tokens(MODELO_PENEIRA, u.input_tokens, u.output_tokens, 0)
    return [g.model_dump() for g in resp.output_parsed.grupos]


def autor_do_link(link: str) -> str:
    m = re.search(r"x\.com/([^/]+)/status", link or "")
    return m.group(1) if m else ""


def main() -> None:
    resultado = {"data": dt.datetime.now(dt.timezone.utc).isoformat(), "tema": TEMA,
                 "parametros": {"modelo": MODELO_X, "esforco": ESFORCO, "turnos_fatos": TURNOS_FATOS,
                                "turnos_garimpo": TURNOS_GARIMPO, "excluidas": EXCLUIDAS,
                                "peneira": MODELO_PENEIRA},
                 "chamadas": [], "candidatos": []}
    destino = SAIDA / "teste4_garimpo_peneira.json"

    def salvar():
        resultado["gasto_usd"] = round(gasto, 4)
        destino.write_text(json.dumps(resultado, ensure_ascii=False, indent=2, default=str))

    candidatos: dict[str, dict] = {}

    def registrar(origem: str, dados, meta, fato_id=None):
        resultado["chamadas"].append({"origem": origem, **meta})
        for it in (dados or {}).get("itens", []):
            link = it["link"].split("?")[0]
            if link in candidatos:
                candidatos[link]["origens"].append(origem)
                continue
            candidatos[link] = {**it, "link": link, "origens": [origem], "fato_id": fato_id,
                                "autor_no_link": autor_do_link(link)}
        salvar()

    print("[A1 passo 1] fatos mais discutidos", flush=True)
    fatos, meta = chamar_grok((PROMPTS / "garimpo_fatos.md").read_text(encoding="utf-8").format(tema=TEMA, perfil=PERFIL),
                              Fatos, TURNOS_FATOS, EXCLUIDAS[:0])  # aqui as contas oficiais são bem-vindas
    resultado["chamadas"].append({"origem": "A1-fatos", **meta, "fatos": fatos})
    salvar()
    for i, f in enumerate((fatos or {}).get("fatos", [])[:5], 1):
        print(f"[A1 passo 2] fato {i}: {f['fato'][:90]}", flush=True)
        excl = [h for h in EXCLUIDAS if h != (f.get("conta_origem") or "")]
        if f.get("conta_origem"):
            excl = [f["conta_origem"]] + excl[:19]
        angulo = (f"comentários e análises de pessoas sobre este fato: {f['fato']} "
                  f"(palavras-chave: {', '.join(f['palavras_chave'])}). Procure também as citações "
                  f"(quote posts) do post de origem {f.get('link_origem') or '(desconhecido)'}, porque o "
                  f"comentário costuma estar nelas. Exclua o autor original e contas institucionais e de veículos. "
                  f"Para cada item, informe se ele é uma citação e qual post cita.")
        try:
            dados, meta = chamar_grok(garimpo_prompt(angulo, "últimas 48 horas", 6), Garimpo, TURNOS_GARIMPO, excl)
        except RuntimeError as e:
            print("   parado:", e); break
        registrar(f"A1-fato{i}", dados, meta, i)

    marcas = [
        ("PT", 'expressões de quem analisa, combinadas com termos do tema: "segue o fio", "fio:", "explico", '
               '"li o acórdão", "li o voto", "li o estudo", "o que muda na prática", "o ponto que passou batido", '
               '"bastidores", "apurei", "vale a leitura". Exclua respostas e republicações; prefira threads. '
               'Teste: nas buscas por palavra-chave, use também o operador de piso de curtidas min_faves:10 e '
               'informe na repercussão apenas o que a ferramenta mostrar.', 12),
        ("EN", 'expressões em inglês de quem analisa, combinadas com termos do tema (direito público, '
               'tribunais, controle externo, tecnologia jurídica, IA para advogados): "thread", "new paper", '
               '"here\'s why", "what this means", "I read the paper", "hands-on", "underrated". Exclua '
               'respostas e republicações; prefira threads.', 8),
    ]
    for nome, angulo, maximo in marcas:
        print(f"[A2 {nome}] marcas de discurso", flush=True)
        try:
            dados, meta = chamar_grok(garimpo_prompt(angulo, "últimas 48 horas", maximo), Garimpo,
                                      TURNOS_GARIMPO, EXCLUIDAS)
        except RuntimeError as e:
            print("   parado:", e); break
        registrar(f"A2-{nome}", dados, meta)

    lista = list(candidatos.values())
    print(f"\n{len(lista)} candidatos únicos; peneira com {MODELO_PENEIRA}", flush=True)
    oai = OpenAI(timeout=300)
    with ThreadPoolExecutor(max_workers=6) as pool:
        for c, n in zip(lista, pool.map(lambda c: peneirar(c, oai), lista)):
            c["peneira"] = n
    aprovados = [c for c in lista if c["peneira"]["aprovado"]]
    resultado["grupos"] = agrupar(aprovados, oai) if aprovados else []
    resultado["candidatos"] = sorted(lista, key=lambda c: (-c["peneira"]["total"], -c["peneira"]["acrescimo"]))
    resultado["resumo"] = {
        "candidatos": len(lista), "aprovados": len(aprovados), "grupos": len(resultado["grupos"]),
        "citacoes": sum(c["e_citacao"] for c in lista), "threads": sum(c["e_thread"] for c in lista),
        "com_repercussao_informada": sum(bool(c.get("repercussao_mostrada")) for c in lista),
        "autor_excluido_que_apareceu": sorted({c["autor_no_link"] for c in lista if c["autor_no_link"] in EXCLUIDAS}),
        "autor_divergente_do_link": [c["link"] for c in lista if c["autor_no_link"]
                                     and c["autor_no_link"].lower() != c["autor"].lower()],
    }
    salvar()
    print(json.dumps(resultado["resumo"], ensure_ascii=False, indent=1))
    print(f"Gasto total: US$ {gasto:.2f}\nSaída: {destino}")


if __name__ == "__main__":
    main()
