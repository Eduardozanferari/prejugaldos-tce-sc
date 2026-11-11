"""Coleta: posts do X (xAI, ferramenta x_search) e itens oficiais (RSS, sem modelo e sem custo)."""
import datetime as dt
import email.utils
import html
import json
import re
import time
import xml.etree.ElementTree as ET
from typing import Optional

import requests
from openai.lib._pydantic import to_strict_json_schema
from pydantic import BaseModel, Field

from . import config, custos, prompts
from .precos import FERRAMENTAS, custo_tokens

AGENTE = "Mozilla/5.0 (compatible; BriefingDeNoticias/0.1; leitor RSS pessoal)"


class PostX(BaseModel):
    link: str = Field(description="URL do post no X, no formato https://x.com/<autor>/status/<id>")
    autor: str = Field(description="Handle do autor, sem @")
    texto: str = Field(description="Texto do post, resumido se for longo")
    assunto: str = Field(description="O fato tratado, em uma linha")


class ColetaX(BaseModel):
    posts: list[PostX]


def _responses_sse(payload: dict, chave: str, timeout: int = 600) -> dict:
    """POST /v1/responses da xAI em streaming (respostas com busca passam de 30 s sem bytes)."""
    payload = {**payload, "stream": True}
    with requests.post("https://api.x.ai/v1/responses", json=payload, stream=True, timeout=timeout,
                       headers={"Authorization": f"Bearer {chave}", "Content-Type": "application/json"}) as r:
        if r.status_code != 200:
            raise RuntimeError(f"xAI HTTP {r.status_code}: {r.text[:300]}")
        final = None
        for bruto in r.iter_lines():
            linha = bruto.decode("utf-8", errors="replace") if bruto else ""
            if not linha.startswith("data:"):
                continue
            dados = linha[5:].strip()
            if dados == "[DONE]":
                break
            ev = json.loads(dados)
            if ev.get("type") in ("response.completed", "response.incomplete", "response.failed"):
                final = ev.get("response")
        if final is None:
            raise RuntimeError("xAI: stream terminou sem resposta final")
        return final


def _custo_xai(resp: dict, modelo: str) -> tuple[float, dict]:
    uso = resp.get("usage") or {}
    det = uso.get("server_side_tool_usage_details") or {}
    cache = (uso.get("input_tokens_details") or {}).get("cached_tokens", 0)
    calculado = (custo_tokens(modelo, uso.get("input_tokens", 0), uso.get("output_tokens", 0), cache)
                 + (det.get("x_posts_fetched") or 0) * FERRAMENTAS["xai_x_search_por_post"]
                 + (det.get("x_users_fetched") or 0) * FERRAMENTAS["xai_x_search_por_perfil"])
    ticks = uso.get("cost_in_usd_ticks")  # valor cobrado pela xAI, em US$ 1e-10
    return (ticks / 1e10 if ticks else calculado), uso


