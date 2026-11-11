"""Portal (leitura e áudio), painel (configuração, execução manual, custos) e agendamento."""
import datetime as dt
import json
import os
import re
import secrets
import threading

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from argon2 import PasswordHasher
from markupsafe import Markup, escape
from argon2.exceptions import VerificationError
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from . import config, custos, db, pipeline

hasher = PasswordHasher()
modelos_html = Jinja2Templates(directory=str(config.RAIZ / "templates"))


def _paragrafos(texto: str) -> Markup:
    """Quebra o corpo em parágrafos e transforma as marcas [n] em links para as fontes."""
    blocos = [b.strip() for b in re.split(r"\n\s*\n|\n", texto or "") if b.strip()]
    html = "".join(f"<p>{escape(b)}</p>" for b in blocos)
    return Markup(re.sub(r"\[(\d{1,2})\]", r'<sup><a href="#ref-\1">[\1]</a></sup>', html))


modelos_html.env.filters["paragrafos"] = _paragrafos
agendador = BackgroundScheduler(timezone=config.FUSO)
LIVRES = ("/login", "/static/", "/manifest.webmanifest", "/sw.js", "/saude")

app = FastAPI(title="Briefing de Notícias", docs_url=None, redoc_url=None, openapi_url=None)


@app.middleware("http")
async def exigir_login(request: Request, call_next):
    if not request.url.path.startswith(LIVRES) and not request.session.get("usuario"):
        return RedirectResponse("/login", status_code=303)
    resposta = await call_next(request)
    resposta.headers["X-Content-Type-Options"] = "nosniff"
    resposta.headers["Referrer-Policy"] = "same-origin"
    return resposta


def _segredo_sessao() -> str:
    segredo = os.environ.get("PORTAL_SEGREDO_SESSAO")
    if segredo:
        return segredo
    db.iniciar()
    linha = db.consultar("SELECT valor FROM config WHERE chave = 'segredo_sessao'")
    if linha:
        return json.loads(linha[0]["valor"])
    novo = secrets.token_urlsafe(48)
    db.gravar_config("segredo_sessao", novo)
    return novo


# A sessão é registrada depois do middleware de login para envolvê-lo (ordem do Starlette).
app.add_middleware(SessionMiddleware, secret_key=_segredo_sessao(), session_cookie="briefing",
                   max_age=60 * 60 * 24 * 30, same_site="lax", https_only=os.environ.get("PORTAL_HTTPS") == "1")
app.mount("/static", StaticFiles(directory=str(config.RAIZ / "static")), name="static")


def pagina(request: Request, nome: str, **ctx) -> HTMLResponse:
    return modelos_html.TemplateResponse(request, nome, {"cfg": db.ler_config(), **ctx})


# Autenticação ------------------------------------------------------------------------------

def definir_senha(usuario: str, senha: str) -> None:
    db.iniciar()
    db.gravar_config("acesso", {"usuario": usuario, "hash": hasher.hash(senha)})


@app.get("/login", response_class=HTMLResponse)
def login_form(request: Request, erro: str | None = None):
    return pagina(request, "login.html", erro=erro)


@app.post("/login")
def login(request: Request, usuario: str = Form(...), senha: str = Form(...)):
    acesso = db.ler_config().get("acesso") or {}
    try:
        ok = usuario == acesso.get("usuario") and hasher.verify(acesso.get("hash", ""), senha)
    except (VerificationError, Exception):
        ok = False
    if not ok:
        return RedirectResponse("/login?erro=1", status_code=303)
    request.session["usuario"] = usuario
    return RedirectResponse("/", status_code=303)


