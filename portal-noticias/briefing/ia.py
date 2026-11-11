"""Chamadas aos modelos: seleção de pautas, verificação e redação (OpenAI), confirmação (Claude)
e síntese de voz (xAI). Toda chamada paga passa por custos.reservar() e custos.registrar()."""
import datetime as dt
import json
import re
from typing import Literal, Optional

import anthropic
import requests
from openai import OpenAI
from pydantic import BaseModel, Field

from . import config, custos, prompts
from .precos import FERRAMENTAS, TOKENS, VOZ_POR_MILHAO_CHARS, custo_tokens

Status = Literal["confirmada", "parcial", "falsa", "nao_confirmada", "contestada"]


def _openai() -> OpenAI:
    # No ambiente em nuvem o proxy injeta a chave; o SDK só exige que exista um valor.
    return OpenAI(api_key=config.chave("OPENAI_API_KEY") or "sk-proxy-injected", timeout=600, max_retries=2)


def _anthropic() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=config.chave("ANTHROPIC_API_KEY"), timeout=600, max_retries=2)


def _stream_openai(client: OpenAI, **kw):
    # Streaming: respostas com busca ficam mais de 30 s sem enviar bytes, e proxies cortam a conexão.
    with client.responses.stream(**kw) as stream:
        for _ in stream:
            pass
        return stream.get_final_response()


def _custo_openai(resp, modelo: str, buscas: int = 0) -> tuple[float, dict]:
    uso = resp.usage.model_dump() if resp.usage else {}
    cache = (uso.get("input_tokens_details") or {}).get("cached_tokens", 0)
    custo = custo_tokens(modelo, uso.get("input_tokens", 0), uso.get("output_tokens", 0), cache)
    return custo + buscas * FERRAMENTAS["openai_web_search_por_chamada"], uso


# Seleção de pautas ---------------------------------------------------------------------------

class Pauta(BaseModel):
    titulo: str = Field(description="Título provisório, factual")
    resumo: str = Field(description="Duas frases sobre o fato")
    afirmacoes: list[str] = Field(description="Afirmações centrais verificáveis isoladamente")
    origens: list[str] = Field(description="Links dos itens e posts usados")


class Selecao(BaseModel):
    pautas: list[Pauta]


def selecionar(tema: dict, posts: list[dict], oficiais: list[dict], cfg: dict, execucao_id: int) -> list[dict]:
    modelo = cfg["modelos"]["selecao"]
    fmt_of = "\n".join(f"- [{i['fonte']}] {i['titulo']} ({i['publicado_em'] or 's/d'}) {i['link']}\n  {i['resumo'][:300]}"
                       for i in oficiais) or "(nenhum)"
    fmt_x = "\n".join(f"- @{p['autor']}: {p['texto'][:400]} {p['link']}" for p in posts) or "(nenhum)"
    entrada = prompts.montar("selecao", tema=tema["nome"], descricao=tema["descricao"],
                             quantidade=tema["candidatos"], afirmacoes=cfg["limites"]["afirmacoes_por_candidato"],
                             itens_oficiais=fmt_of, posts=fmt_x)
    reserva = custos.reservar("selecao")
    try:
        resp = _stream_openai(_openai(), model=modelo, input=[{"role": "user", "content": entrada}],
                              text_format=Selecao, reasoning={"effort": "low"})
    except Exception as e:
        custos.registrar(reserva, execucao_id, "selecao", tema["id"], "openai", modelo, 0.0, False, str(e)[:500])
        raise
    custo, uso = _custo_openai(resp, modelo)
    custos.registrar(reserva, execucao_id, "selecao", tema["id"], "openai", modelo, custo, True, None, uso)
    pautas = resp.output_parsed.pautas if resp.output_parsed else []
    n = int(cfg["limites"]["afirmacoes_por_candidato"])
    return [{**p.model_dump(), "afirmacoes": p.afirmacoes[:n]} for p in pautas[: int(tema["candidatos"])]]


# Verificação ---------------------------------------------------------------------------------

class Verificacao(BaseModel):
    status: Status
    url: Optional[str] = Field(description="URL da fonte aberta que sustenta a decisão; null se nenhuma")
    trecho: Optional[str] = Field(description="Frase literal da fonte que sustenta a decisão; null se nenhuma")
    justificativa: str = Field(description="Uma ou duas frases explicando a decisão")


def verificar(afirmacao: str, tema_id: str, cfg: dict, execucao_id: int) -> dict:
    modelo = cfg["modelos"]["verificacao"]
    hoje = custos.agora().strftime("%d/%m/%Y")
    reserva = custos.reservar("verificacao")
    try:
        resp = _stream_openai(
            _openai(), model=modelo,
            input=[{"role": "user", "content": prompts.montar("verificacao", afirmacao=afirmacao, hoje=hoje)}],
            tools=[{"type": "web_search", "search_context_size": "medium",
                    "user_location": {"type": "approximate", "country": "BR"}}],
            include=["web_search_call.action.sources"], text_format=Verificacao, reasoning={"effort": "low"})
    except Exception as e:
        custos.registrar(reserva, execucao_id, "verificacao", tema_id, "openai", modelo, 0.0, False, str(e)[:500])
        raise
    buscas, fontes = 0, []
    for item in resp.output:
        if item.type == "web_search_call" and getattr(item.action, "type", None) == "search":
            buscas += 1
            fontes += [getattr(s, "url", None) or str(s) for s in (getattr(item.action, "sources", None) or [])]
    custo, uso = _custo_openai(resp, modelo, buscas)
    custos.registrar(reserva, execucao_id, "verificacao", tema_id, "openai", modelo, custo, True, None, uso)
    r = resp.output_parsed.model_dump() if resp.output_parsed else \
        {"status": "nao_confirmada", "url": None, "trecho": None, "justificativa": "resposta fora do formato"}
    r["urls_consultadas"] = sorted(set(fontes))
    return r