def coletar_x(tema: dict, cfg: dict, execucao_id: int) -> list[dict]:
    chave = config.chave("XAI_API_KEY") or "proxy-injected"
    modelo = cfg["modelos"]["coleta_x"]
    lim = cfg["limites"]
    hoje = dt.datetime.now(dt.timezone.utc).date()
    ferramenta = {"type": "x_search", "from_date": (hoje - dt.timedelta(days=1)).isoformat(),
                  "to_date": (hoje + dt.timedelta(days=1)).isoformat()}
    if tema.get("perfis"):
        ferramenta["allowed_x_handles"] = tema["perfis"][:20]
    payload = {
        "model": modelo,
        "input": [{"role": "user", "content": prompts.montar(
            "coleta_x", tema=tema["descricao"], quantidade=lim["posts_por_tema"])}],
        "tools": [ferramenta],
        "reasoning": {"effort": "low"},
        "max_turns": int(lim["max_turns_x"]),
        "text": {"format": {"type": "json_schema", "name": "coleta", "strict": True,
                            "schema": to_strict_json_schema(ColetaX)}},
    }
    tentativas = 1 + int(lim["novas_tentativas_x"])
    for tentativa in range(1, tentativas + 1):
        reserva = custos.reservar("coleta_x")
        try:
            resp = _responses_sse(payload, chave)
        except Exception as e:
            custos.registrar(reserva, execucao_id, "coleta_x", tema["id"], "xai", modelo, 0.0, False,
                             f"tentativa {tentativa}: {e}"[:500])
            if tentativa == tentativas:
                raise
            time.sleep(20)
            continue
        custo, uso = _custo_xai(resp, modelo)
        ok = resp.get("status") == "completed"
        custos.registrar(reserva, execucao_id, "coleta_x", tema["id"], "xai", modelo, custo, ok,
                         None if ok else f"tentativa {tentativa}: {resp.get('error')}"[:500], uso)
        if ok:
            texto = "".join(c.get("text", "") for o in resp.get("output", []) if o.get("type") == "message"
                            for c in o.get("content", []) if c.get("type") == "output_text")
            return [p.model_dump() for p in ColetaX.model_validate_json(texto).posts]
        if tentativa < tentativas:
            time.sleep(30)
    raise RuntimeError(f"xAI: coleta do tema {tema['id']} falhou em {tentativas} tentativas")


# RSS ---------------------------------------------------------------------------------------

def _texto(no: Optional[ET.Element]) -> str:
    if no is None:
        return ""
    bruto = "".join(no.itertext()) if len(no) else (no.text or "")
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", bruto))).strip()


def _data(valor: str) -> Optional[dt.datetime]:
    valor = (valor or "").strip()
    if not valor:
        return None
    try:
        d = email.utils.parsedate_to_datetime(valor)
    except (TypeError, ValueError):
        try:
            d = dt.datetime.fromisoformat(valor.replace("Z", "+00:00"))
        except ValueError:
            return None
    return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)


def ler_feed(url: str, horas: int) -> list[dict]:
    r = requests.get(url, timeout=30, headers={"User-Agent": AGENTE})
    r.raise_for_status()
    raiz = ET.fromstring(r.content)
    limite = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=horas)
    fonte = _texto(raiz.find("./channel/title")) or _texto(raiz.find("{http://www.w3.org/2005/Atom}title")) or url
    itens = []
    for it in raiz.iter():
        tag = it.tag.split("}")[-1]
        if tag not in ("item", "entry"):
            continue
        filho = lambda nome: next((c for c in it if c.tag.split("}")[-1] == nome), None)
        link_no = filho("link")
        link = (link_no.get("href") if link_no is not None and link_no.get("href") else _texto(link_no))
        data = _data(_texto(filho("pubDate")) or _texto(filho("published")) or _texto(filho("updated"))
                     or _texto(filho("date")))
        if data and data < limite:
            continue
        itens.append({"fonte": fonte, "titulo": _texto(filho("title")), "link": link,
                      "publicado_em": data.isoformat() if data else None,
                      "resumo": (_texto(filho("description")) or _texto(filho("summary")))[:600]})
    return itens


def coletar_oficial(tema: dict, cfg: dict) -> tuple[list[dict], list[str]]:
    itens, erros = [], []
    for url in tema.get("feeds", []):
        try:
            itens.extend(ler_feed(url, int(cfg["limites"]["horas_janela"])))
        except Exception as e:  # um feed fora do ar não interrompe os demais
            erros.append(f"{url}: {type(e).__name__}: {str(e)[:150]}")
    itens.sort(key=lambda i: i["publicado_em"] or "", reverse=True)
    vistos, unicos = set(), []
    for i in itens:
        if i["link"] not in vistos:
            vistos.add(i["link"])
            unicos.append(i)
    return unicos[: int(cfg["limites"]["itens_oficiais_por_tema"])], erros