@app.get("/sair")
def sair(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


@app.get("/saude")
def saude():
    return {"ok": True}


# Portal ------------------------------------------------------------------------------------

def _edicao(data: str) -> dict:
    noticias = [dict(n) for n in db.consultar("SELECT * FROM noticias WHERE data_edicao = ? ORDER BY id", (data,))]
    audios = {a["noticia_id"]: dict(a) for a in db.consultar(
        "SELECT * FROM audios WHERE data_edicao = ? ORDER BY id", (data,))}
    resumo = next((dict(a) for a in db.consultar(
        "SELECT * FROM audios WHERE data_edicao = ? AND tipo = 'resumo' ORDER BY id DESC LIMIT 1", (data,))), None)
    for n in noticias:
        n["audio"] = audios.get(n["id"])
    return {"data": data, "noticias": noticias, "resumo": resumo}


@app.get("/", response_class=HTMLResponse)
def inicio(request: Request):
    ultima = db.consultar("SELECT MAX(data_edicao) AS d FROM noticias")[0]["d"]
    return edicao(request, ultima) if ultima else pagina(request, "edicao.html", ed=None, datas=[])


@app.get("/edicao/{data}", response_class=HTMLResponse)
def edicao(request: Request, data: str):
    datas = [r["data_edicao"] for r in db.consultar(
        "SELECT DISTINCT data_edicao FROM noticias ORDER BY data_edicao DESC LIMIT 30")]
    return pagina(request, "edicao.html", ed=_edicao(data), datas=datas)


@app.get("/noticia/{nid}", response_class=HTMLResponse)
def noticia(request: Request, nid: int):
    linhas = db.consultar("SELECT * FROM noticias WHERE id = ?", (nid,))
    if not linhas:
        raise HTTPException(404)
    n = dict(linhas[0])
    n["referencias"] = json.loads(n["referencias"] or "[]")
    afirmacoes = [dict(a) for a in db.consultar(
        "SELECT * FROM afirmacoes WHERE candidato_id = ? ORDER BY ordem", (n["candidato_id"],))]
    cand = dict(db.consultar("SELECT * FROM candidatos WHERE id = ?", (n["candidato_id"],))[0])
    cand["origens"] = json.loads(cand["origens"] or "[]")
    audio = next((dict(a) for a in db.consultar("SELECT * FROM audios WHERE noticia_id = ?", (nid,))), None)
    return pagina(request, "noticia.html", n=n, afirmacoes=afirmacoes, cand=cand, audio=audio)


@app.get("/audio/{data}/{arquivo}")
def audio(data: str, arquivo: str):
    caminho = (config.PASTA_AUDIOS / data / arquivo).resolve()
    if config.PASTA_AUDIOS.resolve() not in caminho.parents or not caminho.is_file():
        raise HTTPException(404)
    return FileResponse(caminho, media_type="audio/mpeg")


# Painel ------------------------------------------------------------------------------------

@app.get("/painel", response_class=HTMLResponse)
def painel(request: Request, aviso: str | None = None):
    execucoes = [dict(e) for e in db.consultar(
        "SELECT e.*, (SELECT COALESCE(SUM(custo_usd),0) FROM custos c WHERE c.execucao_id = e.id) AS gasto "
        "FROM execucoes e ORDER BY id DESC LIMIT 15")]
    por_etapa = [dict(r) for r in db.consultar(
        "SELECT etapa, COUNT(*) AS chamadas, SUM(1 - sucesso) AS falhas, SUM(custo_usd) AS total FROM custos "
        "WHERE quando LIKE ? GROUP BY etapa ORDER BY total DESC", (custos.agora().strftime("%Y-%m") + "%",))]
    proxima = agendador.get_job("diaria")
    return pagina(request, "painel.html", execucoes=execucoes, por_etapa=por_etapa,
                  gasto_dia=custos.gasto("dia"), gasto_mes=custos.gasto("mes"),
                  em_andamento=pipeline.em_andamento(), aviso=aviso,
                  proxima=proxima.next_run_time if proxima else None)


@app.post("/painel/geral")
async def salvar_geral(request: Request):
    f = await request.form()
    cfg = db.ler_config()
    try:
        tetos = {"diario_usd": float(str(f["diario_usd"]).replace(",", ".")),
                 "mensal_usd": float(str(f["mensal_usd"]).replace(",", "."))}
        hora = str(f["hora"]).strip()
        dt.datetime.strptime(hora, "%H:%M")
    except (KeyError, ValueError):
        return RedirectResponse("/painel?aviso=Valores+inválidos", status_code=303)
    db.gravar_config("tetos", tetos)
    db.gravar_config("agenda", {"ativa": f.get("agenda_ativa") == "on", "hora": hora})
    modelos = {k: str(f.get(f"modelo_{k}") or v).strip() for k, v in cfg["modelos"].items()}
    db.gravar_config("modelos", modelos)
    agendar()
    return RedirectResponse("/painel?aviso=Configuração+salva", status_code=303)


@app.post("/painel/temas")
async def salvar_temas(request: Request):
    f = await request.form()
    temas = []
    for t in db.ler_config()["temas"]:
        k = t["id"]
        lista = lambda campo, sep: [x.strip().lstrip("@") for x in str(f.get(f"{k}_{campo}", "")).replace(",", "\n").split("\n") if x.strip()]
        temas.append({**t, "nome": str(f.get(f"{k}_nome", t["nome"])).strip() or t["nome"],
                      "descricao": str(f.get(f"{k}_descricao", t["descricao"])).strip(),
                      "ativo": f.get(f"{k}_ativo") == "on",
                      "candidatos": max(1, min(6, int(f.get(f"{k}_candidatos") or t["candidatos"]))),
                      "publicar": max(0, min(6, int(f.get(f"{k}_publicar") or t["publicar"]))),
                      "perfis": lista("perfis", ",")[:20], "feeds": lista("feeds", "\n")})
    db.gravar_config("temas", temas)
    return RedirectResponse("/painel?aviso=Temas+salvos", status_code=303)


@app.post("/painel/executar")
async def executar_agora(request: Request):
    f = await request.form()
    temas = [t for t in f.getlist("tema") if t] or None
    if pipeline.em_andamento():
        return RedirectResponse("/painel?aviso=Já+existe+uma+execução+em+andamento", status_code=303)
    threading.Thread(target=pipeline.executar, args=("manual", temas), daemon=True).start()
    return RedirectResponse("/painel?aviso=Execução+iniciada", status_code=303)


@app.get("/painel/execucao/{eid}", response_class=HTMLResponse)
def ver_execucao(request: Request, eid: int):
    ex = db.consultar("SELECT * FROM execucoes WHERE id = ?", (eid,))
    if not ex:
        raise HTTPException(404)
    candidatos = [dict(c) for c in db.consultar("SELECT * FROM candidatos WHERE execucao_id = ? ORDER BY tema, id", (eid,))]
    for c in candidatos:
        c["afirmacoes"] = [dict(a) for a in db.consultar(
            "SELECT * FROM afirmacoes WHERE candidato_id = ? ORDER BY ordem", (c["id"],))]
    gastos = [dict(r) for r in db.consultar(
        "SELECT etapa, tema, COUNT(*) AS chamadas, SUM(1 - sucesso) AS falhas, SUM(custo_usd) AS total "
        "FROM custos WHERE execucao_id = ? GROUP BY etapa, tema ORDER BY tema, etapa", (eid,))]
    return pagina(request, "execucao.html", ex=dict(ex[0]), candidatos=candidatos, gastos=gastos)


# PWA -------------------------------------------------------------------------------------------

@app.get("/manifest.webmanifest")
def manifesto():
    return Response(json.dumps({
        "name": "Briefing de Notícias", "short_name": "Briefing", "start_url": "/", "display": "standalone",
        "background_color": "#f6f4ef", "theme_color": "#1f3a5f", "lang": "pt-BR",
        "icons": [{"src": "/static/icone.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "any"}]},
        ensure_ascii=False), media_type="application/manifest+json")


@app.get("/sw.js")
def service_worker():
    return FileResponse(config.RAIZ / "static" / "sw.js", media_type="text/javascript",
                        headers={"Service-Worker-Allowed": "/"})


# Agendamento -------------------------------------------------------------------------------------

def agendar() -> None:
    agenda = db.ler_config()["agenda"]
    if agendador.get_job("diaria"):
        agendador.remove_job("diaria")
    if agenda.get("ativa"):
        h, m = (int(x) for x in agenda["hora"].split(":"))
        agendador.add_job(pipeline.executar, CronTrigger(hour=h, minute=m, timezone=config.FUSO),
                          id="diaria", kwargs={"gatilho": "agenda"}, misfire_grace_time=3600, coalesce=True)


@app.on_event("startup")
def ao_iniciar():
    db.iniciar()
    if os.environ.get("PORTAL_SEM_AGENDA") != "1":
        agendar()
        agendador.start()
