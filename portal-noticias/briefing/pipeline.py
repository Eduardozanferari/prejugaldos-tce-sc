"""Fluxo diário, por tema:

1. coleta no X (perfis curados) e nas fontes oficiais (RSS);
2. seleção de pautas e extração das afirmações centrais;
3. verificação de cada afirmação (OpenAI, com busca na web);
4. confirmação pelo Claude das afirmações que a OpenAI deu como confirmadas;
5. uma pauta só vira notícia com pelo menos N afirmações aprovadas pelos dois; as demais
   afirmações são cortadas e a pauta sem o mínimo é descartada, com o motivo registrado;
6. redação só com as afirmações aprovadas, e áudio da notícia;
7. no fim, áudio do resumo do dia.
O teto de gasto é conferido antes de cada chamada paga; ao atingi-lo, a execução para.
"""
import json
import re
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor

from . import coleta, config, custos, db, ia, prompts

_em_andamento = threading.Lock()
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro",
         "outubro", "novembro", "dezembro"]


class Execucao:
    def __init__(self, gatilho: str, temas: list[str] | None):
        self.inicio = custos.agora()
        self.data = self.inicio.strftime("%Y-%m-%d")
        self.eventos: list[str] = []
        self.id = db.inserir("execucoes", inicio=self.inicio.isoformat(timespec="seconds"), data_edicao=self.data,
                             gatilho=gatilho, status="em_andamento", versao_prompts=prompts.versao(),
                             temas=temas or "todos")

    def log(self, texto: str) -> None:
        linha = f"{custos.agora().strftime('%H:%M:%S')} {texto}"
        print(linha, flush=True)
        self.eventos.append(linha)
        db.atualizar("execucoes", self.id, mensagem="\n".join(self.eventos))

    def fim(self, status: str) -> None:
        db.atualizar("execucoes", self.id, status=status, fim=custos.agora().isoformat(timespec="seconds"),
                     mensagem="\n".join(self.eventos))


def _verificar_e_confirmar(texto: str, ordem: int, cand_id: int, tema_id: str, cfg: dict, ex: Execucao) -> dict:
    v = ia.verificar(texto, tema_id, cfg, ex.id)
    reg = {"candidato_id": cand_id, "ordem": ordem, "texto": texto, "status_verificador": v["status"],
           "url_verificador": v.get("url"), "trecho_verificador": v.get("trecho"),
           "justificativa_verificador": v.get("justificativa"), "urls_consultadas": v.get("urls_consultadas"),
           "verificado_em": custos.agora().isoformat(timespec="seconds")}
    aprovada = False
    if v["status"] == "confirmada" and v.get("url"):
        c = ia.confirmar(texto, v, tema_id, cfg, ex.id)
        aprovada = c.get("concorda") is True
        reg.update(modelo_confirmador=c.get("modelo"), confirmador_concorda=int(aprovada),
                   status_confirmador=c.get("status"), url_confirmador=c.get("url_conferida"),
                   trecho_confirmador=c.get("trecho"), justificativa_confirmador=c.get("justificativa"),
                   confirmado_em=custos.agora().isoformat(timespec="seconds"))
    reg["decisao"] = "aprovada" if aprovada else "cortada"
    reg["id"] = db.inserir("afirmacoes", **reg)
    return reg


def _tema(tema: dict, cfg: dict, ex: Execucao) -> list[int]:
    tid = tema["id"]
    agora = lambda: custos.agora().isoformat(timespec="seconds")
    try:
        posts = coleta.coletar_x(tema, cfg, ex.id)
    except custos.TetoAtingido:
        raise
    except Exception as e:
        posts = []
        ex.log(f"[{tid}] coleta no X falhou, seguindo só com fontes oficiais: {str(e)[:200]}")
    for p in posts:
        db.inserir("posts_origem", execucao_id=ex.id, tema=tid, link=p["link"], autor=p["autor"],
                   texto=p["texto"], assunto=p["assunto"], coletado_em=agora())
    oficiais, erros = coleta.coletar_oficial(tema, cfg)
    for e in erros:
        ex.log(f"[{tid}] feed com erro: {e}")
    for i in oficiais:
        db.inserir("itens_oficiais", execucao_id=ex.id, tema=tid, coletado_em=agora(), **i)
    ex.log(f"[{tid}] coleta: {len(posts)} posts do X, {len(oficiais)} itens oficiais")
    if not posts and not oficiais:
        return []

    pautas = ia.selecionar(tema, posts, oficiais, cfg, ex.id)
    ex.log(f"[{tid}] {len(pautas)} pautas selecionadas")
    minimo = int(cfg["limites"]["minimo_afirmacoes_aprovadas"])
    publicadas: list[int] = []
    for pauta in pautas:
        cand = db.inserir("candidatos", execucao_id=ex.id, tema=tid, titulo=pauta["titulo"], resumo=pauta["resumo"],
                          origens=pauta["origens"], status="em_verificacao")
        if len(publicadas) >= int(tema["publicar"]):
            db.atualizar("candidatos", cand, status="descartado", motivo="limite de notícias do tema já atingido")
            continue
        with ThreadPoolExecutor(max_workers=int(cfg["limites"]["paralelismo"])) as pool:
            futuros = [pool.submit(_verificar_e_confirmar, t, n, cand, tid, cfg, ex)
                       for n, t in enumerate(pauta["afirmacoes"], 1)]
            regs = [f.result() for f in futuros]
        aprovadas = [r for r in regs if r["decisao"] == "aprovada"]
        resumo = ", ".join(f"{r['status_verificador']}" + ("+ok" if r["decisao"] == "aprovada" else "") for r in regs)
        if len(aprovadas) < minimo:
            motivo = (f"{len(aprovadas)} de {len(regs)} afirmações aprovadas pelos dois verificadores "
                      f"(mínimo {minimo}); status: {resumo}")
            db.atualizar("candidatos", cand, status="descartado", motivo=motivo)
            ex.log(f"[{tid}] descartada: {pauta['titulo'][:80]} ({motivo})")
            continue
        texto = ia.redigir(tema, pauta, [{"texto": a["texto"], "url": a["url_verificador"],
                                          "trecho": a["trecho_verificador"]} for a in aprovadas], cfg, ex.id)
        for campo in ("titulo", "linha_fina", "roteiro"):  # marcas de fonte só no corpo
            texto[campo] = re.sub(r"\s*\[\d{1,2}\]", "", texto[campo]).strip()
        refs = [{"n": i, "afirmacao_id": a["id"], "texto": a["texto"], "url": a["url_verificador"],
                 "trecho": a["trecho_verificador"]} for i, a in enumerate(aprovadas, 1)]
        nid = db.inserir("noticias", candidato_id=cand, execucao_id=ex.id, tema=tid, data_edicao=ex.data,
                         titulo=texto["titulo"], linha_fina=texto["linha_fina"], corpo=texto["corpo"],
                         roteiro=texto["roteiro"], referencias=refs, publicado_em=agora())
        db.atualizar("candidatos", cand, status="publicado",
                     motivo=f"{len(aprovadas)} de {len(regs)} afirmações aprovadas; status: {resumo}")
        publicadas.append(nid)
        ex.log(f"[{tid}] publicada: {texto['titulo'][:90]}")
        _audio(nid, "noticia", f"{texto['titulo']}. {texto['roteiro']}", tid, cfg, ex)
    return publicadas