# Confirmação (Claude) ------------------------------------------------------------------------

def confirmar(afirmacao: str, verificacao: dict, tema_id: str, cfg: dict, execucao_id: int) -> dict:
    modelo = cfg["modelos"]["confirmacao"]
    pedido = dict(
        model=modelo, max_tokens=8000, output_config={"effort": "medium"},
        messages=[{"role": "user", "content": prompts.montar(
            "confirmacao", afirmacao=afirmacao, url=verificacao.get("url") or "(nenhuma)",
            trecho=verificacao.get("trecho") or "(nenhum)")}],
        tools=[{"type": "web_fetch_20260318", "name": "web_fetch", "max_uses": 2, "max_content_tokens": 25000},
               {"type": "web_search_20260318", "name": "web_search", "max_uses": 1}],
    )
    client = _anthropic()
    reserva = custos.reservar("confirmacao")
    try:
        if modelo.startswith(("claude-sonnet-5-5", "claude-opus-5-5")):
            # Reserva no servidor: se o modelo recusar, outro modelo responde no lugar.
            with client.beta.messages.stream(**pedido, betas=["server-side-fallback-2026-07-01"],
                                             fallbacks="default") as s:
                msg = s.get_final_message()
        else:
            with client.messages.stream(**pedido) as s:
                msg = s.get_final_message()
    except Exception as e:
        custos.registrar(reserva, execucao_id, "confirmacao", tema_id, "anthropic", modelo, 0.0, False, str(e)[:500])
        raise
    u = msg.usage
    buscas = getattr(u.server_tool_use, "web_search_requests", 0) or 0
    modelo_usado = getattr(msg, "model", None) or modelo
    preco = modelo_usado if modelo_usado in TOKENS else modelo  # a reserva pode ter respondido
    custo = custo_tokens(preco, u.input_tokens, u.output_tokens, u.cache_read_input_tokens or 0) \
        + buscas * FERRAMENTAS["anthropic_web_search_por_busca"]
    custos.registrar(reserva, execucao_id, "confirmacao", tema_id, "anthropic", modelo_usado, custo, True,
                     f"stop_reason={msg.stop_reason}", u.model_dump())
    if msg.stop_reason == "refusal":
        return {"concorda": False, "status": None, "url_conferida": None, "trecho": None,
                "justificativa": "o modelo recusou a tarefa", "modelo": modelo_usado}
    texto = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
    m = re.search(r"\{.*\}", texto, re.S)
    try:
        r = json.loads(m.group(0)) if m else {}
    except json.JSONDecodeError:
        r = {}
    r.setdefault("concorda", False)
    r.setdefault("justificativa", "resposta fora do formato" if not r else "")
    r["modelo"] = modelo_usado
    return r


# Redação ---------------------------------------------------------------------------------------

class Texto(BaseModel):
    titulo: str
    linha_fina: str
    corpo: str
    roteiro: str


def redigir(tema: dict, pauta: dict, aprovadas: list[dict], cfg: dict, execucao_id: int) -> dict:
    modelo = cfg["modelos"]["redacao"]
    lista = "\n".join(f"[{i}] {a['texto']} (fonte: {a['url']}; trecho: \"{(a['trecho'] or '')[:300]}\")"
                      for i, a in enumerate(aprovadas, 1))
    entrada = prompts.montar("redacao", tema=tema["nome"], pauta=f"{pauta['titulo']}. {pauta['resumo']}",
                             afirmacoes=lista)
    reserva = custos.reservar("redacao")
    try:
        resp = _stream_openai(_openai(), model=modelo, input=[{"role": "user", "content": entrada}],
                              text_format=Texto, reasoning={"effort": "low"})
    except Exception as e:
        custos.registrar(reserva, execucao_id, "redacao", tema["id"], "openai", modelo, 0.0, False, str(e)[:500])
        raise
    custo, uso = _custo_openai(resp, modelo)
    custos.registrar(reserva, execucao_id, "redacao", tema["id"], "openai", modelo, custo, True, None, uso)
    return resp.output_parsed.model_dump()


# Voz ---------------------------------------------------------------------------------------------

def sintetizar(texto: str, destino, cfg: dict, execucao_id: int, tema_id: str | None) -> None:
    servico = cfg["modelos"]["voz"]
    if servico != "xai":
        raise ValueError(f"serviço de voz não suportado nesta versão: {servico}")
    custo = len(texto) / 1e6 * VOZ_POR_MILHAO_CHARS["xai_tts"]
    reserva = custos.reservar("voz", max(custo, 0.001))
    try:
        r = requests.post("https://api.x.ai/v1/tts", timeout=300,
                          headers={"Authorization": f"Bearer {config.chave('XAI_API_KEY') or 'proxy-injected'}",
                                   "Content-Type": "application/json"},
                          json={"text": texto, "voice_id": cfg["modelos"]["voz_id"], "language": "pt-BR"})
        r.raise_for_status()
    except Exception as e:
        custos.registrar(reserva, execucao_id, "voz", tema_id, "xai", "tts", 0.0, False, str(e)[:500])
        raise
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(r.content)
    custos.registrar(reserva, execucao_id, "voz", tema_id, "xai", "tts", custo, True, f"{len(texto)} caracteres")