def _audio(noticia_id: int | None, tipo: str, texto: str, tema_id: str | None, cfg: dict, ex: Execucao) -> None:
    nome = f"{ex.id}_{tipo}_{noticia_id or 'dia'}.mp3"
    destino = config.PASTA_AUDIOS / ex.data / nome
    try:
        ia.sintetizar(texto, destino, cfg, ex.id, tema_id)
    except custos.TetoAtingido:
        raise
    except Exception as e:
        ex.log(f"áudio ({tipo}) falhou: {str(e)[:200]}")
        return
    db.inserir("audios", execucao_id=ex.id, noticia_id=noticia_id, tipo=tipo, data_edicao=ex.data,
               arquivo=f"{ex.data}/{nome}", caracteres=len(texto), criado_em=custos.agora().isoformat(timespec="seconds"))


def _resumo_do_dia(cfg: dict, ex: Execucao) -> None:
    nomes = {t["id"]: t["nome"] for t in cfg["temas"]}
    noticias = db.consultar("SELECT * FROM noticias WHERE data_edicao = ? ORDER BY id", (ex.data,))
    if not noticias:
        return
    d = ex.inicio
    partes = [f"Bom dia. Este é o Briefing de Notícias de {d.day} de {MESES[d.month - 1]}. "
              f"Hoje são {len(noticias)} notícias verificadas."]
    tema_atual = None
    for n in noticias:
        if n["tema"] != tema_atual:
            tema_atual = n["tema"]
            partes.append(f"Em {nomes.get(tema_atual, tema_atual)}.")
        partes.append(f"{n['titulo']}. {n['linha_fina']}")
    partes.append("Os detalhes e as fontes de cada notícia estão no portal. Até amanhã.")
    _audio(None, "resumo", " ".join(partes), None, cfg, ex)


def executar(gatilho: str = "manual", temas: list[str] | None = None) -> int | None:
    """Roda o fluxo completo. Devolve o id da execução, ou None se outra já estiver em andamento."""
    if not _em_andamento.acquire(blocking=False):
        return None
    try:
        db.iniciar()
        cfg = db.ler_config()
        ex = Execucao(gatilho, temas)
        ativos = [t for t in cfg["temas"] if t.get("ativo") and (not temas or t["id"] in temas)]
        ex.log(f"início: {len(ativos)} temas; tetos diário US$ {cfg['tetos']['diario_usd']} "
               f"e mensal US$ {cfg['tetos']['mensal_usd']}; gasto hoje US$ {custos.gasto('dia'):.2f}")
        status = "concluida"
        try:
            for tema in ativos:
                try:
                    _tema(tema, cfg, ex)
                except custos.TetoAtingido:
                    raise
                except Exception as e:
                    status = "concluida_com_erros"
                    ex.log(f"[{tema['id']}] erro: {type(e).__name__}: {str(e)[:300]}")
                    traceback.print_exc()
            _resumo_do_dia(cfg, ex)
        except custos.TetoAtingido as e:
            status = "interrompida_teto"
            ex.log(f"execução interrompida: {e}")
        gasto = db.consultar("SELECT COALESCE(SUM(custo_usd),0) AS t FROM custos WHERE execucao_id = ?", (ex.id,))[0]["t"]
        ex.log(f"fim: gasto desta execução US$ {gasto:.2f}")
        ex.fim(status)
        return ex.id
    finally:
        _em_andamento.release()


def em_andamento() -> bool:
    return _em_andamento.locked()


if __name__ == "__main__":
    import sys
    print(json.dumps({"execucao": executar("linha_de_comando", sys.argv[1:] or None)}))
